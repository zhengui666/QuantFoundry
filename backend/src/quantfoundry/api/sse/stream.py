"""Durable SSE replay and live tail; database rows are the only truth."""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from collections.abc import AsyncIterator, Callable
from datetime import UTC
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session


def _wire(
    event: Any,
    envelope: Callable[[dict[str, Any]], dict[str, Any]],
) -> str:
    occurred_at = event.occurred_at
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)
    value = envelope(
        {
            "schema_version": 1,
            "event_id": event.event_id,
            "sequence": str(event.sequence),
            "event_type": event.event_type,
            "occurred_at": occurred_at.astimezone(UTC)
            .isoformat()
            .replace("+00:00", "Z"),
            "object_type": event.object_type,
            "object_id": event.object_id,
            "object_version": event.object_version,
            "object_revision": event.object_revision,
            "request_id": event.request_id,
            "job_id": event.job_id,
            "agent_run_id": event.agent_run_id,
            "tool_call_id": event.tool_call_id,
            "payload": json.loads(event.payload),
        }
    )
    return (
        f"id: {event.sequence}\n"
        f"event: {event.event_type}\n"
        f"data: {json.dumps(value, separators=(',', ':'))}\n\n"
    )


def _resync_wire(
    envelope: Callable[[dict[str, Any]], dict[str, Any]],
    sequence: int,
    now: Callable[[], str],
    *,
    request_id: str | None = None,
) -> str:
    sequence = max(1, sequence)
    event_id = f"EVT-{uuid.uuid4()}"
    value = envelope(
        {
            "schema_version": 1,
            "event_id": event_id,
            "sequence": str(sequence),
            "event_type": "system.resync_required",
            "occurred_at": now(),
            "object_type": "event_stream",
            "object_id": event_id,
            "object_version": None,
            "object_revision": 1,
            "request_id": request_id or f"REQ-{uuid.uuid4()}",
            "job_id": None,
            "agent_run_id": None,
            "tool_call_id": None,
            "payload": {
                "state": "RESYNC_REQUIRED",
                "status": None,
                "resync_from_sequence": str(sequence),
            },
        }
    )
    return (
        f"id: {max(0, sequence - 1)}\n"
        "event: system.resync_required\n"
        f"data: {json.dumps(value, separators=(',', ':'))}\n\n"
    )


async def durable_event_stream(
    session_factory: Callable[[], Session],
    event_model: Any,
    last_event_id: int | None,
    envelope: Callable[[dict[str, Any]], dict[str, Any]],
    now: Callable[[], str],
    *,
    workspace_id: str,
    watermark_model: Any | None = None,
    poll_seconds: float = 0.25,
    heartbeat_seconds: float = 15.0,
    batch_size: int = 100,
) -> AsyncIterator[str]:
    cursor = last_event_id or 0
    heartbeat_at = time.monotonic() + heartbeat_seconds
    while True:

        def poll(*, cursor_value: int = cursor) -> tuple[list[Any], int | None]:
            session = session_factory()
            try:
                earliest = session.execute(
                    select(event_model)
                    .where(event_model.workspace_id == workspace_id)
                    .order_by(event_model.sequence.asc())
                    .limit(1)
                ).scalar_one_or_none()
                stream_state = (
                    session.get(watermark_model, workspace_id)
                    if watermark_model is not None
                    else None
                )
                watermark = (
                    stream_state.last_sequence
                    if stream_state is not None
                    else session.scalar(
                        select(func.max(event_model.sequence)).where(
                            event_model.workspace_id == workspace_id
                        )
                    )
                )
                expired_through = (
                    stream_state.expired_through_sequence
                    if stream_state is not None
                    else None
                )
                has_cursor = last_event_id is not None or cursor_value > 0
                if has_cursor:
                    if (
                        watermark_model is None
                        and earliest is not None
                        and cursor_value + 1 < earliest.sequence
                    ):
                        return [], int(earliest.sequence)
                    if watermark is None and cursor_value > 0:
                        return [], 1
                    if watermark is not None and cursor_value > watermark:
                        return [], int(watermark) + 1
                    if (
                        expired_through is not None
                        and expired_through > 0
                        and cursor_value < expired_through
                    ):
                        resume_sequence = int(expired_through) + 1
                        if earliest is not None and earliest.sequence > resume_sequence:
                            resume_sequence = earliest.sequence
                        return [], resume_sequence
                events = list(
                    session.execute(
                        select(event_model)
                        .where(
                            event_model.sequence > cursor_value,
                            event_model.workspace_id == workspace_id,
                        )
                        .order_by(event_model.sequence.asc())
                        .limit(batch_size)
                    )
                    .scalars()
                    .all()
                )
                if watermark_model is not None and has_cursor:
                    current_state = stream_state
                    if stream_state is not None:
                        session.expire(stream_state)
                        current_state = session.get(watermark_model, workspace_id)
                    if (
                        current_state is not None
                        and cursor_value < current_state.expired_through_sequence
                    ):
                        return [], int(current_state.expired_through_sequence) + 1
                return events, None
            finally:
                session.close()

        events, resync_sequence = await asyncio.to_thread(poll)
        if resync_sequence is not None:
            yield _resync_wire(envelope, resync_sequence, now)
            return
        if events:
            for event in events:
                try:
                    wire = _wire(event, envelope)
                except (json.JSONDecodeError, TypeError, ValueError):
                    yield _resync_wire(
                        envelope,
                        event.sequence,
                        now,
                        request_id=event.request_id,
                    )
                    return
                cursor = event.sequence
                yield wire
                await asyncio.sleep(0)
            heartbeat_at = time.monotonic() + heartbeat_seconds
            continue
        if os.getenv("QF_SSE_TEST_CLOSE") == "1":
            yield ": heartbeat\n\n"
            return
        current = time.monotonic()
        if current >= heartbeat_at:
            yield ": heartbeat\n\n"
            heartbeat_at = current + heartbeat_seconds
        await asyncio.sleep(poll_seconds)
