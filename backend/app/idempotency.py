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
from sqlalchemy import delete, select, update
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
    now = datetime.now(UTC)
    lease_owner_id = uuid.uuid4().hex
    try:
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
            if record.request_hash != request_hash:
                session.rollback()
                raise fail(409, "IDEMPOTENCY_CONFLICT", None)
            if record.state == "SUCCEEDED":
                payload = json.loads(record.response)
                status = record.status
                session.rollback()
                return _json_response(status, path, payload)
            if (
                record.state == "PROCESSING"
                and (_utc(record.lease_expires_at) or now) > now
            ):
                session.rollback()
                raise fail(409, "IDEMPOTENCY_IN_PROGRESS", None)
            if not _takeover_is_safe(record):
                session.rollback()
                raise fail(409, "IDEMPOTENCY_IN_PROGRESS", None)
            record.state = "PROCESSING"
            record.lease_owner_id = lease_owner_id
            record.lease_expires_at = now + timedelta(seconds=LEASE_SECONDS)
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
                raise fail(409, "IDEMPOTENCY_IN_PROGRESS", None) from error

        status, payload = operation()
        completed_at = datetime.now(UTC)
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
                    record_type.lease_expires_at > completed_at,
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
        session.expire(record)
        session.commit()
        persisted = session.execute(
            select(record_type).where(
                record_type.actor_id == actor_id,
                record_type.workspace_id == workspace_id,
                record_type.method == method,
                record_type.path == path,
                record_type.key == key,
            )
        ).scalar_one_or_none()
        if persisted is None or persisted.state != "SUCCEEDED":
            raise RuntimeError("committed idempotency result is unavailable")
        persisted_payload = json.loads(persisted.response)
        if not isinstance(persisted_payload, dict):
            raise RuntimeError("committed idempotency result is invalid")
        return _json_response(persisted.status, path, persisted_payload)
    except Exception:
        session.rollback()
        raise
