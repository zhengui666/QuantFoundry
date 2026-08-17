"""Protect artifact and provenance metadata as immutable evidence.

Revision ID: 0004_quant_evidence_integrity
Revises: 0003_runtime_integrity
"""

from __future__ import annotations

from alembic import op

revision = "0004_quant_evidence_integrity"
down_revision = "0003_runtime_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE FUNCTION qf_reject_immutable_record_change() RETURNS trigger AS $$
            BEGIN
              IF OLD.kind IN ('artifact', 'provenance') THEN
                RAISE EXCEPTION 'immutable record cannot be changed';
              END IF;
              IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            "CREATE TRIGGER qf_records_immutable BEFORE UPDATE OR DELETE ON records "
            "FOR EACH ROW EXECUTE FUNCTION qf_reject_immutable_record_change()"
        )
        op.execute(
            """
            CREATE FUNCTION qf_validate_holdout_transition() RETURNS trigger AS $$
            BEGIN
              IF NOT (
                NEW.holdout_state = OLD.holdout_state OR
                (OLD.holdout_state = 'LOCKED' AND NEW.holdout_state = 'APPROVAL_PENDING') OR
                (OLD.holdout_state = 'APPROVAL_PENDING' AND NEW.holdout_state IN ('LOCKED', 'UNLOCKED')) OR
                (OLD.holdout_state = 'UNLOCKED' AND NEW.holdout_state = 'RUNNING') OR
                (OLD.holdout_state = 'RUNNING' AND NEW.holdout_state = 'EXPOSED') OR
                NEW.holdout_state = 'FAILED'
              ) THEN
                RAISE EXCEPTION 'invalid holdout state transition';
              END IF;
              IF NEW.exposure_count <> (CASE WHEN NEW.holdout_state = 'EXPOSED' THEN 1 ELSE 0 END) THEN
                RAISE EXCEPTION 'holdout exposure count is inconsistent';
              END IF;
              IF NEW.holdout_state = 'APPROVAL_PENDING' AND NOT EXISTS (
                SELECT 1 FROM approval_requests a
                WHERE a.validation_id = OLD.id AND a.status = 'PENDING'
              ) THEN
                RAISE EXCEPTION 'holdout approval evidence is missing';
              END IF;
              IF NEW.holdout_state IN ('UNLOCKED', 'RUNNING') AND NOT EXISTS (
                SELECT 1 FROM approval_requests a
                WHERE a.validation_id = OLD.id AND a.status = 'APPROVED'
              ) THEN
                RAISE EXCEPTION 'approved holdout evidence is missing';
              END IF;
              IF NEW.holdout_state = 'EXPOSED' AND NOT EXISTS (
                SELECT 1 FROM holdout_exposures e
                WHERE e.validation_id = OLD.id
                  AND e.strategy_version_id = NEW.strategy_version_id
              ) THEN
                RAISE EXCEPTION 'holdout exposure evidence is missing';
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            "CREATE TRIGGER qf_validations_holdout_transition BEFORE UPDATE OF "
            "holdout_state, exposure_count, strategy_version_id ON validations FOR EACH ROW "
            "EXECUTE FUNCTION qf_validate_holdout_transition()"
        )
        op.execute(
            """
            CREATE FUNCTION qf_validate_holdout_insert() RETURNS trigger AS $$
            BEGIN
              IF NEW.holdout_state <> 'LOCKED' OR NEW.exposure_count <> 0 THEN
                RAISE EXCEPTION 'validation must start locked without exposure evidence';
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            "CREATE TRIGGER qf_validations_holdout_insert BEFORE INSERT ON validations "
            "FOR EACH ROW EXECUTE FUNCTION qf_validate_holdout_insert()"
        )
        op.execute(
            """
            CREATE FUNCTION qf_reject_approval_evidence_change() RETURNS trigger AS $$
            BEGIN
              IF TG_OP = 'DELETE' OR NEW.validation_id IS DISTINCT FROM OLD.validation_id
                 OR (NEW.status IS DISTINCT FROM OLD.status AND NOT EXISTS (
                   SELECT 1 FROM validations v
                   WHERE v.id = OLD.validation_id
                     AND v.holdout_state = 'APPROVAL_PENDING'
                     AND OLD.status = 'PENDING'
                 )) THEN
                IF EXISTS (SELECT 1 FROM validations v WHERE v.id = OLD.validation_id
                  AND ((v.holdout_state = 'APPROVAL_PENDING' AND OLD.status = 'PENDING')
                    OR (v.holdout_state IN ('UNLOCKED', 'RUNNING') AND OLD.status = 'APPROVED'))) THEN
                  RAISE EXCEPTION 'approval evidence is referenced by active validation';
                END IF;
              END IF;
              RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            "CREATE TRIGGER qf_approval_evidence_immutable BEFORE UPDATE OR DELETE ON "
            "approval_requests FOR EACH ROW EXECUTE FUNCTION qf_reject_approval_evidence_change()"
        )
        op.execute(
            """
            CREATE FUNCTION qf_reject_exposure_evidence_change() RETURNS trigger AS $$
            BEGIN
              IF EXISTS (SELECT 1 FROM validations v WHERE v.id = OLD.validation_id
                AND v.holdout_state = 'EXPOSED'
                AND v.strategy_version_id = OLD.strategy_version_id) THEN
                RAISE EXCEPTION 'exposure evidence is referenced by exposed validation';
              END IF;
              RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            "CREATE TRIGGER qf_exposure_evidence_immutable BEFORE UPDATE OR DELETE ON "
            "holdout_exposures FOR EACH ROW EXECUTE FUNCTION qf_reject_exposure_evidence_change()"
        )
        return
    for action in ("UPDATE", "DELETE"):
        op.execute(
            f"CREATE TRIGGER qf_records_{action.lower()}_immutable "
            f"BEFORE {action} ON records "
            "WHEN OLD.kind IN ('artifact', 'provenance') BEGIN "
            "SELECT RAISE(ABORT, 'immutable record cannot be changed'); END"
        )
    op.execute(
        "CREATE TRIGGER qf_validations_holdout_transition BEFORE UPDATE OF "
        "holdout_state, exposure_count, strategy_version_id ON validations WHEN NOT ("
        "NEW.holdout_state = OLD.holdout_state OR "
        "(OLD.holdout_state = 'LOCKED' AND NEW.holdout_state = 'APPROVAL_PENDING') OR "
        "(OLD.holdout_state = 'APPROVAL_PENDING' AND NEW.holdout_state IN ('LOCKED', 'UNLOCKED')) OR "
        "(OLD.holdout_state = 'UNLOCKED' AND NEW.holdout_state = 'RUNNING') OR "
        "(OLD.holdout_state = 'RUNNING' AND NEW.holdout_state = 'EXPOSED') OR "
        "NEW.holdout_state = 'FAILED') BEGIN SELECT RAISE(ABORT, "
        "'invalid holdout state transition'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_validations_holdout_binding BEFORE UPDATE OF "
        "holdout_state, exposure_count, strategy_version_id ON validations WHEN "
        "(NEW.exposure_count != CASE WHEN NEW.holdout_state = 'EXPOSED' THEN 1 ELSE 0 END) OR "
        "(NEW.holdout_state = 'APPROVAL_PENDING' AND NOT EXISTS (SELECT 1 FROM "
        "approval_requests a WHERE a.validation_id = OLD.id AND a.status = 'PENDING')) OR "
        "(NEW.holdout_state IN ('UNLOCKED', 'RUNNING') AND NOT EXISTS (SELECT 1 FROM "
        "approval_requests a WHERE a.validation_id = OLD.id AND a.status = 'APPROVED')) OR "
        "(NEW.holdout_state = 'EXPOSED' AND NOT EXISTS (SELECT 1 FROM "
        "holdout_exposures e WHERE e.validation_id = OLD.id AND "
        "e.strategy_version_id = NEW.strategy_version_id)) BEGIN SELECT RAISE(ABORT, "
        "'holdout state lacks durable evidence'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_validations_holdout_insert BEFORE INSERT ON validations "
        "WHEN NEW.holdout_state != 'LOCKED' OR NEW.exposure_count != 0 BEGIN "
        "SELECT RAISE(ABORT, 'validation must start locked without exposure evidence'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_approval_evidence_immutable BEFORE UPDATE OF status, validation_id "
        "ON approval_requests WHEN EXISTS (SELECT 1 FROM validations v WHERE v.id = OLD.validation_id "
        "AND ((v.holdout_state = 'APPROVAL_PENDING' AND OLD.status = 'PENDING') OR "
        "(v.holdout_state IN ('UNLOCKED', 'RUNNING') AND OLD.status = 'APPROVED'))) "
        "AND (NEW.validation_id IS NOT OLD.validation_id OR "
        "(NEW.status IS NOT OLD.status AND NOT EXISTS (SELECT 1 FROM validations v2 "
        "WHERE v2.id = OLD.validation_id AND v2.holdout_state = 'APPROVAL_PENDING' "
        "AND OLD.status = 'PENDING'))) BEGIN SELECT "
        "RAISE(ABORT, 'approval evidence is referenced by active validation'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_approval_evidence_delete_immutable BEFORE DELETE ON approval_requests "
        "WHEN EXISTS (SELECT 1 FROM validations v WHERE v.id = OLD.validation_id AND "
        "((v.holdout_state = 'APPROVAL_PENDING' AND OLD.status = 'PENDING') OR "
        "(v.holdout_state IN ('UNLOCKED', 'RUNNING') AND OLD.status = 'APPROVED'))) BEGIN SELECT "
        "RAISE(ABORT, 'approval evidence is referenced by active validation'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_exposure_evidence_update_immutable BEFORE UPDATE ON holdout_exposures "
        "WHEN EXISTS (SELECT 1 FROM validations v WHERE v.id = OLD.validation_id AND "
        "v.holdout_state = 'EXPOSED' AND v.strategy_version_id = OLD.strategy_version_id) BEGIN "
        "SELECT RAISE(ABORT, 'exposure evidence is referenced by exposed validation'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_exposure_evidence_delete_immutable BEFORE DELETE ON holdout_exposures "
        "WHEN EXISTS (SELECT 1 FROM validations v WHERE v.id = OLD.validation_id AND "
        "v.holdout_state = 'EXPOSED' AND v.strategy_version_id = OLD.strategy_version_id) BEGIN "
        "SELECT RAISE(ABORT, 'exposure evidence is referenced by exposed validation'); END"
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER qf_validations_holdout_transition ON validations")
        op.execute("DROP FUNCTION qf_validate_holdout_transition()")
        op.execute("DROP TRIGGER qf_validations_holdout_insert ON validations")
        op.execute("DROP FUNCTION qf_validate_holdout_insert()")
        op.execute("DROP TRIGGER qf_approval_evidence_immutable ON approval_requests")
        op.execute("DROP FUNCTION qf_reject_approval_evidence_change()")
        op.execute("DROP TRIGGER qf_exposure_evidence_immutable ON holdout_exposures")
        op.execute("DROP FUNCTION qf_reject_exposure_evidence_change()")
        op.execute("DROP TRIGGER qf_records_immutable ON records")
        op.execute("DROP FUNCTION qf_reject_immutable_record_change()")
        return
    for action in ("update", "delete"):
        op.execute(f"DROP TRIGGER qf_records_{action}_immutable")
    op.execute("DROP TRIGGER qf_validations_holdout_binding")
    op.execute("DROP TRIGGER qf_validations_holdout_transition")
    op.execute("DROP TRIGGER qf_validations_holdout_insert")
    op.execute("DROP TRIGGER qf_approval_evidence_immutable")
    op.execute("DROP TRIGGER qf_approval_evidence_delete_immutable")
    op.execute("DROP TRIGGER qf_exposure_evidence_update_immutable")
    op.execute("DROP TRIGGER qf_exposure_evidence_delete_immutable")
