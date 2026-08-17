"""Create the frozen UX-001 Bootstrap Control DB relations."""

from alembic import op
import sqlalchemy as sa

revision = "ux001_control_v1"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        sa.Column("base_revision", sa.BigInteger),
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
    )
    op.create_table(
        "configuration_consumer_states",
        sa.Column("consumer", sa.String(80), primary_key=True),
        sa.Column("desired_revision", sa.BigInteger, nullable=False),
        sa.Column("applied_revision", sa.BigInteger),
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
        sa.Column("base_revision", sa.BigInteger),
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
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
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
            "CREATE TRIGGER qf_configuration_values_sensitivity BEFORE INSERT OR UPDATE "
            "ON configuration_values FOR EACH ROW EXECUTE FUNCTION qf_validate_configuration_value()"
        )
        op.execute(
            """
            CREATE FUNCTION qf_validate_bootstrap_audit_insert() RETURNS trigger AS $$
            DECLARE tail_hash TEXT;
            BEGIN
              PERFORM pg_advisory_xact_lock(hashtextextended('qf-bootstrap-audit', 0));
              SELECT event_hash INTO tail_hash FROM bootstrap_audit_events
              ORDER BY sequence DESC LIMIT 1 FOR UPDATE;
              IF NEW.previous_event_hash IS DISTINCT FROM tail_hash THEN
                RAISE EXCEPTION 'bootstrap audit hash chain is disconnected';
              END IF;
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
        "CREATE TRIGGER qf_configuration_values_sensitivity_update BEFORE UPDATE ON configuration_values "
        "WHEN ((SELECT sensitivity FROM configuration_catalog WHERE key = NEW.key) = 'SECRET' "
        "AND (NEW.ciphertext IS NULL OR NEW.secret_key_id IS NULL OR NEW.typed_value IS NOT NULL)) OR "
        "((SELECT sensitivity FROM configuration_catalog WHERE key = NEW.key) != 'SECRET' "
        "AND (NEW.ciphertext IS NOT NULL OR NEW.secret_key_id IS NOT NULL OR NEW.typed_value IS NULL)) "
        "BEGIN SELECT RAISE(ABORT, 'configuration value sensitivity mismatch'); END"
    )
    op.execute(
        "CREATE TRIGGER qf_bootstrap_audit_append_only BEFORE INSERT ON bootstrap_audit_events "
        "WHEN NEW.previous_event_hash IS NOT (SELECT event_hash FROM bootstrap_audit_events "
        "ORDER BY sequence DESC LIMIT 1) BEGIN SELECT RAISE(ABORT, "
        "'bootstrap audit hash chain is disconnected'); END"
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
            "DROP TRIGGER IF EXISTS qf_bootstrap_audit_append_only "
            "ON bootstrap_audit_events"
        )
        op.execute(
            "DROP TRIGGER IF EXISTS qf_bootstrap_audit_immutable "
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
            "qf_validate_bootstrap_audit_insert",
            "qf_reject_bootstrap_audit_change",
        ):
            op.execute(f"DROP FUNCTION IF EXISTS {function_name}()")
