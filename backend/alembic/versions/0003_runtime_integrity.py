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
    sa.Column("input_payload", sa.Text(), nullable=False),
    sa.Column("payload_sha256", sa.String(64), nullable=False),
    sa.Column("queue_name", sa.String(), nullable=False),
    sa.Column("priority", sa.Integer(), nullable=False),
    sa.Column("result_ref", sa.Text()),
    sa.Column("error_code", sa.String()),
    sa.Column("error_detail", sa.Text()),
    sa.Column("attempt", sa.Integer(), nullable=False),
    sa.Column("max_attempts", sa.Integer(), nullable=False),
    sa.Column("lease_owner", sa.String()),
    sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
    sa.Column("heartbeat_at", sa.DateTime(timezone=True)),
    sa.Column("cancel_requested_at", sa.DateTime(timezone=True)),
    sa.Column("fencing_token", sa.Integer(), nullable=False),
    sa.Column("retry_safe", sa.Boolean(), nullable=False),
    sa.Column("progress_mode", sa.String(), nullable=False),
    sa.Column("completed_units", sa.Integer()),
    sa.Column("total_units", sa.Integer()),
    sa.Column("progress_unit", sa.String()),
    sa.Column("current_step_key", sa.String()),
    sa.Column("current_step_label", sa.String()),
    sa.Column(
        "queued_at",
        sa.DateTime(timezone=True),
        nullable=False,
    ),
    sa.Column("started_at", sa.DateTime(timezone=True)),
    sa.Column("finished_at", sa.DateTime(timezone=True)),
    sa.Column("created_by_type", sa.String(), nullable=False),
    sa.Column("created_by_id", sa.String(), nullable=False),
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
    sa.Column("subject_type", sa.String(), nullable=False),
    sa.Column("subject_id", sa.String(), nullable=False),
    sa.Column("subject_version", sa.Integer()),
    sa.Column("subject_revision", sa.Integer(), nullable=False),
    sa.Column("subject_spec_sha256", sa.String(64), nullable=False),
    sa.Column("prerequisites_sha256", sa.String(64), nullable=False),
)


def _add_columns(table: str, columns: tuple[sa.Column, ...]) -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table(table, recreate="always") as batch_op:
            for column in columns:
                batch_op.add_column(column)
        return
    for column in columns:
        op.add_column(table, column)


