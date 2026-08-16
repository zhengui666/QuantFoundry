"""Validate the UX-001 runtime snapshot columns owned by section 14.

The frozen ``0016_section14_physical.json`` already contains these columns.
This revision is intentionally non-destructive: adding or dropping them here
would change PostgreSQL column order and would lose snapshot data on downgrade.
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0018_ux001_runtime_snapshots"
down_revision = "0017_paper_scheduler_state_init"
branch_labels = None
depends_on = None

RUNTIME_COLUMNS = {
    "agent_runs": (
        "ai_connection_id",
        "ai_connection_revision",
        "effective_configuration_revision",
        "effective_configuration_sha256",
        "agent_configuration_revision",
        "runtime_profile",
        "tool_timeout_seconds",
        "max_steps",
        "max_tool_calls",
        "prompt_manifest_sha256",
        "tool_registry_sha256",
    ),
    "tool_calls": (
        "effective_configuration_revision",
        "configuration_sha256",
        "tool_registry_sha256",
    ),
}


def _validate_section14_columns() -> None:
    inspector = sa.inspect(op.get_bind())
    missing = {
        table: sorted(
            set(columns) - {item["name"] for item in inspector.get_columns(table)}
        )
        for table, columns in RUNTIME_COLUMNS.items()
    }
    missing = {table: columns for table, columns in missing.items() if columns}
    if missing:
        raise RuntimeError(
            f"0018 requires the section-14 runtime snapshot columns; missing={missing}"
        )


def _remove_legacy_defaults() -> None:
    if op.get_bind().dialect.name == "sqlite":
        return
    for table, columns in RUNTIME_COLUMNS.items():
        for column in columns:
            op.alter_column(table, column, server_default=None)


def upgrade() -> None:
    _validate_section14_columns()
    _remove_legacy_defaults()


def downgrade() -> None:
    # 0016 owns the physical columns. Keeping them here makes head -> 0017 ->
    # head and the populated 0016 roundtrip lossless and order-preserving.
    return None
