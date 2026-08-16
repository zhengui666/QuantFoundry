"""Make external dataset identities workspace scoped.

Revision ID: 0009_workspace_data_sources
Revises: 0008_event_watermarks_settings
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0009_workspace_data_sources"
down_revision = "0008_event_watermarks_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    null_count = op.get_bind().execute(
        sa.text("SELECT COUNT(*) FROM data_sources WHERE workspace_id IS NULL")
    ).scalar_one()
    if null_count:
        raise RuntimeError(
            "0009 refuses to invent data-source ownership for unscoped rows"
        )
    dialect = op.get_bind().dialect.name
    naming = {"pk": "pk_%(table_name)s"}
    with op.batch_alter_table(
        "data_sources", naming_convention=naming if dialect == "sqlite" else None
    ) as batch_op:
        batch_op.alter_column(
            "workspace_id",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.drop_constraint(
            "pk_data_sources" if dialect == "sqlite" else "data_sources_pkey",
            type_="primary",
        )
        batch_op.create_primary_key("data_sources_pkey", ["id", "workspace_id"])


def downgrade() -> None:
    raise RuntimeError("workspace-scoped dataset identity is irreversible")
