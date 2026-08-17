"""Persist Experiment reproduce lineage.

Revision ID: 0005_reproduce_lineage
Revises: 0004_quant_evidence_integrity
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0005_reproduce_lineage"
down_revision = "0004_quant_evidence_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.add_column("experiments", sa.Column("source_experiment_id", sa.String()))
        op.create_foreign_key(
            "fk_experiments_source_experiment_id",
            "experiments",
            "experiments",
            ["source_experiment_id"],
            ["id"],
        )
        op.create_index(
            "ix_experiments_source_experiment_id",
            "experiments",
            ["source_experiment_id"],
        )
        op.execute(_postgres_lineage_cycle_guard())
        _create_postgres_experiment_guard(include_source=True)
        return
    _drop_sqlite_experiment_guards()
    with op.batch_alter_table("experiments") as batch_op:
        batch_op.add_column(sa.Column("source_experiment_id", sa.String()))
        batch_op.create_foreign_key(
            "fk_experiments_source_experiment_id",
            "experiments",
            ["source_experiment_id"],
            ["id"],
        )
        batch_op.create_index(
            "ix_experiments_source_experiment_id", ["source_experiment_id"]
        )
        batch_op.create_check_constraint(
            "ck_experiments_source_not_self",
            "source_experiment_id IS NULL OR source_experiment_id <> id",
        )
    _create_sqlite_lineage_cycle_guards()
    _create_sqlite_experiment_guards()


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS qf_experiments_lineage_cycle ON experiments")
        op.execute("DROP FUNCTION IF EXISTS qf_reject_experiment_lineage_cycle()")
        _create_postgres_experiment_guard(include_source=False)
        op.drop_index("ix_experiments_source_experiment_id", table_name="experiments")
        op.drop_constraint(
            "fk_experiments_source_experiment_id",
            "experiments",
            type_="foreignkey",
        )
        op.drop_column("experiments", "source_experiment_id")
        return
    _drop_sqlite_experiment_guards()
    _drop_sqlite_lineage_cycle_guards()
    with op.batch_alter_table("experiments") as batch_op:
        batch_op.drop_index("ix_experiments_source_experiment_id")
        batch_op.drop_constraint(
            "fk_experiments_source_experiment_id", type_="foreignkey"
        )
        batch_op.drop_column("source_experiment_id")
    _create_sqlite_experiment_guards(include_source=False)


def _drop_sqlite_experiment_guards() -> None:
    for action in ("update", "delete"):
        op.execute(f"DROP TRIGGER IF EXISTS qf_experiments_{action}_immutable")
    op.execute("DROP TRIGGER IF EXISTS qf_experiments_complete_immutable")
    op.execute("DROP TRIGGER IF EXISTS qf_experiments_complete_binding")


def _drop_sqlite_lineage_cycle_guards() -> None:
    op.execute("DROP TRIGGER IF EXISTS qf_experiments_lineage_cycle_insert")
    op.execute("DROP TRIGGER IF EXISTS qf_experiments_lineage_cycle_update")


def _create_sqlite_lineage_cycle_guards() -> None:
    for action in ("INSERT", "UPDATE"):
        op.execute(
            f"CREATE TRIGGER qf_experiments_lineage_cycle_{action.lower()} "
            f"BEFORE {action} ON experiments "
            "WHEN NEW.source_experiment_id IS NOT NULL BEGIN "
            "SELECT RAISE(ABORT, 'experiment lineage cannot contain a cycle') "
            "WHERE NEW.source_experiment_id = NEW.id OR EXISTS ("
            "WITH RECURSIVE lineage(id) AS ("
            "SELECT NEW.source_experiment_id UNION "
            "SELECT e.source_experiment_id FROM experiments e "
            "JOIN lineage l ON e.id = l.id "
            "WHERE e.source_experiment_id IS NOT NULL) "
            "SELECT 1 FROM lineage WHERE id = NEW.id); END"
        )


def _postgres_lineage_cycle_guard() -> str:
    return """
        CREATE OR REPLACE FUNCTION qf_reject_experiment_lineage_cycle() RETURNS trigger AS $$
        BEGIN
          IF NEW.source_experiment_id IS NOT NULL AND EXISTS (
            WITH RECURSIVE lineage(id) AS (
              SELECT NEW.source_experiment_id
              UNION
              SELECT e.source_experiment_id
              FROM experiments e
              JOIN lineage l ON e.id = l.id
              WHERE e.source_experiment_id IS NOT NULL
            )
            SELECT 1 FROM lineage WHERE id = NEW.id
          ) THEN
            RAISE EXCEPTION 'experiment lineage cannot contain a cycle';
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER qf_experiments_lineage_cycle
        BEFORE INSERT OR UPDATE OF source_experiment_id ON experiments
        FOR EACH ROW EXECUTE FUNCTION qf_reject_experiment_lineage_cycle();
    """


def _create_sqlite_experiment_guards(*, include_source: bool = True) -> None:
    for action in ("UPDATE", "DELETE"):
        op.execute(
            f"CREATE TRIGGER qf_experiments_{action.lower()}_immutable BEFORE {action} "
            "ON experiments WHEN OLD.immutable = 1 BEGIN "
            "SELECT RAISE(ABORT, 'completed experiment cannot be changed'); END"
        )
    source_clause = (
        " OR NEW.source_experiment_id IS NOT OLD.source_experiment_id"
        if include_source
        else ""
    )
    source_binding_clause = (
        "NEW.source_experiment_id IS OLD.source_experiment_id AND "
        if include_source
        else ""
    )
    op.execute(
        "CREATE TRIGGER qf_experiments_complete_immutable BEFORE UPDATE "
        "ON experiments WHEN OLD.immutable = 0 AND NEW.immutable = 0 AND ("
        "NEW.id IS NOT OLD.id OR NEW.research_id IS NOT OLD.research_id OR "
        "NEW.detail IS NOT OLD.detail OR "
        "NEW.revision IS NOT OLD.revision"
        + source_clause
        + ") BEGIN SELECT RAISE(ABORT, 'experiment evidence cannot change while completing'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_experiments_complete_binding BEFORE UPDATE ON experiments "
        "WHEN OLD.immutable = 0 AND NEW.immutable = 1 AND NOT ("
        "NEW.id IS OLD.id AND NEW.research_id IS OLD.research_id AND "
        + source_binding_clause
        + "NEW.revision = OLD.revision + 1 AND "
        "json_remove(NEW.detail, '$.status', '$.validity_state', '$.adapter', "
        "'$.provenance', '$.metrics', '$.artifacts', '$.search_space', "
        "'$.search_configuration', '$.search_result', '$.action_capabilities', "
        "'$.started_at', '$.finished_at') IS "
        "json_remove(OLD.detail, '$.status', '$.validity_state', '$.adapter', "
        "'$.provenance', '$.metrics', '$.artifacts', '$.search_space', "
        "'$.search_configuration', '$.search_result', '$.action_capabilities', "
        "'$.started_at', '$.finished_at') AND "
        "COALESCE(json_extract(NEW.detail, '$.status'), '') = 'COMPLETED' AND "
        "EXISTS (SELECT 1 FROM jobs j WHERE "
        "j.id = json_extract(NEW.detail, '$.job_id') AND "
        "j.job_type = 'EXPERIMENT' AND "
        "j.status IN ('RUNNING', 'COMPLETED') AND "
        "json_extract(j.input_payload, '$.experiment_id') = NEW.id) ) "
        "BEGIN SELECT RAISE(ABORT, 'experiment completion is not bound to a running job'); END"
    )


def _create_postgres_experiment_guard(*, include_source: bool) -> None:
    source_clause = (
        " OR NEW.source_experiment_id IS DISTINCT FROM OLD.source_experiment_id"
        if include_source
        else ""
    )
    source_binding_clause = (
        "               NEW.source_experiment_id IS NOT DISTINCT FROM OLD.source_experiment_id AND\n"
        if include_source
        else ""
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION qf_reject_completed_experiment_change() RETURNS trigger AS $$
        BEGIN
          IF OLD.immutable THEN
            RAISE EXCEPTION 'completed experiment cannot be changed';
          END IF;
          IF TG_OP = 'UPDATE' AND NOT OLD.immutable AND NOT NEW.immutable
             AND (
               NEW.id IS DISTINCT FROM OLD.id OR
               NEW.research_id IS DISTINCT FROM OLD.research_id OR
               NEW.detail IS DISTINCT FROM OLD.detail OR
               NEW.revision IS DISTINCT FROM OLD.revision
        """
        + source_clause
        + """
             ) THEN
            RAISE EXCEPTION 'experiment evidence cannot change while completing';
          END IF;
          IF TG_OP = 'UPDATE' AND NOT OLD.immutable AND NEW.immutable
             AND NOT (
               NEW.id IS NOT DISTINCT FROM OLD.id AND
               NEW.research_id IS NOT DISTINCT FROM OLD.research_id AND
        """
        + source_binding_clause
        + """
               NEW.revision = OLD.revision + 1 AND
               (NEW.detail::jsonb - 'status' - 'validity_state' - 'adapter' -
                'provenance' - 'metrics' - 'artifacts' - 'search_space' -
                'search_configuration' - 'search_result' - 'action_capabilities' -
                'started_at' - 'finished_at') IS NOT DISTINCT FROM
               (OLD.detail::jsonb - 'status' - 'validity_state' - 'adapter' -
                'provenance' - 'metrics' - 'artifacts' - 'search_space' -
                'search_configuration' - 'search_result' - 'action_capabilities' -
                'started_at' - 'finished_at') AND
               COALESCE(NEW.detail::jsonb ->> 'status', '') = 'COMPLETED' AND
               EXISTS (
                 SELECT 1 FROM jobs j
                 WHERE j.id = NEW.detail::jsonb ->> 'job_id'
                   AND j.job_type = 'EXPERIMENT'
                   AND j.status IN ('RUNNING', 'COMPLETED')
                   AND j.input_payload::jsonb ->> 'experiment_id' = NEW.id
               )
             ) THEN
            RAISE EXCEPTION 'experiment completion is not bound to a running job';
          END IF;
          IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
