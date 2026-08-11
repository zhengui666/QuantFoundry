"""Fail-closed, Core-only Paper scheduler baseline readiness gate.

Revision ID: 0017_paper_scheduler_state_initialization
Revises: 0016_section14_schema
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import MetaData, Table, select
from sqlalchemy.engine import Connection

from alembic import op

revision = "0017_paper_scheduler_state_init"
down_revision = "0016_section14_schema"
branch_labels = None
depends_on = None

_STATUS_MAP = {
    "ACTIVE": "ACTIVE",
    "PAUSED": "PAUSED",
    "STOPPED": "DISABLED",
    "PENDING": "DISABLED",
    "FAILED": "DISABLED",
    "DISABLED": "DISABLED",
}
_REQUIRED = {
        "paper_deployments": {"id", "workspace_id", "paper_id", "status", "revision"},
    "paper_scheduler_states": {
        "id", "workspace_id", "paper_id", "scheduler_status",
        "suppressed_since_utc", "resume_watermark_utc", "revision",
    },
    "audit_events": {
        "id", "event_id", "actor_type", "actor_id", "workspace_id", "sequence",
        "action_type", "object_type", "object_id", "object_version", "object_revision",
        "result", "summary", "detail_artifact_id", "prev_event_hash", "event_hash",
        "occurred_at", "input_hash", "before_hash", "after_hash",
    },
}
_EVIDENCE_KEY = "paper_scheduler_state_evidence.v1"
_EVIDENCE_FIELDS = {
    "state_transition_id",
    "workspace_id",
    "paper_id",
    "from_state",
    "to_state",
    "effective_at_utc",
    "suppressed_since_utc",
    "resume_watermark_utc",
    "initialization_utc",
    "revision",
    "reason_code",
    "actor",
    "system",
    "commit_build_locator",
}


class SchedulerInitializationError(RuntimeError):
    """A legacy baseline cannot be proven, so readiness remains blocked."""


def _tables(bind: Connection) -> tuple[Table, Table, Table]:
    metadata = MetaData()
    metadata.reflect(bind=bind, only=list(_REQUIRED))
    missing = sorted(set(_REQUIRED) - set(metadata.tables))
    if missing:
        raise SchedulerInitializationError(f"missing initialization tables: {missing}")
    for name, required in _REQUIRED.items():
        actual = set(metadata.tables[name].c.keys())
        if required - actual:
            raise SchedulerInitializationError(
                f"unclassifiable {name} schema: missing={sorted(required - actual)}"
            )
    return (
        metadata.tables["paper_deployments"],
        metadata.tables["paper_scheduler_states"],
        metadata.tables["audit_events"],
    )


def _utc_timestamp(bind: Connection, value: Any, field: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SchedulerInitializationError(
                f"ambiguous scheduler initialization: invalid {field}"
            ) from exc
    else:
        raise SchedulerInitializationError(
            f"ambiguous scheduler initialization: invalid {field}"
        )
    if parsed.tzinfo is None:
        if bind.dialect.name != "sqlite":
            raise SchedulerInitializationError(
                f"ambiguous scheduler initialization: non-UTC {field}"
            )
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _closed_object(value: Any, fields: set[str], field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise SchedulerInitializationError(
            f"ambiguous scheduler initialization: invalid {field}"
        )
    if any(item in (None, "") for item in value.values()):
        raise SchedulerInitializationError(
            f"ambiguous scheduler initialization: invalid {field}"
        )
    return value


def _validate_evidence(
    bind: Connection,
    audit_events: Table,
    deployment: Mapping[str, Any],
    baseline: Mapping[str, Any],
    target: str,
) -> None:
    audits = bind.execute(
        select(audit_events).where(
            audit_events.c.workspace_id == deployment["workspace_id"],
            audit_events.c.object_type == "paper",
            audit_events.c.object_id == deployment["paper_id"],
            audit_events.c.action_type
            == "SCHEDULER_STATE_INITIALIZED_NO_HISTORY",
            audit_events.c.detail_artifact_id.is_(None),
        )
    ).mappings().all()
    if len(audits) != 1:
        raise SchedulerInitializationError(
            "missing or ambiguous scheduler initialization evidence"
        )
    summary = audits[0]["summary"]
    if not isinstance(summary, Mapping) or set(summary) != {_EVIDENCE_KEY}:
        raise SchedulerInitializationError(
            "ambiguous scheduler initialization evidence"
        )
    evidence = summary[_EVIDENCE_KEY]
    if not isinstance(evidence, Mapping) or set(evidence) != _EVIDENCE_FIELDS:
        raise SchedulerInitializationError(
            "ambiguous scheduler initialization evidence"
        )

    watermark = _utc_timestamp(
        bind, baseline["resume_watermark_utc"], "resume_watermark_utc"
    )
    effective = _utc_timestamp(bind, evidence["effective_at_utc"], "effective_at_utc")
    initialization = _utc_timestamp(
        bind, evidence["initialization_utc"], "initialization_utc"
    )
    evidence_watermark = _utc_timestamp(
        bind, evidence["resume_watermark_utc"], "resume_watermark_utc"
    )
    expected_suppressed = baseline["suppressed_since_utc"]
    evidence_suppressed = evidence["suppressed_since_utc"]
    if expected_suppressed is None:
        suppressed_matches = evidence_suppressed is None
    else:
        suppressed_matches = evidence_suppressed is not None and _utc_timestamp(
            bind, expected_suppressed, "suppressed_since_utc"
        ) == _utc_timestamp(bind, evidence_suppressed, "suppressed_since_utc")

    valid = (
        evidence["state_transition_id"] not in (None, "")
        and str(evidence["workspace_id"]) == str(deployment["workspace_id"])
        and evidence["paper_id"] == deployment["paper_id"]
        and evidence["from_state"] is None
        and evidence["to_state"] == target
        and effective == initialization == watermark == evidence_watermark
        and suppressed_matches
        and evidence["revision"] == baseline["revision"]
        and evidence["reason_code"]
        == "SCHEDULER_STATE_INITIALIZED_NO_HISTORY"
    )
    if not valid:
        raise SchedulerInitializationError(
            "ambiguous scheduler initialization evidence"
        )
    _closed_object(evidence["actor"], {"type", "id"}, "actor")
    _closed_object(evidence["system"], {"service", "instance_id"}, "system")
    _closed_object(
        evidence["commit_build_locator"],
        {"commit_sha", "build_id"},
        "commit_build_locator",
    )


def _validate_baselines(bind: Connection) -> None:
    deployments, states, audit_events = _tables(bind)
    rows = bind.execute(select(deployments).with_for_update()).mappings().all()
    deployment_pairs = {(row["workspace_id"], row["id"]) for row in rows}
    state_rows = bind.execute(select(states).with_for_update()).mappings().all()
    grouped: dict[tuple[Any, Any], list[Mapping[str, Any]]] = {}
    for row in state_rows:
        grouped.setdefault((row["workspace_id"], row["paper_id"]), []).append(row)
    if set(grouped) - deployment_pairs:
        raise SchedulerInitializationError(
            "ambiguous scheduler initialization: orphan state"
        )

    missing = [
        pair for pair in deployment_pairs if not grouped.get(pair)
    ]
    ambiguous = [
        pair for pair in deployment_pairs if len(grouped.get(pair, [])) > 1
    ]
    if missing or ambiguous:
        raise SchedulerInitializationError(
            "missing or ambiguous scheduler state initialization; readiness blocked"
        )

    for deployment in rows:
        target = _STATUS_MAP.get(str(deployment["status"]))
        if target is None:
            raise SchedulerInitializationError(
                "ambiguous scheduler initialization: unclassifiable legacy status"
            )
        existing = grouped.get((deployment["workspace_id"], deployment["id"]), [])
        baseline = existing[0]
        revision = baseline["revision"]
        valid = (
            baseline["scheduler_status"] == target
            and isinstance(revision, int)
            and not isinstance(revision, bool)
            and revision >= 1
            and baseline["resume_watermark_utc"] is not None
            and ((target == "ACTIVE") == (baseline["suppressed_since_utc"] is None))
        )
        if not valid:
            raise SchedulerInitializationError(
                "ambiguous scheduler state initialization; readiness blocked"
            )
        _validate_evidence(bind, audit_events, deployment, baseline, target)


def _run_upgrade(bind: Connection) -> None:
    transaction = bind.begin_nested() if bind.in_transaction() else bind.begin()
    try:
        _validate_baselines(bind)
        transaction.commit()
    except Exception:
        if transaction.is_active:
            transaction.rollback()
        raise


def upgrade() -> None:
    """Block readiness unless every deployment has one proven baseline."""
    bind = op.get_bind()
    _run_upgrade(bind)


def downgrade() -> None:
    """0017 changes data only; 0016 owns the table schema."""
