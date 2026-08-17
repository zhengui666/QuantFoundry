"""Durable Agent dependencies and two-phase artifact publication.

Revision ID: 0014_agent_artifacts
Revises: 0013_metadata_alignment
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0014_agent_artifacts"
down_revision = "0013_metadata_alignment"
branch_labels = None
depends_on = None


def _json_type() -> sa.TypeEngine[object]:
    if op.get_bind().dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    owns_checkpoint_schema = False
    if dialect == "postgresql":
        owns_checkpoint_schema = not bool(
            bind.execute(
                sa.text("SELECT to_regnamespace('agent_checkpoint') IS NOT NULL")
            ).scalar_one()
        )
        op.execute("CREATE SCHEMA IF NOT EXISTS agent_checkpoint")
        if owns_checkpoint_schema:
            op.execute("CREATE TABLE agent_checkpoint._qf_owned_0014 (marker integer)")
    op.add_column(
        "jobs",
        sa.Column(
            "internal_id",
            sa.Uuid(),
            nullable=dialect == "sqlite",
            server_default=sa.text("gen_random_uuid()")
            if dialect == "postgresql"
            else None,
        ),
    )
    if dialect == "sqlite":
        for job_id in bind.execute(sa.text("SELECT id FROM jobs")).scalars():
            bind.execute(
                sa.text("UPDATE jobs SET internal_id = :internal_id WHERE id = :id"),
                {"id": job_id, "internal_id": uuid.uuid4().hex},
            )
        with op.batch_alter_table("jobs") as batch:
            batch.alter_column("internal_id", nullable=False)
    op.create_index("uq_jobs_internal_id", "jobs", ["internal_id"], unique=True)
    op.add_column("jobs", sa.Column("resume_token_hash", sa.String(64)))
    op.create_index(
        "uq_jobs_resume_token_hash", "jobs", ["resume_token_hash"], unique=True
    )
    op.add_column("jobs", sa.Column("resume_fencing_token", sa.Integer()))

    op.create_table(
        "job_dependencies",
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id"), primary_key=True),
        sa.Column(
            "depends_on_job_id",
            sa.String(),
            sa.ForeignKey("jobs.id"),
            primary_key=True,
        ),
        sa.Column(
            "dependency_type",
            sa.String(16),
            nullable=False,
            server_default="SUCCESS",
        ),
        sa.CheckConstraint(
            "dependency_type IN ('SUCCESS', 'TERMINAL')",
            name="job_dependencies_dependency_type_check",
        ),
        sa.CheckConstraint(
            "job_id != depends_on_job_id",
            name="job_dependencies_not_self_check",
        ),
    )
    op.create_index(
        "ix_job_dependencies_depends_on_job_id",
        "job_dependencies",
        ["depends_on_job_id"],
    )

    op.add_column("agent_runs", sa.Column("checkpoint_thread_id", sa.String(128)))
    op.create_index(
        "uq_agent_runs_checkpoint_thread_id",
        "agent_runs",
        ["checkpoint_thread_id"],
        unique=True,
    )
    op.add_column("agent_runs", sa.Column("pending_resume_token_hash", sa.String(64)))
    op.add_column(
        "agent_runs",
        sa.Column(
            "resume_fencing_token",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "tool_calls",
        sa.Column("input_payload", sa.Text(), nullable=False, server_default="{}"),
    )

    op.create_table(
        "artifacts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("artifact_id", sa.String(48), nullable=False, unique=True),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("media_type", sa.String(128), nullable=False),
        sa.Column(
            "storage_backend",
            sa.String(16),
            nullable=False,
            server_default="LOCAL",
        ),
        sa.Column("storage_key", sa.Text(), nullable=False, unique=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("schema_name", sa.String(96)),
        sa.Column("schema_version", sa.Integer()),
        sa.Column("compression", sa.String(16)),
        sa.Column("metadata", _json_type(), nullable=False),
        sa.Column(
            "publication_state",
            sa.String(16),
            nullable=False,
            server_default="STAGED",
        ),
        sa.Column("publication_error", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("immutable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint("size_bytes >= 0", name="artifacts_size_bytes_check"),
        sa.CheckConstraint(
            "storage_backend IN ('LOCAL', 'S3')",
            name="artifacts_storage_backend_check",
        ),
        sa.CheckConstraint(
            "publication_state IN ('STAGED', 'PUBLISHED', 'FAILED')",
            name="artifacts_publication_state_check",
        ),
        sa.CheckConstraint(
            "(publication_state = 'STAGED' AND published_at IS NULL AND "
            "publication_error IS NULL) OR "
            "(publication_state = 'PUBLISHED' AND published_at IS NOT NULL AND "
            "publication_error IS NULL) OR "
            "(publication_state = 'FAILED' AND published_at IS NULL AND "
            "publication_error IS NOT NULL)",
            name="artifacts_publication_lifecycle_check",
        ),
    )
    op.create_index("ix_artifacts_workspace_id", "artifacts", ["workspace_id"])
    op.create_index("ix_artifacts_job_id", "artifacts", ["job_id"])
    op.create_index("ix_artifacts_kind", "artifacts", ["kind"])
    op.create_index("ix_artifacts_sha256", "artifacts", ["sha256"])
    op.create_index(
        "ix_artifacts_publication_state", "artifacts", ["publication_state"]
    )


def downgrade() -> None:
    op.drop_table("artifacts")
    op.drop_column("tool_calls", "input_payload")
    op.drop_index("uq_agent_runs_checkpoint_thread_id", table_name="agent_runs")
    op.drop_column("agent_runs", "resume_fencing_token")
    op.drop_column("agent_runs", "pending_resume_token_hash")
    op.drop_column("agent_runs", "checkpoint_thread_id")
    op.drop_table("job_dependencies")
    op.drop_index("uq_jobs_resume_token_hash", table_name="jobs")
    op.drop_column("jobs", "resume_fencing_token")
    op.drop_column("jobs", "resume_token_hash")
    op.drop_index("uq_jobs_internal_id", table_name="jobs")
    op.drop_column("jobs", "internal_id")
    # A collidable marker cannot prove ownership of a pre-existing checkpoint
    # schema. Leave it untouched on rollback rather than deleting user data.
