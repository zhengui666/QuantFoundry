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
        sa.UniqueConstraint(
            "workspace_id",
            public_column,
            name=f"uq_{name}_workspace_public",
        ),
    )
    op.create_index(f"ix_{name}_workspace_id", name, ["workspace_id"])


def upgrade() -> None:
    _version_table("research_policy_versions", "policy_id")
    op.add_column(
        "research_policy_versions",
        sa.Column("created_by", sa.String(), nullable=False, server_default="system"),
    )
    _version_table("risk_policy_versions", "policy_id")
    _version_table("cost_model_versions", "cost_model_id")
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
            "ai_connection_record_id",
            sa.String(),
            sa.ForeignKey("records.id"),
            nullable=False,
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
    raise RuntimeError("setup reference bindings are irreversible")
