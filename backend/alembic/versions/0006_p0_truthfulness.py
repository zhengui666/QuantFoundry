"""Workspace ownership, scoped idempotency and legal strategy transitions.

Revision ID: 0006_p0_truthfulness
Revises: 0005_reproduce_lineage
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0006_p0_truthfulness"
down_revision = "0005_reproduce_lineage"
branch_labels = None
depends_on = None


WORKSPACE_TABLES = (
    "records",
    "jobs",
    "data_sources",
    "data_snapshots",
    "snapshot_partitions",
    "experiments",
    "factors",
    "strategies",
    "strategy_versions",
    "validations",
    "approval_requests",
    "holdout_exposures",
    "agent_runs",
    "tool_calls",
)

_SCOPED_PARENT_KEYS = (
    "research_cases",
    "experiments",
    "strategies",
    "strategy_versions",
    "validations",
    "approval_requests",
    "jobs",
    "agent_runs",
    "data_snapshots",
)
_SCOPED_REFERENCES = (
    ("experiments", "research_id", "research_cases"),
    ("factors", "research_id", "research_cases"),
    ("strategies", "research_id", "research_cases"),
    ("strategy_versions", "strategy_id", "strategies"),
    ("validations", "strategy_version_id", "strategy_versions"),
    ("approval_requests", "validation_id", "validations"),
    ("holdout_exposures", "validation_id", "validations"),
    ("holdout_exposures", "strategy_version_id", "strategy_versions"),
    ("holdout_exposures", "approval_id", "approval_requests"),
    ("holdout_exposures", "job_id", "jobs"),
    ("agent_runs", "research_id", "research_cases"),
    ("agent_runs", "root_agent_run_id", "agent_runs"),
    ("agent_runs", "parent_agent_run_id", "agent_runs"),
    ("tool_calls", "agent_run_id", "agent_runs"),
    ("tool_calls", "experiment_id", "experiments"),
    ("tool_calls", "job_id", "jobs"),
    ("tool_calls", "research_id", "research_cases"),
    ("snapshot_partitions", "snapshot_id", "data_snapshots"),
)


def _assert_ownership_backfill_is_mappable() -> None:
    bind = op.get_bind()
    tables = (*WORKSPACE_TABLES, "domain_events", "audit_events", "agent_configs")
    locked_tables = (*tables, "research_cases", "idempotency_records")
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                "LOCK TABLE "
                + ", ".join(f'"{table}"' for table in locked_tables)
                + " IN ACCESS EXCLUSIVE MODE"
            )
        )
    elif bind.dialect.name == "sqlite":
        if bind.in_transaction():
            bind.execute(sa.text("UPDATE records SET id = id WHERE 0"))
        else:
            bind.exec_driver_sql("BEGIN IMMEDIATE")
    else:
        raise RuntimeError(
            "0006 ownership migration supports PostgreSQL and SQLite only"
        )
    counts = {
        table: int(bind.execute(sa.text(f"SELECT COUNT(*) FROM {table}")).scalar_one())
        for table in tables
    }
    legacy_idempotency = int(
        bind.execute(sa.text("SELECT COUNT(*) FROM idempotency_records")).scalar_one()
    )
    unowned_research = int(
        bind.execute(
            sa.text("SELECT COUNT(*) FROM research_cases WHERE workspace_id IS NULL")
        ).scalar_one()
    )
    if any(counts.values()) or legacy_idempotency or unowned_research:
        detail = ", ".join(f"{table}={count}" for table, count in counts.items())
        raise RuntimeError(
            "0006 refuses to guess workspace ownership; manual mapping required "
            f"({detail}, idempotency_records={legacy_idempotency}, "
            f"research_cases.workspace_id_null={unowned_research})"
        )


def _add_workspace_column(table: str) -> None:
    column = sa.Column(
        "workspace_id",
        sa.String(),
        sa.ForeignKey("workspaces.id", name=f"fk_{table}_workspace_id_workspaces"),
        nullable=False,
    )
    if op.get_bind().dialect.name != "sqlite":
        op.add_column(table, column)
        return
    connection = op.get_bind()
    trigger_rows = [
        (str(row[0]), str(row[1]))
        for row in connection.execute(
            sa.text(
                "SELECT name, sql FROM sqlite_master "
                "WHERE type = 'trigger' AND "
                "(tbl_name = :table OR lower(sql) LIKE lower(:pattern)) "
                "ORDER BY name"
            ),
            {"table": table, "pattern": f"%{table}%"},
        )
        if row[1]
    ]
    for name, _ in trigger_rows:
        op.execute(f'DROP TRIGGER "{name.replace(chr(34), chr(34) * 2)}"')
    with op.batch_alter_table(
        table,
        naming_convention={
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
        },
    ) as batch_op:
        batch_op.add_column(column)
    for _, sql in trigger_rows:
        op.execute(sql)


def _replace_idempotency() -> None:
    op.create_table(
        "idempotency_records_v2",
        sa.Column("actor_id", sa.String(), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(),
            sa.ForeignKey(
                "workspaces.id",
                name="fk_idempotency_records_workspace_id_workspaces",
            ),
            primary_key=True,
        ),
        sa.Column("method", sa.String(), primary_key=True),
        sa.Column("path", sa.String(), primary_key=True),
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("request_hash", sa.String(), nullable=False),
        sa.Column("status", sa.Integer(), nullable=False),
        sa.Column("response", sa.Text(), nullable=False),
        sa.Column("state", sa.String(), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.drop_table("idempotency_records")
    op.rename_table("idempotency_records_v2", "idempotency_records")
    op.create_index(
        "ix_idempotency_records_expires_at",
        "idempotency_records",
        ["expires_at"],
    )


def _replace_strategy_guard() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS qf_strategy_versions_immutable ON strategy_versions"
        )
        op.execute("DROP FUNCTION IF EXISTS qf_reject_frozen_strategy_change()")
        op.execute(
            """
            CREATE FUNCTION qf_validate_strategy_transition() RETURNS trigger AS $$
            BEGIN
              IF TG_OP = 'INSERT' THEN
                IF NEW.state <> 'CANDIDATE' THEN
                  RAISE EXCEPTION 'strategy version must start as candidate';
                END IF;
                RETURN NEW;
              END IF;
              IF TG_OP = 'DELETE' THEN
                IF OLD.state <> 'CANDIDATE' THEN
                  RAISE EXCEPTION 'non-candidate strategy version cannot be deleted';
                END IF;
                RETURN OLD;
              END IF;
              IF NEW.workspace_id IS DISTINCT FROM OLD.workspace_id THEN
                RAISE EXCEPTION 'strategy workspace ownership is immutable';
              END IF;
              IF (OLD.state <> 'CANDIDATE' OR NEW.state = 'FROZEN') AND (
                   NEW.id IS DISTINCT FROM OLD.id OR
                   NEW.strategy_id IS DISTINCT FROM OLD.strategy_id OR
                   NEW.version IS DISTINCT FROM OLD.version OR
                   NEW.spec_sha256 IS DISTINCT FROM OLD.spec_sha256 OR
                   ((OLD.state <> 'CANDIDATE' OR NEW.state = 'FROZEN') AND
                    (NEW.detail::jsonb - 'lifecycle_state' - 'is_frozen' -
                     'latest_backtest' - 'validation_summary' - 'artifacts' -
                     'provenance' - 'frozen_at' - 'frozen_by' - 'revision' -
                     'action_capabilities') IS DISTINCT FROM
                    (OLD.detail::jsonb - 'lifecycle_state' - 'is_frozen' -
                     'latest_backtest' - 'validation_summary' - 'artifacts' -
                     'provenance' - 'frozen_at' - 'frozen_by' - 'revision' -
                     'action_capabilities')) OR
                   (OLD.state <> 'CANDIDATE' AND NEW.frozen_at IS DISTINCT FROM OLD.frozen_at) OR
                   NEW.workspace_id IS DISTINCT FROM OLD.workspace_id OR
                   (OLD.state = 'CANDIDATE' AND NEW.state = 'FROZEN' AND NEW.frozen_at IS NULL)
              ) THEN
                RAISE EXCEPTION 'frozen strategy specification is immutable';
              END IF;
              IF OLD.state = 'CANDIDATE' AND NEW.state = 'CANDIDATE' AND (
                   NEW.id IS DISTINCT FROM OLD.id OR
                   NEW.strategy_id IS DISTINCT FROM OLD.strategy_id OR
                   NEW.version IS DISTINCT FROM OLD.version OR
                   NEW.spec_sha256 IS DISTINCT FROM OLD.spec_sha256 OR
                   NEW.frozen_at IS DISTINCT FROM OLD.frozen_at OR
                   NEW.detail IS DISTINCT FROM OLD.detail OR
                   NEW.workspace_id IS DISTINCT FROM OLD.workspace_id
              ) THEN
                RAISE EXCEPTION 'candidate strategy evidence must be append-only';
              END IF;
              IF NOT (
                   NEW.state = OLD.state OR
                   (OLD.state = 'CANDIDATE' AND NEW.state = 'FROZEN') OR
                   (OLD.state = 'FROZEN' AND NEW.state = 'VALIDATING') OR
                   (OLD.state = 'VALIDATING' AND NEW.state IN ('VALIDATED', 'REJECTED')) OR
                   (OLD.state = 'VALIDATED' AND NEW.state IN ('REJECTED', 'PAPER', 'RETIRED')) OR
                   (OLD.state = 'PAPER' AND NEW.state = 'RETIRED')
              ) THEN
                RAISE EXCEPTION 'illegal strategy lifecycle transition';
              END IF;
              IF OLD.state <> 'CANDIDATE' AND NEW.state = OLD.state AND
                 (NEW.detail::jsonb - 'lifecycle_state' - 'is_frozen' -
                  'latest_backtest' - 'validation_summary' - 'artifacts' -
                  'provenance' - 'frozen_at' - 'frozen_by' - 'revision' -
                  'action_capabilities') IS DISTINCT FROM
                 (OLD.detail::jsonb - 'lifecycle_state' - 'is_frozen' -
                  'latest_backtest' - 'validation_summary' - 'artifacts' -
                  'provenance' - 'frozen_at' - 'frozen_by' - 'revision' -
                  'action_capabilities') THEN
                RAISE EXCEPTION 'frozen strategy detail cannot change without lifecycle transition';
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            "CREATE TRIGGER qf_strategy_versions_immutable BEFORE INSERT OR UPDATE OR DELETE "
            "ON strategy_versions FOR EACH ROW EXECUTE FUNCTION qf_validate_strategy_transition()"
        )
        return
    for action in ("update", "delete"):
        op.execute(f"DROP TRIGGER IF EXISTS qf_strategy_versions_{action}_immutable")
    op.execute("DROP TRIGGER IF EXISTS qf_strategy_versions_insert_immutable")
    op.execute("DROP TRIGGER IF EXISTS qf_strategy_versions_freeze_immutable")
    op.execute(
        """
        CREATE TRIGGER qf_strategy_versions_delete_immutable BEFORE DELETE
        ON strategy_versions WHEN OLD.state != 'CANDIDATE'
        BEGIN SELECT RAISE(ABORT, 'non-candidate strategy version cannot be deleted'); END
        """
    )
    op.execute(
        """
        CREATE TRIGGER qf_strategy_versions_insert_immutable BEFORE INSERT
        ON strategy_versions WHEN NEW.state != 'CANDIDATE'
        BEGIN SELECT RAISE(ABORT, 'strategy version must start as candidate'); END
        """
    )
    op.execute(
        """
        CREATE TRIGGER qf_strategy_versions_update_immutable BEFORE UPDATE
        ON strategy_versions WHEN
          ((OLD.state != 'CANDIDATE' OR NEW.state = 'FROZEN') AND (
             NEW.id IS NOT OLD.id OR
             NEW.strategy_id IS NOT OLD.strategy_id OR NEW.version IS NOT OLD.version OR
             NEW.spec_sha256 IS NOT OLD.spec_sha256 OR
             ((OLD.state != 'CANDIDATE' OR NEW.state = 'FROZEN') AND
              json_remove(NEW.detail, '$.lifecycle_state', '$.is_frozen',
                '$.latest_backtest', '$.validation_summary', '$.artifacts',
                '$.provenance', '$.frozen_at', '$.frozen_by', '$.revision',
                '$.action_capabilities') IS NOT
              json_remove(OLD.detail, '$.lifecycle_state', '$.is_frozen',
                '$.latest_backtest', '$.validation_summary', '$.artifacts',
                '$.provenance', '$.frozen_at', '$.frozen_by', '$.revision',
                '$.action_capabilities')) OR
             (OLD.state != 'CANDIDATE' AND NEW.frozen_at IS NOT OLD.frozen_at) OR
             COALESCE(NEW.workspace_id, '') IS NOT COALESCE(OLD.workspace_id, '') OR
             (OLD.state = 'CANDIDATE' AND NEW.state = 'FROZEN' AND NEW.frozen_at IS NULL)
          )) OR (OLD.state = 'CANDIDATE' AND NEW.state = 'CANDIDATE' AND (
             NEW.id IS NOT OLD.id OR NEW.strategy_id IS NOT OLD.strategy_id OR
             NEW.version IS NOT OLD.version OR NEW.spec_sha256 IS NOT OLD.spec_sha256 OR
             NEW.frozen_at IS NOT OLD.frozen_at OR NEW.detail IS NOT OLD.detail OR
             COALESCE(NEW.workspace_id, '') IS NOT COALESCE(OLD.workspace_id, '')
          )) OR NOT (
             NEW.state = OLD.state OR
             (OLD.state = 'CANDIDATE' AND NEW.state = 'FROZEN') OR
             (OLD.state = 'FROZEN' AND NEW.state = 'VALIDATING') OR
             (OLD.state = 'VALIDATING' AND NEW.state IN ('VALIDATED', 'REJECTED')) OR
             (OLD.state = 'VALIDATED' AND NEW.state IN ('REJECTED', 'PAPER', 'RETIRED')) OR
             (OLD.state = 'PAPER' AND NEW.state = 'RETIRED')
          )
        BEGIN SELECT RAISE(ABORT, 'illegal or mutable strategy transition'); END
        """
    )


