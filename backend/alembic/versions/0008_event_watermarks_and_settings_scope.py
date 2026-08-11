"""Persist workspace SSE retention watermarks and scope settings storage.

Revision ID: 0008_event_watermarks_settings
Revises: 0007_workspace_snapshot_identity
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0008_event_watermarks_settings"
down_revision = "0007_workspace_snapshot_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_stream_watermarks",
        sa.Column("workspace_id", sa.String(), primary_key=True),
        sa.Column("last_sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "expired_through_sequence", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.execute(
        """
        INSERT INTO event_stream_watermarks
          (workspace_id, last_sequence, expired_through_sequence)
        SELECT COALESCE(workspace_id, 'system'), MAX(sequence), 0
        FROM domain_events
        GROUP BY COALESCE(workspace_id, 'system')
        """
    )
    op.execute(
        """
        UPDATE records
        SET id = 'settings:' || workspace_id
        WHERE id = 'settings' AND kind = 'settings' AND workspace_id IS NOT NULL
        """
    )


def downgrade() -> None:
    raise RuntimeError("durable workspace event retention state is irreversible")
