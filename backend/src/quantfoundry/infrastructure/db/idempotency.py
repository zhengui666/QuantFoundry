"""Atomic idempotency Unit of Work.

Domain state, audit rows, domain events and the replayable response are committed
exactly once.  Operation callbacks may flush but must never commit.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from fastapi.responses import JSONResponse
from sqlalchemy import delete, func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

LEASE_SECONDS = 60
RETENTION_DAYS = 7


def _utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _response_headers(path: str, payload: dict[str, Any]) -> dict[str, str]:
    resource_ref = payload.get("resource_ref")
    if (
        isinstance(resource_ref, dict)
        and resource_ref.get("type") == "experiment"
        and isinstance(resource_ref.get("id"), str)
        and isinstance(payload.get("source_experiment_id"), str)
    ):
        return {"Location": f"/api/v1/experiments/{resource_ref['id']}"}
    identifier = None
    revision = payload.get("revision")
    for key in (
        "settings_id",
        "research_id",
        "factor_id",
        "strategy_id",
        "approval_id",
    ):
        if payload.get(key):
            identifier = payload[key]
            break
    if identifier is None and isinstance(payload.get("approval"), dict):
        identifier = payload["approval"].get("approval_id")
        revision = payload["approval"].get("revision")
    if identifier is not None and revision is not None:
        return {"ETag": f'W/"{identifier}:{revision}"'}
    return {}


def _json_response(status: int, path: str, payload: dict[str, Any]) -> JSONResponse:
    if status >= 400:
        return JSONResponse(
            payload,
            status_code=status,
            headers=_response_headers(path, payload),
            media_type="application/problem+json",
        )
    return JSONResponse(
        payload, status_code=status, headers=_response_headers(path, payload)
    )


def _takeover_is_safe(record: Any) -> bool:
    """Prove that a stale PROCESSING record has no committed side effect evidence."""

    return bool(
        record.state == "PROCESSING"
        and record.completed_at is None
        and record.resource_ref is None
        and record.status == 202
        and record.response in (None, "{}", {})
    )


def _database_now(session: Session) -> datetime:
    value = session.scalar(select(func.current_timestamp()))
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if value is None:
        raise RuntimeError("database clock returned no timestamp")
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError) as error:
        raise RuntimeError("database clock returned an invalid timestamp") from error
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def execute(
    session: Session,
    record_type: Any,
    key: str | None,
    request: dict[str, Any],
    path: str,
    operation: Callable[[], tuple[int, dict[str, Any]]],
    fail: Callable[[int, str, str | None], Exception],
    *,
    actor_id: str,
    workspace_id: str,
    method: str,
) -> JSONResponse:
    session.info["actor_id"] = actor_id
    session.info["workspace_id"] = workspace_id
    if key is None:
        raise fail(428, "PRECONDITION_REQUIRED", "Idempotency-Key required")
    if not 20 <= len(key) <= 128:
        raise fail(422, "INVALID_REQUEST", "Idempotency-Key length must be 20..128")
    request_hash = hashlib.sha256(
        json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    method = method.upper()
    lease_owner_id = uuid.uuid4().hex
    try:
        now = _database_now(session)

        def resolve_existing(existing: Any, current_time: datetime) -> Any:
            if existing.request_hash != request_hash:
                session.rollback()
                raise fail(409, "IDEMPOTENCY_CONFLICT", None)
            if existing.state == "SUCCEEDED":
                payload = json.loads(existing.response)
                if not isinstance(payload, dict):
                    session.rollback()
                    raise RuntimeError("stored idempotency result is invalid")
                status = existing.status
                session.rollback()
                return _json_response(status, path, payload)
            if (
                existing.state == "PROCESSING"
                and (_utc(existing.lease_expires_at) or current_time) > current_time
            ):
                session.rollback()
                raise fail(409, "IDEMPOTENCY_IN_PROGRESS", None)
            if not _takeover_is_safe(existing):
                session.rollback()
                raise fail(409, "IDEMPOTENCY_IN_PROGRESS", None)
            existing.state = "PROCESSING"
            existing.lease_owner_id = lease_owner_id
            existing.lease_expires_at = current_time + timedelta(seconds=LEASE_SECONDS)
            return None

        session.execute(
            delete(record_type).where(
                record_type.workspace_id == workspace_id,
                record_type.expires_at <= now,
            )
        )
        record = session.execute(
            select(record_type)
            .where(
                record_type.actor_id == actor_id,
                record_type.workspace_id == workspace_id,
                record_type.method == method,
                record_type.path == path,
                record_type.key == key,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if record is not None:
            replay = resolve_existing(record, now)
            if replay is not None:
                return replay
        else:
            record = record_type(
                actor_id=actor_id,
                workspace_id=workspace_id,
                key=key,
                method=method,
                path=path,
                request_hash=request_hash,
                status=202,
                response="{}",
                state="PROCESSING",
                lease_owner_id=lease_owner_id,
                lease_expires_at=now + timedelta(seconds=LEASE_SECONDS),
                created_at=now,
                expires_at=now + timedelta(days=RETENTION_DAYS),
            )
            session.add(record)
            try:
                session.flush()
            except IntegrityError as error:
                session.rollback()
                now = _database_now(session)
                record = session.execute(
                    select(record_type)
                    .where(
                        record_type.actor_id == actor_id,
                        record_type.workspace_id == workspace_id,
                        record_type.method == method,
                        record_type.path == path,
                        record_type.key == key,
                    )
                    .with_for_update()
                ).scalar_one_or_none()
                if record is None:
                    raise error
                replay = resolve_existing(record, now)
                if replay is not None:
                    return replay

        status, payload = operation()
        completed_at = _database_now(session)
        response = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        resource_ref = payload.get("resource_ref")
        terminal_write = cast(
            CursorResult[Any],
            session.execute(
                update(record_type)
                .where(
                    record_type.actor_id == actor_id,
                    record_type.workspace_id == workspace_id,
                    record_type.method == method,
                    record_type.path == path,
                    record_type.key == key,
                    record_type.state == "PROCESSING",
                    record_type.lease_owner_id == lease_owner_id,
                )
                .values(
                    status=status,
                    response=response,
                    resource_ref=(
                        resource_ref if isinstance(resource_ref, dict) else None
                    ),
                    state="SUCCEEDED",
                    lease_owner_id=None,
                    lease_expires_at=None,
                    completed_at=completed_at,
                    expires_at=completed_at + timedelta(days=RETENTION_DAYS),
                )
                .execution_options(synchronize_session=False)
            ),
        )
        if terminal_write.rowcount != 1:
            raise fail(409, "IDEMPOTENCY_IN_PROGRESS", None)
        session.commit()
        return _json_response(status, path, payload)
    except Exception:
        session.rollback()
        raise
