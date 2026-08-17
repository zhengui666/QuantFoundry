"""Alembic-owned LangGraph PostgreSQL checkpoint schema.

Revision ID: 0015_langgraph_checkpoint
Revises: 0014_agent_artifacts
"""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0015_langgraph_checkpoint"
down_revision = "0014_agent_artifacts"
branch_labels = None
depends_on = None

SCHEMA = "agent_checkpoint"

_TABLES = {
    "checkpoint_migrations": ({"v"}, ("v",)),
    "checkpoints": (
        {
            "thread_id",
            "checkpoint_ns",
            "checkpoint_id",
            "parent_checkpoint_id",
            "type",
            "checkpoint",
            "metadata",
        },
        ("thread_id", "checkpoint_ns", "checkpoint_id"),
    ),
    "checkpoint_blobs": (
        {"thread_id", "checkpoint_ns", "channel", "version", "type", "blob"},
        ("thread_id", "checkpoint_ns", "channel", "version"),
    ),
    "checkpoint_writes": (
        {
            "thread_id",
            "checkpoint_ns",
            "checkpoint_id",
            "task_id",
            "idx",
            "channel",
            "type",
            "blob",
            "task_path",
        },
        ("thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx"),
    ),
}

_COLUMN_CONTRACTS = {
    "checkpoint_migrations": {"v": ("INTEGER", False, False)},
    "checkpoints": {
        "thread_id": ("TEXT", False, False),
        "checkpoint_ns": ("TEXT", False, True),
        "checkpoint_id": ("TEXT", False, False),
        "parent_checkpoint_id": ("TEXT", True, False),
        "type": ("TEXT", True, False),
        "checkpoint": ("JSONB", False, False),
        "metadata": ("JSONB", False, True),
    },
    "checkpoint_blobs": {
        "thread_id": ("TEXT", False, False),
        "checkpoint_ns": ("TEXT", False, True),
        "channel": ("TEXT", False, False),
        "version": ("TEXT", False, False),
        "type": ("TEXT", False, False),
        "blob": ("BYTEA", True, False),
    },
    "checkpoint_writes": {
        "thread_id": ("TEXT", False, False),
        "checkpoint_ns": ("TEXT", False, True),
        "checkpoint_id": ("TEXT", False, False),
        "task_id": ("TEXT", False, False),
        "idx": ("INTEGER", False, False),
        "channel": ("TEXT", False, False),
        "type": ("TEXT", True, False),
        "blob": ("BYTEA", False, False),
        "task_path": ("TEXT", False, True),
    },
}


def _validate_existing_schema(bind: Any) -> None:
    inspector = sa.inspect(bind)
    present = {name: inspector.has_table(name, schema=SCHEMA) for name in _TABLES}
    if not all(present.values()):
        raise RuntimeError(
            "0015 found a partial LangGraph checkpoint schema; refusing adoption"
        )
    for name, (required_columns, primary_key) in _TABLES.items():
        inspected_columns = inspector.get_columns(name, schema=SCHEMA)
        columns = {item["name"] for item in inspected_columns}
        if not required_columns <= columns:
            raise RuntimeError(
                f"0015 checkpoint table {SCHEMA}.{name} is missing required columns"
            )
        actual_key = (
            inspector.get_pk_constraint(name, schema=SCHEMA).get("constrained_columns")
            or []
        )
        if actual_key != list(primary_key):
            raise RuntimeError(
                f"0015 checkpoint table {SCHEMA}.{name} has an incompatible primary key"
            )
        for column in inspected_columns:
            expected = _COLUMN_CONTRACTS[name].get(column["name"])
            if expected is None:
                continue
            expected_type, nullable, requires_default = expected
            actual_type = str(column["type"]).upper()
            if expected_type not in actual_type or column["nullable"] is not nullable:
                raise RuntimeError(
                    f"0015 checkpoint column {SCHEMA}.{name}.{column['name']} has an incompatible type/nullability"
                )
            if requires_default and column.get("default") is None:
                raise RuntimeError(
                    f"0015 checkpoint column {SCHEMA}.{name}.{column['name']} is missing its required default"
                )
    try:
        versions = {
            int(value)
            for (value,) in bind.execute(
                sa.text(f"SELECT v FROM {SCHEMA}.checkpoint_migrations")
            )
        }
    except (TypeError, ValueError) as error:
        raise RuntimeError(
            "0015 existing LangGraph checkpoint migration versions are invalid"
        ) from error
    if versions != set(range(10)):
        raise RuntimeError(
            "0015 existing LangGraph checkpoint schema has incompatible migration versions"
        )


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # SQLite agents use the dedicated SqliteSaver file and call setup()
        # against that file at runtime; this PostgreSQL-only revision has no
        # domain checkpoint objects to create on the domain SQLite database.
        return
    if bind.dialect.name != "postgresql":
        raise RuntimeError("0015 LangGraph checkpoint schema requires PostgreSQL")
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
    inspector = sa.inspect(bind)
    existing = any(inspector.has_table(name, schema=SCHEMA) for name in _TABLES)
    if existing:
        _validate_existing_schema(bind)
        return
    op.create_table(
        "checkpoint_migrations",
        sa.Column("v", sa.Integer(), primary_key=True),
        schema=SCHEMA,
    )
    op.create_table(
        "checkpoints",
        sa.Column("thread_id", sa.Text(), primary_key=True),
        sa.Column("checkpoint_ns", sa.Text(), primary_key=True, server_default=""),
        sa.Column("checkpoint_id", sa.Text(), primary_key=True),
        sa.Column("parent_checkpoint_id", sa.Text()),
        sa.Column("type", sa.Text()),
        sa.Column("checkpoint", postgresql.JSONB(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        schema=SCHEMA,
    )
    op.create_table(
        "checkpoint_blobs",
        sa.Column("thread_id", sa.Text(), primary_key=True),
        sa.Column("checkpoint_ns", sa.Text(), primary_key=True, server_default=""),
        sa.Column("channel", sa.Text(), primary_key=True),
        sa.Column("version", sa.Text(), primary_key=True),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("blob", sa.LargeBinary()),
        schema=SCHEMA,
    )
    op.create_table(
        "checkpoint_writes",
        sa.Column("thread_id", sa.Text(), primary_key=True),
        sa.Column("checkpoint_ns", sa.Text(), primary_key=True, server_default=""),
        sa.Column("checkpoint_id", sa.Text(), primary_key=True),
        sa.Column("task_id", sa.Text(), primary_key=True),
        sa.Column("idx", sa.Integer(), primary_key=True),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("type", sa.Text()),
        sa.Column("blob", sa.LargeBinary(), nullable=False),
        sa.Column("task_path", sa.Text(), nullable=False, server_default=""),
        schema=SCHEMA,
    )
    op.create_index(
        "checkpoints_thread_id_idx",
        "checkpoints",
        ["thread_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "checkpoint_blobs_thread_id_idx",
        "checkpoint_blobs",
        ["thread_id"],
        schema=SCHEMA,
    )
    op.create_index(
        "checkpoint_writes_thread_id_idx",
        "checkpoint_writes",
        ["thread_id"],
        schema=SCHEMA,
    )
    op.execute(
        sa.text(
            f"INSERT INTO {SCHEMA}.checkpoint_migrations (v) "
            "SELECT generate_series(0, 9)"
        )
    )


def downgrade() -> None:
    # Existing LangGraph installations are adopted without ownership metadata;
    # never destroy their checkpoint data during rollback.
    return None
