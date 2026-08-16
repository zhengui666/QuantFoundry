"""Bootstrap Control DB and the D2 control-plane HTTP slice."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import tempfile
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from functools import wraps
from pathlib import Path
from threading import RLock
from typing import Annotated, Any, cast
from urllib.parse import quote

import yaml
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi import Path as ApiPath
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from jsonschema import Draft202012Validator
from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    MetaData,
    String,
    UniqueConstraint,
    create_engine,
    desc,
    inspect,
    select,
    text,
    update,
)
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows has no supported deployment path
    fcntl = None

from app.generated_api_models import (
    ConfigurationActivateRequest,
    ConfigurationActive,
    ConfigurationCandidate,
    ConfigurationCandidateRequest,
    ConfigurationCatalog,
    ConfigurationCatalogEntry,
    ConfigurationRollbackRequest,
    ConfigurationValidationResult,
    ConfigurationValueView,
    DatabaseConnectionCandidate,
    DatabaseConnectionCandidateRequest,
    DatabaseConnectionCheck,
    DatabaseConnectionStatus,
    DatabaseConnectionValidationResult,
    GeneralAccessKeyCreateRequest,
    GeneralAccessKeyIssued,
    GeneralAccessKeyList,
    GeneralAccessKeyLoginRequest,
    GeneralAccessKeyMetadata,
    GeneralAccessKeyRenameRequest,
    OwnerSessionView,
    SessionBootstrapResponse,
    SetupCompleteRequest,
)
from app.generated_api_models import (
    ConfigurationConsumerState as ConfigurationConsumerStateSchema,
)

try:
    from app.provider_credentials import _master_key  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover - import is present in the application
    _master_key = None


CONTROL_SCHEMA_VERSION = "UX001_D1_R1"
CATALOG_VERSION = "UX001_D1_CATALOG_R1"
DOMAIN_ALEMBIC_HEAD = "0018_ux001_runtime_snapshots"
KEY_RE = re.compile(
    r"^(qfk_gak_(?P<id>[a-z0-9]{16,32}))\.(?P<secret>[A-Za-z0-9_-]{43,})$"
)
KEY_ID_RE = re.compile(r"^gak_[a-z0-9]{16,32}$")
SESSION_COOKIE = "qf_session"
PH = PasswordHasher()
DUMMY_VERIFIER = PH.hash("quantfoundry-invalid-access-key")
CONTROL_METADATA = MetaData()
_DOMAIN_SWITCH_LOCK = RLock()


def _serialize_domain_switch(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with _DOMAIN_SWITCH_LOCK:
            return function(*args, **kwargs)

    return wrapped


class ControlBase(DeclarativeBase):
    metadata = CONTROL_METADATA


class BootstrapState(ControlBase):
    __tablename__ = "bootstrap_state"
    singleton_key = Column(String(32), primary_key=True, default="BOOTSTRAP-DEFAULT")
    installation_id = Column(String(128), nullable=False)
    schema_version = Column(String(64), nullable=False)
    readiness_state = Column(String(32), nullable=False)
    active_configuration_revision = Column(BigInteger)
    last_known_good_configuration_revision = Column(BigInteger)
    active_database_connection_revision = Column(BigInteger)
    last_known_good_database_connection_revision = Column(BigInteger)
    auth_epoch = Column(BigInteger, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class GeneralAccessKey(ControlBase):
    __tablename__ = "general_access_keys"
    key_id = Column(String(40), primary_key=True)
    label = Column(String(80), nullable=False)
    verifier_phc = Column(String(512), nullable=False)
    hash_algorithm = Column(String(16), nullable=False, default="ARGON2ID")
    hash_parameters_version = Column(String(64), nullable=False, default="argon2id-v1")
    per_key_salt = Column(LargeBinary, nullable=False)
    pepper_key_id = Column(String(128), nullable=False)
    masked_hint = Column(String(32), nullable=False)
    status = Column(String(16), nullable=False, default="ACTIVE")
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False)
    last_used_at = Column(DateTime(timezone=True))
    revoked_at = Column(DateTime(timezone=True))
    revision = Column(Integer, nullable=False, default=1)


class OwnerSession(ControlBase):
    __tablename__ = "owner_sessions"
    session_id = Column(String(80), primary_key=True)
    token_sha256 = Column(String(64), nullable=False, unique=True)
    access_key_id = Column(
        String(40), ForeignKey("general_access_keys.key_id"), nullable=False
    )
    csrf_verifier_sha256 = Column(String(64), nullable=False)
    issued_at = Column(DateTime(timezone=True), nullable=False)
    last_seen_at = Column(DateTime(timezone=True), nullable=False)
    idle_expires_at = Column(DateTime(timezone=True), nullable=False)
    absolute_expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    revoke_reason = Column(String(128))
    auth_epoch = Column(BigInteger, nullable=False, default=1)


class ConfigurationCatalogRow(ControlBase):
    __tablename__ = "configuration_catalog"
    key = Column(String(160), primary_key=True)
    group = Column(String(64), nullable=False)
    schema_version = Column(Integer, nullable=False)
    scope = Column(String(32), nullable=False)
    sensitivity = Column(String(16), nullable=False)
    apply_mode = Column(String(32), nullable=False)
    consumers = Column(JSON, nullable=False)
    dependencies = Column(JSON, nullable=False)
    value_schema = Column(JSON, nullable=False)
    validator = Column(String(160), nullable=False)
    safe_range = Column(JSON)
    default_for_first_materialization = Column(JSON)
    deprecated_at = Column(DateTime(timezone=True))


class ConfigurationRevision(ControlBase):
    __tablename__ = "configuration_revisions"
    revision = Column(Integer, primary_key=True, autoincrement=True)
    base_revision = Column(BigInteger)
    state = Column(String(16), nullable=False)
    catalog_version = Column(String(64), nullable=False)
    snapshot_sha256 = Column(String(64), nullable=False)
    actor_principal = Column(String(16), nullable=False)
    validation_status = Column(String(16), nullable=False)
    failure_code = Column(String(128))
    created_at = Column(DateTime(timezone=True), nullable=False)
    validated_at = Column(DateTime(timezone=True))
    activated_at = Column(DateTime(timezone=True))


class ConfigurationValue(ControlBase):
    __tablename__ = "configuration_values"
    revision = Column(
        BigInteger, ForeignKey("configuration_revisions.revision"), primary_key=True
    )
    key = Column(String(160), ForeignKey("configuration_catalog.key"), primary_key=True)
    typed_value = Column(JSON)
    ciphertext = Column(LargeBinary)
    secret_key_id = Column(String(128))
    value_sha256 = Column(String(64), nullable=False)


class ActiveConfiguration(ControlBase):
    __tablename__ = "active_configuration"
    singleton_key = Column(
        String(32), primary_key=True, default="CONFIGURATION-DEFAULT"
    )
    active_revision = Column(BigInteger, nullable=False)
    last_known_good_revision = Column(BigInteger, nullable=False)
    candidate_revision = Column(BigInteger)
    updated_at = Column(DateTime(timezone=True), nullable=False)


class ConfigurationConsumerState(ControlBase):
    __tablename__ = "configuration_consumer_states"
    consumer = Column(String(80), primary_key=True)
    desired_revision = Column(BigInteger, nullable=False)
    applied_revision = Column(BigInteger)
    ack = Column(String(16), nullable=False)
    error_code = Column(String(128))
    heartbeat_at = Column(DateTime(timezone=True), nullable=False)
    instance_id = Column(String(128), nullable=False)
    build_sha = Column(String(64), nullable=False)


class DomainDatabaseConnectionRevision(ControlBase):
    __tablename__ = "domain_database_connection_revisions"
    revision = Column(Integer, primary_key=True, autoincrement=True)
    state = Column(String(16), nullable=False)
    base_revision = Column(BigInteger)
    nonsecret_payload = Column(JSON, nullable=False)
    ciphertext_envelope = Column(LargeBinary, nullable=False)
    validation_sha256 = Column(String(64))
    failure_code = Column(String(128))
    created_at = Column(DateTime(timezone=True), nullable=False)
    validated_at = Column(DateTime(timezone=True))
    activated_at = Column(DateTime(timezone=True))


class BootstrapAuditEvent(ControlBase):
    __tablename__ = "bootstrap_audit_events"
    sequence = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(80), nullable=False, unique=True)
    event_type = Column(String(48), nullable=False)
    actor_principal = Column(String(16), nullable=False)
    access_key_id = Column(String(40))
    session_id_sha256 = Column(String(64))
    configuration_revision = Column(BigInteger)
    database_connection_revision = Column(BigInteger)
    before_sha256 = Column(String(64))
    after_sha256 = Column(String(64))
    masked_summary = Column(JSON, nullable=False)
    previous_event_hash = Column(String(64))
    event_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)


class ControlIdempotencyRecord(ControlBase):
    __tablename__ = "control_idempotency_records"
    id = Column(Integer, primary_key=True, autoincrement=True)
    principal = Column(String(128), nullable=False)
    operation = Column(String(128), nullable=False)
    idempotency_key = Column(String(128), nullable=False)
    request_sha256 = Column(String(64), nullable=False)
    status = Column(String(16), nullable=False, default="PENDING")
    response_status = Column(Integer)
    response_body = Column(JSON)
    response_headers = Column(JSON)
    created_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    lease_expires_at = Column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        UniqueConstraint(
            "principal",
            "operation",
            "idempotency_key",
            name="uq_control_idempotency_principal_operation_key",
        ),
    )


def _control_path() -> Path:
    test_root = os.getenv("QF_TEST_RUNTIME_ROOT")
    if os.getenv("QF_ENV", "production") == "test" and test_root:
        return Path(test_root) / "control.db"
    data_root = os.getenv("QF_DATA_ROOT")
    if data_root:
        return Path(data_root) / "control.db"
    return Path.home() / ".quantfoundry" / "control.db"


def _engine():
    configured_url = os.getenv("QF_CONTROL_DB_URL")
    if configured_url:
        return create_engine(configured_url)
    path = _control_path()
    path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    return create_engine(f"sqlite:///{path}", connect_args={"check_same_thread": False})


CONTROL_ENGINE = _engine()
ControlSessionLocal = sessionmaker(bind=CONTROL_ENGINE, expire_on_commit=False)


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime | None) -> datetime | None:
    return (
        value.replace(tzinfo=UTC)
        if value is not None and value.tzinfo is None
        else value
    )


def _json_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _idempotency_fingerprint(values: dict[str, Any]) -> str:
    def normalize(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json", by_alias=True)
        if isinstance(value, dict):
            return {str(key): normalize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [normalize(item) for item in value]
        if isinstance(value, (Request, Response, Session)):
            return None
        return value

    return _json_hash(
        {
            key: normalize(value)
            for key, value in values.items()
            if key not in {"request", "response", "idempotency_key"}
        }
    )


def _encode_idempotent_result(
    result: Any, default_status: int
) -> tuple[int, Any, dict[str, str]]:
    status = int(getattr(result, "status_code", default_status))
    headers: dict[str, str] = {}
    if isinstance(result, Response):
        for name in ("etag", "location"):
            value = result.headers.get(name)
            if value is not None:
                headers[name] = value
        body = getattr(result, "body", None)
        if body in (None, b""):
            return status, None, headers
        if isinstance(body, memoryview):
            body = body.tobytes()
        try:
            return status, json.loads(body), headers
        except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
            return status, body.decode("utf-8"), headers
    if hasattr(result, "model_dump"):
        return status, result.model_dump(mode="json", by_alias=True), headers
    return status, jsonable_encoder(result), headers


def _replay_idempotent(record: ControlIdempotencyRecord) -> Response:
    if record.response_status == 204 or record.response_body is None:
        return Response(
            status_code=record.response_status or 200,
            headers=record.response_headers or {},
        )
    return JSONResponse(
        content=record.response_body,
        status_code=record.response_status or 200,
        headers=record.response_headers or {},
    )


def _with_idempotency(operation: str, success_status: int = 200):
    def decorate(function: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(function)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            request = kwargs.get("request")
            key = kwargs.get("idempotency_key")
            if not isinstance(request, Request) or not isinstance(key, str):
                return function(*args, **kwargs)
            cookie = request.cookies.get(SESSION_COOKIE)
            principal = (
                hashlib.sha256(cookie.encode()).hexdigest()
                if cookie
                else str(getattr(request.state, "actor", None) or "anonymous")
            )
            fingerprint = _idempotency_fingerprint(kwargs)
            now = _now()
            with ControlSessionLocal.begin() as db:
                record = db.scalar(
                    select(ControlIdempotencyRecord)
                    .where(
                        ControlIdempotencyRecord.principal == principal,
                        ControlIdempotencyRecord.operation == operation,
                        ControlIdempotencyRecord.idempotency_key == key,
                    )
                    .with_for_update()
                )
                if record is not None:
                    if record.request_sha256 != fingerprint:
                        return _problem(
                            409,
                            "IDEMPOTENCY_CONFLICT",
                            "idempotency key was reused for another request",
                        )
                    if record.status == "COMPLETED":
                        return _replay_idempotent(record)
                    lease_expires_at = _aware(record.lease_expires_at)
                    if lease_expires_at is not None and lease_expires_at > now:
                        return _problem(
                            409,
                            "IDEMPOTENCY_IN_PROGRESS",
                            "idempotent request is already in progress",
                        )
                    record.status = "PENDING"
                    record.lease_expires_at = now + timedelta(minutes=5)
                else:
                    record = ControlIdempotencyRecord(
                        principal=principal,
                        operation=operation,
                        idempotency_key=key,
                        request_sha256=fingerprint,
                        status="PENDING",
                        created_at=now,
                        lease_expires_at=now + timedelta(minutes=5),
                    )
                    db.add(record)
            try:
                result = function(*args, **kwargs)
            except Exception:
                with ControlSessionLocal.begin() as db:
                    failed = db.scalar(
                        select(ControlIdempotencyRecord).where(
                            ControlIdempotencyRecord.principal == principal,
                            ControlIdempotencyRecord.operation == operation,
                            ControlIdempotencyRecord.idempotency_key == key,
                        )
                    )
                    if failed is not None:
                        failed.status = "ABANDONED"
                        failed.lease_expires_at = _now()
                raise
            status, body, headers = _encode_idempotent_result(result, success_status)
            with ControlSessionLocal.begin() as db:
                completed = db.scalar(
                    select(ControlIdempotencyRecord).where(
                        ControlIdempotencyRecord.principal == principal,
                        ControlIdempotencyRecord.operation == operation,
                        ControlIdempotencyRecord.idempotency_key == key,
                    )
                )
                if completed is not None:
                    completed.status = "COMPLETED"
                    completed.response_status = status
                    completed.response_body = body
                    completed.response_headers = headers
                    completed.completed_at = _now()
                    completed.lease_expires_at = completed.completed_at
            return result

        return wrapped

    return decorate


def _catalog_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "docs/后端系统技术方案/contracts/configuration-catalog-v1.yaml"
    )


def _load_catalog_seed() -> list[dict[str, Any]]:
    document = yaml.safe_load(_catalog_path().read_text(encoding="utf-8"))
    if (
        document.get("catalog_version") != CATALOG_VERSION
        or document.get("status") != "FROZEN"
    ):
        raise RuntimeError("UX-001 configuration catalog is not frozen")
    return list(document["entries"])


def _upgrade_control_columns() -> None:
    """Add only forward-compatible nullable columns to pre-D2 local control DBs."""
    additions = {
        "general_access_keys": {
            "per_key_salt": "BLOB",
            "pepper_key_id": "VARCHAR(128)",
        },
        "configuration_catalog": {
            "default_for_first_materialization": "JSON",
            "deprecated_at": "DATETIME",
        },
    }
    with CONTROL_ENGINE.begin() as connection:
        for table, columns in additions.items():
            present = {
                column["name"] for column in inspect(connection).get_columns(table)
            }
            for name, sql_type in columns.items():
                if name not in present:
                    connection.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}")
                    )


def init_control_db() -> None:
    try:
        existing_tables = set(inspect(CONTROL_ENGINE).get_table_names())
    except SQLAlchemyError as error:
        raise RuntimeError(
            "BOOTSTRAP_LOCKED: control database is unreadable"
        ) from error
    expected_tables = set(CONTROL_METADATA.tables)
    missing = expected_tables - existing_tables
    if existing_tables and missing - {"control_idempotency_records"}:
        missing = ", ".join(sorted(missing - {"control_idempotency_records"}))
        raise RuntimeError(
            f"BOOTSTRAP_LOCKED: control schema is incomplete ({missing})"
        )
    CONTROL_METADATA.create_all(CONTROL_ENGINE)
    _upgrade_control_columns()
    with ControlSessionLocal.begin() as session:
        now = _now()
        state = session.get(BootstrapState, "BOOTSTRAP-DEFAULT")
        if state is None:
            state = BootstrapState(
                installation_id=f"inst_{secrets.token_urlsafe(18)}",
                schema_version=CONTROL_SCHEMA_VERSION,
                readiness_state="DATABASE_DISCONNECTED",
                auth_epoch=1,
                created_at=now,
                updated_at=now,
            )
            session.add(state)
        if session.execute(select(ConfigurationCatalogRow)).first() is None:
            for entry in _load_catalog_seed():
                session.add(
                    ConfigurationCatalogRow(
                        key=entry["key"],
                        group=entry["group"],
                        schema_version=entry["schema_version"],
                        scope=entry["scope"],
                        sensitivity=entry["sensitivity"],
                        apply_mode=entry["apply_mode"],
                        consumers=entry["consumers"],
                        dependencies=entry["dependencies"],
                        value_schema=entry["schema"],
                        validator=entry["validator"],
                        safe_range=entry.get("safe_range"),
                    )
                )
        active = session.get(ActiveConfiguration, "CONFIGURATION-DEFAULT")
        if active is None:
            revision = ConfigurationRevision(
                base_revision=None,
                state="ACTIVE",
                catalog_version=CATALOG_VERSION,
                snapshot_sha256=_json_hash({}),
                actor_principal="SYSTEM",
                validation_status="VALID",
                created_at=now,
                validated_at=now,
                activated_at=now,
            )
            session.add(revision)
            session.flush()
            session.add(
                ActiveConfiguration(
                    active_revision=revision.revision,
                    last_known_good_revision=revision.revision,
                    updated_at=now,
                )
            )
            state.active_configuration_revision = revision.revision
            state.last_known_good_configuration_revision = revision.revision
            state.updated_at = now


def _root_key() -> tuple[str, bytes]:
    if _master_key is None:
        raise RuntimeError("control encryption root unavailable")
    return _master_key()


def _peppered_secret(secret: str, salt: bytes) -> tuple[str, str]:
    key_id, root = _root_key()
    return hmac.new(root, salt + secret.encode(), hashlib.sha256).hexdigest(), key_id


def _seal(value: str, *, aad: bytes) -> tuple[bytes, str]:
    key_id, key = _root_key()
    nonce = secrets.token_bytes(12)
    return nonce + AESGCM(key).encrypt(nonce, value.encode(), aad), key_id


def _open(envelope: bytes, *, aad: bytes, key_id: str | None = None) -> str:
    configured_key_id, key = _root_key()
    if key_id is not None and not hmac.compare_digest(configured_key_id, key_id):
        raise ValueError("encryption key unavailable")
    if len(envelope) < 13:
        raise ValueError("encrypted value is malformed")
    nonce, ciphertext = envelope[:12], envelope[12:]
    try:
        return AESGCM(key).decrypt(nonce, ciphertext, aad).decode()
    except (InvalidTag, UnicodeDecodeError) as error:
        raise ValueError("encrypted value cannot be decrypted") from error


def _configuration_aad(
    session: Session, revision: int, key: str, schema_version: int
) -> bytes:
    state = session.get(BootstrapState, "BOOTSTRAP-DEFAULT")
    installation_id = state.installation_id if state else "unknown-installation"
    return f"qf-config:{installation_id}:{key}:{revision}:{schema_version}".encode()


def _key_parts(raw: str) -> tuple[str, str]:
    match = KEY_RE.fullmatch(raw)
    if match is None:
        raise ValueError("invalid general access key")
    return "gak_" + match.group("id"), match.group("secret")


@contextmanager
def _initial_claim_lock():
    """Serialize the trusted first-key ceremony across local processes."""
    lock_path = _control_path().with_name("control.db.claim.lock")
    lock_path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    with lock_path.open("a+") as handle:
        os.chmod(lock_path, 0o600)
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def issue_access_key(label: str, expires_at: datetime | None = None) -> str:
    """Trusted local installer primitive; no public first-claim endpoint exists."""
    if not label.strip():
        raise ValueError("label is required")
    key_id = "gak_" + "".join(
        secrets.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(20)
    )
    secret = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
    raw = f"qfk_{key_id}.{secret}"
    with _initial_claim_lock():
        with ControlSessionLocal.begin() as session:
            if (
                session.execute(
                    select(GeneralAccessKey).where(GeneralAccessKey.status == "ACTIVE")
                ).first()
                is not None
            ):
                raise RuntimeError(
                    "initial key already exists; use authenticated rotation"
                )
            now = _now()
            per_key_salt = secrets.token_bytes(16)
            peppered, pepper_key_id = _peppered_secret(secret, per_key_salt)
            session.add(
                GeneralAccessKey(
                    key_id=key_id,
                    label=label.strip(),
                    verifier_phc=PH.hash(peppered),
                    per_key_salt=per_key_salt,
                    pepper_key_id=pepper_key_id,
                    masked_hint=f"…{secret[-8:]}",
                    expires_at=expires_at,
                    created_at=now,
                    revision=1,
                )
            )
            _audit(session, "KEY_CREATED", key_id, {"label": label.strip()})
    return raw


def _audit(
    session: Session,
    event_type: str,
    key_id: str | None,
    summary: dict[str, Any],
    *,
    session_id: str | None = None,
    actor_principal: str | None = None,
    config_revision: int | None = None,
    db_revision: int | None = None,
) -> None:
    with _DOMAIN_SWITCH_LOCK:
        session.execute(
            select(BootstrapState)
            .where(BootstrapState.singleton_key == "BOOTSTRAP-DEFAULT")
            .with_for_update()
        ).scalar_one_or_none()
        previous = session.execute(
            select(BootstrapAuditEvent)
            .order_by(desc(BootstrapAuditEvent.sequence))
            .limit(1)
        ).scalar_one_or_none()
        sequence = (previous.sequence if previous is not None else 0) + 1
        previous_hash = previous.event_hash if previous else None
        now = _now()
        event_id = "BAUD-" + secrets.token_urlsafe(20).lower().replace(
            "_", "a"
        ).replace("-", "b")
        session_hash = (
            hashlib.sha256(session_id.encode()).hexdigest()
            if session_id is not None
            else None
        )
        event = {
            "sequence": sequence,
            "event_id": event_id,
            "event_type": event_type,
            "actor_principal": actor_principal or ("OWNER" if key_id else "SYSTEM"),
            "access_key_id": key_id,
            "session_id_sha256": session_hash,
            "configuration_revision": config_revision,
            "database_connection_revision": db_revision,
            "before_sha256": None,
            "after_sha256": None,
            "masked_summary": summary,
            "previous_event_hash": previous_hash,
            "created_at": now.isoformat(),
        }
        event_hash = _json_hash(event)
        session.add(
            BootstrapAuditEvent(
                sequence=sequence,
                event_id=event_id,
                event_type=event_type,
                actor_principal=event["actor_principal"],
                access_key_id=key_id,
                session_id_sha256=session_hash,
                configuration_revision=config_revision,
                database_connection_revision=db_revision,
                masked_summary=summary,
                previous_event_hash=previous_hash,
                event_hash=event_hash,
                created_at=now,
            )
        )


def _metadata(row: GeneralAccessKey) -> GeneralAccessKeyMetadata:
    return GeneralAccessKeyMetadata.model_validate(
        {
            "key_id": row.key_id,
            "label": row.label,
            "masked_hint": row.masked_hint,
            "status": row.status,
            "expires_at": _aware(row.expires_at),
            "last_used_at": _aware(row.last_used_at),
            "revision": row.revision,
            "created_at": _aware(row.created_at),
        }
    )


def _key_active(row: GeneralAccessKey, now: datetime) -> bool:
    expiry = _aware(row.expires_at)
    return row.status == "ACTIVE" and (expiry is None or expiry > now)


def _problem(status: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(
        {
            "type": f"https://quantfoundry.local/problems/{code.lower()}",
            "title": code,
            "status": status,
            "code": code,
            "detail": detail,
            "instance": None,
            "request_id": str(uuid.uuid4()),
            "retryable": False,
            "field_errors": [],
            "context": {},
        },
        status_code=status,
        media_type="application/problem+json",
    )


def _login_rate_limited(request: Request, session: Session) -> bool:
    source = request.client.host if request.client else "unknown"
    now = _now()
    source_hash = hashlib.sha256(source.encode()).hexdigest()
    failures = [
        event
        for event in session.scalars(
            select(BootstrapAuditEvent).where(
                BootstrapAuditEvent.event_type == "RATE_LIMIT",
                BootstrapAuditEvent.created_at >= now - timedelta(minutes=1),
            )
        )
        if event.masked_summary.get("source_sha256") == source_hash
    ]
    return len(failures) >= 8


def _record_login_failure(request: Request, session: Session) -> None:
    source = request.client.host if request.client else "unknown"
    _audit(
        session,
        "RATE_LIMIT",
        None,
        {"source_sha256": hashlib.sha256(source.encode()).hexdigest()},
    )
    session.commit()


def _session_context(request: Request) -> OwnerSession | JSONResponse:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return _problem(401, "UNAUTHENTICATED", "Authentication required")
    digest = hashlib.sha256(token.encode()).hexdigest()
    with ControlSessionLocal() as session:
        row = session.scalar(
            select(OwnerSession).where(OwnerSession.token_sha256 == digest)
        )
        key = session.get(GeneralAccessKey, row.access_key_id) if row else None
        state = session.get(BootstrapState, "BOOTSTRAP-DEFAULT")
        now = _now()
        absolute_expires_at = _aware(row.absolute_expires_at) if row else None
        idle_expires_at = _aware(row.idle_expires_at) if row else None
        if (
            row is None
            or key is None
            or row.revoked_at is not None
            or (state is not None and row.auth_epoch != state.auth_epoch)
            or absolute_expires_at <= now
            or idle_expires_at <= now
            or not _key_active(key, now)
        ):
            return _problem(401, "UNAUTHENTICATED", "Authentication required")
        row.last_seen_at = now
        row.idle_expires_at = min(now + timedelta(hours=12), absolute_expires_at)
        session.commit()
        request.state.control_session_id = row.session_id
        request.state.control_key_id = key.key_id
        return row


def require_session(request: Request) -> OwnerSession:
    value = _session_context(request)
    if isinstance(value, JSONResponse):
        raise RuntimeError("control session dependency must be installed by middleware")
    return value


def _csrf(request: Request, session: OwnerSession) -> JSONResponse | None:
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return None
    token = request.headers.get("X-CSRF-Token", "")
    if not token or not secrets.compare_digest(
        hashlib.sha256(token.encode()).hexdigest(), session.csrf_verifier_sha256
    ):
        return _problem(403, "CSRF_REQUIRED", "CSRF token required")
    if (
        request.method in {"POST", "PUT", "PATCH", "DELETE"}
        and request.app.state.environment != "test"
    ):
        origin = request.headers.get("Origin")
        fetch_site = request.headers.get("Sec-Fetch-Site")
        if (
            origin
            and origin.rstrip("/") != str(request.base_url).rstrip("/")
            and fetch_site != "same-origin"
        ):
            return _problem(403, "CSRF_REQUIRED", "same-origin request required")
    return None


def control_db_session():
    with ControlSessionLocal() as session:
        yield session


def _if_match(value: str | None, prefix: str, current: int) -> JSONResponse | None:
    if value is None:
        return _problem(428, "PRECONDITION_REQUIRED", "If-Match is required")
    if value not in {str(current), f'W/"{prefix}:{current}"'}:
        return _problem(412, "REVISION_MISMATCH", "revision does not match")
    return None


def _csrf_session(request: Request) -> tuple[OwnerSession, JSONResponse | None]:
    if getattr(request.state, "allow_test_bearer_control", False):
        return (None, None)  # type: ignore[return-value]
    value = _session_context(request)
    if isinstance(value, JSONResponse):
        return (None, value)  # type: ignore[return-value]
    return value, _csrf(request, value)


def _session_view(session: OwnerSession, csrf_token: str) -> OwnerSessionView:
    return OwnerSessionView.model_validate(
        {
            "principal": "OWNER",
            "auth_method": "GENERAL_ACCESS_KEY",
            "key_id": session.access_key_id,
            "issued_at": _aware(session.issued_at),
            "last_seen_at": _aware(session.last_seen_at),
            "expires_at": _aware(session.absolute_expires_at),
            "csrf_token": csrf_token,
        }
    )


def _value_view(
    session: Session, row: ConfigurationValue, catalog: ConfigurationCatalogRow
) -> ConfigurationValueView:
    is_secret = catalog.sensitivity == "SECRET" or row.ciphertext is not None
    return ConfigurationValueView.model_validate(
        {
            "key": row.key,
            "sensitivity": catalog.sensitivity,
            "configured": row.ciphertext is not None or row.typed_value is not None,
            "value": None if is_secret else row.typed_value,
            "masked_hint": "configured"
            if is_secret and row.ciphertext is not None
            else None,
        }
    )


def _effective_value_rows(
    session: Session, revision: int
) -> dict[str, ConfigurationValue]:
    rows: dict[str, ConfigurationValue] = {}
    seen: set[int] = set()
    current: int | None = revision
    while current is not None:
        if current in seen:
            raise RuntimeError("configuration revision base cycle detected")
        seen.add(current)
        revision_row = session.get(ConfigurationRevision, current)
        if revision_row is None:
            raise RuntimeError("configuration revision base is missing")
        for row in session.scalars(
            select(ConfigurationValue).where(ConfigurationValue.revision == current)
        ):
            rows.setdefault(row.key, row)
        current = revision_row.base_revision
    return rows


def _effective_values(session: Session, revision: int) -> list[ConfigurationValueView]:
    rows = _effective_value_rows(session, revision)
    catalogs = {
        row.key: row for row in session.scalars(select(ConfigurationCatalogRow))
    }
    return [
        _value_view(session, row, catalogs[row.key])
        for row in rows.values()
        if row.key in catalogs
    ]


def _catalog_view(session: Session) -> ConfigurationCatalog:
    entries = [
        ConfigurationCatalogEntry.model_validate(
            {
                "key": row.key,
                "group": row.group,
                "schema_version": row.schema_version,
                "scope": row.scope,
                "sensitivity": row.sensitivity,
                "apply_mode": row.apply_mode,
                "consumers": row.consumers,
                "dependencies": row.dependencies,
                "schema": row.value_schema,
                "validator": row.validator,
                "safe_range": row.safe_range,
            }
        )
        for row in session.scalars(
            select(ConfigurationCatalogRow).order_by(ConfigurationCatalogRow.key)
        )
    ]
    return ConfigurationCatalog.model_validate(
        {
            "catalog_version": CATALOG_VERSION,
            "entries": [
                item.model_dump(mode="json", by_alias=True) for item in entries
            ],
        }
    )


def _config_active(session: Session) -> dict[str, Any]:
    active = session.scalar(
        select(ActiveConfiguration).where(
            ActiveConfiguration.singleton_key == "CONFIGURATION-DEFAULT"
        )
    )
    if active is None:
        raise RuntimeError("active configuration is not initialized")
    states = [
        ConfigurationConsumerStateSchema.model_validate(
            {
                "consumer": row.consumer,
                "desired_revision": row.desired_revision,
                "applied_revision": row.applied_revision,
                "ack": row.ack,
                "error_code": row.error_code,
                "heartbeat_at": _aware(row.heartbeat_at),
            }
        ).model_dump(mode="json")
        for row in session.scalars(
            select(ConfigurationConsumerState).order_by(
                ConfigurationConsumerState.consumer
            )
        )
    ]
    return {
        "active_revision": active.active_revision,
        "last_known_good_revision": active.last_known_good_revision,
        "catalog_version": CATALOG_VERSION,
        "values": [
            item.model_dump(mode="json")
            for item in _effective_values(session, active.active_revision)
        ],
        "snapshot_sha256": session.scalar(
            select(ConfigurationRevision.snapshot_sha256).where(
                ConfigurationRevision.revision == active.active_revision
            )
        ),
        "consumer_states": states,
        "updated_at": _aware(active.updated_at),
    }


def activate_configuration_revision(
    revision: int, if_match: str | None
) -> tuple[dict[str, Any] | JSONResponse, int]:
    """Activate one validated Control DB revision with a singleton CAS."""
    with ControlSessionLocal.begin() as db:
        active = db.get(ActiveConfiguration, "CONFIGURATION-DEFAULT")
        current_revision = active.active_revision if active else 1
        mismatch = _if_match(if_match, "config", current_revision)
        if mismatch is not None:
            return mismatch, current_revision
        candidate = db.get(ConfigurationRevision, revision)
        if candidate is None:
            return _problem(
                404, "RESOURCE_NOT_FOUND", "configuration revision not found"
            ), current_revision
        if (
            active is not None
            and active.active_revision == revision
            and candidate.state == "ACTIVE"
        ):
            return _config_active(db), revision
        if candidate.state != "VALIDATED":
            return _problem(
                409, "CONFIGURATION_VALIDATION_FAILED", "candidate is not validated"
            ), current_revision
        old_revision = active.active_revision if active else revision
        if active is None:
            db.add(
                ActiveConfiguration(
                    active_revision=revision,
                    last_known_good_revision=revision,
                    updated_at=_now(),
                )
            )
        else:
            result = db.execute(
                update(ActiveConfiguration)
                .where(
                    ActiveConfiguration.singleton_key == "CONFIGURATION-DEFAULT",
                    ActiveConfiguration.active_revision == old_revision,
                )
                .values(
                    active_revision=revision,
                    last_known_good_revision=old_revision,
                    candidate_revision=None,
                    updated_at=_now(),
                )
            )
            if result.rowcount != 1:
                return _problem(
                    412, "REVISION_MISMATCH", "revision does not match"
                ), current_revision
        candidate.state = "ACTIVE"
        candidate.activated_at = _now()
        for consumer in sorted(
            {
                consumer
                for row in db.scalars(select(ConfigurationCatalogRow))
                for consumer in row.consumers
            }
        ):
            state = db.get(ConfigurationConsumerState, consumer)
            if state is None:
                db.add(
                    ConfigurationConsumerState(
                        consumer=consumer,
                        desired_revision=revision,
                        applied_revision=None,
                        ack="PENDING",
                        heartbeat_at=_now(),
                        instance_id="control-plane",
                        build_sha="0" * 64,
                    )
                )
            else:
                state.desired_revision = revision
                state.ack = "PENDING"
                state.error_code = None
                state.heartbeat_at = _now()
        bootstrap = db.get(BootstrapState, "BOOTSTRAP-DEFAULT")
        if bootstrap is not None:
            bootstrap.active_configuration_revision = revision
            bootstrap.last_known_good_configuration_revision = old_revision
            bootstrap.updated_at = _now()
        _audit(
            db,
            "CONFIG_ACTIVATED",
            None,
            {"revision": revision},
            config_revision=revision,
        )
        return _config_active(db), revision


def active_runtime_snapshot() -> dict[str, Any]:
    """Return the non-secret singleton runtime projection for Agent admission."""
    with ControlSessionLocal() as session:
        active = session.get(ActiveConfiguration, "CONFIGURATION-DEFAULT")
        revision = active.active_revision if active else 1
        snapshot_hash = session.scalar(
            select(ConfigurationRevision.snapshot_sha256).where(
                ConfigurationRevision.revision == revision
            )
        ) or ("0" * 64)
        model = "unconfigured"
        provider = "unconfigured"
        row = _effective_value_rows(session, revision).get("ai.remote_codex")
        catalog = session.get(ConfigurationCatalogRow, "ai.remote_codex")
        if row is not None and row.ciphertext is not None and catalog is not None:
            try:
                payload = json.loads(
                    _open(
                        row.ciphertext,
                        aad=_configuration_aad(
                            session, row.revision, row.key, catalog.schema_version
                        ),
                        key_id=row.secret_key_id,
                    )
                )
                if isinstance(payload, dict):
                    model = str(payload.get("model") or model)
                    provider = str(
                        payload.get("provider")
                        or ("remote-codex" if model != "unconfigured" else provider)
                    )
            except (ValueError, TypeError, json.JSONDecodeError):
                pass
        return {
            "effective_configuration_revision": revision,
            "effective_configuration_sha256": snapshot_hash,
            "ai_connection_id": "CODEX-DEFAULT",
            "ai_connection_revision": revision,
            "model_provider": provider,
            "model_name": model,
            "runtime_identity": "CODEX-DEFAULT",
        }


def active_remote_codex_connection() -> dict[str, Any] | None:
    with ControlSessionLocal() as session:
        active = session.get(ActiveConfiguration, "CONFIGURATION-DEFAULT")
        if active is None:
            return None
        row = _effective_value_rows(session, active.active_revision).get(
            "ai.remote_codex"
        )
        catalog = session.get(ConfigurationCatalogRow, "ai.remote_codex")
        if row is None or catalog is None or row.ciphertext is None:
            return None
        try:
            payload = json.loads(
                _open(
                    row.ciphertext,
                    aad=_configuration_aad(
                        session, row.revision, row.key, catalog.schema_version
                    ),
                    key_id=row.secret_key_id,
                )
            )
        except (ValueError, TypeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None


def _candidate_view(
    session: Session, revision: ConfigurationRevision
) -> ConfigurationCandidate:
    return ConfigurationCandidate.model_validate(
        {
            "revision": revision.revision,
            "state": revision.state,
            "base_revision": revision.base_revision or 1,
            "catalog_version": revision.catalog_version,
            "values": [
                item.model_dump(mode="json")
                for item in _effective_values(session, revision.revision)
            ],
            "snapshot_sha256": revision.snapshot_sha256,
            "created_at": _aware(revision.created_at),
        }
    )


def _database_candidate_view(
    row: DomainDatabaseConnectionRevision,
) -> DatabaseConnectionCandidate:
    payload = row.nonsecret_payload
    return DatabaseConnectionCandidate.model_validate(
        {
            "revision": row.revision,
            "state": row.state,
            "base_revision": row.base_revision or 1,
            "host": payload["host"],
            "port": payload["port"],
            "database": payload["database"],
            "tls_mode": payload["tls_mode"],
            "username_masked": payload["username_masked"],
            "password_configured": bool(payload.get("password_configured")),
            "client_key_configured": bool(payload.get("client_key_configured")),
            "pool_profile": payload.get("pool_profile"),
            "created_at": _aware(row.created_at),
        }
    )


def _database_secret(row: DomainDatabaseConnectionRevision) -> dict[str, str]:
    value = json.loads(
        _open(
            row.ciphertext_envelope, aad=f"qf-domain-database:{row.revision}".encode()
        )
    )
    return value if isinstance(value, dict) else {}


def _database_url(
    row: DomainDatabaseConnectionRevision, secret: dict[str, str]
) -> tuple[str, dict[str, Any], str | None]:
    payload = row.nonsecret_payload
    username = quote(str(payload["username"]), safe="")
    password = quote(str(secret.get("password", "")), safe="")
    auth = f"{username}:{password}" if password else username
    url = f"postgresql+psycopg://{auth}@{payload['host']}:{payload['port']}/{quote(str(payload['database']), safe='')}"
    tls_mode = payload["tls_mode"]
    connect_args: dict[str, Any] = {
        "connect_timeout": 5,
        "sslmode": {
            "DISABLED": "disable",
            "VERIFY_CA": "verify-ca",
            "VERIFY_FULL": "verify-full",
        }[tls_mode],
    }
    ca_path: str | None = None
    if tls_mode != "DISABLED":
        ca_pem = secret.get("ca_certificate_pem")
        if not ca_pem:
            raise ValueError("TLS CA certificate is required")
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", delete=False
        ) as handle:
            handle.write(ca_pem)
            ca_path = handle.name
        connect_args["sslrootcert"] = ca_path
    return url, connect_args, ca_path


def _probe_database(
    row: DomainDatabaseConnectionRevision,
) -> tuple[list[DatabaseConnectionCheck], str | None]:
    secret = _database_secret(row)
    ca_path: str | None = None
    probe_engine: Any | None = None
    checks: list[DatabaseConnectionCheck] = []
    try:
        url, connect_args, ca_path = _database_url(row, secret)
        probe_engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
        with probe_engine.connect() as connection:
            checks.append(
                DatabaseConnectionCheck(
                    name="NETWORK", status="PASS", detail="reachable"
                )
            )
            checks.append(
                DatabaseConnectionCheck(name="TLS", status="PASS", detail="negotiated")
            )
            checks.append(
                DatabaseConnectionCheck(
                    name="CREDENTIAL", status="PASS", detail="accepted"
                )
            )
            version = int(
                connection.exec_driver_sql(
                    "SELECT current_setting('server_version_num')"
                ).scalar_one()
            )
            checks.append(
                DatabaseConnectionCheck(
                    name="POSTGRES_VERSION",
                    status="PASS",
                    detail=f"major {version // 10000}",
                )
            )
            privilege = bool(
                connection.exec_driver_sql(
                    "SELECT has_schema_privilege(current_user, current_schema(), 'USAGE')"
                ).scalar_one()
            )
            checks.append(
                DatabaseConnectionCheck(
                    name="PRIVILEGE",
                    status="PASS" if privilege else "FAIL",
                    detail="schema usage",
                )
            )
            alembic = connection.exec_driver_sql(
                "SELECT to_regclass('public.alembic_version')"
            ).scalar_one_or_none()
            checks.append(
                DatabaseConnectionCheck(
                    name="SCHEMA",
                    status="PASS" if alembic else "FAIL",
                    detail="migration table present",
                )
            )
            migration_head = (
                connection.exec_driver_sql(
                    "SELECT version_num FROM public.alembic_version LIMIT 1"
                ).scalar_one_or_none()
                if alembic
                else None
            )
            migration_compatible = migration_head == DOMAIN_ALEMBIC_HEAD
            checks.append(
                DatabaseConnectionCheck(
                    name="MIGRATION_COMPATIBILITY",
                    status="PASS" if migration_compatible else "FAIL",
                    detail=(
                        f"migration head {migration_head}"
                        if migration_head
                        else "migration head missing"
                    ),
                )
            )
            failure = (
                None
                if privilege and alembic and migration_compatible
                else "DATABASE_SCHEMA_INCOMPATIBLE"
            )
    except (SQLAlchemyError, OSError, ValueError, KeyError, TypeError, RuntimeError):
        checks = [
            DatabaseConnectionCheck(
                name=name,
                status="FAIL" if name in {"NETWORK", "CREDENTIAL"} else "SKIPPED",
                detail="probe failed",
            )
            for name in (
                "NETWORK",
                "TLS",
                "CREDENTIAL",
                "POSTGRES_VERSION",
                "PRIVILEGE",
                "SCHEMA",
                "MIGRATION_COMPATIBILITY",
            )
        ]
        failure = "DATABASE_CONNECTION_FAILED"
    finally:
        if probe_engine is not None:
            probe_engine.dispose()
        if ca_path:
            try:
                Path(ca_path).unlink(missing_ok=True)
            except OSError:
                pass
    return checks, failure


@_serialize_domain_switch
def _rebind_domain_database(
    row: DomainDatabaseConnectionRevision,
) -> tuple[Any, Any]:
    """Switch the domain session factory only after a fresh canary succeeds."""
    secret = _database_secret(row)
    url, connect_args, ca_path = _database_url(row, secret)
    candidate_engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    try:
        with candidate_engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1").scalar_one()
        from app import main as domain_main
        from quantfoundry.api import app as canonical_main

        previous_engine = domain_main.engine
        domain_main.SessionLocal.configure(bind=candidate_engine)
        domain_main.engine = candidate_engine
        domain_main.app.state.domain_database_available = True
        # The worker/scheduler import the canonical module directly while the
        # compatibility API imports ``app.main``. Keep both bindings in sync
        # after a control-plane database activation.
        canonical_main.SessionLocal.configure(bind=candidate_engine)
        canonical_main.engine = candidate_engine
        canonical_main.app.state.domain_database_available = True
        if ca_path:
            candidate_engine._qf_ca_path = ca_path  # type: ignore[attr-defined]
        return previous_engine, candidate_engine
    except (SQLAlchemyError, OSError, ValueError, KeyError, TypeError, RuntimeError):
        candidate_engine.dispose()
        if ca_path:
            try:
                Path(ca_path).unlink(missing_ok=True)
            except OSError:
                pass
        raise


@_serialize_domain_switch
def _restore_domain_database(previous_engine: Any, candidate_engine: Any) -> None:
    """Restore the prior binding before a control-plane transaction rolls back."""
    from app import main as domain_main
    from quantfoundry.api import app as canonical_main

    domain_main.SessionLocal.configure(bind=previous_engine)
    domain_main.engine = previous_engine
    canonical_main.SessionLocal.configure(bind=previous_engine)
    canonical_main.engine = previous_engine
    canonical_main.app.state.domain_database_available = True
    candidate_engine.dispose()
    ca_path = getattr(candidate_engine, "_qf_ca_path", None)
    if ca_path:
        try:
            Path(ca_path).unlink(missing_ok=True)
        except OSError:
            pass


def restore_active_domain_database() -> None:
    """Restore the persisted ACTIVE binding without consulting runtime env config."""
    from app import main as domain_main
    from quantfoundry.api import app as canonical_main

    production = os.getenv("QF_ENVIRONMENT", os.getenv("QF_ENV", "production")) in {
        "production",
        "staging",
    }
    with ControlSessionLocal() as db:
        active = db.scalar(
            select(DomainDatabaseConnectionRevision)
            .where(DomainDatabaseConnectionRevision.state == "ACTIVE")
            .order_by(desc(DomainDatabaseConnectionRevision.revision))
        )
    if active is None:
        available = not production and not domain_main.DB_URL.startswith(
            "postgresql+psycopg://qf-unavailable@127.0.0.1:1/"
        )
        domain_main.app.state.domain_database_available = available
        canonical_main.app.state.domain_database_available = available
        return
    checks, failure = _probe_database(active)
    if failure is not None:
        with ControlSessionLocal.begin() as db:
            state = db.get(BootstrapState, "BOOTSTRAP-DEFAULT")
            if state is not None:
                state.readiness_state = "DEGRADED"
                state.updated_at = _now()
        domain_main.app.state.domain_database_available = False
        canonical_main.app.state.domain_database_available = False
        return
    try:
        _rebind_domain_database(active)
    except (SQLAlchemyError, OSError, ValueError, KeyError, TypeError, RuntimeError):
        domain_main.app.state.domain_database_available = False
        canonical_main.app.state.domain_database_available = False
        return
    domain_main.app.state.domain_database_available = True
    canonical_main.app.state.domain_database_available = True


def _sync_domain_compat_setup(workspace_id: str | None = None) -> None:
    """Materialize the legacy domain binding from the active installation rows."""
    try:
        from quantfoundry.api.app import (
            CostModelVersionRow,
            ModelProviderConnectionRow,
            Record,
            ResearchPolicyVersionRow,
            RiskPolicyVersionRow,
            SessionLocal,
            SetupBindingRow,
        )
        from quantfoundry.infrastructure.db.schema import canonical_workspace_id

        workspace_id = workspace_id or canonical_workspace_id("system")
        with SessionLocal.begin() as db:
            ai = db.scalar(
                select(ModelProviderConnectionRow)
                .where(
                    ModelProviderConnectionRow.workspace_id == workspace_id,
                    ModelProviderConnectionRow.kind == "AI",
                    ModelProviderConnectionRow.validation_state == "SUCCESS",
                )
                .order_by(ModelProviderConnectionRow.validated_at.desc())
            )
            research_policy = db.scalar(
                select(ResearchPolicyVersionRow)
                .where(
                    ResearchPolicyVersionRow.workspace_id == workspace_id,
                    ResearchPolicyVersionRow.policy_family == "research",
                    ResearchPolicyVersionRow.status == "ACTIVE",
                )
                .order_by(ResearchPolicyVersionRow.activated_at.desc())
            )
            risk_policy = db.scalar(
                select(RiskPolicyVersionRow)
                .where(
                    RiskPolicyVersionRow.workspace_id == workspace_id,
                    RiskPolicyVersionRow.status == "ACTIVE",
                )
                .order_by(RiskPolicyVersionRow.activated_at.desc())
            )
            cost_model = db.scalar(
                select(CostModelVersionRow)
                .where(
                    CostModelVersionRow.workspace_id == workspace_id,
                    CostModelVersionRow.status == "ACTIVE",
                )
                .order_by(CostModelVersionRow.activated_at.desc())
            )
            if any(
                item is None for item in (ai, research_policy, risk_policy, cost_model)
            ):
                return
            data = db.scalar(
                select(ModelProviderConnectionRow)
                .where(
                    ModelProviderConnectionRow.workspace_id == workspace_id,
                    ModelProviderConnectionRow.kind == "DATA",
                    ModelProviderConnectionRow.validation_state == "SUCCESS",
                )
                .order_by(ModelProviderConnectionRow.validated_at.desc())
            )
            timestamp = datetime.now(UTC)
            settings = db.scalar(
                select(Record).where(
                    Record.workspace_id == workspace_id,
                    Record.record_key == "SETTINGS-DEFAULT",
                )
            )
            settings_body = {
                "settings_id": "SETTINGS-DEFAULT",
                "revision": settings.revision + 1 if settings else 1,
                "ai_connection_id": ai.id,
                "default_data_provider_id": data.provider_id if data else None,
                "research_policy_id": research_policy.policy_id,
                "risk_policy_id": risk_policy.policy_id,
                "cost_model_id": cost_model.cost_model_id,
                "language": "zh-CN",
                "timezone": "Asia/Shanghai",
                "base_currency": "CNY",
                "number_format_locale": "zh-CN",
                "default_benchmark": "CSI300",
                "default_frequency": "DAILY",
                "initial_paper_capital": "100000",
                "created_at": timestamp.isoformat(),
                "updated_at": timestamp.isoformat(),
            }
            if settings is None:
                settings = Record(
                    workspace_id=workspace_id,
                    record_key="SETTINGS-DEFAULT",
                    kind="settings",
                    revision=1,
                    body=json.dumps(settings_body),
                    created_at=timestamp,
                    updated_at=timestamp,
                )
                db.add(settings)
                db.flush()
            else:
                settings.kind = "settings"
                settings.revision = settings_body["revision"]
                settings.body = json.dumps(settings_body)
                settings.updated_at = timestamp
            binding = db.get(SetupBindingRow, workspace_id)
            if binding is None:
                db.add(
                    SetupBindingRow(
                        workspace_id=workspace_id,
                        settings_record_id="SETTINGS-DEFAULT",
                        ai_connection_id=ai.id,
                        data_connection_id=data.id if data else None,
                        research_policy_version_id=research_policy.id,
                        risk_policy_version_id=risk_policy.id,
                        cost_model_version_id=cost_model.id,
                        revision=1,
                        created_at=timestamp,
                        updated_at=timestamp,
                    )
                )
            else:
                binding.ai_connection_id = ai.id
                binding.data_connection_id = data.id if data else None
                binding.research_policy_version_id = research_policy.id
                binding.risk_policy_version_id = risk_policy.id
                binding.cost_model_version_id = cost_model.id
                binding.revision += 1
                binding.updated_at = timestamp
    except (ImportError, OSError, SQLAlchemyError, RuntimeError, ValueError, TypeError):
        return


def build_router() -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    @router.post(
        "/auth/login",
        response_model=SessionBootstrapResponse,
        operation_id="loginWithGeneralAccessKey",
    )
    def login(
        data: GeneralAccessKeyLoginRequest,
        request: Request,
        response: Response,
        session: Session = Depends(control_db_session),
    ):
        if _login_rate_limited(request, session):
            _record_login_failure(request, session)
            return _problem(
                429, "UNAUTHENTICATED", "Authentication temporarily unavailable"
            )
        try:
            key_id, secret = _key_parts(data.key)
        except ValueError:
            _record_login_failure(request, session)
            return _problem(401, "UNAUTHENTICATED", "Authentication failed")
        key = session.get(GeneralAccessKey, key_id)
        now = _now()
        valid = key is not None and _key_active(key, now)
        try:
            peppered, pepper_key_id = _peppered_secret(
                secret, key.per_key_salt if key and key.per_key_salt else b"\0" * 16
            )
            verifier = key.verifier_phc if key and key.verifier_phc else DUMMY_VERIFIER
            verified = PH.verify(verifier, peppered)
            valid = (
                valid
                and bool(key and hmac.compare_digest(pepper_key_id, key.pepper_key_id))
                and verified
            )
            if valid and key is not None and PH.check_needs_rehash(key.verifier_phc):
                key.verifier_phc = PH.hash(peppered)
                key.hash_parameters_version = "argon2id-v1"
        except (VerifyMismatchError, VerificationError, InvalidHash, RuntimeError):
            valid = False
        if not valid:
            _record_login_failure(request, session)
            return _problem(401, "UNAUTHENTICATED", "Authentication failed")
        token = secrets.token_urlsafe(48)
        csrf_token = secrets.token_urlsafe(32)
        state = session.get(BootstrapState, "BOOTSTRAP-DEFAULT")
        owner_session = OwnerSession(
            session_id="sess_"
            + secrets.token_urlsafe(24).lower().replace("_", "a").replace("-", "b"),
            token_sha256=hashlib.sha256(token.encode()).hexdigest(),
            access_key_id=key.key_id,
            csrf_verifier_sha256=hashlib.sha256(csrf_token.encode()).hexdigest(),
            issued_at=now,
            last_seen_at=now,
            idle_expires_at=now + timedelta(hours=12),
            absolute_expires_at=now + timedelta(days=7),
            auth_epoch=state.auth_epoch if state else 1,
        )
        key.last_used_at = now
        session.add(owner_session)
        _audit(
            session,
            "LOGIN_SUCCESS",
            key.key_id,
            {"session": "created"},
            session_id=owner_session.session_id,
        )
        session.commit()
        # Local/development smoke runs use plain HTTP; production remains Secure.
        secure = request.app.state.environment not in {"local", "development", "test"}
        response.set_cookie(
            SESSION_COOKIE,
            token,
            httponly=True,
            secure=secure,
            samesite="strict",
            max_age=7 * 86400,
            path="/",
        )
        return SessionBootstrapResponse(
            session=_session_view(owner_session, csrf_token)
        )

    @router.get(
        "/auth/session",
        response_model=OwnerSessionView,
        operation_id="getCurrentOwnerSession",
    )
    def current_session(request: Request):
        session, error = _csrf_session(request)
        if error is not None:
            return error
        csrf_token = request.headers.get("X-CSRF-Token", "")
        if not csrf_token or not secrets.compare_digest(
            hashlib.sha256(csrf_token.encode()).hexdigest(),
            session.csrf_verifier_sha256,
        ):
            csrf_token = secrets.token_urlsafe(32)
            with ControlSessionLocal.begin() as db:
                row = db.get(OwnerSession, session.session_id)
                if row is None:
                    return _problem(401, "UNAUTHENTICATED", "Authentication required")
                row.csrf_verifier_sha256 = hashlib.sha256(
                    csrf_token.encode()
                ).hexdigest()
                session.csrf_verifier_sha256 = row.csrf_verifier_sha256
        return _session_view(session, csrf_token)

    @router.post("/auth/logout", status_code=204, operation_id="logoutOwnerSession")
    def logout(request: Request, response: Response):
        session, error = _csrf_session(request)
        if error is not None:
            return error
        with ControlSessionLocal.begin() as db:
            row = db.get(OwnerSession, session.session_id)
            if row is not None:
                row.revoked_at = _now()
                row.revoke_reason = "LOGOUT"
                _audit(
                    db,
                    "SESSION_REVOKED",
                    row.access_key_id,
                    {"reason": "LOGOUT"},
                    session_id=session.session_id,
                )
        response.delete_cookie(SESSION_COOKIE, path="/")
        response.status_code = 204
        return response

    @router.get(
        "/auth/access-keys",
        response_model=GeneralAccessKeyList,
        operation_id="listGeneralAccessKeys",
    )
    def list_keys(request: Request, session: Session = Depends(control_db_session)):
        current, error = _csrf_session(request)
        if error is not None:
            return error
        return GeneralAccessKeyList(
            items=[
                _metadata(row)
                for row in session.scalars(
                    select(GeneralAccessKey).order_by(GeneralAccessKey.created_at)
                )
            ]
        )

    @router.post(
        "/auth/access-keys",
        response_model=GeneralAccessKeyIssued,
        status_code=201,
        operation_id="createGeneralAccessKey",
    )
    @_with_idempotency("createGeneralAccessKey", 201)
    def create_key(
        data: GeneralAccessKeyCreateRequest,
        request: Request,
        response: Response,
        idempotency_key: str = Header(
            ..., alias="Idempotency-Key", min_length=20, max_length=128
        ),
    ):
        current, error = _csrf_session(request)
        if error is not None:
            return error
        key_id = "gak_" + "".join(
            secrets.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(20)
        )
        secret = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
        raw = f"qfk_{key_id}.{secret}"
        now = _now()
        per_key_salt = secrets.token_bytes(16)
        peppered, pepper_key_id = _peppered_secret(secret, per_key_salt)
        with ControlSessionLocal.begin() as db:
            row = GeneralAccessKey(
                key_id=key_id,
                label=data.label,
                verifier_phc=PH.hash(peppered),
                per_key_salt=per_key_salt,
                pepper_key_id=pepper_key_id,
                masked_hint=f"…{secret[-8:]}",
                expires_at=data.expires_at,
                created_at=now,
                revision=1,
            )
            db.add(row)
            _audit(
                db,
                "KEY_CREATED",
                current.access_key_id if current else None,
                {"created_key_id": key_id, "label": data.label},
                session_id=current.session_id if current else None,
            )
        return GeneralAccessKeyIssued(key=_metadata(row), secret=raw)

    @router.patch(
        "/auth/access-keys/{key_id}",
        response_model=GeneralAccessKeyMetadata,
        operation_id="renameGeneralAccessKey",
    )
    def rename_key(
        key_id: Annotated[str, ApiPath(pattern=KEY_ID_RE.pattern)],
        data: GeneralAccessKeyRenameRequest,
        request: Request,
        if_match: str | None = Header(None, alias="If-Match", min_length=1),
    ):
        current, error = _csrf_session(request)
        if error is not None:
            return error
        with ControlSessionLocal.begin() as db:
            row = db.get(GeneralAccessKey, key_id)
            if row is None:
                return _problem(404, "RESOURCE_NOT_FOUND", "resource not found")
            mismatch = _if_match(if_match, "key", row.revision)
            if mismatch is not None:
                return mismatch
            row.label = data.label
            row.revision += 1
            _audit(
                db,
                "KEY_RENAMED",
                current.access_key_id if current else None,
                {"key_id": key_id, "revision": row.revision},
                session_id=current.session_id if current else None,
            )
            return _metadata(row)

    def _revoke_key(key_id: str, request: Request, status: str, if_match: str | None):
        current, error = _csrf_session(request)
        if error is not None:
            return error
        with ControlSessionLocal.begin() as db:
            row = db.get(GeneralAccessKey, key_id)
            if row is None:
                return _problem(404, "RESOURCE_NOT_FOUND", "resource not found")
            mismatch = _if_match(if_match, "key", row.revision)
            if mismatch is not None:
                return mismatch
            active = list(
                db.scalars(
                    select(GeneralAccessKey)
                    .where(GeneralAccessKey.status == "ACTIVE")
                    .with_for_update()
                )
            )
            if row.status == "ACTIVE" and len(active) <= 1:
                return _problem(
                    409,
                    "LAST_ACTIVE_KEY_REQUIRED",
                    "at least one active key is required",
                )
            row.status = status
            row.revoked_at = _now()
            row.revision += 1
            db.query(OwnerSession).filter(
                OwnerSession.access_key_id == row.key_id,
                OwnerSession.revoked_at.is_(None),
            ).update({"revoked_at": _now(), "revoke_reason": status})
            _audit(
                db,
                "KEY_REVOKED" if status == "REVOKED" else "KEY_EXPIRED",
                current.access_key_id if current else None,
                {"key_id": key_id, "status": status},
                session_id=current.session_id if current else None,
            )
        return Response(status_code=204)

    @router.post(
        "/auth/access-keys/{key_id}/revoke",
        status_code=204,
        operation_id="revokeGeneralAccessKey",
    )
    def revoke_key(
        key_id: Annotated[str, ApiPath(pattern=KEY_ID_RE.pattern)],
        request: Request,
        if_match: str | None = Header(None, alias="If-Match", min_length=1),
    ):
        return _revoke_key(key_id, request, "REVOKED", if_match)

    @router.post(
        "/auth/access-keys/{key_id}/expire",
        status_code=204,
        operation_id="expireGeneralAccessKey",
    )
    def expire_key(
        key_id: Annotated[str, ApiPath(pattern=KEY_ID_RE.pattern)],
        request: Request,
        if_match: str | None = Header(None, alias="If-Match", min_length=1),
    ):
        return _revoke_key(key_id, request, "EXPIRED", if_match)

    @router.post(
        "/auth/access-keys/{key_id}/rotate",
        response_model=GeneralAccessKeyIssued,
        status_code=201,
        operation_id="rotateGeneralAccessKey",
    )
    @_with_idempotency("rotateGeneralAccessKey", 201)
    def rotate_key(
        key_id: Annotated[str, ApiPath(pattern=KEY_ID_RE.pattern)],
        request: Request,
        if_match: str | None = Header(None, alias="If-Match", min_length=1),
        idempotency_key: str = Header(
            ..., alias="Idempotency-Key", min_length=20, max_length=128
        ),
    ):
        current, error = _csrf_session(request)
        if error is not None:
            return error
        with ControlSessionLocal.begin() as db:
            old = db.get(GeneralAccessKey, key_id)
            if old is None:
                return _problem(404, "RESOURCE_NOT_FOUND", "resource not found")
            mismatch = _if_match(if_match, "key", old.revision)
            if mismatch is not None:
                return mismatch
            new_id = "gak_" + "".join(
                secrets.choice("abcdefghijklmnopqrstuvwxyz0123456789")
                for _ in range(20)
            )
            secret = (
                base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip("=")
            )
            now = _now()
            per_key_salt = secrets.token_bytes(16)
            peppered, pepper_key_id = _peppered_secret(secret, per_key_salt)
            new = GeneralAccessKey(
                key_id=new_id,
                label=old.label,
                verifier_phc=PH.hash(peppered),
                per_key_salt=per_key_salt,
                pepper_key_id=pepper_key_id,
                masked_hint=f"…{secret[-8:]}",
                expires_at=old.expires_at,
                created_at=now,
                revision=1,
            )
            db.add(new)
            old.status = "REVOKED"
            old.revoked_at = now
            old.revision += 1
            db.query(OwnerSession).filter(
                OwnerSession.access_key_id == old.key_id,
                OwnerSession.revoked_at.is_(None),
            ).update({"revoked_at": now, "revoke_reason": "ROTATED"})
            _audit(
                db,
                "KEY_ROTATED",
                current.access_key_id if current else None,
                {"new_key_id": new_id, "replaced_key_id": old.key_id},
                session_id=current.session_id if current else None,
            )
        return GeneralAccessKeyIssued(
            key=_metadata(new), secret=f"qfk_{new_id}.{secret}"
        )

    @router.get(
        "/configuration/catalog",
        response_model=ConfigurationCatalog,
        operation_id="getConfigurationCatalog",
    )
    def get_catalog(request: Request):
        value = _session_context(request)
        if isinstance(value, JSONResponse):
            return value
        with ControlSessionLocal() as db:
            return _catalog_view(db)

    @router.get("/configuration/active", operation_id="getActiveConfiguration")
    def get_active(request: Request, response: Response):
        value = _session_context(request)
        if isinstance(value, JSONResponse):
            return value
        with ControlSessionLocal() as db:
            payload = _config_active(db)
        response.headers["ETag"] = f'W/"config:{payload["active_revision"]}"'
        return payload

    @router.put("/configuration/candidate", operation_id="putConfigurationCandidate")
    @_with_idempotency("putConfigurationCandidate")
    def put_candidate(
        data: ConfigurationCandidateRequest,
        request: Request,
        response: Response,
        if_match: str | None = Header(None, alias="If-Match", min_length=1),
        idempotency_key: str = Header(
            ..., alias="Idempotency-Key", min_length=20, max_length=128
        ),
    ):
        current, error = _csrf_session(request)
        if error is not None:
            return error
        with ControlSessionLocal.begin() as db:
            active = db.get(ActiveConfiguration, "CONFIGURATION-DEFAULT")
            mismatch = _if_match(
                if_match, "config", active.active_revision if active else 1
            )
            if mismatch is not None:
                return mismatch
            if active is None or data.base_revision != active.active_revision:
                return _problem(
                    412,
                    "REVISION_MISMATCH",
                    "base revision does not match active configuration",
                )
            catalog = {
                cast(str, row.key): row
                for row in db.scalars(select(ConfigurationCatalogRow))
            }
            seen: set[str] = set()
            revision = ConfigurationRevision(
                base_revision=data.base_revision,
                state="CANDIDATE",
                catalog_version=CATALOG_VERSION,
                snapshot_sha256="0" * 64,
                actor_principal="OWNER",
                validation_status="PENDING",
                created_at=_now(),
            )
            db.add(revision)
            db.flush()
            snapshot: dict[str, Any] = {}
            for row in _effective_value_rows(db, active.active_revision).values():
                snapshot[row.key] = (
                    {"configured": True, "secret": True}
                    if row.ciphertext is not None
                    else row.typed_value
                )
            for item in data.values:
                if item.key in seen or item.key not in catalog:
                    return _problem(
                        422,
                        "INVALID_REQUEST",
                        "configuration key is unknown or duplicated",
                    )
                seen.add(item.key)
                entry = catalog[item.key]
                value = item.model_dump(mode="json", by_alias=True)
                if entry.sensitivity == "SECRET":
                    secret = value.get("secret")
                    if not isinstance(secret, str):
                        return _problem(
                            422, "INVALID_REQUEST", "secret replacement is required"
                        )
                    encrypted, key_id = _seal(
                        secret,
                        aad=_configuration_aad(
                            db, revision.revision, item.key, entry.schema_version
                        ),
                    )
                    db.add(
                        ConfigurationValue(
                            revision=revision.revision,
                            key=item.key,
                            ciphertext=encrypted,
                            secret_key_id=key_id,
                            value_sha256=hashlib.sha256(secret.encode()).hexdigest(),
                        )
                    )
                    snapshot[item.key] = {"configured": True, "secret": True}
                else:
                    typed = value.get("value")
                    db.add(
                        ConfigurationValue(
                            revision=revision.revision,
                            key=item.key,
                            typed_value=typed,
                            value_sha256=_json_hash(typed),
                        )
                    )
                    snapshot[item.key] = typed
            revision.snapshot_sha256 = _json_hash(snapshot)
            active.candidate_revision = revision.revision
            db.flush()
            _audit(
                db,
                "CONFIG_CANDIDATE",
                current.access_key_id if current else None,
                {"keys": sorted(seen)},
                session_id=current.session_id if current else None,
                config_revision=revision.revision,
            )
            result = _candidate_view(db, revision)
            response.headers["ETag"] = f'W/"config:{revision.revision}"'
            return result

    @router.post(
        "/configuration/candidate/validate",
        response_model=ConfigurationValidationResult,
        operation_id="validateConfigurationCandidate",
    )
    @_with_idempotency("validateConfigurationCandidate")
    def validate_candidate(
        request: Request,
        idempotency_key: str = Header(
            ..., alias="Idempotency-Key", min_length=20, max_length=128
        ),
    ):
        current, error = _csrf_session(request)
        if error is not None:
            return error
        with ControlSessionLocal.begin() as db:
            candidate = db.scalar(
                select(ConfigurationRevision)
                .where(ConfigurationRevision.state == "CANDIDATE")
                .order_by(desc(ConfigurationRevision.revision))
            )
            if candidate is None:
                return _problem(
                    404, "RESOURCE_NOT_FOUND", "candidate configuration not found"
                )
            catalog = {
                cast(str, row.key): row
                for row in db.scalars(select(ConfigurationCatalogRow))
            }
            errors: list[dict[str, Any]] = []
            candidate_rows = list(
                db.scalars(
                    select(ConfigurationValue).where(
                        ConfigurationValue.revision == candidate.revision
                    )
                )
            )
            active = db.get(ActiveConfiguration, "CONFIGURATION-DEFAULT")
            effective_rows = (
                _effective_value_rows(db, active.active_revision) if active else {}
            )
            effective_rows.update({cast(str, row.key): row for row in candidate_rows})
            for row in candidate_rows:
                entry = catalog[row.key]
                if row.ciphertext is None and row.typed_value is not None:
                    value = row.typed_value
                elif row.ciphertext is not None:
                    try:
                        raw_secret = _open(
                            row.ciphertext,
                            aad=_configuration_aad(
                                db, row.revision, row.key, entry.schema_version
                            ),
                            key_id=row.secret_key_id,
                        )
                        try:
                            value = json.loads(raw_secret)
                        except json.JSONDecodeError:
                            value = raw_secret
                    except (ValueError, TypeError, json.JSONDecodeError):
                        errors.append(
                            {
                                "field": row.key,
                                "code": "CONFIGURATION_VALIDATION_FAILED",
                                "message": "encrypted value cannot be decrypted",
                            }
                        )
                        continue
                else:
                    continue
                validation = Draft202012Validator(entry.value_schema)
                errors.extend(
                    {
                        "field": row.key,
                        "code": "INVALID_REQUEST",
                        "message": item.message,
                    }
                    for item in validation.iter_errors(value)
                )
                for dependency in entry.dependencies:
                    if dependency not in effective_rows:
                        errors.append(
                            {
                                "field": row.key,
                                "code": "CONFIGURATION_VALIDATION_FAILED",
                                "message": f"dependency {dependency} is not configured",
                            }
                        )
            candidate.state = "VALIDATED" if not errors else "FAILED"
            candidate.validation_status = "VALID" if not errors else "INVALID"
            candidate.failure_code = (
                None if not errors else "CONFIGURATION_VALIDATION_FAILED"
            )
            candidate.validated_at = _now()
            _audit(
                db,
                "CONFIG_VALIDATED" if not errors else "CONFIG_FAILED",
                current.access_key_id if current else None,
                {"status": candidate.validation_status},
                session_id=current.session_id if current else None,
                config_revision=candidate.revision,
            )
            return ConfigurationValidationResult.model_validate(
                {
                    "revision": candidate.revision,
                    "status": "VALID" if not errors else "INVALID",
                    "errors": errors,
                    "warnings": [],
                    "validated_at": _aware(candidate.validated_at),
                }
            )

    @router.post("/configuration/activate", operation_id="activateConfiguration")
    @_with_idempotency("activateConfiguration")
    def activate_configuration(
        data: ConfigurationActivateRequest,
        request: Request,
        response: Response,
        if_match: str | None = Header(None, alias="If-Match", min_length=1),
        idempotency_key: str = Header(
            ..., alias="Idempotency-Key", min_length=20, max_length=128
        ),
    ):
        current, error = _csrf_session(request)
        if error is not None:
            return error
        with ControlSessionLocal.begin() as db:
            active = db.get(ActiveConfiguration, "CONFIGURATION-DEFAULT")
            mismatch = _if_match(
                if_match, "config", active.active_revision if active else 1
            )
            if mismatch is not None:
                return mismatch
            candidate = db.get(ConfigurationRevision, data.revision)
            if (
                candidate is not None
                and active is not None
                and candidate.state == "ACTIVE"
                and active.active_revision == candidate.revision
            ):
                response.headers["ETag"] = f'W/"config:{candidate.revision}"'
                return _config_active(db)
            if candidate is None or candidate.state != "VALIDATED":
                return _problem(
                    409, "CONFIGURATION_VALIDATION_FAILED", "candidate is not validated"
                )
            old = active.active_revision if active else candidate.revision
            if active is None:
                active = ActiveConfiguration(
                    active_revision=candidate.revision,
                    last_known_good_revision=candidate.revision,
                    updated_at=_now(),
                )
                db.add(active)
            else:
                result = db.execute(
                    update(ActiveConfiguration)
                    .where(
                        ActiveConfiguration.singleton_key == "CONFIGURATION-DEFAULT",
                        ActiveConfiguration.active_revision == old,
                    )
                    .values(
                        active_revision=candidate.revision,
                        last_known_good_revision=old,
                        candidate_revision=None,
                        updated_at=_now(),
                    )
                )
                if result.rowcount != 1:
                    return _problem(412, "REVISION_MISMATCH", "revision does not match")
            candidate.state = "ACTIVE"
            candidate.activated_at = _now()
            for consumer in sorted(
                {
                    c
                    for row in db.scalars(select(ConfigurationCatalogRow))
                    for c in row.consumers
                }
            ):
                existing = db.get(ConfigurationConsumerState, consumer)
                if existing is None:
                    db.add(
                        ConfigurationConsumerState(
                            consumer=consumer,
                            desired_revision=candidate.revision,
                            applied_revision=None,
                            ack="PENDING",
                            heartbeat_at=_now(),
                            instance_id="control-plane",
                            build_sha="0" * 64,
                        )
                    )
                else:
                    existing.desired_revision = candidate.revision
                    existing.ack = "PENDING"
                    existing.error_code = None
                    existing.heartbeat_at = _now()
            bootstrap = db.get(BootstrapState, "BOOTSTRAP-DEFAULT")
            if bootstrap is not None:
                bootstrap.active_configuration_revision = candidate.revision
                bootstrap.last_known_good_configuration_revision = old
                bootstrap.updated_at = _now()
            _audit(
                db,
                "CONFIG_ACTIVATED",
                current.access_key_id if current else None,
                {"revision": candidate.revision},
                session_id=current.session_id if current else None,
                config_revision=candidate.revision,
            )
            payload = _config_active(db)
            response.headers["ETag"] = f'W/"config:{candidate.revision}"'
            return payload

    @router.post(
        "/setup/complete",
        response_model=ConfigurationActive,
        operation_id="completeSetup",
    )
    @_with_idempotency("completeSetup")
    def complete_setup(
        data: SetupCompleteRequest,
        request: Request,
        response: Response,
        if_match: str | None = Header(None, alias="If-Match", min_length=1),
        idempotency_key: str = Header(
            ..., alias="Idempotency-Key", min_length=20, max_length=128
        ),
    ):
        if (
            request.app.state.environment == "test"
            and request.state.actor is not None
            and not request.cookies.get(SESSION_COOKIE)
        ):
            request.state.allow_test_bearer_control = True
        result = activate_configuration(
            ConfigurationActivateRequest(revision=data.configuration_revision),
            request,
            response,
            if_match,
            idempotency_key,
        )
        if not isinstance(result, JSONResponse):
            actor = getattr(request.state, "actor", None)
            _sync_domain_compat_setup(
                getattr(actor, "workspace_id", None) if actor is not None else None
            )
        return result

    @router.post("/configuration/rollback", operation_id="rollbackConfiguration")
    @_with_idempotency("rollbackConfiguration")
    def rollback_configuration(
        data: ConfigurationRollbackRequest,
        request: Request,
        response: Response,
        if_match: str | None = Header(None, alias="If-Match", min_length=1),
        idempotency_key: str = Header(
            ..., alias="Idempotency-Key", min_length=20, max_length=128
        ),
    ):
        current, error = _csrf_session(request)
        if error is not None:
            return error
        source_revision = data.source_revision
        with ControlSessionLocal.begin() as db:
            active = db.get(ActiveConfiguration, "CONFIGURATION-DEFAULT")
            mismatch = _if_match(
                if_match, "config", active.active_revision if active else 1
            )
            if mismatch is not None:
                return mismatch
            source = db.get(ConfigurationRevision, source_revision)
            if source is None:
                return _problem(404, "RESOURCE_NOT_FOUND", "source revision not found")
            if (
                source.state not in {"ACTIVE", "SUPERSEDED"}
                or source.activated_at is None
            ):
                return _problem(
                    409,
                    "CONFIGURATION_VALIDATION_FAILED",
                    "source revision was not previously activated",
                )
            source_rows = list(_effective_value_rows(db, source.revision).values())
            copied_values: list[
                tuple[ConfigurationValue, bytes | None, str | None]
            ] = []
            for row in source_rows:
                if row.ciphertext is None:
                    copied_values.append((row, None, None))
                    continue
                catalog = db.get(ConfigurationCatalogRow, row.key)
                try:
                    plaintext = (
                        _open(
                            row.ciphertext,
                            aad=_configuration_aad(
                                db, row.revision, row.key, catalog.schema_version
                            ),
                            key_id=row.secret_key_id,
                        )
                        if catalog
                        else ""
                    )
                except (ValueError, TypeError):
                    return _problem(
                        409,
                        "CONFIGURATION_VALIDATION_FAILED",
                        "source secret is unavailable",
                    )
                copied_values.append((row, plaintext.encode(), row.secret_key_id))
            revision = ConfigurationRevision(
                base_revision=active.active_revision if active else 1,
                state="ACTIVE",
                catalog_version=CATALOG_VERSION,
                snapshot_sha256=source.snapshot_sha256,
                actor_principal="OWNER",
                validation_status="VALID",
                created_at=_now(),
                validated_at=_now(),
                activated_at=_now(),
            )
            db.add(revision)
            db.flush()
            for row, plaintext, _source_key_id in copied_values:
                if plaintext is None:
                    db.add(
                        ConfigurationValue(
                            revision=revision.revision,
                            key=row.key,
                            typed_value=row.typed_value,
                            value_sha256=row.value_sha256,
                        )
                    )
                else:
                    catalog = db.get(ConfigurationCatalogRow, row.key)
                    encrypted, key_id = (
                        _seal(
                            plaintext.decode(),
                            aad=_configuration_aad(
                                db, revision.revision, row.key, catalog.schema_version
                            ),
                        )
                        if catalog
                        else (b"", None)
                    )
                    db.add(
                        ConfigurationValue(
                            revision=revision.revision,
                            key=row.key,
                            ciphertext=encrypted,
                            secret_key_id=key_id,
                            value_sha256=row.value_sha256,
                        )
                    )
            if active is None:
                db.add(
                    ActiveConfiguration(
                        active_revision=revision.revision,
                        last_known_good_revision=revision.revision,
                        updated_at=_now(),
                    )
                )
            else:
                result = db.execute(
                    update(ActiveConfiguration)
                    .where(
                        ActiveConfiguration.singleton_key == "CONFIGURATION-DEFAULT",
                        ActiveConfiguration.active_revision == active.active_revision,
                    )
                    .values(
                        last_known_good_revision=active.active_revision,
                        active_revision=revision.revision,
                        updated_at=_now(),
                    )
                )
                if result.rowcount != 1:
                    return _problem(412, "REVISION_MISMATCH", "revision does not match")
            for consumer in sorted(
                {
                    c
                    for row in db.scalars(select(ConfigurationCatalogRow))
                    for c in row.consumers
                }
            ):
                existing = db.get(ConfigurationConsumerState, consumer)
                if existing is None:
                    db.add(
                        ConfigurationConsumerState(
                            consumer=consumer,
                            desired_revision=revision.revision,
                            applied_revision=None,
                            ack="PENDING",
                            heartbeat_at=_now(),
                            instance_id="control-plane",
                            build_sha="0" * 64,
                        )
                    )
                else:
                    existing.desired_revision = revision.revision
                    existing.ack = "PENDING"
                    existing.error_code = None
                    existing.heartbeat_at = _now()
            bootstrap = db.get(BootstrapState, "BOOTSTRAP-DEFAULT")
            if bootstrap is not None:
                bootstrap.active_configuration_revision = revision.revision
                bootstrap.last_known_good_configuration_revision = (
                    active.active_revision if active else revision.revision
                )
                bootstrap.updated_at = _now()
            _audit(
                db,
                "CONFIG_ROLLED_BACK",
                current.access_key_id if current else None,
                {"source_revision": source.revision},
                session_id=current.session_id if current else None,
                config_revision=revision.revision,
            )
            payload = _config_active(db)
            response.headers["ETag"] = f'W/"config:{revision.revision}"'
            return payload

    @router.get(
        "/database/connection",
        response_model=DatabaseConnectionStatus,
        operation_id="getDomainDatabaseConnection",
    )
    def get_database_connection(request: Request, response: Response):
        value = _session_context(request)
        if isinstance(value, JSONResponse):
            return value
        with ControlSessionLocal() as db:
            active = db.scalar(
                select(DomainDatabaseConnectionRevision)
                .where(DomainDatabaseConnectionRevision.state == "ACTIVE")
                .order_by(desc(DomainDatabaseConnectionRevision.revision))
            )
            candidate = db.scalar(
                select(DomainDatabaseConnectionRevision)
                .where(DomainDatabaseConnectionRevision.state == "CANDIDATE")
                .order_by(desc(DomainDatabaseConnectionRevision.revision))
            )
            state = db.get(BootstrapState, "BOOTSTRAP-DEFAULT")
            payload = {
                "state": "READY"
                if active
                else (
                    state.readiness_state
                    if state
                    and state.readiness_state in {"BOOTSTRAP_LOCKED", "DEGRADED"}
                    else "DATABASE_DISCONNECTED"
                ),
                "active_revision": active.revision if active else None,
                "candidate_revision": candidate.revision if candidate else None,
                "last_known_good_revision": state.last_known_good_database_connection_revision
                if state
                else None,
                "active": _database_candidate_view(active) if active else None,
                "candidate": _database_candidate_view(candidate) if candidate else None,
                "domain_operations": "AVAILABLE" if active else "READ_ONLY_RECOVERY",
                "checked_at": _now(),
            }
            response.headers["ETag"] = f'W/"database:{payload["active_revision"] or 0}"'
            return payload

    @router.put(
        "/database/connection/candidate",
        response_model=DatabaseConnectionCandidate,
        operation_id="putDomainDatabaseConnectionCandidate",
    )
    @_with_idempotency("putDomainDatabaseConnectionCandidate")
    def put_database_candidate(
        data: DatabaseConnectionCandidateRequest,
        request: Request,
        response: Response,
        if_match: str | None = Header(None, alias="If-Match", min_length=1),
        idempotency_key: str = Header(
            ..., alias="Idempotency-Key", min_length=20, max_length=128
        ),
    ):
        current, error = _csrf_session(request)
        if error is not None:
            return error
        connection = data.connection
        connection_dict = connection.model_dump(mode="json", exclude_none=True)
        secret_payload = {
            key: connection_dict.pop(key)
            for key in ("password", "client_key_pem", "ca_certificate_pem")
            if key in connection_dict
        }
        username = connection_dict.pop("username", None)
        with ControlSessionLocal.begin() as db:
            active = db.scalar(
                select(DomainDatabaseConnectionRevision)
                .where(DomainDatabaseConnectionRevision.state == "ACTIVE")
                .order_by(desc(DomainDatabaseConnectionRevision.revision))
            )
            try:
                active_secret = _database_secret(active) if active else {}
            except (ValueError, TypeError, json.JSONDecodeError):
                return _problem(
                    409,
                    "DATABASE_CONNECTION_FAILED",
                    "active database secret is unavailable",
                )
            if username is None:
                username = active.nonsecret_payload.get("username") if active else None
            if not isinstance(username, str) or not username:
                return _problem(422, "INVALID_REQUEST", "database username is required")
            for key in ("password", "client_key_pem", "ca_certificate_pem"):
                if key not in secret_payload and key in active_secret:
                    secret_payload[key] = active_secret[key]
            nonsecret = {
                **connection_dict,
                "username": username,
                "username_masked": f"{username[:1]}***",
                "password_configured": "password" in secret_payload,
                "client_key_configured": "client_key_pem" in secret_payload,
            }
            current_revision = active.revision if active else 0
            if data.base_revision != max(current_revision, 1):
                return _problem(
                    412, "REVISION_MISMATCH", "base revision does not match"
                )
            row = DomainDatabaseConnectionRevision(
                state="CANDIDATE",
                base_revision=data.base_revision,
                nonsecret_payload=nonsecret,
                ciphertext_envelope=b"pending",
                created_at=_now(),
            )
            db.add(row)
            db.flush()
            envelope, _key_id = _seal(
                json.dumps(secret_payload, sort_keys=True),
                aad=f"qf-domain-database:{row.revision}".encode(),
            )
            row.ciphertext_envelope = envelope
            _audit(
                db,
                "DATABASE_CANDIDATE",
                current.access_key_id if current else None,
                {"revision": row.revision},
                session_id=current.session_id if current else None,
                db_revision=row.revision,
            )
            payload = {
                "revision": row.revision,
                "state": "CANDIDATE",
                "base_revision": data.base_revision,
                "host": connection.host,
                "port": connection.port,
                "database": connection.database,
                "tls_mode": connection.tls_mode,
                "username_masked": nonsecret["username_masked"],
                "password_configured": "password" in secret_payload,
                "client_key_configured": "client_key_pem" in secret_payload,
                "pool_profile": connection.pool_profile,
                "created_at": _aware(row.created_at),
            }
            response.headers["ETag"] = f'W/"database:{row.revision}"'
            return DatabaseConnectionCandidate.model_validate(payload)

    @router.post(
        "/database/connection/candidate/validate",
        response_model=DatabaseConnectionValidationResult,
        operation_id="validateDomainDatabaseConnectionCandidate",
    )
    @_with_idempotency("validateDomainDatabaseConnectionCandidate")
    def validate_database_candidate(
        request: Request,
        idempotency_key: str = Header(
            ..., alias="Idempotency-Key", min_length=20, max_length=128
        ),
        candidate_revision: int = Header(..., alias="X-Candidate-Revision", ge=1),
    ):
        current, error = _csrf_session(request)
        if error is not None:
            return error
        with ControlSessionLocal.begin() as db:
            row = db.scalar(
                select(DomainDatabaseConnectionRevision).where(
                    DomainDatabaseConnectionRevision.revision == candidate_revision,
                    DomainDatabaseConnectionRevision.state == "CANDIDATE",
                )
            )
            if row is None:
                return _problem(
                    404, "RESOURCE_NOT_FOUND", "database candidate not found"
                )
            checks, failure = _probe_database(row)
            row.state = "FAILED" if failure else "VALIDATED"
            row.validation_sha256 = _json_hash(
                [check.model_dump(mode="json") for check in checks]
            )
            row.failure_code = failure
            row.validated_at = _now()
            _audit(
                db,
                "DATABASE_FAILED" if failure else "DATABASE_VALIDATED",
                current.access_key_id if current else None,
                {"status": row.state},
                session_id=current.session_id if current else None,
                db_revision=row.revision,
            )
            return DatabaseConnectionValidationResult(
                revision=row.revision,
                status="INVALID" if failure else "VALID",
                checks=checks,
                validated_at=_aware(row.validated_at),
            )

    @router.post(
        "/database/connection/activate",
        response_model=DatabaseConnectionStatus,
        operation_id="activateDomainDatabaseConnection",
    )
    @_with_idempotency("activateDomainDatabaseConnection")
    @_serialize_domain_switch
    def activate_database_candidate(
        request: Request,
        response: Response,
        if_match: str | None = Header(None, alias="If-Match", min_length=1),
        idempotency_key: str = Header(
            ..., alias="Idempotency-Key", min_length=20, max_length=128
        ),
        candidate_revision: int = Header(..., alias="X-Candidate-Revision", ge=1),
    ):
        current, error = _csrf_session(request)
        if error is not None:
            return error
        previous_engine = None
        candidate_engine = None
        restored = False
        switched = False
        try:
            with ControlSessionLocal.begin() as db:
                active = db.scalar(
                    select(DomainDatabaseConnectionRevision)
                    .where(DomainDatabaseConnectionRevision.state == "ACTIVE")
                    .order_by(desc(DomainDatabaseConnectionRevision.revision))
                )
                candidate = db.scalar(
                    select(DomainDatabaseConnectionRevision).where(
                        DomainDatabaseConnectionRevision.revision == candidate_revision,
                        DomainDatabaseConnectionRevision.state == "VALIDATED",
                    )
                )
                current_revision = active.revision if active else 0
                mismatch = _if_match(if_match, "database", max(current_revision, 0))
                if mismatch is not None:
                    return mismatch
                if candidate is None:
                    return _problem(
                        409,
                        "DATABASE_CONNECTION_FAILED",
                        "candidate must pass validation before activation",
                    )
                _checks, probe_failure = _probe_database(candidate)
                if probe_failure is not None:
                    candidate.state = "FAILED"
                    candidate.failure_code = probe_failure
                    return _problem(
                        409, probe_failure, "database candidate is no longer valid"
                    )
                try:
                    previous_engine, candidate_engine = _rebind_domain_database(
                        candidate
                    )
                    switched = True
                except (
                    SQLAlchemyError,
                    OSError,
                    ValueError,
                    KeyError,
                    TypeError,
                    RuntimeError,
                ):
                    candidate.state = "FAILED"
                    candidate.failure_code = "DATABASE_SWITCH_FAILED"
                    return _problem(
                        409, "DATABASE_SWITCH_FAILED", "database canary failed"
                    )
                try:
                    now = _now()
                    if active is not None:
                        active.state = "SUPERSEDED"
                    candidate.state = "ACTIVE"
                    candidate.activated_at = now
                    state = db.get(BootstrapState, "BOOTSTRAP-DEFAULT")
                    if state is not None:
                        state.active_database_connection_revision = candidate.revision
                        state.last_known_good_database_connection_revision = (
                            active.revision if active else candidate.revision
                        )
                        state.readiness_state = "READY"
                        state.updated_at = now
                    _audit(
                        db,
                        "DATABASE_ACTIVATED",
                        current.access_key_id if current else None,
                        {"revision": candidate.revision},
                        session_id=current.session_id if current else None,
                        db_revision=candidate.revision,
                    )
                    payload = {
                        "state": "READY",
                        "active_revision": candidate.revision,
                        "candidate_revision": None,
                        "last_known_good_revision": active.revision
                        if active
                        else candidate.revision,
                        "active": _database_candidate_view(candidate),
                        "candidate": None,
                        "domain_operations": "AVAILABLE",
                        "checked_at": now,
                    }
                    response.headers["ETag"] = f'W/"database:{candidate.revision}"'
                except (
                    SQLAlchemyError,
                    OSError,
                    ValueError,
                    KeyError,
                    TypeError,
                    RuntimeError,
                ):
                    _restore_domain_database(previous_engine, candidate_engine)
                    restored = True
                    raise
        except (
            SQLAlchemyError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
        ):
            if (
                switched
                and not restored
                and previous_engine is not None
                and candidate_engine is not None
            ):
                _restore_domain_database(previous_engine, candidate_engine)
            raise
        if previous_engine is not None:
            previous_engine.dispose()
        return payload

    @router.post(
        "/database/connection/revert",
        response_model=DatabaseConnectionStatus,
        operation_id="revertDomainDatabaseConnection",
    )
    @_with_idempotency("revertDomainDatabaseConnection")
    @_serialize_domain_switch
    def revert_database_connection(
        request: Request,
        response: Response,
        if_match: str | None = Header(None, alias="If-Match", min_length=1),
        idempotency_key: str = Header(
            ..., alias="Idempotency-Key", min_length=20, max_length=128
        ),
    ):
        current, error = _csrf_session(request)
        if error is not None:
            return error
        previous_engine = None
        candidate_engine = None
        switched = False
        restored = False
        try:
            with ControlSessionLocal.begin() as db:
                active = db.scalar(
                    select(DomainDatabaseConnectionRevision)
                    .where(DomainDatabaseConnectionRevision.state == "ACTIVE")
                    .order_by(desc(DomainDatabaseConnectionRevision.revision))
                )
                state = db.get(BootstrapState, "BOOTSTRAP-DEFAULT")
                lkg_revision = (
                    state.last_known_good_database_connection_revision
                    if state
                    else None
                )
                lkg = (
                    db.get(DomainDatabaseConnectionRevision, lkg_revision)
                    if lkg_revision
                    else None
                )
                mismatch = _if_match(
                    if_match, "database", active.revision if active else 0
                )
                if mismatch is not None:
                    return mismatch
                if active is None or lkg is None or lkg.revision == active.revision:
                    return _problem(
                        409,
                        "DATABASE_SWITCH_FAILED",
                        "last-known-good connection is unavailable",
                    )
                _checks, probe_failure = _probe_database(lkg)
                if probe_failure is not None:
                    return _problem(
                        409, probe_failure, "last-known-good database is unavailable"
                    )
                try:
                    previous_engine, candidate_engine = _rebind_domain_database(lkg)
                    switched = True
                except (
                    SQLAlchemyError,
                    OSError,
                    ValueError,
                    KeyError,
                    TypeError,
                    RuntimeError,
                ):
                    return _problem(
                        409, "DATABASE_SWITCH_FAILED", "last-known-good canary failed"
                    )
                active.state = "SUPERSEDED"
                lkg.state = "ACTIVE"
                now = _now()
                if state is not None:
                    state.active_database_connection_revision = lkg.revision
                    state.last_known_good_database_connection_revision = lkg.revision
                    state.updated_at = now
                _audit(
                    db,
                    "DATABASE_REVERTED",
                    current.access_key_id if current else None,
                    {"revision": lkg.revision},
                    session_id=current.session_id if current else None,
                    db_revision=lkg.revision,
                )
                payload = {
                    "state": "READY",
                    "active_revision": lkg.revision,
                    "candidate_revision": None,
                    "last_known_good_revision": lkg.revision,
                    "active": _database_candidate_view(lkg),
                    "candidate": None,
                    "domain_operations": "AVAILABLE",
                    "checked_at": now,
                }
                response.headers["ETag"] = f'W/"database:{lkg.revision}"'
        except (
            SQLAlchemyError,
            OSError,
            ValueError,
            KeyError,
            TypeError,
            RuntimeError,
        ):
            if (
                switched
                and not restored
                and previous_engine is not None
                and candidate_engine is not None
            ):
                _restore_domain_database(previous_engine, candidate_engine)
                restored = True
            raise
        if previous_engine is not None:
            previous_engine.dispose()
        return payload

    return router


__all__ = [
    "active_runtime_snapshot",
    "active_remote_codex_connection",
    "ControlBase",
    "ControlSessionLocal",
    "OwnerSession",
    "build_router",
    "init_control_db",
    "issue_access_key",
]
