"""Add workspace-owned setup policy/cost aggregates and exact FK bindings.

Revision ID: 0010_setup_reference_bindings
Revises: 0009_workspace_data_sources
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0010_setup_reference_bindings"
down_revision = "0009_workspace_data_sources"
branch_labels = None
depends_on = None


def _version_table(name: str, public_column: str) -> None:
    op.create_table(
        name,
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(),
            sa.ForeignKey("workspaces.id"),
            nullable=False,
        ),
        sa.Column(public_column, sa.String(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("version >= 1", name=f"{name}_version_positive"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'RETIRED')",
            name=f"{name}_status_valid",
        ),
        sa.CheckConstraint(
            "(status = 'DRAFT' AND activated_at IS NULL) OR "
            "(status IN ('ACTIVE', 'RETIRED') AND activated_at IS NOT NULL)",
            name=f"{name}_activation_timestamp_valid",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            public_column,
            "version",
            name=f"uq_{name}_workspace_public",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "id",
            name=f"uq_{name}_workspace_id",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "id",
            "status",
            name=f"uq_{name}_workspace_id_status",
        ),
    )
    op.create_index(f"ix_{name}_workspace_id", name, ["workspace_id"])


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name not in {"postgresql", "sqlite"}:
        raise RuntimeError(
            "0010 setup reference bindings supports PostgreSQL and SQLite only"
        )
    _version_table("research_policy_versions", "policy_id")
    op.add_column(
        "research_policy_versions",
        sa.Column("created_by", sa.String(), nullable=False, server_default="system"),
    )
    _version_table("risk_policy_versions", "policy_id")
    _version_table("cost_model_versions", "cost_model_id")
    for table, public_column in (
        ("research_policy_versions", "policy_id"),
        ("risk_policy_versions", "policy_id"),
        ("cost_model_versions", "cost_model_id"),
    ):
        op.create_index(
            f"uq_{table}_workspace_public_active",
            table,
            ["workspace_id", public_column],
            unique=True,
            postgresql_where=sa.text("status = 'ACTIVE'"),
            sqlite_where=sa.text("status = 'ACTIVE'"),
        )
    op.create_index(
        "uq_records_workspace_id_id",
        "records",
        ["workspace_id", "id"],
        unique=True,
    )
    op.create_index(
        "uq_records_workspace_id_id_kind",
        "records",
        ["workspace_id", "id", "kind"],
        unique=True,
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
            "settings_record_kind",
            sa.String(32),
            nullable=False,
            server_default="settings",
        ),
        sa.Column(
            "ai_connection_record_id",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "ai_connection_record_kind",
            sa.String(32),
            nullable=False,
            server_default="ai_connection",
        ),
        sa.Column(
            "research_policy_version_id",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "research_policy_version_status",
            sa.String(16),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column(
            "risk_policy_version_id",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "risk_policy_version_status",
            sa.String(16),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column(
            "cost_model_version_id",
            sa.String(),
            nullable=False,
        ),
        sa.Column(
            "cost_model_version_status",
            sa.String(16),
            nullable=False,
            server_default="ACTIVE",
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["workspace_id", "settings_record_id", "settings_record_kind"],
            ["records.workspace_id", "records.id", "records.kind"],
            name="fk_setup_bindings_settings_record_records",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "ai_connection_record_id", "ai_connection_record_kind"],
            ["records.workspace_id", "records.id", "records.kind"],
            name="fk_setup_bindings_ai_connection_record_records",
        ),
        sa.CheckConstraint(
            "settings_record_kind = 'settings'",
            name="setup_bindings_settings_exact",
        ),
        sa.CheckConstraint(
            "ai_connection_record_kind = 'ai_connection'",
            name="setup_bindings_ai_connection_kind",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "research_policy_version_id", "research_policy_version_status"],
            ["research_policy_versions.workspace_id", "research_policy_versions.id", "research_policy_versions.status"],
            name="fk_setup_bindings_research_policy_versions",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "risk_policy_version_id", "risk_policy_version_status"],
            ["risk_policy_versions.workspace_id", "risk_policy_versions.id", "risk_policy_versions.status"],
            name="fk_setup_bindings_risk_policy_versions",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "cost_model_version_id", "cost_model_version_status"],
            ["cost_model_versions.workspace_id", "cost_model_versions.id", "cost_model_versions.status"],
            name="fk_setup_bindings_cost_model_versions",
        ),
        sa.CheckConstraint(
            "research_policy_version_status = 'ACTIVE'",
            name="setup_bindings_research_policy_active",
        ),
        sa.CheckConstraint(
            "risk_policy_version_status = 'ACTIVE'",
            name="setup_bindings_risk_policy_active",
        ),
        sa.CheckConstraint(
            "cost_model_version_status = 'ACTIVE'",
            name="setup_bindings_cost_model_active",
        ),
    )


def downgrade() -> None:
    raise RuntimeError("setup reference bindings are irreversible")
