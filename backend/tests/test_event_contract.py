"""P0 R2 16-case closed SSE allowlist and recovery matrix."""

from __future__ import annotations

import asyncio
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from app.event_contract import (
    EVENT_TYPES,
    safe_resync_payload,
    validate_event_payload,
    validate_event_type,
    validate_sse_envelope,
)
from app.generated_api_models import EventType
from app.main import Event, SessionLocal, emit
from app.sse import durable_event_stream

LEGACY_WORKSPACE_ID = "00000000-0000-4000-8000-000000000777"


def _canonical_locator(event_type: str) -> tuple[str, str, int | None]:
    prefix_by_type = {
        "job": "JOB",
        "research": "RSCH",
        "conclusion": "CONC",
        "experiment": "EXP",
        "factor": "FAC",
        "strategy_version": "STRAT",
        "validation": "VAL",
        "approval": "APR",
        "paper": "PAPER",
        "paper_run": "PRUN",
        "review": "REV",
        "capability": "CAP",
        "snapshot": "DS",
        "agent_run": "ARUN",
        "tool_call": "TCALL",
        "memo": "MEMO",
        "notification": "NOTIF",
        "event_stream": "EVT",
    }
    if event_type == "job.updated":
        object_type = "job"
    elif event_type.startswith("research.conclusion"):
        object_type = "conclusion"
    elif event_type.startswith("research."):
        object_type = "research"
    elif event_type.startswith("experiment."):
        object_type = "experiment"
    elif event_type.startswith("factor."):
        object_type = "factor"
    elif event_type.startswith("strategy."):
        object_type = "strategy_version"
    elif event_type.startswith("validation."):
        object_type = "validation"
    elif event_type.startswith("approval."):
        object_type = "approval"
    elif event_type == "paper.run.updated":
        object_type = "paper_run"
    elif event_type.startswith("paper."):
        object_type = "paper"
    elif event_type.startswith("review."):
        object_type = "review"
    elif event_type == "data.provider.updated":
        return "provider_connection", str(uuid.uuid4()), None
    elif event_type == "data.capability.updated":
        object_type = "capability"
    elif event_type == "data.quality.updated":
        object_type = "snapshot"
    elif event_type == "agent.run.updated":
        object_type = "agent_run"
    elif event_type == "tool.call.updated":
        object_type = "tool_call"
    elif event_type.startswith("memo."):
        object_type = "memo"
    elif event_type == "setup.completed":
        return "settings", "SETTINGS-DEFAULT", None
    elif event_type == "notification.created":
        object_type = "notification"
    elif event_type == "notification.updated":
        return "agent_config", "RESEARCH_DIRECTOR", None
    else:
        object_type = "event_stream"
    return (
        object_type,
        f"{prefix_by_type[object_type]}-{uuid.uuid4()}",
        1 if object_type == "strategy_version" else None,
    )


def _envelope(
    event_type: str = "job.updated",
    payload: dict[str, Any] | None = None,
    *,
    sequence: int = 1,
) -> dict[str, Any]:
    job_id = f"JOB-{uuid.uuid4()}"
    object_type, object_id, object_version = _canonical_locator(event_type)
    return {
        "schema_version": 1,
        "event_id": f"EVT-{uuid.uuid4()}",
        "sequence": sequence,
        "event_type": event_type,
        "occurred_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "object_type": object_type,
        "object_id": object_id,
        "object_version": object_version,
        "object_revision": 1,
        "request_id": f"REQ-{uuid.uuid4()}",
        "job_id": job_id,
        "agent_run_id": None,
        "tool_call_id": None,
        "payload": payload if payload is not None else {},
    }


def _publish(event_type: str, payload: dict[str, Any]) -> Event:
    suffix = uuid.uuid4().hex
    object_type, object_id, object_version = _canonical_locator(event_type)
    session = SessionLocal()
    try:
        session.info.update(
            {
                "actor_id": "test-owner",
                "workspace_id": "test-workspace",
                "request_id": f"REQ-{suffix}",
            }
        )
        emit(
            session,
            object_type,
            object_id,
            1,
            event_type,
            payload=payload,
            object_version=object_version,
        )
        session.commit()
        return session.execute(
            select(Event).where(Event.request_id == f"REQ-{suffix}")
        ).scalar_one()
    finally:
        session.close()


class LegacyBase(DeclarativeBase):
    pass


class LegacyEvent(LegacyBase):
    __tablename__ = "legacy_sse_events"
    sequence = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String, nullable=False)
    workspace_id = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    object_type = Column(String, nullable=False)
    object_id = Column(String, nullable=False)
    object_version = Column(Integer)
    object_revision = Column(Integer)
    revision = Column(Integer)
    payload = Column(Text, nullable=False)
    request_id = Column(String)
    job_id = Column(String)
    agent_run_id = Column(String)
    tool_call_id = Column(String)
    occurred_at = Column(DateTime(timezone=True), nullable=False)


