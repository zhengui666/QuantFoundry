"""Add durable opaque session-token verification.

Revision ID: 0002_session_tokens
Revises: 0001_p0_core
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_session_tokens"
down_revision = "0001_p0_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "session_tokens",
        sa.Column("token_sha256", sa.String(length=64), primary_key=True),
        sa.Column("actor_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "workspace_id", sa.String(), sa.ForeignKey("workspaces.id"), nullable=False
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_session_tokens_actor_id", "session_tokens", ["actor_id"])
    op.create_index(
        "ix_session_tokens_workspace_id", "session_tokens", ["workspace_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_session_tokens_workspace_id", table_name="session_tokens")
    op.drop_index("ix_session_tokens_actor_id", table_name="session_tokens")
    op.drop_table("session_tokens")
