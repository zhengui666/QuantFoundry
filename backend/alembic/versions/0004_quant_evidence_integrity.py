"""Protect artifact and provenance metadata as immutable evidence.

Revision ID: 0004_quant_evidence_integrity
Revises: 0003_runtime_integrity
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0004_quant_evidence_integrity"
down_revision = "0003_runtime_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name not in {"postgresql", "sqlite"}:
        raise RuntimeError(
            "0004 evidence migration supports PostgreSQL and SQLite only"
        )
    if bind.dialect.name == "postgresql":
        bind.execute(
            sa.text(
                "LOCK TABLE validations, approval_requests, strategy_versions, "
                "holdout_exposures IN ACCESS EXCLUSIVE MODE"
            )
        )
    elif bind.dialect.name == "sqlite":
        if bind.in_transaction():
            bind.execute(sa.text("UPDATE validations SET revision = revision WHERE 0"))
        else:
            bind.exec_driver_sql("BEGIN IMMEDIATE")
    invalid_legacy_row = bind.execute(
        sa.text(
            """
            SELECT v.id
            FROM validations v
            WHERE v.holdout_state IS NULL
               OR v.holdout_state NOT IN ('LOCKED', 'APPROVAL_PENDING', 'UNLOCKED', 'RUNNING', 'EXPOSED', 'FAILED')
               OR v.exposure_count IS NULL
               OR v.exposure_count <> CASE WHEN v.holdout_state = 'EXPOSED' THEN 1 ELSE 0 END
               OR (v.holdout_state = 'APPROVAL_PENDING' AND NOT EXISTS (
                    SELECT 1 FROM approval_requests a
                    JOIN strategy_versions sv ON sv.id = v.strategy_version_id
                    WHERE a.validation_id = v.id AND a.status = 'PENDING'
                      AND a.subject_spec_sha256 = sv.spec_sha256
               ))
               OR (v.holdout_state IN ('UNLOCKED', 'RUNNING', 'EXPOSED') AND NOT EXISTS (
                    SELECT 1 FROM approval_requests a
                    JOIN strategy_versions sv ON sv.id = v.strategy_version_id
                    WHERE a.validation_id = v.id AND a.status = 'APPROVED'
                      AND a.subject_spec_sha256 = sv.spec_sha256
               ))
               OR (v.holdout_state = 'EXPOSED' AND NOT EXISTS (
                    SELECT 1 FROM holdout_exposures e
                    JOIN approval_requests a ON a.id = e.approval_id
                    JOIN strategy_versions sv ON sv.id = e.strategy_version_id
                    WHERE e.validation_id = v.id
                      AND e.strategy_version_id = v.strategy_version_id
                      AND a.validation_id = v.id
                      AND a.status = 'APPROVED'
                      AND a.subject_spec_sha256 = sv.spec_sha256
               ))
            LIMIT 1
            """
        )
    ).scalar_one_or_none()
    if invalid_legacy_row is not None:
        raise RuntimeError(
            "0004 refuses to install evidence guards over invalid legacy validation "
            f"{invalid_legacy_row}; manual backfill required"
        )
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
                (OLD.holdout_state IN ('LOCKED', 'APPROVAL_PENDING', 'UNLOCKED', 'RUNNING')
                 AND NEW.holdout_state = 'FAILED')
              ) THEN
                RAISE EXCEPTION 'invalid holdout state transition';
              END IF;
              IF NEW.exposure_count <> (CASE WHEN NEW.holdout_state = 'EXPOSED' THEN 1 ELSE 0 END) THEN
                RAISE EXCEPTION 'holdout exposure count is inconsistent';
              END IF;
              IF NEW.holdout_state = 'APPROVAL_PENDING' THEN
                PERFORM 1
                FROM approval_requests a
                JOIN strategy_versions sv ON sv.id = NEW.strategy_version_id
                WHERE a.validation_id = OLD.id
                  AND a.status = 'PENDING'
                  AND a.subject_spec_sha256 = sv.spec_sha256
                ;
                IF NOT FOUND THEN
                  RAISE EXCEPTION 'holdout approval evidence is missing';
                END IF;
              END IF;
              IF NEW.holdout_state IN ('UNLOCKED', 'RUNNING', 'EXPOSED') THEN
                PERFORM 1
                FROM approval_requests a
                JOIN strategy_versions sv ON sv.id = NEW.strategy_version_id
                WHERE a.validation_id = OLD.id
                  AND a.status = 'APPROVED'
                  AND a.subject_spec_sha256 = sv.spec_sha256
                ;
                IF NOT FOUND THEN
                  RAISE EXCEPTION 'approved holdout evidence is missing';
                END IF;
              END IF;
              IF NEW.holdout_state = 'EXPOSED' THEN
                PERFORM 1
                FROM holdout_exposures e
                JOIN approval_requests a ON a.id = e.approval_id
                JOIN strategy_versions sv ON sv.id = e.strategy_version_id
                WHERE e.validation_id = OLD.id
                  AND e.strategy_version_id = NEW.strategy_version_id
                  AND a.validation_id = OLD.id
                  AND a.status = 'APPROVED'
                  AND a.subject_spec_sha256 = sv.spec_sha256
                ;
                IF NOT FOUND THEN
                  RAISE EXCEPTION 'holdout exposure evidence is missing';
                END IF;
              END IF;
              IF OLD.holdout_state <> 'LOCKED'
                 AND NEW.strategy_version_id IS DISTINCT FROM OLD.strategy_version_id THEN
                RAISE EXCEPTION 'holdout strategy binding is immutable after approval request';
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
              PERFORM 1 FROM validations WHERE id = OLD.validation_id FOR UPDATE;
              IF TG_OP = 'DELETE' OR NEW.validation_id IS DISTINCT FROM OLD.validation_id
                 OR NEW.subject_sha256 IS DISTINCT FROM OLD.subject_sha256
                 OR NEW.subject_type IS DISTINCT FROM OLD.subject_type
                 OR NEW.subject_id IS DISTINCT FROM OLD.subject_id
                 OR NEW.subject_version IS DISTINCT FROM OLD.subject_version
                 OR NEW.subject_revision IS DISTINCT FROM OLD.subject_revision
                 OR NEW.subject_spec_sha256 IS DISTINCT FROM OLD.subject_spec_sha256
                 OR NEW.prerequisites_sha256 IS DISTINCT FROM OLD.prerequisites_sha256
                 OR (NEW.status IS DISTINCT FROM OLD.status AND NOT (
                   OLD.status = 'PENDING' AND NEW.status <> 'PENDING' AND EXISTS (
                     SELECT 1 FROM validations v
                     WHERE v.id = OLD.validation_id
                       AND v.holdout_state = 'APPROVAL_PENDING'
                   )
                 )) THEN
                IF EXISTS (SELECT 1 FROM validations v WHERE v.id = OLD.validation_id
                  AND ((v.holdout_state IN ('APPROVAL_PENDING', 'FAILED') AND OLD.status = 'PENDING')
                    OR (v.holdout_state IN ('UNLOCKED', 'RUNNING', 'EXPOSED', 'FAILED')
                        AND OLD.status = 'APPROVED'))) THEN
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
            CREATE FUNCTION qf_sync_approval_validation() RETURNS trigger AS $$
            BEGIN
              IF OLD.status = 'PENDING' AND NEW.status <> 'PENDING' THEN
                UPDATE validations
                SET holdout_state = CASE
                      WHEN EXISTS (SELECT 1 FROM approval_requests a
                                   JOIN validations v ON v.id = NEW.validation_id
                                   JOIN strategy_versions sv ON sv.id = v.strategy_version_id
                                   WHERE a.validation_id = NEW.validation_id
                                     AND a.status = 'APPROVED'
                                     AND a.subject_spec_sha256 = sv.spec_sha256) THEN 'UNLOCKED'
                      WHEN EXISTS (SELECT 1 FROM approval_requests a
                                   JOIN validations v ON v.id = NEW.validation_id
                                   JOIN strategy_versions sv ON sv.id = v.strategy_version_id
                                   WHERE a.validation_id = NEW.validation_id
                                     AND a.status = 'PENDING'
                                     AND a.subject_spec_sha256 = sv.spec_sha256) THEN 'APPROVAL_PENDING'
                      ELSE 'LOCKED'
                    END,
                    revision = revision + 1
                WHERE id = NEW.validation_id AND holdout_state = 'APPROVAL_PENDING';
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            "CREATE TRIGGER qf_sync_approval_validation AFTER UPDATE OF status ON "
            "approval_requests FOR EACH ROW EXECUTE FUNCTION qf_sync_approval_validation()"
        )
        op.execute(
            """
            CREATE FUNCTION qf_reject_exposure_evidence_change() RETURNS trigger AS $$
            BEGIN
              PERFORM 1 FROM validations v
                WHERE v.id = OLD.validation_id FOR UPDATE;
              IF EXISTS (SELECT 1 FROM validations v WHERE v.id = OLD.validation_id
                AND v.holdout_state IN ('EXPOSED', 'FAILED')
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
        "(OLD.holdout_state IN ('LOCKED', 'APPROVAL_PENDING', 'UNLOCKED', 'RUNNING') AND "
        "NEW.holdout_state = 'FAILED')) BEGIN SELECT RAISE(ABORT, "
        "'invalid holdout state transition'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_validations_holdout_binding BEFORE UPDATE OF "
        "holdout_state, exposure_count, strategy_version_id ON validations WHEN "
        "(NEW.exposure_count != CASE WHEN NEW.holdout_state = 'EXPOSED' THEN 1 ELSE 0 END) OR "
        "(OLD.holdout_state != 'LOCKED' AND NEW.strategy_version_id IS NOT OLD.strategy_version_id) OR "
        "(NEW.holdout_state = 'APPROVAL_PENDING' AND NOT EXISTS (SELECT 1 FROM "
        "approval_requests a JOIN strategy_versions sv ON sv.id = NEW.strategy_version_id "
        "WHERE a.validation_id = OLD.id AND a.status = 'PENDING' AND "
        "a.subject_spec_sha256 IS sv.spec_sha256)) OR "
        "(NEW.holdout_state IN ('UNLOCKED', 'RUNNING', 'EXPOSED') AND NOT EXISTS (SELECT 1 FROM "
        "approval_requests a JOIN strategy_versions sv ON sv.id = NEW.strategy_version_id "
        "WHERE a.validation_id = OLD.id AND a.status = 'APPROVED' AND "
        "a.subject_spec_sha256 IS sv.spec_sha256)) OR "
        "(NEW.holdout_state = 'EXPOSED' AND NOT EXISTS (SELECT 1 FROM "
        "holdout_exposures e JOIN approval_requests a ON a.id = e.approval_id "
        "JOIN strategy_versions sv ON sv.id = e.strategy_version_id WHERE "
        "e.validation_id = OLD.id AND e.strategy_version_id = NEW.strategy_version_id AND "
        "a.validation_id = OLD.id AND a.status = 'APPROVED' AND "
        "a.subject_spec_sha256 IS sv.spec_sha256)) BEGIN SELECT RAISE(ABORT, "
        "'holdout state lacks durable evidence'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_validations_holdout_insert BEFORE INSERT ON validations "
        "WHEN NEW.holdout_state != 'LOCKED' OR NEW.exposure_count != 0 BEGIN "
        "SELECT RAISE(ABORT, 'validation must start locked without exposure evidence'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_approval_evidence_immutable BEFORE UPDATE "
        "ON approval_requests WHEN EXISTS (SELECT 1 FROM validations v WHERE v.id = OLD.validation_id "
        "AND ((v.holdout_state IN ('APPROVAL_PENDING', 'FAILED') AND OLD.status = 'PENDING') OR "
        "(v.holdout_state IN ('UNLOCKED', 'RUNNING', 'EXPOSED', 'FAILED') AND "
        "OLD.status = 'APPROVED'))) AND ("
        "NEW.validation_id IS NOT OLD.validation_id OR NEW.subject_sha256 IS NOT OLD.subject_sha256 OR "
        "NEW.subject_type IS NOT OLD.subject_type OR NEW.subject_id IS NOT OLD.subject_id OR "
        "NEW.subject_version IS NOT OLD.subject_version OR NEW.subject_revision IS NOT OLD.subject_revision OR "
        "NEW.subject_spec_sha256 IS NOT OLD.subject_spec_sha256 OR "
        "NEW.prerequisites_sha256 IS NOT OLD.prerequisites_sha256 OR "
        "(NEW.status IS NOT OLD.status AND NOT (OLD.status = 'PENDING' AND "
        "NEW.status != 'PENDING' AND EXISTS (SELECT 1 FROM validations v2 WHERE "
        "v2.id = OLD.validation_id AND v2.holdout_state = 'APPROVAL_PENDING')))) BEGIN SELECT "
        "RAISE(ABORT, 'approval evidence is referenced by active validation'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_approval_evidence_delete_immutable BEFORE DELETE ON approval_requests "
        "WHEN EXISTS (SELECT 1 FROM validations v WHERE v.id = OLD.validation_id AND "
        "((v.holdout_state IN ('APPROVAL_PENDING', 'FAILED') AND OLD.status = 'PENDING') OR "
        "(v.holdout_state IN ('UNLOCKED', 'RUNNING', 'EXPOSED', 'FAILED') AND "
        "OLD.status = 'APPROVED'))) BEGIN SELECT "
        "RAISE(ABORT, 'approval evidence is referenced by active validation'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_sync_approval_validation AFTER UPDATE OF status ON approval_requests "
        "WHEN OLD.status = 'PENDING' AND NEW.status != 'PENDING' BEGIN "
        "UPDATE validations SET holdout_state = CASE "
        "WHEN EXISTS (SELECT 1 FROM approval_requests a JOIN strategy_versions sv ON sv.id = (SELECT strategy_version_id FROM validations WHERE id = NEW.validation_id) WHERE a.validation_id = NEW.validation_id AND a.status = 'APPROVED' AND a.subject_spec_sha256 IS sv.spec_sha256) THEN 'UNLOCKED' "
        "WHEN EXISTS (SELECT 1 FROM approval_requests a JOIN strategy_versions sv ON sv.id = (SELECT strategy_version_id FROM validations WHERE id = NEW.validation_id) WHERE a.validation_id = NEW.validation_id AND a.status = 'PENDING' AND a.subject_spec_sha256 IS sv.spec_sha256) THEN 'APPROVAL_PENDING' "
        "ELSE 'LOCKED' END, revision = revision + 1 "
        "WHERE id = NEW.validation_id AND holdout_state = 'APPROVAL_PENDING'; END"
    )
    op.execute(
        "CREATE TRIGGER qf_exposure_evidence_update_immutable BEFORE UPDATE ON holdout_exposures "
        "WHEN EXISTS (SELECT 1 FROM validations v WHERE v.id = OLD.validation_id AND "
        "v.holdout_state IN ('EXPOSED', 'FAILED') AND "
        "v.strategy_version_id = OLD.strategy_version_id) BEGIN "
        "SELECT RAISE(ABORT, 'exposure evidence is referenced by exposed validation'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_exposure_evidence_delete_immutable BEFORE DELETE ON holdout_exposures "
        "WHEN EXISTS (SELECT 1 FROM validations v WHERE v.id = OLD.validation_id AND "
        "v.holdout_state IN ('EXPOSED', 'FAILED') AND "
        "v.strategy_version_id = OLD.strategy_version_id) BEGIN "
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
        op.execute("DROP TRIGGER qf_sync_approval_validation ON approval_requests")
        op.execute("DROP FUNCTION qf_sync_approval_validation()")
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
    op.execute("DROP TRIGGER qf_sync_approval_validation")
    op.execute("DROP TRIGGER qf_exposure_evidence_update_immutable")
    op.execute("DROP TRIGGER qf_exposure_evidence_delete_immutable")
