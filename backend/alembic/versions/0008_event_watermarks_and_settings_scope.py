"""Persist workspace SSE retention watermarks and scope settings storage.

Revision ID: 0008_event_watermarks_settings
Revises: 0007_workspace_snapshot_identity
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0008_event_watermarks_settings"
down_revision = "0007_workspace_snapshot_identity"
branch_labels = None
depends_on = None


def _scope_domain_event_primary_key() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    primary_key = inspector.get_pk_constraint("domain_events")
    columns = primary_key.get("constrained_columns", [])
    if columns == ["workspace_id", "sequence"] or columns == [
        "sequence",
        "workspace_id",
    ]:
        return
    if bind.dialect.name == "sqlite":
        triggers = [
            row[0]
            for row in bind.execute(
                sa.text(
                    "SELECT sql FROM sqlite_master "
                    "WHERE type = 'trigger' AND tbl_name = 'domain_events' "
                    "AND sql IS NOT NULL ORDER BY name"
                )
            )
        ]
        naming_convention = {"pk": "pk_%(table_name)s"}
        with op.batch_alter_table(
            "domain_events", recreate="always", naming_convention=naming_convention
        ) as batch:
            batch.drop_constraint(
                primary_key.get("name") or "pk_domain_events", type_="primary"
            )
            batch.create_primary_key("pk_domain_events", ["workspace_id", "sequence"])
        for sql in triggers:
            op.execute(sql)
        return
    if primary_key.get("name"):
        op.drop_constraint(primary_key["name"], "domain_events", type_="primary")
    op.create_primary_key(
        "pk_domain_events", "domain_events", ["workspace_id", "sequence"]
    )


def _restore_domain_events_update_guard(bind) -> None:
    if bind.dialect.name == "postgresql":
        op.execute(
            "CREATE TRIGGER qf_domain_events_update_immutable BEFORE UPDATE ON "
            "domain_events FOR EACH ROW EXECUTE FUNCTION qf_reject_change()"
        )
    else:
        op.execute(
            "CREATE TRIGGER qf_domain_events_update_immutable BEFORE UPDATE ON "
            "domain_events BEGIN SELECT RAISE(ABORT, "
            "'immutable evidence cannot be changed'); END"
        )


def upgrade() -> None:
    # Materialize legacy system events before workspace_id becomes part of the key.
    bind = op.get_bind()
    if bind.dialect.name not in {"postgresql", "sqlite"}:
        raise RuntimeError(
            f"0008 event watermark migration does not support dialect {bind.dialect.name}"
        )
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text("LOCK TABLE domain_events, records IN ACCESS EXCLUSIVE MODE")
        )
    else:
        if bind.in_transaction():
            bind.execute(
                sa.text("UPDATE domain_events SET sequence = sequence WHERE 0")
            )
        else:
            bind.exec_driver_sql("BEGIN IMMEDIATE")
    collision = bind.execute(
        sa.text(
            "SELECT 1 FROM records source JOIN records target "
            "ON target.id = 'settings:' || source.workspace_id "
            "AND target.id <> source.id "
            "WHERE source.id = 'settings' AND source.kind = 'settings' "
            "AND source.workspace_id IS NOT NULL LIMIT 1"
        )
    ).first()
    if collision is not None:
        raise RuntimeError(
            "settings record identity migration has a canonical ID collision"
        )
    if bind.dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS qf_domain_events_update_immutable ON domain_events"
        )
    else:
        op.execute("DROP TRIGGER IF EXISTS qf_domain_events_update_immutable")
    try:
        op.execute(
            "UPDATE domain_events SET workspace_id = 'system' WHERE workspace_id IS NULL"
        )
    finally:
        _restore_domain_events_update_guard(bind)
    op.create_table(
        "event_stream_watermarks",
        sa.Column("workspace_id", sa.String(), primary_key=True),
        sa.Column(
            "last_sequence",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "expired_through_sequence",
            sa.BigInteger().with_variant(sa.Integer(), "sqlite"),
            nullable=False,
            server_default="0",
        ),
    )
    op.execute(
        """
        INSERT INTO event_stream_watermarks
          (workspace_id, last_sequence, expired_through_sequence)
        SELECT COALESCE(workspace_id, 'system'), MAX(sequence), 0
        FROM domain_events
        GROUP BY COALESCE(workspace_id, 'system')
        """
    )
    _scope_domain_event_primary_key()
    op.execute(
        """
        UPDATE records
        SET id = 'settings:' || workspace_id
        WHERE id = 'settings' AND kind = 'settings' AND workspace_id IS NOT NULL
        """
    )


def downgrade() -> None:
    raise RuntimeError("durable workspace event retention state is irreversible")
