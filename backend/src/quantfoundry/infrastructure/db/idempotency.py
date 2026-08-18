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
from sqlalchemy import delete, event, func, select, text, update
from sqlalchemy.engine import Connection, CursorResult, Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

LEASE_SECONDS = 60
RETENTION_DAYS = 7


@event.listens_for(Session, "before_commit")
def _reject_operation_commit(session: Session) -> None:
    if session.info.get("qf_idempotency_operation_active"):
        raise RuntimeError("idempotency operation must not commit its session")


@event.listens_for(Engine, "commit")
def _reject_operation_connection_commit(connection: Connection) -> None:
    if connection.info.get("qf_idempotency_operation_active"):
        raise RuntimeError("idempotency operation must not commit its connection")


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


def _request_hashes(request: dict[str, Any]) -> list[str]:
    candidates = request.get("__qf_fingerprint_candidates__")
    if not isinstance(candidates, list) or not candidates or not isinstance(
        request.get("credential_fingerprint"), str
    ):
        return [
            hashlib.sha256(
                json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
        ]
    base = {key: value for key, value in request.items() if key != "__qf_fingerprint_candidates__"}
    hashes: list[str] = []
    for candidate in candidates:
        if not isinstance(candidate, str):
            continue
        value = dict(base)
        value["credential_fingerprint"] = candidate
        digest = hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if digest not in hashes:
            hashes.append(digest)
    return hashes


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


def _require_isolated_session(session: Session) -> None:
    if session.info.get("qf_idempotency_operation_active"):
        raise RuntimeError("nested idempotency operations are not supported")
    if (
        session.in_transaction()
        or session.in_nested_transaction()
        or session.new
        or session.dirty
        or session.deleted
    ):
        raise RuntimeError(
            "idempotency requires a fresh Session; it must not commit caller state"
        )


def _execute(
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
    if key is None:
        raise fail(428, "PRECONDITION_REQUIRED", "Idempotency-Key required")
    if not 20 <= len(key) <= 128:
        raise fail(422, "INVALID_REQUEST", "Idempotency-Key length must be 20..128")
    request_hashes = _request_hashes(request)
    if not request_hashes:
        raise fail(422, "INVALID_REQUEST", "request fingerprint is invalid")
    request_hash = request_hashes[0]
    method = method.upper()
    lease_owner_id = uuid.uuid4().hex
    try:
        dialect = session.get_bind().dialect.name
        if dialect == "sqlite":
            # ponytail: one SQLite writer lock is enough; split-key locking needs
            # a database that supports row/advisory locks.
            session.execute(text("BEGIN IMMEDIATE"))
        now = _database_now(session)
        if dialect == "postgresql":
            coordination_key = "\x1f".join((actor_id, workspace_id, method, path, key))
            if not session.scalar(
                text("SELECT pg_try_advisory_xact_lock(hashtext(:key))"),
                {"key": coordination_key},
            ):
                raise fail(409, "IDEMPOTENCY_IN_PROGRESS", None)

        def resolve_existing(existing: Any, current_time: datetime) -> Any:
            if existing.request_hash not in request_hashes:
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

        session.info["qf_idempotency_operation_active"] = True
        root_transaction = session.get_transaction()
        operation_connection = session.connection()
        operation_connection.info["qf_idempotency_operation_active"] = True
        original_rollback = session.rollback
        original_close = session.close

        def reject_transaction_reset(*_: Any, **__: Any) -> None:
            raise RuntimeError("idempotency operation must not reset its session")

        session.rollback = reject_transaction_reset  # type: ignore[method-assign]
        session.close = reject_transaction_reset  # type: ignore[method-assign]
        try:
            status, payload = operation()
        finally:
            session.rollback = original_rollback  # type: ignore[method-assign]
            session.close = original_close  # type: ignore[method-assign]
            session.info.pop("qf_idempotency_operation_active", None)
            operation_connection.info.pop("qf_idempotency_operation_active", None)
        if session.get_transaction() is not root_transaction:
            raise RuntimeError("idempotency operation replaced its root transaction")
        completed_at = _database_now(session)
        response = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
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
    _require_isolated_session(session)
    sentinel = object()
    previous = {
        name: session.info.get(name, sentinel) for name in ("actor_id", "workspace_id")
    }
    session.info.update(actor_id=actor_id, workspace_id=workspace_id)
    try:
        return _execute(
            session,
            record_type,
            key,
            request,
            path,
            operation,
            fail,
            actor_id=actor_id,
            workspace_id=workspace_id,
            method=method,
        )
    finally:
        for name, value in previous.items():
            if value is sentinel:
                session.info.pop(name, None)
            else:
                session.info[name] = value
