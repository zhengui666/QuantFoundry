"""Align migrated indexes with the authoritative ORM metadata.

Revision ID: 0013_metadata_alignment
Revises: 0012_closed_events
"""

from __future__ import annotations

from alembic import op

revision = "0013_metadata_alignment"
down_revision = "0012_closed_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # workspace_id is already the second member of the composite primary key;
    # the historical single-column index is not part of current metadata.
    op.drop_index("ix_data_sources_workspace_id", table_name="data_sources")


def downgrade() -> None:
    op.create_index(
        "ix_data_sources_workspace_id",
        "data_sources",
        ["workspace_id"],
        unique=False,
    )
