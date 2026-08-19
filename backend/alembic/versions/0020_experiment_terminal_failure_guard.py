"""Allow bound jobs to close mutable experiments as failed or cancelled."""

from __future__ import annotations

from alembic import op

revision = "0020_experiment_terminal_guard"
down_revision = "0019_strategy_candidate_evidence"
branch_labels = None
depends_on = None


def _replace_guard() -> None:
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
             )
             AND NOT (
               NEW.id IS NOT DISTINCT FROM OLD.id AND
               NEW.research_id IS NOT DISTINCT FROM OLD.research_id AND
               NEW.experiment_id IS NOT DISTINCT FROM OLD.experiment_id AND
               NEW.workspace_id IS NOT DISTINCT FROM OLD.workspace_id AND
               OLD.status IN ('QUEUED', 'RUNNING') AND
               NEW.status IN ('FAILED', 'CANCELLED') AND
               NEW.validity_state = 'INVALID' AND
               NEW.revision = OLD.revision + 1 AND
               (NEW.detail::jsonb - 'status' - 'validity_state' -
                'action_capabilities' - 'finished_at' - 'invalidated_at' -
                'invalid_reason_code' - 'invalid_reason_detail') IS NOT DISTINCT FROM
               (OLD.detail::jsonb - 'status' - 'validity_state' -
                'action_capabilities' - 'finished_at' - 'invalidated_at' -
                'invalid_reason_code' - 'invalid_reason_detail') AND
               COALESCE(NEW.detail::jsonb ->> 'status', '') = NEW.status AND
               COALESCE(NEW.detail::jsonb ->> 'validity_state', '') = NEW.validity_state AND
               EXISTS (
                 SELECT 1 FROM jobs j
                 WHERE j.job_id = NEW.detail::jsonb ->> 'job_id'
                   AND j.job_type IN ('EXPERIMENT', 'EXPERIMENT_REPRODUCE', 'FACTOR_ANALYSIS')
                   AND j.input_payload::jsonb ->> 'experiment_id' = NEW.experiment_id
                   AND j.status IN ('QUEUED', 'RUNNING')
                   AND (
                     (NEW.status = 'FAILED' AND j.cancel_requested_at IS NULL) OR
                     (NEW.status = 'CANCELLED' AND
                      (j.cancel_requested_at IS NOT NULL OR j.status = 'QUEUED'))
                   )
               )
             ) THEN
            RAISE EXCEPTION 'experiment evidence cannot change while completing';
          END IF;
          IF TG_OP = 'UPDATE' AND NOT OLD.immutable AND NEW.immutable
             AND NOT (
               NEW.id IS NOT DISTINCT FROM OLD.id AND
               NEW.research_id IS NOT DISTINCT FROM OLD.research_id AND
               NEW.experiment_id IS NOT DISTINCT FROM OLD.experiment_id AND
               NEW.workspace_id IS NOT DISTINCT FROM OLD.workspace_id AND
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
                 WHERE j.job_id = NEW.detail::jsonb ->> 'job_id'
                   AND j.job_type IN ('EXPERIMENT', 'EXPERIMENT_REPRODUCE', 'FACTOR_ANALYSIS')
                   AND j.status IN ('RUNNING', 'COMPLETED')
                   AND j.input_payload::jsonb ->> 'experiment_id' = NEW.experiment_id
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


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        _replace_guard()


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
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
                 ) THEN
                RAISE EXCEPTION 'experiment evidence cannot change while completing';
              END IF;
              IF TG_OP = 'UPDATE' AND NOT OLD.immutable AND NEW.immutable
                 AND NOT (
                   NEW.id IS NOT DISTINCT FROM OLD.id AND
                   NEW.research_id IS NOT DISTINCT FROM OLD.research_id AND
                   NEW.experiment_id IS NOT DISTINCT FROM OLD.experiment_id AND
                   NEW.workspace_id IS NOT DISTINCT FROM OLD.workspace_id AND
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
                     WHERE j.job_id = NEW.detail::jsonb ->> 'job_id'
                       AND j.job_type IN ('EXPERIMENT', 'EXPERIMENT_REPRODUCE', 'FACTOR_ANALYSIS')
                       AND j.status IN ('RUNNING', 'COMPLETED')
                       AND j.input_payload::jsonb ->> 'experiment_id' = NEW.experiment_id
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