def _scope_existing_foreign_keys() -> None:
    """Make every pre-0016 ownership reference include its workspace key."""
    bind = op.get_bind()
    naming = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}
    trigger_sql: list[tuple[str, str]] = []
    if bind.dialect.name == "sqlite":
        trigger_rows = bind.execute(
            sa.text(
                "SELECT name, sql FROM sqlite_master "
                "WHERE type = 'trigger' AND sql IS NOT NULL ORDER BY name"
            )
        )
        trigger_sql = [(str(row[0]), str(row[1])) for row in trigger_rows]
        for name, _ in trigger_sql:
            op.execute(f'DROP TRIGGER "{name.replace(chr(34), chr(34) * 2)}"')
    try:
        for table in _SCOPED_PARENT_KEYS:
            with op.batch_alter_table(table, naming_convention=naming) as batch_op:
                batch_op.create_unique_constraint(
                    f"uq_{table}_workspace_id_id", ["workspace_id", "id"]
                )
        inspector = sa.inspect(bind)
        for child, column, parent in _SCOPED_REFERENCES:
            existing = next(
                (
                    foreign_key
                    for foreign_key in inspector.get_foreign_keys(child)
                    if foreign_key.get("referred_table") == parent
                    and foreign_key.get("constrained_columns") == [column]
                    and foreign_key.get("referred_columns") == ["id"]
                ),
                None,
            )
            with op.batch_alter_table(child, naming_convention=naming) as batch_op:
                if existing is not None:
                    constraint_name = existing.get("name") or (
                        f"fk_{child}_{column}_{parent}"
                    )
                    batch_op.drop_constraint(constraint_name, type_="foreignkey")
                batch_op.create_foreign_key(
                    f"fk_{child}_{column}_{parent}",
                    parent,
                    ["workspace_id", column],
                    ["workspace_id", "id"],
                )
    finally:
        for name, sql in trigger_sql:
            if name in {
                "qf_strategy_versions_update_immutable",
                "qf_strategy_versions_delete_immutable",
                "qf_strategy_versions_freeze_immutable",
            }:
                continue
            op.execute(sql)
    if bind.dialect.name == "sqlite":
        op.execute(
            """
            CREATE TRIGGER qf_strategy_versions_delete_immutable BEFORE DELETE
            ON strategy_versions WHEN OLD.state != 'CANDIDATE'
            BEGIN SELECT RAISE(ABORT, 'non-candidate strategy version cannot be deleted'); END
            """
        )
        op.execute(
            """
            CREATE TRIGGER qf_strategy_versions_update_immutable BEFORE UPDATE
            ON strategy_versions WHEN
              ((OLD.state != 'CANDIDATE' OR NEW.state = 'FROZEN') AND (
                 NEW.strategy_id != OLD.strategy_id OR NEW.version != OLD.version OR
                 NEW.spec_sha256 != OLD.spec_sha256 OR
                 (OLD.state != 'CANDIDATE' AND NEW.frozen_at IS NOT OLD.frozen_at) OR
                 COALESCE(NEW.workspace_id, '') != COALESCE(OLD.workspace_id, '') OR
                 (OLD.state != 'CANDIDATE' AND json_remove(NEW.detail,
                  '$.lifecycle_state', '$.is_frozen', '$.latest_backtest',
                  '$.validation_summary', '$.artifacts', '$.provenance',
                  '$.frozen_at', '$.frozen_by', '$.revision',
                  '$.action_capabilities') IS NOT json_remove(OLD.detail,
                  '$.lifecycle_state', '$.is_frozen', '$.latest_backtest',
                  '$.validation_summary', '$.artifacts', '$.provenance',
                  '$.frozen_at', '$.frozen_by', '$.revision',
                  '$.action_capabilities'))
              )) OR (OLD.state = 'CANDIDATE' AND NEW.state = 'CANDIDATE' AND (
                 NEW.id IS NOT OLD.id OR NEW.strategy_id IS NOT OLD.strategy_id OR
                 NEW.version IS NOT OLD.version OR NEW.spec_sha256 IS NOT OLD.spec_sha256 OR
                 NEW.frozen_at IS NOT OLD.frozen_at OR NEW.detail IS NOT OLD.detail
              )) OR NOT (
                 NEW.state = OLD.state OR
                 (OLD.state = 'CANDIDATE' AND NEW.state = 'FROZEN') OR
                 (OLD.state = 'FROZEN' AND NEW.state = 'VALIDATING') OR
                 (OLD.state = 'VALIDATING' AND NEW.state IN ('VALIDATED', 'REJECTED')) OR
                 (OLD.state = 'VALIDATED' AND NEW.state IN ('REJECTED', 'PAPER', 'RETIRED')) OR
                 (OLD.state = 'PAPER' AND NEW.state = 'RETIRED')
              )
            BEGIN SELECT RAISE(ABORT, 'illegal or mutable strategy transition'); END
            """
        )


