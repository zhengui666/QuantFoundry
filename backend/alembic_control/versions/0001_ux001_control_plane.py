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
    CONTROL_METADATA.drop_all(op.get_bind())
