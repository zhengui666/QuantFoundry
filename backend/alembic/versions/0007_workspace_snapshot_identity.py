"""Scope immutable snapshot identities to a workspace.

Revision ID: 0007_workspace_snapshot_identity
Revises: 0006_p0_truthfulness
"""

from __future__ import annotations

from alembic import op

revision = "0007_workspace_snapshot_identity"
down_revision = "0006_p0_truthfulness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
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
    with op.batch_alter_table(
        "data_snapshots",
        naming_convention={"uq": "uq_%(table_name)s_%(column_0_name)s"},
    ) as batch_op:
        batch_op.drop_constraint("uq_data_snapshots_content_sha256", type_="unique")
        batch_op.create_unique_constraint(
            "uq_data_snapshots_workspace_content",
            ["workspace_id", "content_sha256"],
        )


def downgrade() -> None:
    raise RuntimeError("workspace-scoped snapshot identity is irreversible")
