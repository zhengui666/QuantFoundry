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
    _create_sqlite_experiment_guards()


def _drop_sqlite_experiment_guards() -> None:
    for action in ("update", "delete"):
        op.execute(f"DROP TRIGGER IF EXISTS qf_experiments_{action}_immutable")


def _create_sqlite_experiment_guards() -> None:
    for action in ("UPDATE", "DELETE"):
        op.execute(
            f"CREATE TRIGGER qf_experiments_{action.lower()}_immutable BEFORE {action} "
            "ON experiments WHEN OLD.immutable = 1 BEGIN "
            "SELECT RAISE(ABORT, 'completed experiment cannot be changed'); END"
        )
