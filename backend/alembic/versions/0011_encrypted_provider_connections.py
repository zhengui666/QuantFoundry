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
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        bind.execute(sa.text("LOCK TABLE setup_bindings IN ACCESS EXCLUSIVE MODE"))
    elif bind.dialect.name == "sqlite":
        if bind.in_transaction():
            # Alembic may have already opened a deferred transaction; a no-op
            # write upgrades it to SQLite's RESERVED lock before the check.
            bind.execute(
                sa.text("UPDATE setup_bindings SET workspace_id = workspace_id WHERE 0")
            )
        else:
            bind.exec_driver_sql("BEGIN IMMEDIATE")
    existing_bindings = bind.execute(
        sa.text("SELECT COUNT(*) FROM setup_bindings")
    ).scalar_one()
    if existing_bindings:
        raise RuntimeError(
            "0011 cannot discard populated setup_bindings; migrate the legacy "
            "metadata bindings through an explicit credential/quarantine flow first"
        )
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
        sa.Column("model_name", sa.String(128), nullable=False),
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
        sa.CheckConstraint(
            "(status = 'VALIDATED' AND consumed_at IS NULL AND expires_at IS NOT NULL) OR "
            "(status = 'ACTIVE' AND consumed_at IS NOT NULL AND expires_at IS NULL) OR "
            "(status = 'REVOKED' AND consumed_at IS NOT NULL AND expires_at IS NULL)",
            name="provider_connection_lifecycle",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "id",
            "kind",
            name="uq_model_provider_connections_workspace_id_id_kind",
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
            nullable=False,
        ),
        sa.Column(
            "ai_connection_id",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "ai_connection_kind", sa.String(8), nullable=False, server_default="AI"
        ),
        sa.Column(
            "data_connection_id",
            sa.String(),
        ),
        sa.Column(
            "data_connection_kind", sa.String(8), nullable=False, server_default="DATA"
        ),
        sa.Column(
            "research_policy_version_id",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "risk_policy_version_id",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "cost_model_version_id",
            sa.String(),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id", "settings_record_id"],
            ["records.workspace_id", "records.id"],
            name="fk_setup_bindings_settings_record_records",
        ),
        sa.CheckConstraint(
            "settings_record_id = 'SETTINGS-DEFAULT'",
            name="setup_bindings_settings_record_key",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "ai_connection_id", "ai_connection_kind"],
            [
                "model_provider_connections.workspace_id",
                "model_provider_connections.id",
                "model_provider_connections.kind",
            ],
            name="fk_setup_bindings_ai_connection_model_provider_connections",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "data_connection_id", "data_connection_kind"],
            [
                "model_provider_connections.workspace_id",
                "model_provider_connections.id",
                "model_provider_connections.kind",
            ],
            name="fk_setup_bindings_data_connection_model_provider_connections",
        ),
        sa.CheckConstraint("ai_connection_kind = 'AI'", name="setup_bindings_ai_kind"),
        sa.CheckConstraint(
            "data_connection_kind = 'DATA'", name="setup_bindings_data_kind"
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "research_policy_version_id"],
            ["research_policy_versions.workspace_id", "research_policy_versions.id"],
            name="fk_setup_bindings_research_policy_versions",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "risk_policy_version_id"],
            ["risk_policy_versions.workspace_id", "risk_policy_versions.id"],
            name="fk_setup_bindings_risk_policy_versions",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "cost_model_version_id"],
            ["cost_model_versions.workspace_id", "cost_model_versions.id"],
            name="fk_setup_bindings_cost_model_versions",
        ),
    )


def downgrade() -> None:
    raise RuntimeError("encrypted provider connection migration is irreversible")
