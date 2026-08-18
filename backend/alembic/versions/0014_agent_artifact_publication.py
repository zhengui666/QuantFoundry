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


def _install_experiment_completion_binding() -> None:
    if op.get_bind().dialect.name != "sqlite":
        return
    op.execute(
        "CREATE TRIGGER qf_experiments_complete_binding BEFORE UPDATE ON "
        "experiments WHEN OLD.immutable = 0 AND NEW.immutable = 1 AND NOT ("
        "NEW.id IS OLD.id AND NEW.research_id IS OLD.research_id AND "
        "NEW.source_experiment_id IS OLD.source_experiment_id AND "
        "NEW.revision = OLD.revision + 1 AND "
        "json_remove(NEW.detail, '$.status', '$.validity_state', '$.adapter', "
        "'$.provenance', '$.metrics', '$.artifacts', '$.search_space', "
        "'$.search_configuration', '$.search_result', '$.action_capabilities', "
        "'$.started_at', '$.finished_at') IS json_remove(OLD.detail, '$.status', "
        "'$.validity_state', '$.adapter', '$.provenance', '$.metrics', '$.artifacts', "
        "'$.search_space', '$.search_configuration', '$.search_result', "
        "'$.action_capabilities', '$.started_at', '$.finished_at') AND "
        "COALESCE(json_extract(NEW.detail, '$.status'), '') = 'COMPLETED' AND "
        "EXISTS (SELECT 1 FROM jobs j WHERE j.id = json_extract(NEW.detail, '$.job_id') "
        "AND j.job_type = 'EXPERIMENT' AND j.status IN ('RUNNING', 'COMPLETED') "
        "AND json_extract(j.input_payload, '$.experiment_id') = NEW.id)) "
        "BEGIN SELECT RAISE(ABORT, 'experiment completion is not bound to a running job'); END"
    )


def _install_artifact_immutability_guards() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            """
            CREATE FUNCTION qf_reject_published_artifact_change() RETURNS trigger AS $$
            BEGIN
              IF TG_OP = 'DELETE' OR OLD.publication_state <> 'STAGED' THEN
                RAISE EXCEPTION 'published artifact is immutable';
              END IF;
              IF NEW.id IS DISTINCT FROM OLD.id
                 OR NEW.artifact_id IS DISTINCT FROM OLD.artifact_id
                 OR NEW.workspace_id IS DISTINCT FROM OLD.workspace_id
                 OR NEW.job_id IS DISTINCT FROM OLD.job_id
                 OR NEW.kind IS DISTINCT FROM OLD.kind
                 OR NEW.media_type IS DISTINCT FROM OLD.media_type
                 OR NEW.storage_backend IS DISTINCT FROM OLD.storage_backend
                 OR NEW.storage_key IS DISTINCT FROM OLD.storage_key
                 OR NEW.size_bytes IS DISTINCT FROM OLD.size_bytes
                 OR NEW.sha256 IS DISTINCT FROM OLD.sha256
                 OR NEW.schema_name IS DISTINCT FROM OLD.schema_name
                 OR NEW.schema_version IS DISTINCT FROM OLD.schema_version
                 OR NEW.compression IS DISTINCT FROM OLD.compression
                 OR NEW.metadata IS DISTINCT FROM OLD.metadata
                 OR NEW.created_at IS DISTINCT FROM OLD.created_at
                 OR NEW.immutable IS DISTINCT FROM OLD.immutable
                 OR NEW.publication_state NOT IN ('PUBLISHED', 'FAILED') THEN
                RAISE EXCEPTION 'artifact metadata is immutable';
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            "CREATE TRIGGER qf_artifacts_immutable BEFORE UPDATE OR DELETE ON artifacts "
            "FOR EACH ROW EXECUTE FUNCTION qf_reject_published_artifact_change()"
        )
        return
    if dialect == "sqlite":
        op.execute(
            "CREATE TRIGGER qf_artifacts_immutable BEFORE UPDATE ON artifacts WHEN "
            "OLD.publication_state != 'STAGED' OR NEW.id IS NOT OLD.id OR "
            "NEW.artifact_id IS NOT OLD.artifact_id OR NEW.workspace_id IS NOT OLD.workspace_id OR "
            "NEW.job_id IS NOT OLD.job_id OR NEW.kind IS NOT OLD.kind OR "
            "NEW.media_type IS NOT OLD.media_type OR NEW.storage_backend IS NOT OLD.storage_backend OR "
            "NEW.storage_key IS NOT OLD.storage_key OR NEW.size_bytes IS NOT OLD.size_bytes OR "
            "NEW.sha256 IS NOT OLD.sha256 OR NEW.schema_name IS NOT OLD.schema_name OR "
            "NEW.schema_version IS NOT OLD.schema_version OR NEW.compression IS NOT OLD.compression OR "
            "NEW.metadata IS NOT OLD.metadata OR NEW.created_at IS NOT OLD.created_at OR "
            "NEW.immutable IS NOT OLD.immutable OR NEW.publication_state NOT IN ('PUBLISHED', 'FAILED') "
            "BEGIN SELECT RAISE(ABORT, 'artifact metadata is immutable'); END"
        )
        op.execute(
            "CREATE TRIGGER qf_artifacts_delete_immutable BEFORE DELETE ON artifacts "
            "BEGIN SELECT RAISE(ABORT, 'artifact is immutable'); END"
        )
        return
    raise RuntimeError(f"0014 artifact guards do not support dialect {dialect}")


def _drop_artifact_immutability_guards() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS qf_artifacts_immutable ON artifacts")
        op.execute("DROP FUNCTION IF EXISTS qf_reject_published_artifact_change()")
    elif dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS qf_artifacts_immutable")
        op.execute("DROP TRIGGER IF EXISTS qf_artifacts_delete_immutable")


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name
    if dialect == "sqlite":
        # SQLite rebuilds jobs for the NOT NULL backfill; a trigger on
        # experiments that references jobs makes the temporary-table rename
        # fail while jobs is absent.
        op.execute("DROP TRIGGER IF EXISTS qf_experiments_complete_binding")
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
    _install_artifact_immutability_guards()
    _install_experiment_completion_binding()


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS qf_experiments_complete_binding")
    _drop_artifact_immutability_guards()
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
    if bind.dialect.name == "postgresql":
        owns_marker = bool(
            bind.execute(
                sa.text(
                    "SELECT to_regclass('agent_checkpoint._qf_owned_0014') IS NOT NULL"
                )
            ).scalar_one()
        )
        if owns_marker:
            table_count = bind.execute(
                sa.text(
                    "SELECT count(*) FROM pg_class c "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'agent_checkpoint' AND c.relkind IN ('r', 'p') "
                    "AND c.relname <> '_qf_owned_0014'"
                )
            ).scalar_one()
            if table_count == 0:
                op.execute("DROP TABLE agent_checkpoint._qf_owned_0014")
                op.execute("DROP SCHEMA agent_checkpoint")
    elif bind.dialect.name == "sqlite":
        _install_experiment_completion_binding()