def _assert_integrity_backfill_is_mappable() -> None:
    bind = op.get_bind()
    tables = (
        "jobs",
        "domain_events",
        "audit_events",
        "approval_requests",
        "tool_calls",
    )
    counts = {
        table: int(bind.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar_one())
        for table in tables
    }
    null_events = int(
        bind.execute(
            sa.text("SELECT COUNT(*) FROM domain_events WHERE expires_at IS NULL")
        ).scalar_one()
    )
    if any(counts.values()) or null_events:
        detail = ", ".join(f"{table}={count}" for table, count in counts.items())
        raise RuntimeError(
            "0003 refuses to synthesize integrity evidence; manual backfill required "
            f"({detail}, domain_events.expires_at_null={null_events})"
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
              IF TG_OP = 'UPDATE' AND OLD.state = 'CANDIDATE' AND NEW.state = 'FROZEN'
                 AND (
                   NEW.strategy_id IS DISTINCT FROM OLD.strategy_id OR
                   NEW.version IS DISTINCT FROM OLD.version OR
                   NEW.spec_sha256 IS DISTINCT FROM OLD.spec_sha256 OR
                   NEW.detail IS DISTINCT FROM OLD.detail
                 ) THEN
                RAISE EXCEPTION 'strategy evidence cannot change while freezing';
              END IF;
              IF TG_OP = 'UPDATE' AND OLD.state = 'CANDIDATE' AND NEW.state = 'CANDIDATE'
                 AND (
                   NEW.strategy_id IS DISTINCT FROM OLD.strategy_id OR
                   NEW.version IS DISTINCT FROM OLD.version OR
                   NEW.spec_sha256 IS DISTINCT FROM OLD.spec_sha256 OR
                   NEW.detail IS DISTINCT FROM OLD.detail
                 ) THEN
                RAISE EXCEPTION 'candidate strategy evidence must be append-only';
              END IF;
              IF TG_OP = 'UPDATE' AND NOT (
                   NEW.state = OLD.state OR
                   (OLD.state = 'CANDIDATE' AND NEW.state = 'FROZEN') OR
                   (OLD.state = 'FROZEN' AND NEW.state = 'VALIDATING') OR
                   (OLD.state = 'VALIDATING' AND NEW.state IN ('VALIDATED', 'REJECTED')) OR
                   (OLD.state = 'VALIDATED' AND NEW.state IN ('PAPER', 'RETIRED')) OR
                   (OLD.state = 'PAPER' AND NEW.state = 'RETIRED')
              ) THEN
                RAISE EXCEPTION 'illegal strategy lifecycle transition';
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
              IF TG_OP = 'UPDATE' AND NOT OLD.immutable AND NOT NEW.immutable
                 AND (
                   NEW.research_id IS DISTINCT FROM OLD.research_id OR
                   NEW.detail IS DISTINCT FROM OLD.detail OR
                   NEW.revision IS DISTINCT FROM OLD.revision
                 ) THEN
                RAISE EXCEPTION 'experiment evidence cannot change while completing';
              END IF;
              IF TG_OP = 'UPDATE' AND NOT OLD.immutable AND NEW.immutable
                 AND NOT (
                   NEW.research_id IS NOT DISTINCT FROM OLD.research_id AND
                   NEW.revision = OLD.revision + 1 AND
                   (NEW.detail::jsonb ->> 'status') = 'COMPLETED'
                 ) THEN
                RAISE EXCEPTION 'experiment completion is not bound to a running job';
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
              IF TG_OP = 'UPDATE' AND NEW.status <> 'PENDING'
                 AND (
                   NEW.validation_id IS DISTINCT FROM OLD.validation_id OR
                   NEW.subject_sha256 IS DISTINCT FROM OLD.subject_sha256 OR
                   NEW.subject_type IS DISTINCT FROM OLD.subject_type OR
                   NEW.subject_id IS DISTINCT FROM OLD.subject_id OR
                   NEW.subject_version IS DISTINCT FROM OLD.subject_version OR
                   NEW.subject_revision IS DISTINCT FROM OLD.subject_revision OR
                   NEW.subject_spec_sha256 IS DISTINCT FROM OLD.subject_spec_sha256 OR
                   NEW.prerequisites_sha256 IS DISTINCT FROM OLD.prerequisites_sha256
                 ) THEN
                RAISE EXCEPTION 'approval evidence cannot change while resolving';
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
        op.execute(
            """
            CREATE FUNCTION qf_reject_pending_approval_evidence_change() RETURNS trigger AS $$
            BEGIN
              IF TG_OP = 'UPDATE' AND (
                NEW.validation_id IS DISTINCT FROM OLD.validation_id OR
                NEW.subject_sha256 IS DISTINCT FROM OLD.subject_sha256 OR
                NEW.subject_type IS DISTINCT FROM OLD.subject_type OR
                NEW.subject_id IS DISTINCT FROM OLD.subject_id OR
                NEW.subject_version IS DISTINCT FROM OLD.subject_version OR
                NEW.subject_revision IS DISTINCT FROM OLD.subject_revision OR
                NEW.subject_spec_sha256 IS DISTINCT FROM OLD.subject_spec_sha256 OR
                NEW.prerequisites_sha256 IS DISTINCT FROM OLD.prerequisites_sha256
              ) THEN
                RAISE EXCEPTION 'approval evidence cannot be changed';
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            "CREATE TRIGGER qf_approval_requests_pending_evidence_immutable BEFORE UPDATE "
            "ON approval_requests FOR EACH ROW EXECUTE FUNCTION qf_reject_pending_approval_evidence_change()"
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
    op.execute(
        "CREATE TRIGGER qf_strategy_versions_freeze_immutable BEFORE UPDATE "
        "ON strategy_versions WHEN OLD.state = 'CANDIDATE' AND NEW.state = 'FROZEN' AND ("
        "NEW.strategy_id IS NOT OLD.strategy_id OR NEW.version IS NOT OLD.version OR "
        "NEW.spec_sha256 IS NOT OLD.spec_sha256 OR NEW.detail IS NOT OLD.detail) OR NOT ("
        "NEW.state = OLD.state OR (OLD.state = 'CANDIDATE' AND NEW.state = 'FROZEN') OR "
        "(OLD.state = 'FROZEN' AND NEW.state = 'VALIDATING') OR "
        "(OLD.state = 'VALIDATING' AND NEW.state IN ('VALIDATED', 'REJECTED')) OR "
        "(OLD.state = 'VALIDATED' AND NEW.state IN ('PAPER', 'RETIRED')) OR "
        "(OLD.state = 'PAPER' AND NEW.state = 'RETIRED')) "
        "BEGIN SELECT RAISE(ABORT, 'strategy evidence cannot change while freezing'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_strategy_versions_candidate_immutable BEFORE UPDATE "
        "ON strategy_versions WHEN OLD.state = 'CANDIDATE' AND NEW.state = 'CANDIDATE' AND ("
        "NEW.strategy_id IS NOT OLD.strategy_id OR NEW.version IS NOT OLD.version OR "
        "NEW.spec_sha256 IS NOT OLD.spec_sha256 OR NEW.detail IS NOT OLD.detail) "
        "BEGIN SELECT RAISE(ABORT, 'candidate strategy evidence must be append-only'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_experiments_complete_immutable BEFORE UPDATE "
        "ON experiments WHEN OLD.immutable = 0 AND NEW.immutable = 0 AND ("
        "NEW.research_id IS NOT OLD.research_id OR NEW.detail IS NOT OLD.detail OR "
        "NEW.revision IS NOT OLD.revision) "
        "BEGIN SELECT RAISE(ABORT, 'experiment evidence cannot change while completing'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_experiments_complete_binding BEFORE UPDATE ON experiments "
        "WHEN OLD.immutable = 0 AND NEW.immutable = 1 AND NOT ("
        "NEW.research_id IS OLD.research_id AND NEW.revision = OLD.revision + 1 AND "
        "json_extract(NEW.detail, '$.status') = 'COMPLETED') "
        "BEGIN SELECT RAISE(ABORT, 'experiment completion is not bound to a running job'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_approval_requests_pending_evidence_immutable BEFORE UPDATE "
        "ON approval_requests WHEN NEW.validation_id IS NOT OLD.validation_id OR "
        "NEW.subject_sha256 IS NOT OLD.subject_sha256 OR NEW.subject_type IS NOT OLD.subject_type OR "
        "NEW.subject_id IS NOT OLD.subject_id OR NEW.subject_version IS NOT OLD.subject_version OR "
        "NEW.subject_revision IS NOT OLD.subject_revision OR "
        "NEW.subject_spec_sha256 IS NOT OLD.subject_spec_sha256 OR "
        "NEW.prerequisites_sha256 IS NOT OLD.prerequisites_sha256 BEGIN SELECT "
        "RAISE(ABORT, 'approval evidence cannot be changed'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_approval_requests_resolve_immutable BEFORE UPDATE "
        "ON approval_requests WHEN OLD.status = 'PENDING' AND NEW.status != 'PENDING' AND ("
        "NEW.validation_id IS NOT OLD.validation_id OR "
        "NEW.subject_sha256 IS NOT OLD.subject_sha256 OR "
        "NEW.subject_type IS NOT OLD.subject_type OR NEW.subject_id IS NOT OLD.subject_id OR "
        "NEW.subject_version IS NOT OLD.subject_version OR "
        "NEW.subject_revision IS NOT OLD.subject_revision OR "
        "NEW.subject_spec_sha256 IS NOT OLD.subject_spec_sha256 OR "
        "NEW.prerequisites_sha256 IS NOT OLD.prerequisites_sha256) "
        "BEGIN SELECT RAISE(ABORT, 'approval evidence cannot change while resolving'); END"
    )


def upgrade() -> None:
    _assert_integrity_backfill_is_mappable()
    _add_columns("jobs", JOB_COLUMNS)
    _add_columns("domain_events", EVENT_COLUMNS)
    _add_columns(
        "audit_events",
        (
            sa.Column("previous_sha256", sa.String(64)),
            sa.Column("event_sha256", sa.String(64), nullable=False),
        ),
    )
    _add_columns("approval_requests", APPROVAL_COLUMNS)
    _add_columns(
        "tool_calls", (sa.Column("semantic_scope", sa.String(), nullable=False),)
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
        batch_op.create_check_constraint(
            "jobs_attempt_limit_check", "attempt <= max_attempts"
        )
        batch_op.create_check_constraint(
            "jobs_progress_bounds_check",
            "completed_units IS NULL OR total_units IS NULL OR completed_units <= total_units",
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
        op.execute(
            "DROP TRIGGER qf_approval_requests_pending_evidence_immutable ON approval_requests"
        )
        op.execute("DROP FUNCTION qf_reject_pending_approval_evidence_change()")
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
    op.execute("DROP TRIGGER qf_strategy_versions_freeze_immutable")
    op.execute("DROP TRIGGER qf_strategy_versions_candidate_immutable")
    op.execute("DROP TRIGGER qf_experiments_complete_immutable")
    op.execute("DROP TRIGGER qf_approval_requests_pending_evidence_immutable")
    op.execute("DROP TRIGGER qf_approval_requests_resolve_immutable")


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
        batch_op.drop_constraint("jobs_attempt_limit_check", type_="check")
        batch_op.drop_constraint("jobs_progress_bounds_check", type_="check")
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