def _legacy_event(
    sequence: int, event_type: str, payload: dict[str, Any]
) -> LegacyEvent:
    uuid_suffix = f"00000000-0000-4000-8000-{sequence:012x}"
    object_type = "job" if event_type == "job.updated" else "experiment"
    object_prefix = "JOB" if object_type == "job" else "EXP"
    return LegacyEvent(
        sequence=sequence,
        event_id=f"EVT-{uuid_suffix}",
        workspace_id=LEGACY_WORKSPACE_ID,
        event_type=event_type,
        object_type=object_type,
        object_id=f"{object_prefix}-{uuid_suffix}",
        object_version=None,
        object_revision=1,
        revision=1,
        payload=json.dumps(payload),
        request_id=f"REQ-legacy-{sequence}",
        occurred_at=datetime.now(UTC),
    )


async def _replay_legacy(rows: list[LegacyEvent], cursor: int, count: int) -> list[str]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    LegacyBase.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    session = sessions()
    session.add_all(rows)
    session.commit()
    session.close()

    def current_time() -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    stream = durable_event_stream(
        sessions,
        LegacyEvent,
        cursor,
        validate_sse_envelope,
        current_time,
        workspace_id=LEGACY_WORKSPACE_ID,
        poll_seconds=0.001,
    )
    try:
        return [await anext(stream) for _ in range(count)]
    finally:
        await stream.aclose()
        engine.dispose()


def test_sse_case_01_event_type_has_exact_31_generated_members() -> None:
    generated = tuple(EventType.model_json_schema(mode="validation")["enum"])
    assert generated == EVENT_TYPES
    assert len(generated) == len(set(generated)) == 31
    for value in generated:
        assert validate_event_type(value) == value


