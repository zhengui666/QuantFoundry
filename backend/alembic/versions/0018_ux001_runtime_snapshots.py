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

_RUNTIME_COLUMN_CONTRACT = {
    "agent_runs": {
        "ai_connection_id": ("varchar", None),
        "ai_connection_revision": ("bigint", None),
        "effective_configuration_revision": ("bigint", None),
        "effective_configuration_sha256": ("varchar", 64),
        "agent_configuration_revision": ("bigint", None),
        "runtime_profile": ("varchar", None),
        "tool_timeout_seconds": ("integer", None),
        "max_steps": ("integer", None),
        "max_tool_calls": ("integer", None),
        "prompt_manifest_sha256": ("varchar", 64),
        "tool_registry_sha256": ("varchar", 64),
    },
    "tool_calls": {
        "effective_configuration_revision": ("bigint", None),
        "configuration_sha256": ("varchar", 64),
        "tool_registry_sha256": ("varchar", 64),
    },
}


def _type_matches(column: dict[str, object], expected: str, length: int | None) -> bool:
    actual = str(column["type"]).lower().replace(" ", "")
    if expected == "bigint":
        matches = "bigint" in actual
    elif expected == "integer":
        matches = "integer" in actual and "bigint" not in actual
    else:
        matches = actual.startswith(("varchar", "charactervarying", "string"))
    if not matches:
        return False
    return length is None or getattr(column["type"], "length", None) == length


def _validate_section14_columns() -> None:
    inspector = sa.inspect(op.get_bind())
    invalid: dict[str, list[str]] = {}
    for table, columns in _RUNTIME_COLUMN_CONTRACT.items():
        reflected = {item["name"]: item for item in inspector.get_columns(table)}
        for name, (expected_type, length) in columns.items():
            column = reflected.get(name)
            if (
                column is None
                or bool(column["nullable"])
                or not _type_matches(column, expected_type, length)
            ):
                invalid.setdefault(table, []).append(name)
    if invalid:
        raise RuntimeError(
            f"0018 requires exact section-14 runtime snapshot columns; invalid={invalid}"
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
