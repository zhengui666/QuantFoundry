"""P0 durable domain schema; intentionally mirrors app.main.Base metadata.

Revision ID: 0001_p0_core
"""

import sqlalchemy as sa

from alembic import op

revision = "0001_p0_core"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "records",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("kind", sa.String()),
        sa.Column("revision", sa.Integer()),
        sa.Column("body", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_records_kind", "records", ["kind"])
    op.create_table(
        "idempotency_records",
        sa.Column("method", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.Integer()),
        sa.Column("response", sa.Text()),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint(
            "method", "path", "key", name="pk_idempotency_records"
        ),
    )
    op.create_table(
        "domain_events",
        sa.Column(
            "sequence",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            primary_key=True,
            autoincrement=True,
        ),
        # Legacy rows are canonicalized by 0012 before the closed event contract.
        sa.Column("event_id", sa.String(), unique=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("object_type", sa.String(), nullable=False),
        sa.Column("object_id", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer()),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sqlite_autoincrement=True,
    )
    op.create_index("ix_domain_events_expires_at", "domain_events", ["expires_at"])
    op.create_table(
        "users",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
    )
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("owner_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.UniqueConstraint("id", "owner_id", name="uq_workspaces_id_owner_id"),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("object_type", sa.String(), nullable=False),
        sa.Column("object_id", sa.String(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("job_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
    )
    op.create_table(
        "data_sources",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("provider_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
    )
    op.create_table(
        "data_snapshots",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("dataset_id", sa.String(), nullable=False),
        sa.Column("content_sha256", sa.String(64), nullable=False, unique=True),
        sa.Column("immutable", sa.Boolean(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
    )
    op.create_index("ix_data_snapshots_dataset_id", "data_snapshots", ["dataset_id"])
    op.create_table(
        "research_cases",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("workspace_id", sa.String(), sa.ForeignKey("workspaces.id")),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
    )
    op.create_table(
        "experiments",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "research_id",
            sa.String(),
            sa.ForeignKey("research_cases.id"),
            nullable=False,
        ),
        sa.Column("immutable", sa.Boolean(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
    )
    op.create_index("ix_experiments_research_id", "experiments", ["research_id"])
    op.create_table(
        "factors",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "research_id",
            sa.String(),
            sa.ForeignKey("research_cases.id"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
    )
    op.create_index("ix_factors_research_id", "factors", ["research_id"])
    op.create_table(
        "strategies",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "research_id",
            sa.String(),
            sa.ForeignKey("research_cases.id"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
    )
    op.create_index("ix_strategies_research_id", "strategies", ["research_id"])
    op.create_table(
        "strategy_versions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "strategy_id", sa.String(), sa.ForeignKey("strategies.id"), nullable=False
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("spec_sha256", sa.String(64), nullable=False),
        sa.Column("frozen_at", sa.DateTime(timezone=True)),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.UniqueConstraint("strategy_id", "version"),
        sa.CheckConstraint("version >= 1", name="strategy_versions_version_check"),
    )
    op.create_table(
        "validations",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "strategy_version_id",
            sa.String(),
            sa.ForeignKey("strategy_versions.id"),
            nullable=False,
        ),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("holdout_state", sa.String(), nullable=False),
        sa.Column("exposure_count", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "exposure_count >= 0", name="validations_exposure_count_check"
        ),
    )
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("validation_id", sa.String(), sa.ForeignKey("validations.id")),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("subject_sha256", sa.String(64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
    )
    op.create_table(
        "agent_configs",
        sa.Column("role", sa.String(), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("model_provider", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("runtime_profile", sa.String(), nullable=False),
        sa.Column("tool_timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("max_steps_override", sa.Integer()),
        sa.Column("max_tool_calls_override", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "tool_timeout_seconds >= 1",
            name="ck_agent_configs_tool_timeout_seconds_valid",
        ),
        sa.CheckConstraint(
            "max_steps_override IS NULL OR max_steps_override >= 1",
            name="ck_agent_configs_max_steps_override_valid",
        ),
        sa.CheckConstraint(
            "max_tool_calls_override IS NULL OR max_tool_calls_override >= 1",
            name="ck_agent_configs_max_tool_calls_override_valid",
        ),
    )
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "role", sa.String(), sa.ForeignKey("agent_configs.role"), nullable=False
        ),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("checkpoint", sa.Text()),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("agent_version", sa.String(), nullable=False),
        sa.Column("model_provider", sa.String(), nullable=False),
        sa.Column("model_name", sa.String(), nullable=False),
        sa.Column("research_id", sa.String()),
        sa.Column("object_type", sa.String()),
        sa.Column("object_id", sa.String()),
        sa.Column("objective", sa.String(), nullable=False),
        sa.Column("decision_summary", sa.Text()),
        sa.Column("next_action", sa.Text()),
        sa.Column("root_agent_run_id", sa.String(), sa.ForeignKey("agent_runs.id")),
        sa.Column("parent_agent_run_id", sa.String(), sa.ForeignKey("agent_runs.id")),
        sa.Column("context_sha256", sa.String(64), nullable=False),
        sa.Column("model_call_count", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("tool_call_count", sa.Integer(), nullable=False),
        sa.Column("step_count", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "model_call_count >= 0", name="ck_agent_runs_model_call_count_valid"
        ),
        sa.CheckConstraint(
            "input_tokens >= 0", name="ck_agent_runs_input_tokens_valid"
        ),
        sa.CheckConstraint(
            "output_tokens >= 0", name="ck_agent_runs_output_tokens_valid"
        ),
        sa.CheckConstraint(
            "tool_call_count >= 0", name="ck_agent_runs_tool_call_count_valid"
        ),
        sa.CheckConstraint("step_count >= 0", name="ck_agent_runs_step_count_valid"),
    )
    op.create_index(
        "ix_agent_runs_root_agent_run_id", "agent_runs", ["root_agent_run_id"]
    )
    op.create_index(
        "ix_agent_runs_parent_agent_run_id", "agent_runs", ["parent_agent_run_id"]
    )
    op.create_table(
        "tool_calls",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "agent_run_id", sa.String(), sa.ForeignKey("agent_runs.id"), nullable=False
        ),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("tool_version", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("input_sha256", sa.String(64), nullable=False),
        sa.Column("objective", sa.Text()),
        sa.Column("research_id", sa.String(), sa.ForeignKey("research_cases.id")),
        sa.Column("experiment_id", sa.String(), sa.ForeignKey("experiments.id")),
        sa.Column("job_id", sa.String(), sa.ForeignKey("jobs.id")),
        sa.Column("policy_version_ref", sa.String(), nullable=False),
        sa.Column("result_summary", sa.Text()),
        sa.Column("output_artifact_id", sa.String()),
        sa.Column("warnings", sa.Text(), nullable=False),
        sa.Column("provenance", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Integer()),
        sa.CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_tool_calls_duration_ms_valid",
        ),
    )
    op.create_index("ix_tool_calls_agent_run_id", "tool_calls", ["agent_run_id"])
    op.create_index("ix_tool_calls_research_id", "tool_calls", ["research_id"])
    op.create_index("ix_tool_calls_experiment_id", "tool_calls", ["experiment_id"])
    op.create_index("ix_tool_calls_job_id", "tool_calls", ["job_id"])


def downgrade() -> None:
    for name in (
        "tool_calls",
        "agent_runs",
        "agent_configs",
        "approval_requests",
        "validations",
        "strategy_versions",
        "strategies",
        "factors",
        "experiments",
        "research_cases",
        "data_snapshots",
        "data_sources",
        "jobs",
        "audit_events",
        "workspaces",
        "users",
        "domain_events",
        "idempotency_records",
        "records",
    ):
        op.drop_table(name)
