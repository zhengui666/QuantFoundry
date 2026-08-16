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
    token_check = (
        "token_sha256 ~ '^[0-9a-f]{64}$'"
        if op.get_bind().dialect.name == "postgresql"
        else "length(token_sha256) = 64 AND token_sha256 NOT GLOB '*[^0-9a-f]*'"
    )
    op.create_table(
        "session_tokens",
        sa.Column("token_sha256", sa.String(length=64), primary_key=True),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["users.id"], name="fk_session_tokens_actor_id_users"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id"],
            ["workspaces.id"],
            name="fk_session_tokens_workspace_id_workspaces",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "actor_id"],
            ["workspaces.id", "workspaces.owner_id"],
            name="fk_session_tokens_workspace_owner",
        ),
        sa.CheckConstraint(token_check, name="ck_session_tokens_sha256_valid"),
    )
    op.create_index("ix_session_tokens_actor_id", "session_tokens", ["actor_id"])
    op.create_index(
        "ix_session_tokens_workspace_id", "session_tokens", ["workspace_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_session_tokens_workspace_id", table_name="session_tokens")
    op.drop_index("ix_session_tokens_actor_id", table_name="session_tokens")
    op.drop_table("session_tokens")
