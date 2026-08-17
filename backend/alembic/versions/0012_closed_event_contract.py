"""Enforce the closed P0 R2 SSE event contract.

Revision ID: 0012_closed_events
Revises: 0011_provider_credentials
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa

from alembic import op
from quantfoundry.domain.value_objects.public_ids import is_public_id

revision = "0012_closed_events"
down_revision = "0011_provider_credentials"
branch_labels = None
depends_on = None

EVENT_TYPES = (
    "job.updated",
    "research.created",
    "research.updated",
    "research.conclusion.created",
    "experiment.created",
    "experiment.updated",
    "factor.updated",
    "strategy.created",
    "strategy.updated",
    "validation.created",
    "validation.updated",
    "validation.holdout.updated",
    "approval.created",
    "approval.updated",
    "paper.created",
    "paper.updated",
    "paper.run.updated",
    "review.created",
    "review.updated",
    "data.provider.updated",
    "data.capability.updated",
    "data.quality.updated",
    "agent.run.updated",
    "tool.call.updated",
    "memo.created",
    "memo.updated",
    "setup.completed",
    "configuration.updated",
    "configuration.apply_failed",
    "database.connection.updated",
    "database.connection.failed",
    "notification.created",
    "notification.updated",
    "system.health.updated",
    "system.resync_required",
)

EVENT_OBJECT_TYPES = {
    "job.updated": "job",
    "research.created": "research",
    "research.updated": "research",
    "research.conclusion.created": "conclusion",
    "experiment.created": "experiment",
    "experiment.updated": "experiment",
    "factor.updated": "factor",
    "strategy.created": "strategy_version",
    "strategy.updated": "strategy_version",
    "validation.created": "validation",
    "validation.updated": "validation",
    "validation.holdout.updated": "validation",
    "approval.created": "approval",
    "approval.updated": "approval",
    "paper.created": "paper",
    "paper.updated": "paper",
    "paper.run.updated": "paper_run",
    "review.created": "review",
    "review.updated": "review",
    "data.provider.updated": "provider_connection",
    "data.capability.updated": "capability",
    "data.quality.updated": "snapshot",
    "agent.run.updated": "agent_run",
    "tool.call.updated": "tool_call",
    "memo.created": "memo",
    "memo.updated": "memo",
    "setup.completed": "settings",
    "configuration.updated": "settings",
    "configuration.apply_failed": "settings",
    "database.connection.updated": "provider_connection",
    "database.connection.failed": "provider_connection",
    "notification.created": "notification",
    "notification.updated": "agent_config",
    "system.health.updated": "event_stream",
    "system.resync_required": "event_stream",
}

_EVENT_PAYLOAD_FIELDS = {
    "status",
    "state",
    "reason_code",
    "resync_from_sequence",
    "progress_mode",
    "completed_units",
    "total_units",
    "current_step_key",
    "agent_run_id",
    "role",
    "objective",
    "research_id",
    "object_type",
    "object_id",
    "object_version",
    "object_revision",
    "waiting_on",
}


def _migrated_public_id(prefix: str, workspace_id: str, sequence: int) -> str:
    digest = hashlib.sha256(f"{prefix}:{workspace_id}:{sequence}".encode()).hexdigest()
    uuid4 = (
        f"{digest[:8]}-{digest[8:12]}-4{digest[13:16]}-8{digest[17:20]}-{digest[20:32]}"
    )
    return f"{prefix}-{uuid4}"


def _fallback_object_id(object_type: str, workspace_id: str, sequence: int) -> str:
    prefixes = {
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
    if object_type == "settings":
        return "SETTINGS-DEFAULT"
    if object_type == "agent_config":
        return "RESEARCH_DIRECTOR"
    if object_type == "provider_connection":
        return _migrated_public_id("CONN", workspace_id, sequence).removeprefix("CONN-")
    return _migrated_public_id(prefixes[object_type], workspace_id, sequence)


_OBJECT_ID_KINDS = {
    "job": "job",
    "research": "research",
    "conclusion": "conclusion",
    "experiment": "experiment",
    "factor": "factor",
    "strategy_version": "strategy",
    "validation": "validation",
    "approval": "approval",
    "paper": "paper",
    "paper_run": "paper_run",
    "review": "performance_review",
    "capability": "capability",
    "snapshot": "snapshot",
    "agent_run": "agent_run",
    "tool_call": "tool_call",
    "memo": "memo",
    "notification": "notification",
}


def _valid_existing_object_id(object_type: str, value: str | None) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if object_type == "settings":
        return value == "SETTINGS-DEFAULT"
    if object_type == "agent_config":
        return value in {
            "RESEARCH_DIRECTOR",
            "FACTOR_SCIENTIST",
            "STRATEGY_SCIENTIST",
            "PORTFOLIO_ANALYST",
            "RED_TEAM_RESEARCHER",
            "PERFORMANCE_ANALYST",
        }
    if object_type == "provider_connection":
        return (
            re.fullmatch(
                r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
                value,
            )
            is not None
        )
    if object_type == "event_stream":
        return is_public_id("domain_event", value)
    kind = _OBJECT_ID_KINDS.get(object_type)
    return kind is not None and is_public_id(kind, value)


def _canonical_event_type(value: str | None) -> str:
    if value in EVENT_TYPES:
        return value
    if value == "research.CREATED":
        return "research.created"
    if value and value.startswith("research."):
        return "research.updated"
    if value in {"experiment.CREATED", "experiment.REPRODUCE_QUEUED"}:
        return "experiment.created"
    if value and value.startswith("experiment."):
        return "experiment.updated"
    if value and value.startswith("factor."):
        return "factor.updated"
    if value == "strategy_version.CREATED":
        return "strategy.created"
    if value and value.startswith("strategy_version."):
        return "strategy.updated"
    if value == "validation.CREATED":
        return "validation.created"
    if value and value.startswith("validation.HOLDOUT"):
        return "validation.holdout.updated"
    if value and value.startswith("validation."):
        return "validation.updated"
    if value == "approval.CREATED":
        return "approval.created"
    if value and value.startswith("approval."):
        return "approval.updated"
    if value and value.startswith("job."):
        return "job.updated"
    if value and value.startswith("agent_run."):
        return "agent.run.updated"
    if value and value.startswith("tool_call."):
        return "tool.call.updated"
    if value == "memo.CREATED":
        return "memo.created"
    if value and value.startswith("memo."):
        return "memo.updated"
    if value and value.startswith("settings."):
        return "setup.completed"
    if value and value.startswith("provider_connection."):
        return "data.provider.updated"
    if value and value.startswith("snapshot."):
        return "data.quality.updated"
    if value and value.startswith("agent_config."):
        return "notification.updated"
    return "system.resync_required"


def _preserved_payload(raw: object) -> str | None:
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        return None
    if not isinstance(value, dict) or not set(value).issubset(_EVENT_PAYLOAD_FIELDS):
        return None
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def upgrade() -> None:
    connection = op.get_bind()
    dialect = connection.dialect.name
    if dialect == "postgresql":
        connection.execute(sa.text("LOCK TABLE domain_events IN ACCESS EXCLUSIVE MODE"))
        op.execute(
            "DROP TRIGGER IF EXISTS qf_domain_events_update_immutable ON domain_events"
        )
    else:
        if dialect == "sqlite":
            if connection.in_transaction():
                connection.execute(
                    sa.text("UPDATE domain_events SET sequence = sequence WHERE 0")
                )
            else:
                connection.exec_driver_sql("BEGIN IMMEDIATE")
        op.execute("DROP TRIGGER IF EXISTS qf_domain_events_update_immutable")
    now = datetime.now(UTC)
    occurred_at_value = (
        now.strftime("%Y-%m-%d %H:%M:%S") if dialect == "sqlite" else now
    )
    expires_at_value = (
        (now + timedelta(days=7)).strftime("%Y-%m-%d %H:%M:%S")
        if dialect == "sqlite"
        else now + timedelta(days=7)
    )
    rows = (
        connection.execute(
            sa.text(
                "SELECT workspace_id, sequence, event_id, event_type, object_id, "
                "object_type, payload "
                "FROM domain_events"
            )
        )
        .mappings()
        .all()
    )
    for row in rows:
        event_type = _canonical_event_type(row["event_type"])
        object_type = EVENT_OBJECT_TYPES[event_type]
        event_id = (
            row["event_id"]
            if is_public_id("domain_event", row["event_id"] or "")
            else _migrated_public_id("EVT", row["workspace_id"], row["sequence"])
        )
        if event_type == "system.resync_required":
            object_id = event_id
        elif _valid_existing_object_id(object_type, row["object_id"]):
            object_id = row["object_id"]
        else:
            event_type = "system.resync_required"
            object_type = EVENT_OBJECT_TYPES[event_type]
            object_id = event_id
        payload = (
            json.dumps(
                {"state": "RESYNC_REQUIRED", "status": None},
                separators=(",", ":"),
            )
            if event_type == "system.resync_required"
            else (_preserved_payload(row["payload"]) or "{}")
        )
        connection.execute(
            sa.text(
                """
                UPDATE domain_events
                SET event_id = :event_id,
                    event_type = :event_type,
                    object_type = :object_type,
                    object_id = :object_id,
                    payload = :payload,
                    request_id = COALESCE(request_id, :request_id),
                    occurred_at = COALESCE(occurred_at, :occurred_at),
                    expires_at = COALESCE(expires_at, :expires_at)
                WHERE workspace_id = :workspace_id AND sequence = :sequence
                """
            ),
            {
                "workspace_id": row["workspace_id"],
                "sequence": row["sequence"],
                "event_id": event_id,
                "event_type": event_type,
                "object_type": object_type,
                "object_id": object_id,
                "payload": payload,
                "request_id": f"REQ-MIGRATED-{row['sequence']}",
                "occurred_at": occurred_at_value,
                "expires_at": expires_at_value,
            },
        )

    quoted = ", ".join("'" + value + "'" for value in EVENT_TYPES)
    with op.batch_alter_table("domain_events") as batch:
        batch.alter_column("event_id", existing_type=sa.String(), nullable=False)
        batch.alter_column(
            "event_type", existing_type=sa.String(), type_=sa.String(96), nullable=False
        )
        batch.alter_column("object_type", existing_type=sa.String(), nullable=False)
        batch.alter_column("object_id", existing_type=sa.String(), nullable=False)
        batch.alter_column("payload", existing_type=sa.Text(), nullable=False)
        batch.alter_column(
            "occurred_at", existing_type=sa.DateTime(timezone=True), nullable=False
        )
        batch.alter_column(
            "expires_at", existing_type=sa.DateTime(timezone=True), nullable=False
        )
        batch.alter_column("request_id", existing_type=sa.String(), nullable=False)
        batch.create_check_constraint(
            "domain_events_event_type_check",
            f"event_type IN ({quoted})",
        )
        object_mapping = " OR ".join(
            f"(event_type = '{event_type}' AND object_type = '{object_type}')"
            for event_type, object_type in EVENT_OBJECT_TYPES.items()
        )
        batch.create_check_constraint(
            "domain_events_event_object_type_check",
            object_mapping,
        )
    if dialect == "postgresql":
        op.execute(
            "CREATE TRIGGER qf_domain_events_update_immutable BEFORE UPDATE ON "
            "domain_events FOR EACH ROW EXECUTE FUNCTION qf_reject_change()"
        )
    else:
        op.execute("DROP TRIGGER IF EXISTS qf_domain_events_delete_immutable")
        op.execute(
            "CREATE TRIGGER qf_domain_events_update_immutable BEFORE UPDATE ON "
            "domain_events BEGIN SELECT RAISE(ABORT, "
            "'immutable evidence cannot be changed'); END"
        )
        op.execute(
            "CREATE TRIGGER qf_domain_events_delete_immutable BEFORE DELETE ON "
            "domain_events WHEN datetime(OLD.expires_at) > datetime('now') BEGIN "
            "SELECT RAISE(ABORT, 'unexpired event cannot be deleted'); END"
        )


def downgrade() -> None:
    raise RuntimeError("closed event-contract migration is irreversible")
