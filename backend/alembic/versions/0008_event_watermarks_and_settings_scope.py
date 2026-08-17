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


def upgrade() -> None:
    # Materialize legacy system events before workspace_id becomes part of the key.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS qf_domain_events_update_immutable ON domain_events")
    else:
        op.execute("DROP TRIGGER IF EXISTS qf_domain_events_update_immutable")
    op.execute(
        "UPDATE domain_events SET workspace_id = 'system' WHERE workspace_id IS NULL"
    )
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
    op.create_table(
        "event_stream_watermarks",
        sa.Column("workspace_id", sa.String(), primary_key=True),
        sa.Column("last_sequence", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "expired_through_sequence", sa.Integer(), nullable=False, server_default="0"
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