def upgrade() -> None:
    _assert_ownership_backfill_is_mappable()
    _replace_idempotency()
    op.create_table(
        "audit_chain_heads",
        sa.Column(
            "workspace_id",
            sa.String(),
            sa.ForeignKey(
                "workspaces.id", name="fk_audit_chain_heads_workspace_id_workspaces"
            ),
            primary_key=True,
        ),
        sa.Column("event_sha256", sa.String(64)),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
    )
    for table in WORKSPACE_TABLES:
        _add_workspace_column(table)
        op.create_index(f"ix_{table}_workspace_id", table, ["workspace_id"])
    op.add_column("jobs", sa.Column("request_id", sa.String()))
    op.create_index("ix_jobs_request_id", "jobs", ["request_id"])
    _add_workspace_column("domain_events")
    op.add_column("domain_events", sa.Column("actor_id", sa.String()))
    op.create_index("ix_domain_events_workspace_id", "domain_events", ["workspace_id"])
    op.create_index("ix_domain_events_actor_id", "domain_events", ["actor_id"])
    _add_workspace_column("audit_events")
    op.add_column("audit_events", sa.Column("request_id", sa.String()))
    op.create_index("ix_audit_events_workspace_id", "audit_events", ["workspace_id"])
    op.create_index("ix_audit_events_request_id", "audit_events", ["request_id"])

    dialect = op.get_bind().dialect.name
    naming = {
        "pk": "pk_%(table_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    }
    with op.batch_alter_table(
        "agent_runs", naming_convention=naming if dialect == "sqlite" else None
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_agent_runs_role_agent_configs"
            if dialect == "sqlite"
            else "agent_runs_role_fkey",
            type_="foreignkey",
        )
    with op.batch_alter_table(
        "agent_configs", naming_convention=naming if dialect == "sqlite" else None
    ) as batch_op:
        batch_op.add_column(
            sa.Column(
                "workspace_id",
                sa.String(),
                sa.ForeignKey(
                    "workspaces.id", name="fk_agent_configs_workspace_id_workspaces"
                ),
                nullable=False,
            )
        )
        batch_op.drop_constraint(
            "pk_agent_configs" if dialect == "sqlite" else "agent_configs_pkey",
            type_="primary",
        )
        batch_op.create_primary_key("agent_configs_pkey", ["workspace_id", "role"])
    if dialect == "sqlite":
        with op.batch_alter_table("agent_runs", naming_convention=naming) as batch_op:
            batch_op.create_foreign_key(
                "fk_agent_runs_workspace_role_agent_configs",
                "agent_configs",
                ["workspace_id", "role"],
                ["workspace_id", "role"],
            )
    else:
        op.create_foreign_key(
            "fk_agent_runs_workspace_role_agent_configs",
            "agent_runs",
            "agent_configs",
            ["workspace_id", "role"],
            ["workspace_id", "role"],
        )
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        with op.batch_alter_table("research_cases") as batch_op:
            batch_op.alter_column("workspace_id", nullable=False)
    else:
        op.alter_column("research_cases", "workspace_id", nullable=False)
    _scope_existing_foreign_keys()
    op.drop_index("uq_tool_calls_active_semantic", table_name="tool_calls")
    op.create_index(
        "uq_tool_calls_active_semantic",
        "tool_calls",
        ["workspace_id", "semantic_scope", "tool_name", "input_sha256"],
        unique=True,
        postgresql_where=sa.text("status IN ('RUNNING', 'SUCCESS')"),
        sqlite_where=sa.text("status IN ('RUNNING', 'SUCCESS')"),
    )
    _replace_strategy_guard()


def downgrade() -> None:
    raise RuntimeError("0006 contains an irreversible ownership-key migration")
