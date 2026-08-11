"""Durable jobs, immutable evidence and runtime health state.

Revision ID: 0003_runtime_integrity
Revises: 0002_session_tokens
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003_runtime_integrity"
down_revision = "0002_session_tokens"
branch_labels = None
depends_on = None


JOB_COLUMNS = (
    sa.Column("input_payload", sa.Text(), nullable=False, server_default="{}"),
    sa.Column("payload_sha256", sa.String(64), nullable=False, server_default="0" * 64),
    sa.Column("queue_name", sa.String(), nullable=False, server_default="core"),
    sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
    sa.Column("result_ref", sa.Text()),
    sa.Column("error_code", sa.String()),
    sa.Column("error_detail", sa.Text()),
    sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
    sa.Column("lease_owner", sa.String()),
    sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
    sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
    sa.Column("cancel_requested_at", sa.DateTime(timezone=True)),
    sa.Column("fencing_token", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("retry_safe", sa.Boolean(), nullable=False, server_default=sa.true()),
    sa.Column("progress_mode", sa.String(), nullable=False, server_default="NONE"),
    sa.Column("completed_units", sa.Integer()),
    sa.Column("total_units", sa.Integer()),
    sa.Column("progress_unit", sa.String()),
    sa.Column("current_step_key", sa.String()),
    sa.Column("current_step_label", sa.String()),
    sa.Column(
        "queued_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    ),
    sa.Column("started_at", sa.DateTime(timezone=True)),
    sa.Column("finished_at", sa.DateTime(timezone=True)),
    sa.Column("created_by_type", sa.String(), nullable=False, server_default="USER"),
    sa.Column("created_by_id", sa.String(), nullable=False, server_default="system"),
    sa.Column("correlation_id", sa.String()),
)

EVENT_COLUMNS = (
    sa.Column("request_id", sa.String()),
    sa.Column("correlation_id", sa.String()),
    sa.Column("causation_id", sa.String()),
    sa.Column("job_id", sa.String()),
    sa.Column("agent_run_id", sa.String()),
    sa.Column("tool_call_id", sa.String()),
)

APPROVAL_COLUMNS = (
    sa.Column("subject_type", sa.String(), nullable=False, server_default="validation"),
    sa.Column("subject_id", sa.String(), nullable=False, server_default=""),
    sa.Column("subject_version", sa.Integer()),
    sa.Column("subject_revision", sa.Integer(), nullable=False, server_default="1"),
    sa.Column(
        "subject_spec_sha256", sa.String(64), nullable=False, server_default="0" * 64
    ),
    sa.Column(
        "prerequisites_sha256", sa.String(64), nullable=False, server_default="0" * 64
    ),
)


def _create_immutability_guards() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE FUNCTION qf_reject_change() RETURNS trigger AS $$
            BEGIN
              RAISE EXCEPTION 'immutable evidence cannot be changed';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        for table in (
            "audit_events",
            "holdout_exposures",
            "data_snapshots",
            "snapshot_partitions",
        ):
            op.execute(
                f"CREATE TRIGGER qf_{table}_immutable BEFORE UPDATE OR DELETE ON {table} "
                "FOR EACH ROW EXECUTE FUNCTION qf_reject_change()"
            )
        op.execute(
            "CREATE TRIGGER qf_domain_events_update_immutable BEFORE UPDATE ON domain_events "
            "FOR EACH ROW EXECUTE FUNCTION qf_reject_change()"
        )
        op.execute(
            """
            CREATE FUNCTION qf_reject_unexpired_event_delete() RETURNS trigger AS $$
            BEGIN
              IF OLD.expires_at > now() THEN
                RAISE EXCEPTION 'unexpired event cannot be deleted';
              END IF;
              RETURN OLD;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            "CREATE TRIGGER qf_domain_events_delete_immutable BEFORE DELETE ON domain_events "
            "FOR EACH ROW EXECUTE FUNCTION qf_reject_unexpired_event_delete()"
        )
        op.execute(
            """
            CREATE FUNCTION qf_reject_frozen_strategy_change() RETURNS trigger AS $$
            BEGIN
              IF OLD.state = 'FROZEN' THEN
                RAISE EXCEPTION 'frozen strategy version cannot be changed';
              END IF;
              IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            "CREATE TRIGGER qf_strategy_versions_immutable BEFORE UPDATE OR DELETE "
            "ON strategy_versions FOR EACH ROW EXECUTE FUNCTION qf_reject_frozen_strategy_change()"
        )
        op.execute(
            """
            CREATE FUNCTION qf_reject_completed_experiment_change() RETURNS trigger AS $$
            BEGIN
              IF OLD.immutable THEN
                RAISE EXCEPTION 'completed experiment cannot be changed';
              END IF;
              IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            "CREATE TRIGGER qf_experiments_immutable BEFORE UPDATE OR DELETE ON experiments "
            "FOR EACH ROW EXECUTE FUNCTION qf_reject_completed_experiment_change()"
        )
        op.execute(
            """
            CREATE FUNCTION qf_reject_terminal_approval_change() RETURNS trigger AS $$
            BEGIN
              IF OLD.status <> 'PENDING' THEN
                RAISE EXCEPTION 'terminal approval cannot be changed';
              END IF;
              IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            "CREATE TRIGGER qf_approval_requests_immutable BEFORE UPDATE OR DELETE "
            "ON approval_requests FOR EACH ROW EXECUTE FUNCTION qf_reject_terminal_approval_change()"
        )
        return

    for table in (
        "audit_events",
        "holdout_exposures",
        "data_snapshots",
        "snapshot_partitions",
    ):
        for action in ("UPDATE", "DELETE"):
            op.execute(
                f"CREATE TRIGGER qf_{table}_{action.lower()}_immutable BEFORE {action} ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'immutable evidence cannot be changed'); END"
            )
    op.execute(
        "CREATE TRIGGER qf_domain_events_update_immutable BEFORE UPDATE ON domain_events "
        "BEGIN SELECT RAISE(ABORT, 'immutable evidence cannot be changed'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_domain_events_delete_immutable BEFORE DELETE ON domain_events "
        "WHEN OLD.expires_at > CURRENT_TIMESTAMP BEGIN "
        "SELECT RAISE(ABORT, 'unexpired event cannot be deleted'); END"
    )
    for action in ("UPDATE", "DELETE"):
        op.execute(
            f"CREATE TRIGGER qf_strategy_versions_{action.lower()}_immutable BEFORE {action} "
            "ON strategy_versions WHEN OLD.state = 'FROZEN' BEGIN "
            "SELECT RAISE(ABORT, 'frozen strategy version cannot be changed'); END"
        )
        op.execute(
            f"CREATE TRIGGER qf_experiments_{action.lower()}_immutable BEFORE {action} "
            "ON experiments WHEN OLD.immutable = 1 BEGIN "
            "SELECT RAISE(ABORT, 'completed experiment cannot be changed'); END"
        )
        op.execute(
            f"CREATE TRIGGER qf_approval_requests_{action.lower()}_immutable BEFORE {action} "
            "ON approval_requests WHEN OLD.status != 'PENDING' BEGIN "
            "SELECT RAISE(ABORT, 'terminal approval cannot be changed'); END"
        )


def upgrade() -> None:
    for column in JOB_COLUMNS:
        op.add_column("jobs", column)
    for column in EVENT_COLUMNS:
        op.add_column("domain_events", column)
    op.add_column("audit_events", sa.Column("previous_sha256", sa.String(64)))
    op.add_column(
        "audit_events",
        sa.Column(
            "event_sha256", sa.String(64), nullable=False, server_default="0" * 64
        ),
    )
    for column in APPROVAL_COLUMNS:
        op.add_column("approval_requests", column)
    op.add_column(
        "tool_calls",
        sa.Column("semantic_scope", sa.String(), nullable=False, server_default=""),
    )
    op.create_index(
        "uq_tool_calls_active_semantic",
        "tool_calls",
        ["semantic_scope", "tool_name", "input_sha256"],
        unique=True,
        postgresql_where=sa.text("status IN ('RUNNING', 'SUCCESS')"),
        sqlite_where=sa.text("status IN ('RUNNING', 'SUCCESS')"),
    )

    op.create_index("ix_jobs_lease_expires_at", "jobs", ["lease_expires_at"])
    op.create_index("ix_jobs_correlation_id", "jobs", ["correlation_id"])
    op.create_index(
        "ix_jobs_claim",
        "jobs",
        ["queue_name", "status", "priority", "queued_at"],
    )
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.create_check_constraint("jobs_priority_check", "priority >= 0")
        batch_op.create_check_constraint("jobs_attempt_check", "attempt >= 0")
        batch_op.create_check_constraint("jobs_max_attempts_check", "max_attempts >= 1")
        batch_op.create_check_constraint(
            "jobs_fencing_token_check", "fencing_token >= 0"
        )
        batch_op.create_check_constraint(
            "jobs_completed_units_check",
            "completed_units IS NULL OR completed_units >= 0",
        )
        batch_op.create_check_constraint(
            "jobs_total_units_check", "total_units IS NULL OR total_units >= 0"
        )
    for name in ("correlation_id", "job_id", "agent_run_id", "tool_call_id"):
        op.create_index(f"ix_domain_events_{name}", "domain_events", [name])

    op.create_table(
        "holdout_exposures",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "validation_id",
            sa.String(),
            sa.ForeignKey("validations.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "strategy_version_id",
            sa.String(),
            sa.ForeignKey("strategy_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "approval_id",
            sa.String(),
            sa.ForeignKey("approval_requests.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "job_id", sa.String(), sa.ForeignKey("jobs.id"), nullable=False, unique=True
        ),
        sa.Column("result_artifact_id", sa.String(), nullable=False),
        sa.Column("provenance_id", sa.String(), nullable=False),
        sa.Column("result_sha256", sa.String(64), nullable=False),
        sa.Column("period", sa.Text(), nullable=False),
        sa.Column("result", sa.Text(), nullable=False),
        sa.Column("exposed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "contamination", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.create_table(
        "runtime_heartbeats",
        sa.Column("component", sa.String(), primary_key=True),
        sa.Column("instance_id", sa.String(), primary_key=True),
        sa.Column("queue_name", sa.String()),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_runtime_heartbeats_occurred_at", "runtime_heartbeats", ["occurred_at"]
    )
    op.create_table(
        "snapshot_partitions",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "snapshot_id",
            sa.String(),
            sa.ForeignKey("data_snapshots.id"),
            nullable=False,
        ),
        sa.Column("partition", sa.String(), nullable=False),
        sa.Column("artifact_id", sa.String(), nullable=False, unique=True),
        sa.Column("content_sha256", sa.String(64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("snapshot_id", "partition"),
        sa.CheckConstraint(
            "row_count >= 0", name="snapshot_partitions_row_count_check"
        ),
    )
    op.create_index(
        "ix_snapshot_partitions_snapshot_id", "snapshot_partitions", ["snapshot_id"]
    )
    _create_immutability_guards()


def _drop_immutability_guards() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in (
            "audit_events",
            "holdout_exposures",
            "data_snapshots",
            "snapshot_partitions",
        ):
            op.execute(f"DROP TRIGGER qf_{table}_immutable ON {table}")
        op.execute("DROP TRIGGER qf_domain_events_update_immutable ON domain_events")
        op.execute("DROP TRIGGER qf_domain_events_delete_immutable ON domain_events")
        op.execute("DROP TRIGGER qf_strategy_versions_immutable ON strategy_versions")
        op.execute("DROP TRIGGER qf_experiments_immutable ON experiments")
        op.execute("DROP TRIGGER qf_approval_requests_immutable ON approval_requests")
        op.execute("DROP FUNCTION qf_reject_change()")
        op.execute("DROP FUNCTION qf_reject_frozen_strategy_change()")
        op.execute("DROP FUNCTION qf_reject_completed_experiment_change()")
        op.execute("DROP FUNCTION qf_reject_unexpired_event_delete()")
        op.execute("DROP FUNCTION qf_reject_terminal_approval_change()")
        return
    for table in (
        "audit_events",
        "holdout_exposures",
        "data_snapshots",
        "snapshot_partitions",
    ):
        for action in ("update", "delete"):
            op.execute(f"DROP TRIGGER qf_{table}_{action}_immutable")
    op.execute("DROP TRIGGER qf_domain_events_update_immutable")
    op.execute("DROP TRIGGER qf_domain_events_delete_immutable")
    for table in ("strategy_versions", "experiments", "approval_requests"):
        for action in ("update", "delete"):
            op.execute(f"DROP TRIGGER qf_{table}_{action}_immutable")


def downgrade() -> None:
    _drop_immutability_guards()
    op.drop_index(
        "ix_snapshot_partitions_snapshot_id", table_name="snapshot_partitions"
    )
    op.drop_table("snapshot_partitions")
    op.drop_table("runtime_heartbeats")
    op.drop_table("holdout_exposures")
    op.drop_index("uq_tool_calls_active_semantic", table_name="tool_calls")
    op.drop_column("tool_calls", "semantic_scope")
    for name in ("tool_call_id", "agent_run_id", "job_id", "correlation_id"):
        op.drop_index(f"ix_domain_events_{name}", table_name="domain_events")
    op.drop_index("ix_jobs_claim", table_name="jobs")
    with op.batch_alter_table("jobs") as batch_op:
        batch_op.drop_constraint("jobs_total_units_check", type_="check")
        batch_op.drop_constraint("jobs_completed_units_check", type_="check")
        batch_op.drop_constraint("jobs_fencing_token_check", type_="check")
        batch_op.drop_constraint("jobs_max_attempts_check", type_="check")
        batch_op.drop_constraint("jobs_attempt_check", type_="check")
        batch_op.drop_constraint("jobs_priority_check", type_="check")
    op.drop_index("ix_jobs_correlation_id", table_name="jobs")
    op.drop_index("ix_jobs_lease_expires_at", table_name="jobs")
    for column in reversed(APPROVAL_COLUMNS):
        op.drop_column("approval_requests", column.name)
    op.drop_column("audit_events", "event_sha256")
    op.drop_column("audit_events", "previous_sha256")
    for column in reversed(EVENT_COLUMNS):
        op.drop_column("domain_events", column.name)
    for column in reversed(JOB_COLUMNS):
        op.drop_column("jobs", column.name)
