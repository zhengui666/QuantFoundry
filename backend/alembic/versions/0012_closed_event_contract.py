"""Enforce the closed P0 R2 SSE event contract.

Revision ID: 0012_closed_events
Revises: 0011_provider_credentials
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

import sqlalchemy as sa

from alembic import op

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


def _migrated_public_id(prefix: str, sequence: int) -> str:
    digest = hashlib.sha256(f"{prefix}:{sequence}".encode()).hexdigest()
    uuid4 = (
        f"{digest[:8]}-{digest[8:12]}-4{digest[13:16]}-8{digest[17:20]}-{digest[20:32]}"
    )
    return f"{prefix}-{uuid4}"


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


def upgrade() -> None:
    connection = op.get_bind()
    dialect = connection.dialect.name
    if dialect == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS qf_domain_events_update_immutable ON domain_events"
        )
    else:
        op.execute("DROP TRIGGER IF EXISTS qf_domain_events_update_immutable")
    now = datetime.now(UTC)
    occurred_at_value = now.isoformat() if dialect == "sqlite" else now
    expires_at_value = (
        (now + timedelta(days=7)).isoformat()
        if dialect == "sqlite"
        else now + timedelta(days=7)
    )
    rows = (
        connection.execute(
            sa.text("SELECT sequence, event_id, event_type FROM domain_events")
        )
        .mappings()
        .all()
    )
    for row in rows:
        event_type = _canonical_event_type(row["event_type"])
        payload = (
            json.dumps(
                {"state": "RESYNC_REQUIRED", "status": None},
                separators=(",", ":"),
            )
            if event_type == "system.resync_required"
            else "{}"
        )
        connection.execute(
            sa.text(
                """
                UPDATE domain_events
                SET event_id = :event_id,
                    event_type = :event_type,
                    object_type = COALESCE(object_type, 'event_stream'),
                    object_id = COALESCE(object_id, 'events'),
                    payload = :payload,
                    request_id = COALESCE(request_id, :request_id),
                    occurred_at = COALESCE(occurred_at, :occurred_at),
                    expires_at = COALESCE(expires_at, :expires_at)
                WHERE sequence = :sequence
                """
            ),
            {
                "sequence": row["sequence"],
                "event_id": row["event_id"]
                or _migrated_public_id("EVT", row["sequence"]),
                "event_type": event_type,
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
        batch.create_check_constraint(
            "domain_events_event_type_check",
            f"event_type IN ({quoted})",
        )
    if dialect == "postgresql":
        op.execute(
            "CREATE TRIGGER qf_domain_events_update_immutable BEFORE UPDATE ON "
            "domain_events FOR EACH ROW EXECUTE FUNCTION qf_reject_change()"
        )
    else:
        op.execute(
            "CREATE TRIGGER qf_domain_events_update_immutable BEFORE UPDATE ON "
            "domain_events BEGIN SELECT RAISE(ABORT, "
            "'immutable evidence cannot be changed'); END"
        )
        op.execute(
            "CREATE TRIGGER qf_domain_events_delete_immutable BEFORE DELETE ON "
            "domain_events WHEN OLD.expires_at > CURRENT_TIMESTAMP BEGIN "
            "SELECT RAISE(ABORT, 'unexpired event cannot be deleted'); END"
        )


def downgrade() -> None:
    raise RuntimeError("closed event-contract migration is irreversible")
