"""Create the frozen UX-001 Bootstrap Control DB relations."""

import hashlib
import json
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision = "ux001_control_v1"
down_revision = None
branch_labels = None
depends_on = None


def _sqlite_audit_hash(
    sequence,
    event_id,
    event_type,
    actor_principal,
    access_key_id,
    session_id_sha256,
    configuration_revision,
    database_connection_revision,
    before_sha256,
    after_sha256,
    masked_summary,
    previous_event_hash,
    created_at,
):
    if isinstance(masked_summary, str):
        try:
            masked_summary = json.loads(masked_summary)
        except json.JSONDecodeError:
            pass
    created_at = str(created_at)
    try:
        parsed = datetime.fromisoformat(created_at.replace(" ", "T"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        created_at = parsed.astimezone(UTC).isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )
    except ValueError:
        pass
    payload = {
        "sequence": sequence,
        "event_id": event_id,
        "event_type": event_type,
        "actor_principal": actor_principal,
        "access_key_id": access_key_id,
        "session_id_sha256": session_id_sha256,
        "configuration_revision": configuration_revision,
        "database_connection_revision": database_connection_revision,
        "before_sha256": before_sha256,
        "after_sha256": after_sha256,
        "masked_summary": masked_summary,
        "previous_event_hash": previous_event_hash,
        "created_at": created_at,
    }
    return hashlib.sha256(
        _canonical_json(payload).encode()
    ).hexdigest()


def _canonical_json(value):
    """Match PostgreSQL jsonb output ordering for the control audit vector."""
    if isinstance(value, dict):
        items = sorted(
            value.items(),
            key=lambda item: (len(str(item[0]).encode()), str(item[0]).encode()),
        )
        return "{" + ",".join(
            f"{json.dumps(str(key), ensure_ascii=False)}:{_canonical_json(item)}"
            for key, item in items
        ) + "}"
    if isinstance(value, list):
        return "[" + ",".join(_canonical_json(item) for item in value) + "]"
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name not in {"postgresql", "sqlite"}:
        raise RuntimeError("UX-001 control migration supports PostgreSQL and SQLite only")
    op.create_table(
        "general_access_keys",
        sa.Column("key_id", sa.String(40), primary_key=True),
        sa.Column("label", sa.String(80), nullable=False),
        sa.Column("verifier_phc", sa.String(512), nullable=False),
        sa.Column("hash_algorithm", sa.String(16), nullable=False),
        sa.Column("hash_parameters_version", sa.String(64), nullable=False),
        sa.Column("per_key_salt", sa.LargeBinary, nullable=False),
        sa.Column("pepper_key_id", sa.String(128), nullable=False),
        sa.Column("masked_hint", sa.String(32), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True)),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revision", sa.Integer, nullable=False),
    )
    op.create_table(
        "bootstrap_state",
        sa.Column("singleton_key", sa.String(32), primary_key=True),
        sa.Column("installation_id", sa.String(128), nullable=False),
        sa.Column("schema_version", sa.String(64), nullable=False),
        sa.Column("readiness_state", sa.String(32), nullable=False),
        sa.Column(
            "active_configuration_revision",
            sa.BigInteger,
        ),
        sa.Column(
            "last_known_good_configuration_revision",
            sa.BigInteger,
        ),
        sa.Column(
            "active_database_connection_revision",
            sa.BigInteger,
        ),
        sa.Column(
            "last_known_good_database_connection_revision",
            sa.BigInteger,
        ),
        sa.Column("auth_epoch", sa.BigInteger, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "singleton_key = 'BOOTSTRAP-DEFAULT'",
            name="bootstrap_state_singleton_key_check",
        ),
    )
    op.create_table(
        "configuration_catalog",
        sa.Column("key", sa.String(160), primary_key=True),
        sa.Column("group", sa.String(64), nullable=False),
        sa.Column("schema_version", sa.Integer, nullable=False),
        sa.Column("scope", sa.String(32), nullable=False),
        sa.Column("sensitivity", sa.String(16), nullable=False),
        sa.Column("apply_mode", sa.String(32), nullable=False),
        sa.Column("consumers", sa.JSON, nullable=False),
        sa.Column("dependencies", sa.JSON, nullable=False),
        sa.Column("value_schema", sa.JSON, nullable=False),
        sa.Column("validator", sa.String(160), nullable=False),
        sa.Column("safe_range", sa.JSON),
        sa.Column("default_for_first_materialization", sa.JSON),
        sa.Column("deprecated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "configuration_revisions",
        sa.Column("revision", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "base_revision",
            sa.BigInteger,
            sa.ForeignKey("configuration_revisions.revision"),
        ),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("catalog_version", sa.String(64), nullable=False),
        sa.Column("snapshot_sha256", sa.String(64), nullable=False),
        sa.Column("actor_principal", sa.String(16), nullable=False),
        sa.Column("validation_status", sa.String(16), nullable=False),
        sa.Column("failure_code", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True)),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "owner_sessions",
        sa.Column("session_id", sa.String(80), primary_key=True),
        sa.Column("token_sha256", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "access_key_id",
            sa.String(40),
            sa.ForeignKey("general_access_keys.key_id"),
            nullable=False,
        ),
        sa.Column("csrf_verifier_sha256", sa.String(64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idle_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("absolute_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("revoke_reason", sa.String(128)),
        sa.Column("auth_epoch", sa.BigInteger, nullable=False),
    )
    op.create_table(
        "configuration_values",
        sa.Column(
            "revision",
            sa.BigInteger,
            sa.ForeignKey("configuration_revisions.revision"),
            primary_key=True,
        ),
        sa.Column(
            "key",
            sa.String(160),
            sa.ForeignKey("configuration_catalog.key"),
            primary_key=True,
        ),
        sa.Column("typed_value", sa.JSON),
        sa.Column("ciphertext", sa.LargeBinary),
        sa.Column("secret_key_id", sa.String(128)),
        sa.Column("value_sha256", sa.String(64), nullable=False),
        sa.CheckConstraint(
            "(typed_value IS NULL) <> (ciphertext IS NULL)",
            name="configuration_values_exactly_one_value",
        ),
    )
    op.create_table(
        "active_configuration",
        sa.Column("singleton_key", sa.String(32), primary_key=True),
        sa.Column(
            "active_revision",
            sa.BigInteger,
            sa.ForeignKey("configuration_revisions.revision"),
            nullable=False,
        ),
        sa.Column(
            "last_known_good_revision",
            sa.BigInteger,
            sa.ForeignKey("configuration_revisions.revision"),
            nullable=False,
        ),
        sa.Column(
            "candidate_revision",
            sa.BigInteger,
            sa.ForeignKey("configuration_revisions.revision"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "singleton_key = 'CONFIGURATION-DEFAULT'",
            name="active_configuration_singleton_key_check",
        ),
    )
    op.create_table(
        "configuration_consumer_states",
        sa.Column("consumer", sa.String(80), primary_key=True),
        sa.Column(
            "desired_revision",
            sa.BigInteger,
            sa.ForeignKey("configuration_revisions.revision"),
            nullable=False,
        ),
        sa.Column(
            "applied_revision",
            sa.BigInteger,
            sa.ForeignKey("configuration_revisions.revision"),
        ),
        sa.Column("ack", sa.String(16), nullable=False),
        sa.Column("error_code", sa.String(128)),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("instance_id", sa.String(128), nullable=False),
        sa.Column("build_sha", sa.String(64), nullable=False),
    )
    op.create_table(
        "domain_database_connection_revisions",
        sa.Column("revision", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column(
            "base_revision",
            sa.BigInteger,
            sa.ForeignKey("domain_database_connection_revisions.revision"),
        ),
        sa.Column("nonsecret_payload", sa.JSON, nullable=False),
        sa.Column("ciphertext_envelope", sa.LargeBinary, nullable=False),
        sa.Column("secret_key_id", sa.String(128)),
        sa.Column("validation_sha256", sa.String(64)),
        sa.Column("failure_code", sa.String(128)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("validated_at", sa.DateTime(timezone=True)),
        sa.Column("activated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "bootstrap_audit_events",
        sa.Column("sequence", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(80), nullable=False, unique=True),
        sa.Column("event_type", sa.String(48), nullable=False),
        sa.Column("actor_principal", sa.String(16), nullable=False),
        sa.Column("access_key_id", sa.String(40)),
        sa.Column("session_id_sha256", sa.String(64)),
        sa.Column("configuration_revision", sa.BigInteger),
        sa.Column("database_connection_revision", sa.BigInteger),
        sa.Column("before_sha256", sa.String(64)),
        sa.Column("after_sha256", sa.String(64)),
        sa.Column("masked_summary", sa.JSON, nullable=False),
        sa.Column("previous_event_hash", sa.String(64)),
        sa.Column("event_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "control_idempotency_records",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("principal", sa.String(128), nullable=False),
        sa.Column("operation", sa.String(128), nullable=False),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("request_sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("response_status", sa.Integer),
        sa.Column("response_body", sa.JSON),
        sa.Column("response_headers", sa.JSON),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "principal",
            "operation",
            "idempotency_key",
            name="uq_control_idempotency_principal_operation_key",
        ),
    )
    if bind.dialect.name == "sqlite":
        raw_connection = bind.connection.driver_connection
        raw_connection.create_function("qf_bootstrap_audit_hash", 13, _sqlite_audit_hash)
        op.execute(sa.text("PRAGMA foreign_keys=ON"))
        if bind.execute(sa.text("PRAGMA foreign_keys")).scalar_one() != 1:
            raise RuntimeError("SQLite control migration requires foreign_keys=ON")
        with op.batch_alter_table("bootstrap_state", recreate="always") as batch:
            batch.create_foreign_key(
                "fk_bootstrap_state_active_configuration_revision",
                "configuration_revisions",
                ["active_configuration_revision"],
                ["revision"],
            )
            batch.create_foreign_key(
                "fk_bootstrap_state_last_known_good_configuration_revision",
                "configuration_revisions",
                ["last_known_good_configuration_revision"],
                ["revision"],
            )
            batch.create_foreign_key(
                "fk_bootstrap_state_active_database_connection_revision",
                "domain_database_connection_revisions",
                ["active_database_connection_revision"],
                ["revision"],
            )
            batch.create_foreign_key(
                "fk_bootstrap_state_last_known_good_database_connection_revision",
                "domain_database_connection_revisions",
                ["last_known_good_database_connection_revision"],
                ["revision"],
            )
    else:
        op.create_foreign_key(
            "fk_bootstrap_state_active_configuration_revision",
            "bootstrap_state",
            "configuration_revisions",
            ["active_configuration_revision"],
            ["revision"],
        )
        op.create_foreign_key(
            "fk_bootstrap_state_last_known_good_configuration_revision",
            "bootstrap_state",
            "configuration_revisions",
            ["last_known_good_configuration_revision"],
            ["revision"],
        )
        op.create_foreign_key(
            "fk_bootstrap_state_active_database_connection_revision",
            "bootstrap_state",
            "domain_database_connection_revisions",
            ["active_database_connection_revision"],
            ["revision"],
        )
        op.create_foreign_key(
            "fk_bootstrap_state_last_known_good_database_connection_revision",
            "bootstrap_state",
            "domain_database_connection_revisions",
            ["last_known_good_database_connection_revision"],
            ["revision"],
        )
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
        op.execute(
            """
            CREATE FUNCTION qf_validate_configuration_value() RETURNS trigger AS $$
            DECLARE sensitivity_value TEXT;
            BEGIN
              SELECT sensitivity INTO sensitivity_value
              FROM configuration_catalog WHERE key = NEW.key;
              IF sensitivity_value = 'SECRET' AND (
                   NEW.ciphertext IS NULL OR NEW.secret_key_id IS NULL OR NEW.typed_value IS NOT NULL
                 ) THEN
                RAISE EXCEPTION 'secret configuration values require ciphertext and key metadata';
              END IF;
              IF sensitivity_value <> 'SECRET' AND (
                   NEW.ciphertext IS NOT NULL OR NEW.secret_key_id IS NOT NULL OR NEW.typed_value IS NULL
                 ) THEN
                RAISE EXCEPTION 'non-secret configuration values require typed_value only';
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE FUNCTION qf_validate_configuration_catalog_sensitivity() RETURNS trigger AS $$
            BEGIN
              IF NEW.sensitivity = 'SECRET' AND EXISTS (
                SELECT 1 FROM configuration_values
                WHERE key = NEW.key AND (
                  ciphertext IS NULL OR secret_key_id IS NULL OR typed_value IS NOT NULL
                )
              ) THEN
                RAISE EXCEPTION 'catalog sensitivity change leaves plaintext configuration values';
              END IF;
              IF NEW.sensitivity <> 'SECRET' AND EXISTS (
                SELECT 1 FROM configuration_values
                WHERE key = NEW.key AND (
                  ciphertext IS NOT NULL OR secret_key_id IS NOT NULL OR typed_value IS NULL
                )
              ) THEN
                RAISE EXCEPTION 'catalog sensitivity change leaves encrypted configuration values';
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            "CREATE TRIGGER qf_configuration_catalog_sensitivity BEFORE UPDATE OF sensitivity "
            "ON configuration_catalog FOR EACH ROW EXECUTE FUNCTION "
            "qf_validate_configuration_catalog_sensitivity()"
        )
        op.execute(
            "CREATE TRIGGER qf_configuration_values_sensitivity BEFORE INSERT OR UPDATE "
            "ON configuration_values FOR EACH ROW EXECUTE FUNCTION qf_validate_configuration_value()"
        )
        op.execute(
            """
            CREATE FUNCTION qf_canonical_jsonb(value JSONB) RETURNS TEXT AS $$
            DECLARE result TEXT;
            BEGIN
              CASE jsonb_typeof(value)
                WHEN 'object' THEN
                  SELECT '{' || COALESCE(string_agg(
                    to_jsonb(key)::text || ':' || qf_canonical_jsonb(item),
                    ',' ORDER BY octet_length(key), convert_to(key, 'UTF8')
                  ), '') || '}' INTO result
                  FROM jsonb_each(value) AS entries(key, item);
                WHEN 'array' THEN
                  SELECT '[' || COALESCE(string_agg(
                    qf_canonical_jsonb(item), ',' ORDER BY ordinal
                  ), '') || ']' INTO result
                  FROM jsonb_array_elements(value) WITH ORDINALITY AS entries(item, ordinal);
                ELSE
                  result := value::text;
              END CASE;
              RETURN result;
            END;
            $$ LANGUAGE plpgsql IMMUTABLE
            """
        )
        op.execute(
            """
            CREATE FUNCTION qf_validate_bootstrap_audit_insert() RETURNS trigger AS $$
            DECLARE tail_hash TEXT;
            DECLARE tail_sequence BIGINT;
            BEGIN
              PERFORM pg_advisory_xact_lock(hashtextextended('qf-bootstrap-audit', 0));
              SELECT sequence, event_hash INTO tail_sequence, tail_hash FROM bootstrap_audit_events
              ORDER BY sequence DESC LIMIT 1 FOR UPDATE;
              IF NEW.sequence IS NULL OR NEW.sequence <= COALESCE(tail_sequence, 0) THEN
                NEW.sequence := COALESCE(tail_sequence, 0) + 1;
              END IF;
              IF NEW.previous_event_hash IS DISTINCT FROM tail_hash THEN
                RAISE EXCEPTION 'bootstrap audit hash chain is disconnected';
              END IF;
              NEW.event_hash := encode(digest(convert_to(
                qf_canonical_jsonb(jsonb_build_object(
                  'sequence', NEW.sequence,
                  'event_id', NEW.event_id,
                  'event_type', NEW.event_type,
                  'actor_principal', NEW.actor_principal,
                  'access_key_id', NEW.access_key_id,
                  'session_id_sha256', NEW.session_id_sha256,
                  'configuration_revision', NEW.configuration_revision,
                  'database_connection_revision', NEW.database_connection_revision,
                  'before_sha256', NEW.before_sha256,
                  'after_sha256', NEW.after_sha256,
                  'masked_summary', NEW.masked_summary,
                  'previous_event_hash', NEW.previous_event_hash,
                  'created_at', to_char(NEW.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US"Z"')
                )),
                'UTF8'
              ), 'sha256'), 'hex');
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            "CREATE TRIGGER qf_bootstrap_audit_append_only BEFORE INSERT ON "
            "bootstrap_audit_events FOR EACH ROW EXECUTE FUNCTION qf_validate_bootstrap_audit_insert()"
        )
        op.execute(
            """
            CREATE FUNCTION qf_reject_bootstrap_audit_change() RETURNS trigger AS $$
            BEGIN
              RAISE EXCEPTION 'bootstrap audit events are append-only';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            "CREATE TRIGGER qf_bootstrap_audit_immutable BEFORE UPDATE OR DELETE ON "
            "bootstrap_audit_events FOR EACH ROW EXECUTE FUNCTION qf_reject_bootstrap_audit_change()"
        )
        op.execute(
            "CREATE TRIGGER qf_bootstrap_audit_no_truncate BEFORE TRUNCATE ON "
            "bootstrap_audit_events FOR EACH STATEMENT EXECUTE FUNCTION qf_reject_bootstrap_audit_change()"
        )
        return
    op.execute(
        "CREATE TRIGGER qf_configuration_values_sensitivity BEFORE INSERT ON configuration_values "
        "WHEN ((SELECT sensitivity FROM configuration_catalog WHERE key = NEW.key) = 'SECRET' "
        "AND (NEW.ciphertext IS NULL OR NEW.secret_key_id IS NULL OR NEW.typed_value IS NOT NULL)) OR "
        "((SELECT sensitivity FROM configuration_catalog WHERE key = NEW.key) != 'SECRET' "
        "AND (NEW.ciphertext IS NOT NULL OR NEW.secret_key_id IS NOT NULL OR NEW.typed_value IS NULL)) "
        "BEGIN SELECT RAISE(ABORT, 'configuration value sensitivity mismatch'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_configuration_catalog_sensitivity BEFORE UPDATE OF sensitivity "
        "ON configuration_catalog WHEN NEW.sensitivity != OLD.sensitivity AND ("
        "(NEW.sensitivity = 'SECRET' AND EXISTS (SELECT 1 FROM configuration_values v "
        "WHERE v.key = NEW.key AND (v.ciphertext IS NULL OR v.secret_key_id IS NULL OR v.typed_value IS NOT NULL))) OR "
        "(NEW.sensitivity != 'SECRET' AND EXISTS (SELECT 1 FROM configuration_values v "
        "WHERE v.key = NEW.key AND (v.ciphertext IS NOT NULL OR v.secret_key_id IS NOT NULL OR v.typed_value IS NULL)))"
        ") BEGIN SELECT RAISE(ABORT, 'catalog sensitivity change conflicts with values'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_configuration_values_sensitivity_update BEFORE UPDATE ON configuration_values "
        "WHEN ((SELECT sensitivity FROM configuration_catalog WHERE key = NEW.key) = 'SECRET' "
        "AND (NEW.ciphertext IS NULL OR NEW.secret_key_id IS NULL OR NEW.typed_value IS NOT NULL)) OR "
        "((SELECT sensitivity FROM configuration_catalog WHERE key = NEW.key) != 'SECRET' "
        "AND (NEW.ciphertext IS NOT NULL OR NEW.secret_key_id IS NOT NULL OR NEW.typed_value IS NULL)) "
        "BEGIN SELECT RAISE(ABORT, 'configuration value sensitivity mismatch'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_bootstrap_audit_append_only BEFORE INSERT ON bootstrap_audit_events "
        "WHEN NEW.sequence IS NULL OR NEW.sequence <= 0 OR "
        "NEW.sequence <> COALESCE((SELECT MAX(sequence) FROM bootstrap_audit_events), 0) + 1 OR "
        "EXISTS (SELECT 1 FROM bootstrap_audit_events WHERE event_id = NEW.event_id) OR "
        "NEW.previous_event_hash IS NOT (SELECT event_hash FROM bootstrap_audit_events "
        "ORDER BY sequence DESC LIMIT 1) OR NEW.event_hash IS NOT qf_bootstrap_audit_hash("
        "NEW.sequence, NEW.event_id, NEW.event_type, NEW.actor_principal, NEW.access_key_id, "
        "NEW.session_id_sha256, NEW.configuration_revision, NEW.database_connection_revision, "
        "NEW.before_sha256, NEW.after_sha256, NEW.masked_summary, NEW.previous_event_hash, "
        "NEW.created_at) BEGIN SELECT RAISE(ABORT, "
        "'bootstrap audit hash chain or event hash is invalid'); END"
    )
    for action in ("UPDATE", "DELETE"):
        op.execute(
            f"CREATE TRIGGER qf_bootstrap_audit_{action.lower()}_immutable BEFORE {action} "
            "ON bootstrap_audit_events BEGIN SELECT RAISE(ABORT, "
            "'bootstrap audit events are append-only'); END"
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS qf_configuration_values_sensitivity "
            "ON configuration_values"
        )
        op.execute(
            "DROP TRIGGER IF EXISTS qf_configuration_catalog_sensitivity "
            "ON configuration_catalog"
        )
        op.execute(
            "DROP TRIGGER IF EXISTS qf_bootstrap_audit_append_only "
            "ON bootstrap_audit_events"
        )
        op.execute(
            "DROP TRIGGER IF EXISTS qf_bootstrap_audit_immutable "
            "ON bootstrap_audit_events"
        )
        op.execute(
            "DROP TRIGGER IF EXISTS qf_bootstrap_audit_no_truncate "
            "ON bootstrap_audit_events"
        )
    for table_name in (
        "control_idempotency_records",
        "configuration_values",
        "owner_sessions",
        "bootstrap_audit_events",
        "configuration_consumer_states",
        "active_configuration",
        "bootstrap_state",
        "domain_database_connection_revisions",
        "configuration_revisions",
        "configuration_catalog",
        "general_access_keys",
    ):
        op.drop_table(table_name)
    if bind.dialect.name == "postgresql":
        for function_name in (
            "qf_validate_configuration_value",
            "qf_validate_configuration_catalog_sensitivity",
            "qf_validate_bootstrap_audit_insert",
            "qf_canonical_jsonb",
            "qf_reject_bootstrap_audit_change",
        ):
            op.execute(f"DROP FUNCTION IF EXISTS {function_name}()")
