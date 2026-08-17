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
    _create_sqlite_experiment_guards()


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
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
    op.execute(
        "CREATE TRIGGER qf_experiments_complete_immutable BEFORE UPDATE "
        "ON experiments WHEN OLD.immutable = 0 AND NEW.immutable = 0 AND ("
        "NEW.research_id IS NOT OLD.research_id OR NEW.detail IS NOT OLD.detail OR "
        "NEW.revision IS NOT OLD.revision"
        + source_clause
        + ") BEGIN SELECT RAISE(ABORT, 'experiment evidence cannot change while completing'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_experiments_complete_binding BEFORE UPDATE ON experiments "
        "WHEN OLD.immutable = 0 AND NEW.immutable = 1 AND NOT ("
        "NEW.research_id IS OLD.research_id AND NEW.revision = OLD.revision + 1 AND "
        "NEW.source_experiment_id IS OLD.source_experiment_id AND "
        "NEW.job_id IS NOT NULL AND json_extract(NEW.detail, '$.status') = 'COMPLETED' AND "
        "EXISTS (SELECT 1 FROM jobs j WHERE j.id = NEW.job_id AND "
        "j.workspace_id = NEW.workspace_id AND j.status = 'RUNNING')) "
        "BEGIN SELECT RAISE(ABORT, 'experiment completion is not bound to a running job'); END"
    )


def _create_postgres_experiment_guard(*, include_source: bool) -> None:
    source_clause = (
        " OR NEW.source_experiment_id IS DISTINCT FROM OLD.source_experiment_id"
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
               NEW.research_id IS NOT DISTINCT FROM OLD.research_id AND
               NEW.source_experiment_id IS NOT DISTINCT FROM OLD.source_experiment_id AND
               NEW.revision = OLD.revision + 1 AND
               NEW.job_id IS NOT NULL AND
               (NEW.detail::jsonb ->> 'status') = 'COMPLETED' AND
               EXISTS (
                 SELECT 1 FROM jobs j
                 WHERE j.id = NEW.job_id
                   AND j.workspace_id = NEW.workspace_id
                   AND j.status = 'RUNNING'
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
