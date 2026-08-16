"""Create the UX-001 Bootstrap Control DB relations."""

from alembic import op
from app.control_plane import CONTROL_METADATA

revision = "ux001_control_v1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    CONTROL_METADATA.create_all(op.get_bind())


def downgrade() -> None:
    for table_name in (
        "configuration_values",
        "owner_sessions",
        "bootstrap_audit_events",
        "configuration_consumer_states",
        "active_configuration",
        "domain_database_connection_revisions",
        "configuration_revisions",
        "configuration_catalog",
        "bootstrap_state",
        "general_access_keys",
    ):
        op.drop_table(table_name)