def test_sse_case_02_publisher_and_database_accept_exact_allowlist_only() -> None:
    suffix = uuid.uuid4().hex
    session = SessionLocal()
    session.info.update(
        {
            "actor_id": "test-owner",
            "workspace_id": "test-workspace",
            "request_id": f"REQ-{suffix}",
        }
    )
    for index, event_type in enumerate(EVENT_TYPES, start=1):
        payload = (
            safe_resync_payload(index) if event_type == "system.resync_required" else {}
        )
        object_type, object_id, object_version = _canonical_locator(event_type)
        emit(
            session,
            object_type,
            object_id,
            1,
            event_type,
            payload=payload,
            object_version=object_version,
        )
    session.commit()
    persisted = (
        session.execute(
            select(Event.event_type)
            .where(
                Event.workspace_id == "test-workspace",
                Event.request_id == f"REQ-{suffix}",
            )
            .order_by(Event.sequence)
        )
        .scalars()
        .all()
    )
    assert tuple(persisted) == EVENT_TYPES
    session.add(
        Event(
            sequence=(
                session.execute(
                    select(Event.sequence)
                    .where(Event.workspace_id == "test-workspace")
                    .order_by(Event.sequence.desc())
                    .limit(1)
                ).scalar_one()
                + 1
            ),
            event_id=f"EVT-{uuid.uuid4()}",
            workspace_id="test-workspace",
            event_type="future.invalid",
            object_type="test",
            object_id=f"EVT-{uuid.uuid4()}",
            payload="{}",
            request_id=f"REQ-{suffix}",
            occurred_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.close()


def test_sse_case_03_case_drift_is_rejected() -> None:
    for value in ("Experiment.Updated", "EXPERIMENT.UPDATED", "experiment.Updated"):
        with pytest.raises(ValidationError):
            validate_event_type(value)


def test_sse_case_04_unknown_publisher_member_becomes_no_leak_resync() -> None:
    event = _publish("experiment.future", {"credential": "must-not-leak"})
    assert event.event_type == "system.resync_required"
    assert json.loads(event.payload) == {
        "state": "RESYNC_REQUIRED",
        "status": None,
    }
    assert "credential" not in event.payload


def test_sse_case_05_unknown_schema_version_is_rejected() -> None:
    value = _envelope()
    value["schema_version"] = 2
    with pytest.raises(ValidationError):
        validate_sse_envelope(value)


def test_sse_case_06_envelope_is_closed_and_all_required_fields_are_enforced() -> None:
    valid = _envelope()
    required = {
        "schema_version",
        "event_id",
        "sequence",
        "event_type",
        "occurred_at",
        "object_type",
        "object_id",
        "object_version",
        "object_revision",
        "request_id",
        "job_id",
        "agent_run_id",
        "tool_call_id",
        "payload",
    }
    assert validate_sse_envelope(valid) == valid
    for field in required:
        with pytest.raises(ValidationError):
            validate_sse_envelope(
                {key: value for key, value in valid.items() if key != field}
            )
    with pytest.raises(ValidationError):
        validate_sse_envelope(valid | {"unknown": True})


def test_sse_case_07_payload_is_closed_and_invalid_writes_fail() -> None:
    with pytest.raises(ValidationError):
        validate_event_payload({"status": "RUNNING", "unknown": "truth"})
    session = SessionLocal()
    before = session.query(Event).count()
    with pytest.raises(ValidationError):
        emit(
            session,
            "job",
            f"JOB-{uuid.uuid4()}",
            1,
            "job.updated",
            payload={"result_ref": {"secret": True}},
        )
    session.rollback()
    assert session.query(Event).count() == before
    session.close()


def test_sse_case_08_waiting_on_job_shape_is_accepted() -> None:
    payload = {"waiting_on": {"type": "JOB", "job_id": f"JOB-{uuid.uuid4()}"}}
    assert validate_event_payload(payload) == payload


def test_sse_case_09_waiting_on_required_const_and_scalar_are_enforced() -> None:
    job_id = f"JOB-{uuid.uuid4()}"
    invalid = [
        {"type": "JOB"},
        {"job_id": job_id},
        {"type": "TOOL", "job_id": job_id},
        {"type": "JOB", "job_id": 7},
    ]
    for waiting_on in invalid:
        with pytest.raises(ValidationError):
            validate_event_payload({"waiting_on": waiting_on})


def test_sse_case_10_waiting_on_is_closed() -> None:
    with pytest.raises(ValidationError):
        validate_event_payload(
            {
                "waiting_on": {
                    "type": "JOB",
                    "job_id": f"JOB-{uuid.uuid4()}",
                    "ref": "leak",
                }
            }
        )


def test_sse_case_11_holdout_gate_metadata_is_accepted() -> None:
    value = _envelope(
        "validation.holdout.updated",
        {"state": "EXPOSED", "status": "COMPLETED", "reason_code": None},
    )
    assert validate_sse_envelope(value) == value


def test_sse_case_12_holdout_result_and_secret_fields_never_validate() -> None:
    for key in (
        "result",
        "metric",
        "chart_point",
        "sentinel",
        "credential",
        "raw_tool_input",
        "raw_model_output",
    ):
        with pytest.raises(ValidationError):
            validate_sse_envelope(
                _envelope("validation.holdout.updated", {key: "protected"})
            )


def test_sse_case_13_replay_is_strictly_ordered_after_cursor() -> None:
    replay = asyncio.run(
        _replay_legacy(
            [
                _legacy_event(3, "job.updated", {"status": "COMPLETED"}),
                _legacy_event(1, "job.updated", {"status": "QUEUED"}),
                _legacy_event(2, "job.updated", {"status": "RUNNING"}),
            ],
            cursor=1,
            count=2,
        )
    )
    assert "id: 2\n" in replay[0] and "id: 3\n" in replay[1]
    assert "EVT-00000000-0000-4000-8000-000000000001" not in "".join(replay)


def test_sse_case_14_experiment_created_is_exact_notification_only() -> None:
    research_id = f"RSCH-{uuid.uuid4()}"
    experiment_id = f"EXP-{uuid.uuid4()}"
    event = _publish(
        "experiment.created",
        {
            "status": "QUEUED",
            "research_id": research_id,
            "object_type": "experiment",
            "object_id": experiment_id,
            "object_version": None,
            "object_revision": 1,
        },
    )
    assert event.event_type == "experiment.created"
    assert set(json.loads(event.payload)) == {
        "status",
        "research_id",
        "object_type",
        "object_id",
        "object_version",
        "object_revision",
    }


def test_sse_case_15_experiment_updated_is_exact_notification_only() -> None:
    event = _publish(
        "experiment.updated",
        {"status": "COMPLETED", "research_id": f"RSCH-{uuid.uuid4()}"},
    )
    assert event.event_type == "experiment.updated"
    assert "metrics" not in event.payload and "provenance" not in event.payload


def test_sse_case_16_unknown_replay_enters_same_no_leak_resync_recovery() -> None:
    replay = asyncio.run(
        _replay_legacy(
            [
                _legacy_event(
                    8,
                    "future.event",
                    {"credential": "secret", "holdout_metric": 99},
                )
            ],
            cursor=7,
            count=1,
        )
    )[0]
    assert "event: system.resync_required" in replay
    assert '"resync_from_sequence":8' in replay
    assert "future.event" not in replay
    assert "credential" not in replay and "holdout_metric" not in replay
