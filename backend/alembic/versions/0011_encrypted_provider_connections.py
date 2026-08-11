"""Replace metadata-only setup refs with encrypted provider connections.

Revision ID: 0011_provider_credentials
Revises: 0010_setup_reference_bindings
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0011_provider_credentials"
down_revision = "0010_setup_reference_bindings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("setup_bindings")
    op.create_table(
        "model_provider_connections",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(
            "owner_actor_id",
            sa.String(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("provider_id", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("model_name", sa.String(128)),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("nonce", sa.LargeBinary(), nullable=False),
        sa.Column("key_id", sa.String(64), nullable=False),
        sa.Column(
            "validation_state",
            sa.String(16),
            nullable=False,
            server_default="SUCCESS",
        ),
        sa.Column("status", sa.String(16), nullable=False, server_default="VALIDATED"),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("consumed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("kind IN ('AI', 'DATA')", name="provider_connection_kind"),
        sa.CheckConstraint(
            "validation_state = 'SUCCESS'",
            name="provider_connection_validation_success",
        ),
        sa.CheckConstraint(
            "status IN ('VALIDATED', 'ACTIVE', 'REVOKED')",
            name="provider_connection_status",
        ),
    )
    op.create_index(
        "ix_model_provider_connections_workspace_id",
        "model_provider_connections",
        ["workspace_id"],
    )
    op.create_index(
        "ix_model_provider_connections_owner_actor_id",
        "model_provider_connections",
        ["owner_actor_id"],
    )
    op.create_index(
        "ix_model_provider_connections_provider_id",
        "model_provider_connections",
        ["provider_id"],
    )
    op.create_table(
        "setup_bindings",
        sa.Column(
            "workspace_id",
            sa.String(),
            sa.ForeignKey("workspaces.id"),
            primary_key=True,
        ),
        sa.Column(
            "settings_record_id",
            sa.String(),
            sa.ForeignKey("records.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "ai_connection_id",
            sa.String(),
            sa.ForeignKey("model_provider_connections.id"),
            nullable=False,
        ),
        sa.Column(
            "data_connection_id",
            sa.String(),
            sa.ForeignKey("model_provider_connections.id"),
        ),
        sa.Column(
            "research_policy_version_id",
            sa.String(),
            sa.ForeignKey("research_policy_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "risk_policy_version_id",
            sa.String(),
            sa.ForeignKey("risk_policy_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "cost_model_version_id",
            sa.String(),
            sa.ForeignKey("cost_model_versions.id"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    raise RuntimeError("encrypted provider connection migration is irreversible")
