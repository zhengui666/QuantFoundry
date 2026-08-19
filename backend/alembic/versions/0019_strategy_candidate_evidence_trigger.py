"""Allow append-only candidate strategy evidence updates."""

from __future__ import annotations

from alembic import op

revision = "0019_strategy_candidate_evidence"
down_revision = "0018_ux001_runtime_snapshots"
branch_labels = None
depends_on = None

_APPEND_ONLY_FIELDS = """
                 (NEW.detail::jsonb - 'lifecycle_state' - 'is_frozen' -
                  'latest_backtest' - 'validation_summary' - 'artifacts' -
                  'provenance' - 'frozen_at' - 'frozen_by' - 'revision' -
                  'action_capabilities') IS DISTINCT FROM
                 (OLD.detail::jsonb - 'lifecycle_state' - 'is_frozen' -
                  'latest_backtest' - 'validation_summary' - 'artifacts' -
                  'provenance' - 'frozen_at' - 'frozen_by' - 'revision' -
                  'action_capabilities')
"""


def _replace_trigger(*, allow_append_only_fields: bool) -> None:
    detail_check = (
        _APPEND_ONLY_FIELDS
        if allow_append_only_fields
        else "                 NEW.detail IS DISTINCT FROM OLD.detail\n"
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION qf_validate_strategy_transition() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            IF OLD.state <> 'CANDIDATE' THEN
              RAISE EXCEPTION 'non-candidate strategy version cannot be deleted';
            END IF;
            RETURN OLD;
          END IF;
          IF (OLD.state <> 'CANDIDATE' OR NEW.state = 'FROZEN') AND (
               NEW.id IS DISTINCT FROM OLD.id OR
               NEW.strategy_public_id IS DISTINCT FROM OLD.strategy_public_id OR
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
               NEW.workspace_id IS DISTINCT FROM OLD.workspace_id
          ) THEN
            RAISE EXCEPTION 'frozen strategy specification is immutable';
          END IF;
          IF NEW.state = 'FROZEN' AND NEW.frozen_at IS NULL THEN
            RAISE EXCEPTION 'frozen strategy requires frozen_at';
          END IF;
          IF OLD.state = 'CANDIDATE' AND NEW.state = 'CANDIDATE' AND (
               NEW.strategy_public_id IS DISTINCT FROM OLD.strategy_public_id OR
               NEW.version IS DISTINCT FROM OLD.version OR
               NEW.spec_sha256 IS DISTINCT FROM OLD.spec_sha256 OR
{detail_check}
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
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        _replace_trigger(allow_append_only_fields=True)


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        _replace_trigger(allow_append_only_fields=False)
