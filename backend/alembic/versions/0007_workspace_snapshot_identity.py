"""Scope immutable snapshot identities to a workspace.

Revision ID: 0007_workspace_snapshot_identity
Revises: 0006_p0_truthfulness
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0007_workspace_snapshot_identity"
down_revision = "0006_p0_truthfulness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name not in {"postgresql", "sqlite"}:
        raise RuntimeError(
            "0007 workspace snapshot identity supports PostgreSQL and SQLite only"
        )
    null_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM data_snapshots WHERE workspace_id IS NULL")
    ).scalar_one()
    if null_count:
        raise RuntimeError(
            "data_snapshots contains rows without authoritative workspace ownership"
        )
    if bind.dialect.name == "postgresql":
        op.alter_column("data_snapshots", "workspace_id", nullable=False)
        op.drop_constraint(
            "data_snapshots_content_sha256_key",
            "data_snapshots",
            type_="unique",
        )
        op.create_unique_constraint(
            "uq_data_snapshots_workspace_content",
            "data_snapshots",
            ["workspace_id", "content_sha256"],
        )
        return
    op.execute("DROP TRIGGER IF EXISTS qf_data_snapshots_update_immutable")
    op.execute("DROP TRIGGER IF EXISTS qf_data_snapshots_delete_immutable")
    with op.batch_alter_table(
        "data_snapshots",
        naming_convention={"uq": "uq_%(table_name)s_%(column_0_name)s"},
    ) as batch_op:
        batch_op.drop_constraint("uq_data_snapshots_content_sha256", type_="unique")
        batch_op.create_unique_constraint(
            "uq_data_snapshots_workspace_content",
            ["workspace_id", "content_sha256"],
        )
        batch_op.alter_column("workspace_id", nullable=False)
    op.execute(
        "CREATE TRIGGER qf_data_snapshots_update_immutable BEFORE UPDATE ON "
        "data_snapshots BEGIN SELECT RAISE(ABORT, 'immutable evidence cannot be changed'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_data_snapshots_delete_immutable BEFORE DELETE ON "
        "data_snapshots BEGIN SELECT RAISE(ABORT, 'immutable evidence cannot be changed'); END"
    )


def downgrade() -> None:
    raise RuntimeError("workspace-scoped snapshot identity is irreversible")
