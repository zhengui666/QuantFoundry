from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from typing import Annotated, Any, Literal, Protocol, cast

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Security
from fastapi import Path as ApiPath
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.routing import APIRoute
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.utils import create_model_field
from sqlalchemy import (
    DDL,
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    create_engine,
    event,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.api_models import (
    SCHEMA_MODELS,
    AgentConfigUpdate,
    ApprovalDecisionRequest,
    ApprovalRejectRequest,
    BacktestRequest,
    CapabilityEvaluationRequest,
    DatasetValidationRequest,
    ExperimentCreateRequest,
    ExperimentReproduceRequest,
    FactorAnalysisRequest,
    FactorCreateRequest,
    FreezeStrategyRequest,
    HoldoutApprovalRequest,
    HoldoutRunRequest,
    MemoGenerateRequest,
    ResearchCreateRequest,
    ResearchStartRequest,
    SetupCompleteRequest,
    SetupProviderConnectionValidationRequest,
    SnapshotCreateRequest,
    StrategyCreateRequest,
    ValidationCreateRequest,
    application_schemas,
)
from app.contract_route import CanonicalRoute
from app.contracts import canonical_openapi, validated_payload
from app.contracts import now as NOW
from app.engines import (
    EngineInputError,
    load_cost_model,
    load_dataset,
    load_validation_policy,
    snapshot_content_sha256,
    snapshot_rows,
)
from app.event_contract import (
    EVENT_TYPE_CHECK_SQL,
    safe_resync_payload,
    validate_event_payload,
    validate_event_type,
    validate_sse_envelope,
)
from app.event_contract import (
    ValidationError as EventValidationError,
)
from app.idempotency import execute as execute_idempotent
from app.locator_contract import register_sqlite_functions
from app.provider_credentials import (
    CredentialConfigurationError,
    credential_aad,
    credential_fingerprint,
    decrypt_credential,
    encrypt_credential,
    encryption_is_configured,
)
from app.public_ids import (
    PUBLIC_ID_PATTERNS,
    PUBLIC_ID_PREFIXES,
    new_public_id,
    public_id_json_schema,
)
from app.section14_schema import (
    DateRangeCompat,
    augment_section14_metadata,
    canonical_workspace_id,
)
from app.services import probe_health
from app.sse import durable_event_stream

DB_URL = os.getenv("QF_DATABASE_URL")
ENVIRONMENT = os.getenv("QF_ENVIRONMENT") or os.getenv("QF_ENV", "production")
if not DB_URL:
    raise RuntimeError(
        "QF_DATABASE_URL is required; production never defaults to SQLite"
    )
if ENVIRONMENT == "production" and DB_URL.startswith("sqlite"):
    raise RuntimeError(
        "production database must be configured through Alembic/PostgreSQL"
    )
GIT_COMMIT = os.getenv("QF_GIT_COMMIT")
BUILD_ID = os.getenv("QF_BUILD_ID")
if ENVIRONMENT == "production" and (not GIT_COMMIT or not BUILD_ID):
    raise RuntimeError("QF_GIT_COMMIT and QF_BUILD_ID are required in production")
GIT_COMMIT = GIT_COMMIT or "test-source"
BUILD_ID = BUILD_ID or "test-build"
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql+psycopg://", 1)
engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False} if DB_URL.startswith("sqlite") else {},
)
logger = logging.getLogger(__name__)

type JsonScalar = None | bool | int | float | str
type JsonValue = JsonScalar | list[JsonValue] | dict[str, JsonValue]
type JsonObject = dict[str, JsonValue]


class _ExperimentReferenceFields(Protocol):
    data_snapshot_ref_id: uuid.UUID | None


class _ApprovalTimestampFields(Protocol):
    requested_at: datetime
    decided_at: datetime | None


class _ApprovalDetailFields(_ApprovalTimestampFields, Protocol):
    approval_type: str
    subject_hash: str
    requested_by_type: str
    requested_by_id: str
    reason: str
    prerequisites: JsonValue
    risk_summary: JsonValue
    effects: JsonValue
    decision_reason: str | None
    decided_by: str | None


class _HoldoutReferenceFields(Protocol):
    validation_run_ref_id: uuid.UUID | None
    provenance_ref_id: uuid.UUID | None
    exposure_count: int
    contaminated_for_future_versions: bool


class _WatermarkFields(Protocol):
    last_sequence: int


class _AuditChainHeadFields(Protocol):
    event_sha256: str
    revision: int


class _ApprovalMutationFields(Protocol):
    status: str
    revision: int
    detail: str


class _ValidationMutationFields(Protocol):
    holdout_state: str
    revision: int


class _AgentConfigMutationFields(Protocol):
    revision: int
    updated_at: datetime


def _as_str(value: object) -> str:
    """Narrow legacy SQLAlchemy runtime values to their persisted string form."""
    return cast(str, value)


def _json_loads(value: object) -> JsonObject:
    """Decode persisted JSON text from legacy declarative model attributes."""
    return cast(JsonObject, json.loads(_as_str(value)))


def _as_optional_str(value: object) -> str | None:
    return cast(str | None, value)


def _as_int(value: object) -> int:
    return cast(int, value)


def _as_json_object(value: JsonValue) -> JsonObject:
    return cast(JsonObject, value)


def _as_json_objects(value: JsonValue) -> list[JsonObject]:
    return cast(list[JsonObject], value)


if DB_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection: Any, _: Any) -> None:
        register_sqlite_functions(dbapi_connection)
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def optional_idempotency_key(
    value: Annotated[
        str | None, Header(alias="Idempotency-Key", min_length=20, max_length=128)
    ] = None,
) -> str | None:
    return value


def optional_if_match(
    value: Annotated[str | None, Header(alias="If-Match", min_length=1)] = None,
) -> str | None:
    return value


IdempotencyKey = Annotated[str | None, Depends(optional_idempotency_key)]
IfMatch = Annotated[str | None, Depends(optional_if_match)]
DatasetId = Annotated[str, ApiPath(pattern=PUBLIC_ID_PATTERNS["dataset"])]
SnapshotId = Annotated[str, ApiPath(pattern=PUBLIC_ID_PATTERNS["snapshot"])]
ResearchId = Annotated[str, ApiPath(pattern=PUBLIC_ID_PATTERNS["research"])]
ExperimentId = Annotated[str, ApiPath(pattern=PUBLIC_ID_PATTERNS["experiment"])]
FactorId = Annotated[str, ApiPath(pattern=PUBLIC_ID_PATTERNS["factor"])]
StrategyId = Annotated[str, ApiPath(pattern=PUBLIC_ID_PATTERNS["strategy"])]
ValidationId = Annotated[str, ApiPath(pattern=PUBLIC_ID_PATTERNS["validation"])]
MemoId = Annotated[str, ApiPath(pattern=PUBLIC_ID_PATTERNS["memo"])]
ApprovalId = Annotated[str, ApiPath(pattern=PUBLIC_ID_PATTERNS["approval"])]
AgentRunId = Annotated[str, ApiPath(pattern=PUBLIC_ID_PATTERNS["agent_run"])]
ToolCallId = Annotated[str, ApiPath(pattern=PUBLIC_ID_PATTERNS["tool_call"])]
JobId = Annotated[str, ApiPath(pattern=PUBLIC_ID_PATTERNS["job"])]
Version = Annotated[int, ApiPath(ge=1)]
LastEventId = Annotated[int | None, Header(alias="Last-Event-ID", ge=0)]
AgentRole = Literal[
    "RESEARCH_DIRECTOR",
    "FACTOR_SCIENTIST",
    "STRATEGY_SCIENTIST",
    "PORTFOLIO_ANALYST",
    "RED_TEAM_RESEARCHER",
    "PERFORMANCE_ANALYST",
]


class Base(DeclarativeBase):
    pass


class Record(Base):
    __tablename__ = "records"
    id = Column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid7,
        server_default=text("uuidv7()"),
    )
    workspace_id = Column(
        String, ForeignKey("workspaces.id"), nullable=False, index=True
    )
    record_key = Column(String(42), nullable=False)
    kind = Column(String(32), nullable=False, index=True)
    revision = Column(Integer, nullable=False, default=1)
    body = Column(Text, nullable=False, default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_records_workspace_id_id"),
        UniqueConstraint(
            "workspace_id", "record_key", name="uq_records_workspace_id_record_key"
        ),
    )


class Idempotency(Base):
    __tablename__ = "idempotency_records"
    internal_id = Column("id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_id = Column(String, nullable=False)
    workspace_id = Column(String, nullable=False)
    method = Column(String, nullable=False)
    path = Column("normalized_route", Text, nullable=False)
    key = Column(String, nullable=False)
    request_hash = Column("request_sha256", String(64), nullable=False)
    status = Column("response_status", Integer)
    response = Column("response_body", Text)
    resource_ref = Column(JSON)
    state = Column(String, nullable=False, default="PROCESSING")
    lease_owner_id = Column(String(64))
    lease_expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    __table_args__ = (
        UniqueConstraint(
            "actor_id",
            "workspace_id",
            "method",
            "normalized_route",
            "key",
            name="uq_idempotency_actor_workspace_operation_key",
        ),
    )
    __mapper_args__ = {"primary_key": [actor_id, workspace_id, method, path, key]}


class Event(Base):
    __tablename__ = "domain_events"
    sequence = Column(
        BigInteger,
        primary_key=True,
        autoincrement=False,
    )
    event_id = Column(String, unique=True, nullable=False)
    workspace_id = Column(String, primary_key=True, index=True)
    actor_id = Column(String, index=True)
    event_type = Column(String(96), nullable=False)
    object_type = Column(String, nullable=False)
    object_id = Column(String, nullable=False)
    object_version = Column(Integer)
    object_revision = Column(BigInteger)
    revision = Column(Integer)
    payload = Column(Text, nullable=False, default="{}")
    request_id = Column(String)
    correlation_id = Column(String, index=True)
    causation_id = Column(String)
    job_id = Column(String, index=True)
    agent_run_id = Column(String, index=True)
    tool_call_id = Column(String, index=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    __table_args__ = (
        CheckConstraint(
            EVENT_TYPE_CHECK_SQL,
            name="domain_events_event_type_check",
        ),
    )


class EventStreamWatermark(Base):
    __tablename__ = "event_stream_watermarks"
    workspace_id = Column(String, primary_key=True)
    last_sequence = Column(Integer, nullable=False, default=0)
    expired_through_sequence = Column(Integer, nullable=False, default=0)


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    role = Column(String, nullable=False, default="OWNER")
    revision = Column(Integer, nullable=False, default=1)


class Workspace(Base):
    __tablename__ = "workspaces"
    id = Column(String, primary_key=True)
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    revision = Column(Integer, nullable=False, default=1)


class ResearchPolicyVersionRow(Base):
    __tablename__ = "research_policy_versions"
    internal_id = Column("id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = Column("legacy_id", String, nullable=False, unique=True)
    workspace_id = Column(
        String, ForeignKey("workspaces.id"), nullable=False, index=True
    )
    policy_id = Column(String, nullable=False)
    version = Column(Integer, nullable=False)
    policy_family = Column(String(32), nullable=False, default="research")
    status = Column(String, nullable=False)
    rules = Column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )
    content_sha256 = Column(String(64), nullable=False)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    activated_at = Column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "legacy_id",
            name="uq_research_policy_versions_workspace_id_legacy_id",
        ),
        UniqueConstraint(
            "workspace_id",
            "policy_id",
            name="uq_research_policy_versions_workspace_public",
        ),
        CheckConstraint(
            "version >= 1", name="research_policy_versions_version_positive"
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'RETIRED')",
            name="research_policy_versions_status_valid",
        ),
    )
    __mapper_args__ = {"primary_key": [id]}


class RiskPolicyVersionRow(Base):
    __tablename__ = "risk_policy_versions"
    internal_id = Column("id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = Column("legacy_id", String, nullable=False, unique=True)
    workspace_id = Column(
        String, ForeignKey("workspaces.id"), nullable=False, index=True
    )
    policy_id = Column(String, nullable=False)
    policy_family = Column(String(32), nullable=False, default="risk")
    version = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    content_sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    activated_at = Column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "legacy_id",
            name="uq_risk_policy_versions_workspace_id_legacy_id",
        ),
        UniqueConstraint(
            "workspace_id",
            "policy_id",
            name="uq_risk_policy_versions_workspace_public",
        ),
        CheckConstraint("version >= 1", name="risk_policy_versions_version_positive"),
        CheckConstraint(
            "policy_family = 'risk'",
            name="risk_policy_versions_policy_family_valid",
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'RETIRED')",
            name="risk_policy_versions_status_valid",
        ),
    )
    __mapper_args__ = {"primary_key": [id]}


class CostModelVersionRow(Base):
    __tablename__ = "cost_model_versions"
    internal_id = Column("id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = Column("legacy_id", String, nullable=False, unique=True)
    workspace_id = Column(
        String, ForeignKey("workspaces.id"), nullable=False, index=True
    )
    cost_model_id = Column(String, nullable=False)
    version = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    content_sha256 = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    activated_at = Column(DateTime(timezone=True))
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "legacy_id",
            name="uq_cost_model_versions_workspace_id_legacy_id",
        ),
        UniqueConstraint(
            "workspace_id",
            "cost_model_id",
            name="uq_cost_model_versions_workspace_public",
        ),
        CheckConstraint("version >= 1", name="cost_model_versions_version_positive"),
        CheckConstraint(
            "status IN ('DRAFT', 'ACTIVE', 'RETIRED')",
            name="cost_model_versions_status_valid",
        ),
    )
    __mapper_args__ = {"primary_key": [id]}


class ModelProviderConnectionRow(Base):
    """Workspace/owner-bound encrypted provider credential aggregate."""

    __tablename__ = "model_provider_connections"
    id = Column(
        Uuid(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    workspace_id = Column(
        String, ForeignKey("workspaces.id"), nullable=False, index=True
    )
    owner_actor_id = Column(String, nullable=False, index=True)
    provider_id = Column(String(64), nullable=False, index=True)
    kind = Column(String(8), nullable=False)
    model_name = Column(String(128), nullable=False)
    ciphertext = Column(LargeBinary, nullable=False)
    nonce = Column(LargeBinary, nullable=False)
    key_id = Column(String(64), nullable=False)
    validation_state = Column(String(16), nullable=False, default="SUCCESS")
    status = Column(String(16), nullable=False, default="VALIDATED")
    validated_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True))
    consumed_at = Column(DateTime(timezone=True))
    __table_args__ = (
        CheckConstraint("kind IN ('AI', 'DATA')", name="provider_connection_kind"),
        CheckConstraint(
            "validation_state = 'SUCCESS'",
            name="provider_connection_validation_success",
        ),
        CheckConstraint(
            "status IN ('VALIDATED', 'ACTIVE', 'REVOKED')",
            name="provider_connection_status",
        ),
    )


class SetupBindingRow(Base):
    """Internal FK bindings behind the public, closed SettingsDetail payload."""

    __tablename__ = "setup_bindings"
    workspace_id = Column(String, ForeignKey("workspaces.id"), primary_key=True)
    settings_record_id = Column(String(42), nullable=False)
    ai_connection_id = Column(
        Uuid(as_uuid=False), ForeignKey("model_provider_connections.id"), nullable=False
    )
    data_connection_id = Column(
        Uuid(as_uuid=False), ForeignKey("model_provider_connections.id")
    )
    research_policy_version_id = Column(
        String, ForeignKey("research_policy_versions.legacy_id"), nullable=False
    )
    risk_policy_version_id = Column(
        String, ForeignKey("risk_policy_versions.legacy_id"), nullable=False
    )
    cost_model_version_id = Column(
        String, ForeignKey("cost_model_versions.legacy_id"), nullable=False
    )
    revision = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ("workspace_id", "settings_record_id"),
            ("records.workspace_id", "records.record_key"),
            name="fk_setup_bindings_settings_record_records",
        ),
        CheckConstraint(
            "settings_record_id = 'SETTINGS-DEFAULT'",
            name="ck_setup_bindings_settings_record_id",
        ),
    )


class SessionToken(Base):
    """Opaque session-token verifier; plaintext credentials are never persisted."""

    __tablename__ = "session_tokens"
    token_sha256 = Column(String(64), primary_key=True)
    actor_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    workspace_id = Column(
        String, ForeignKey("workspaces.id"), nullable=False, index=True
    )
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))


class PaperSchedulerStateRow(Base):
    """Authoritative, workspace-scoped suppression truth for Paper discovery."""

    __tablename__ = "paper_scheduler_states"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(Uuid(as_uuid=True), nullable=False, index=True)
    paper_id = Column(Uuid(as_uuid=True), nullable=False)
    scheduler_status = Column(String(16), nullable=False)
    suppressed_since_utc = Column(DateTime(timezone=True))
    resume_watermark_utc = Column(DateTime(timezone=True), nullable=False)
    last_eligible_trading_date = Column(Date)
    revision = Column(BigInteger, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        ForeignKeyConstraint(
            ("workspace_id",),
            ("workspaces.id",),
            name="fk_paper_scheduler_states_workspace_id_workspaces",
        ),
        ForeignKeyConstraint(
            ("workspace_id", "paper_id"),
            ("paper_deployments.workspace_id", "paper_deployments.id"),
            name="fk_paper_scheduler_states_workspace_id_paper_id_paper_deploymen",
        ),
        UniqueConstraint(
            "workspace_id",
            "paper_id",
            name="uq_paper_scheduler_states_workspace_id_paper_id",
        ),
        CheckConstraint(
            "scheduler_status IN ('ACTIVE', 'PAUSED', 'DISABLED')",
            name="ck_paper_scheduler_states_status",
        ),
        CheckConstraint(
            "((scheduler_status = 'ACTIVE' AND suppressed_since_utc IS NULL) OR "
            "(scheduler_status IN ('PAUSED', 'DISABLED') AND suppressed_since_utc IS NOT NULL)) "
            "AND resume_watermark_utc IS NOT NULL",
            name="ck_paper_scheduler_states_suppression_invariant",
        ),
        Index(
            "ix_paper_scheduler_states_workspace_id_scheduler_status",
            "workspace_id",
            "scheduler_status",
        ),
    )


class Audit(Base):
    __tablename__ = "audit_events"
    internal_id = Column("id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = Column("event_id", String(48), nullable=False, unique=True)
    actor_type = Column(String(16), nullable=False)
    actor_id = Column(String, nullable=False)
    workspace_id = Column(String, index=True)
    sequence = Column(BigInteger, nullable=False)
    request_id = Column(String, index=True)
    action = Column("action_type", String(96), nullable=False)
    object_type = Column(String, nullable=False)
    object_id = Column(String, nullable=False)
    object_version = Column(Integer)
    object_revision = Column(BigInteger)
    result = Column(String(16), nullable=False, default="SUCCESS")
    payload = Column("summary", Text, nullable=False, default="{}")
    detail_artifact_id = Column(Uuid(as_uuid=True), nullable=True)
    previous_sha256 = Column("prev_event_hash", String(64))
    event_sha256 = Column("event_hash", String(64), nullable=False, default="0" * 64)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    __mapper_args__ = {"primary_key": [id]}


class AuditChainHead(Base):
    __tablename__ = "audit_chain_heads"
    workspace_id = Column(String, primary_key=True)
    event_sha256 = Column(String(64))
    revision = Column(Integer, nullable=False, default=0)


class JobRow(Base):
    __tablename__ = "jobs"
    internal_id = Column("id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = Column("job_id", String(48), nullable=False, unique=True)
    workspace_id = Column(String, index=True)
    job_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    revision = Column(BigInteger, nullable=False, default=1)
    payload = Column(Text, nullable=False, default="{}")
    input_payload = Column(Text, nullable=False, default="{}")
    payload_sha256 = Column(String(64), nullable=False, default="0" * 64)
    queue_name = Column(String, nullable=False, default="core")
    priority = Column(SmallInteger, nullable=False, default=100)
    result_ref = Column(Text)
    error_code = Column(String)
    error_detail = Column(Text)
    attempt = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    lease_owner = Column(String)
    lease_expires_at = Column(DateTime(timezone=True), index=True)
    heartbeat_at = Column(DateTime(timezone=True))
    cancel_requested_at = Column(DateTime(timezone=True))
    fencing_token = Column(Integer, nullable=False, default=0)
    retry_safe = Column(Boolean, nullable=False, default=True)
    progress_mode = Column(String, nullable=False, default="NONE")
    completed_units = Column(BigInteger)
    total_units = Column(BigInteger)
    progress_unit = Column(String)
    current_step_key = Column(String)
    current_step_label = Column(String)
    queued_at = Column(DateTime(timezone=True), nullable=False)
    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))
    created_by_type = Column(String, nullable=False, default="USER")
    created_by_id = Column(String, nullable=False, default="system")
    correlation_id = Column(String, index=True)
    request_id = Column(String, index=True)
    resume_token_hash = Column(String(64))
    resume_fencing_token = Column(Integer)

    __table_args__ = (
        CheckConstraint("priority >= 0", name="jobs_priority_check"),
        CheckConstraint("attempt >= 0", name="jobs_attempt_check"),
        CheckConstraint("max_attempts >= 1", name="jobs_max_attempts_check"),
        CheckConstraint("fencing_token >= 0", name="jobs_fencing_token_check"),
        CheckConstraint(
            "completed_units IS NULL OR completed_units >= 0",
            name="jobs_completed_units_check",
        ),
        CheckConstraint(
            "total_units IS NULL OR total_units >= 0", name="jobs_total_units_check"
        ),
        Index("ix_jobs_claim", "queue_name", "status", "priority", "queued_at"),
        Index("uq_jobs_resume_token_hash", "resume_token_hash", unique=True),
    )
    __mapper_args__ = {"primary_key": [id]}


class JobDependencyRow(Base):
    __tablename__ = "job_dependencies"
    job_internal_id = Column(
        "job_id", Uuid(as_uuid=True), ForeignKey("jobs.id"), primary_key=True
    )
    depends_on_job_internal_id = Column(
        "depends_on_job_id",
        Uuid(as_uuid=True),
        ForeignKey("jobs.id"),
        primary_key=True,
        index=True,
    )
    workspace_id = Column(String, primary_key=True, nullable=False, index=True)
    job_id = Column("job_public_id", String(48), nullable=False)
    depends_on_job_id = Column(
        "depends_on_job_public_id", String(48), nullable=False, index=True
    )
    dependency_type = Column(String(16), nullable=False, default="SUCCESS")
    __table_args__ = (
        CheckConstraint(
            "dependency_type IN ('SUCCESS', 'TERMINAL')",
            name="job_dependencies_dependency_type_check",
        ),
        CheckConstraint(
            "job_id != depends_on_job_id",
            name="job_dependencies_not_self_check",
        ),
        UniqueConstraint(
            "job_public_id",
            "depends_on_job_public_id",
            name="uq_job_dependencies_public",
        ),
    )
    __mapper_args__ = {"primary_key": [job_id, depends_on_job_id]}


class ArtifactRow(Base):
    __tablename__ = "artifacts"
    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    artifact_id = Column(String(48), nullable=False, unique=True)
    workspace_id = Column(String, nullable=False, index=True)
    job_id = Column(String(48), ForeignKey("jobs.job_id"), nullable=False, index=True)
    kind = Column(String(64), nullable=False, index=True)
    media_type = Column(String(128), nullable=False)
    storage_backend = Column(String(16), nullable=False, default="LOCAL")
    storage_key = Column(Text, nullable=False, unique=True)
    size_bytes = Column(BigInteger, nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    schema_name = Column(String(96))
    schema_version = Column(Integer)
    compression = Column(String(16))
    metadata_json = Column(
        "metadata",
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )

    publication_state = Column(String(16), nullable=False, default="STAGED", index=True)
    publication_error = Column(String(128))
    created_at = Column(DateTime(timezone=True), nullable=False)
    published_at = Column(DateTime(timezone=True))
    immutable = Column(Boolean, nullable=False, default=True)
    __table_args__ = (
        CheckConstraint("size_bytes >= 0", name="artifacts_size_bytes_check"),
        CheckConstraint(
            "storage_backend IN ('LOCAL', 'S3')",
            name="artifacts_storage_backend_check",
        ),
        CheckConstraint(
            "publication_state IN ('STAGED', 'PUBLISHED', 'FAILED')",
            name="artifacts_publication_state_check",
        ),
    )


_SCHEDULER_STATE_EVIDENCE_KEYS = frozenset(
    {
        "state_transition_id",
        "workspace_id",
        "paper_id",
        "from_state",
        "to_state",
        "effective_at_utc",
        "suppressed_since_utc",
        "resume_watermark_utc",
        "initialization_utc",
        "revision",
        "reason_code",
        "actor",
        "system",
        "commit_build_locator",
    }
)


@event.listens_for(Session, "before_flush")
def _enforce_paper_scheduler_evidence_boundary(
    session: Session, _context: Any, _instances: Any
) -> None:
    """Keep state Audit and execution Artifact evidence non-interchangeable."""
    pending_jobs = {row.id: row for row in session.new if isinstance(row, JobRow)}
    for artifact in session.new:
        if (
            not isinstance(artifact, ArtifactRow)
            or artifact.schema_name != "paper_scheduler_evidence"
        ):
            continue
        job = pending_jobs.get(artifact.job_id)
        if job is None:
            job = (
                session.query(JobRow)
                .filter_by(id=artifact.job_id, workspace_id=artifact.workspace_id)
                .one_or_none()
            )
        if (
            artifact.schema_version != 1
            or artifact.kind != "JSON"
            or artifact.media_type != "application/json"
            or job is None
            or job.workspace_id != artifact.workspace_id
            or job.job_type != "PAPER_DAILY_RUN"
        ):
            raise RuntimeError(
                "paper scheduler execution evidence requires its PaperDailyRun Job"
            )
    for audit in session.new:
        if not isinstance(audit, Audit):
            continue
        try:
            summary = _json_loads(audit.payload)
        except (TypeError, json.JSONDecodeError) as error:
            raise RuntimeError("audit summary must be JSON") from error
        if not isinstance(summary, dict) or "state_transition_id" not in summary:
            continue
        if (
            set(summary) != _SCHEDULER_STATE_EVIDENCE_KEYS
            or audit.detail_artifact_id is not None
        ):
            raise RuntimeError(
                "scheduler state evidence must remain Audit-only and closed"
            )


class DataSource(Base):
    __tablename__ = "data_sources"
    id = Column(String, primary_key=True)
    workspace_id = Column(String, primary_key=True)
    provider_id = Column(String, nullable=False)
    status = Column(String, nullable=False)
    revision = Column(Integer, nullable=False, default=1)


class SnapshotRow(Base):
    __tablename__ = "data_snapshots"
    id = Column(String, primary_key=True)
    workspace_id = Column(String, index=True)
    dataset_id = Column(String, nullable=False, index=True)
    content_sha256 = Column(String(64), nullable=False)
    immutable = Column(Boolean, nullable=False, default=True)
    revision = Column(Integer, nullable=False, default=1)
    detail = Column(Text, nullable=False, default="{}")
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "content_sha256",
            name="uq_data_snapshots_workspace_content",
        ),
    )


class SnapshotPartitionRow(Base):
    """Internal immutable partition binding; HOLDOUT rows are never in public detail."""

    __tablename__ = "snapshot_partitions"
    id = Column(String, primary_key=True)
    snapshot_id = Column(
        String, ForeignKey("data_snapshots.id"), nullable=False, index=True
    )
    partition = Column(String, nullable=False)
    artifact_id = Column(String, nullable=False, unique=True)
    content_sha256 = Column(String(64), nullable=False)
    row_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False)
    __table_args__ = (
        UniqueConstraint("snapshot_id", "partition"),
        CheckConstraint("row_count >= 0", name="snapshot_partitions_row_count_check"),
    )


class ResearchRow(Base):
    __tablename__ = "research_cases"
    internal_id = Column("id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = Column("research_id", String(40), nullable=False, unique=True)
    workspace_id = Column(String, ForeignKey("workspaces.id"))
    status = Column(String, nullable=False)
    revision = Column(BigInteger, nullable=False, default=1)
    title = Column(String, nullable=False)
    research_policy_ref_id = Column(
        "research_policy_id",
        Uuid(as_uuid=True),
        ForeignKey("research_policy_versions.id"),
        nullable=False,
    )
    detail = Column(Text, nullable=False, default="{}")
    __mapper_args__ = {"primary_key": [id]}


class ExperimentRow(Base):
    __tablename__ = "experiments"
    internal_id = Column("id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = Column("experiment_id", String(48), nullable=False, unique=True)
    workspace_id = Column(String, index=True)
    research_ref_id = Column(
        "research_id",
        Uuid(as_uuid=True),
        ForeignKey("research_cases.id"),
        nullable=False,
        index=True,
    )
    research_id = Column("research_public_id", String(40), nullable=False, index=True)
    source_experiment_ref_id = Column(
        "source_experiment_id",
        Uuid(as_uuid=True),
        ForeignKey("experiments.id"),
        index=True,
    )
    source_experiment_id = Column("source_experiment_public_id", String(48), index=True)
    data_snapshot_ref_id = Column(
        "data_snapshot_id",
        Uuid(as_uuid=True),
        ForeignKey("dataset_snapshots.id"),
        nullable=False,
    )
    cost_model_ref_id = Column(
        "cost_model_id",
        Uuid(as_uuid=True),
        ForeignKey("cost_model_versions.id"),
        nullable=False,
    )
    research_policy_ref_id = Column(
        "research_policy_id",
        Uuid(as_uuid=True),
        ForeignKey("research_policy_versions.id"),
        nullable=False,
    )
    immutable = Column(Boolean, nullable=False, default=False)
    revision = Column(Integer, nullable=False, default=1)
    detail = Column(Text, nullable=False, default="{}")
    __mapper_args__ = {"primary_key": [id]}


class FactorRow(Base):
    __tablename__ = "factors"
    internal_id = Column("id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = Column("factor_id", String(40), nullable=False, unique=True)
    workspace_id = Column(String, index=True)
    research_id = Column(
        String(40), ForeignKey("research_cases.research_id"), nullable=False, index=True
    )
    revision = Column(BigInteger, nullable=False, default=1)
    detail = Column(Text, nullable=False, default="{}")
    __mapper_args__ = {"primary_key": [id]}


class StrategyRow(Base):
    __tablename__ = "strategies"
    internal_id = Column("id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = Column("strategy_id", String(40), nullable=False, unique=True)
    workspace_id = Column(String, index=True)
    research_id = Column(
        String(40), ForeignKey("research_cases.research_id"), nullable=False, index=True
    )
    revision = Column(BigInteger, nullable=False, default=1)
    detail = Column(Text, nullable=False, default="{}")
    __mapper_args__ = {"primary_key": [id]}


class StrategyVersionRow(Base):
    __tablename__ = "strategy_versions"
    internal_id = Column("id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = Column("legacy_id", String(64), nullable=False, unique=True)
    workspace_id = Column(String, index=True)
    strategy_ref_id = Column(
        "strategy_id", Uuid(as_uuid=True), ForeignKey("strategies.id"), nullable=False
    )
    strategy_id = Column("strategy_public_id", String(40), nullable=False)
    cost_model_ref_id = Column(
        "cost_model_id",
        Uuid(as_uuid=True),
        ForeignKey("cost_model_versions.id"),
        nullable=False,
    )
    version = Column(Integer, nullable=False)
    state = Column(String, nullable=False, default="CANDIDATE")
    spec_sha256 = Column(String(64), nullable=False)
    frozen_at = Column(DateTime(timezone=True))
    revision = Column(BigInteger, nullable=False, default=1)
    detail = Column(Text, nullable=False, default="{}")
    research_period_range: Any = Column(
        "research_period", DateRangeCompat(), nullable=False
    )
    validation_period_range: Any = Column(
        "validation_period", DateRangeCompat(), nullable=False
    )
    holdout_period_range: Any = Column("holdout_period", DateRangeCompat())
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "legacy_id",
            name="uq_strategy_versions_workspace_id_legacy_id",
        ),
        UniqueConstraint("strategy_public_id", "version"),
        CheckConstraint("version >= 1", name="strategy_versions_version_check"),
    )
    __mapper_args__ = {"primary_key": [id]}


class ValidationRow(Base):
    __tablename__ = "validations"
    id = Column(String, primary_key=True)
    workspace_id = Column(String, index=True)
    strategy_version_id = Column(
        String, ForeignKey("strategy_versions.legacy_id"), nullable=False
    )
    status = Column(String, nullable=False)
    holdout_state = Column(String, nullable=False, default="LOCKED")
    exposure_count = Column(Integer, nullable=False, default=0)
    revision = Column(Integer, nullable=False, default=1)
    detail = Column(Text, nullable=False, default="{}")
    __table_args__ = (
        CheckConstraint("exposure_count >= 0", name="validations_exposure_count_check"),
    )


class ApprovalRow(Base):
    __tablename__ = "approval_requests"
    internal_id = Column("id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = Column("approval_id", String(40), nullable=False, unique=True)
    workspace_id = Column(String, index=True)
    validation_id = Column(String, ForeignKey("validations.id"))
    status = Column(String, nullable=False, default="PENDING")
    subject_sha256 = Column(String(64), nullable=False)
    subject_type = Column(String, nullable=False, default="VALIDATION")
    subject_id = Column(String, nullable=False, default="")
    subject_version = Column(Integer)
    subject_revision = Column(BigInteger, nullable=False, default=1)
    subject_spec_sha256 = Column(String(64), nullable=False, default="0" * 64)
    prerequisites_sha256 = Column(String(64), nullable=False, default="0" * 64)
    approval_type = Column("type", String(32), nullable=False)
    subject_hash = Column(String(64), nullable=False)
    requested_by_type = Column(String(16), nullable=False)
    requested_by_id = Column(String(64), nullable=False)
    reason = Column(Text, nullable=False)
    prerequisites = Column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict
    )
    risk_summary = Column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict
    )
    effects = Column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list
    )
    decision_reason = Column(Text)
    requested_at = Column(DateTime(timezone=True), nullable=False)
    decided_at = Column(DateTime(timezone=True))
    decided_by = Column(String(64))
    revision = Column(BigInteger, nullable=False, default=1)
    detail = Column(Text, nullable=False, default="{}")
    __mapper_args__ = {"primary_key": [id]}


class HoldoutExposureRow(Base):
    __tablename__ = "holdout_exposures"
    internal_id = Column("id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = Column("exposure_id", String(40), nullable=False, unique=True)
    workspace_id = Column(String, index=True)
    validation_id = Column(
        String, ForeignKey("validations.id"), nullable=False, unique=True
    )
    validation_run_ref_id = Column(
        "validation_run_id",
        Uuid(as_uuid=True),
        ForeignKey("validation_runs.id"),
        nullable=False,
        index=True,
    )
    strategy_version_ref_id = Column(
        "strategy_version_id",
        Uuid(as_uuid=True),
        ForeignKey("strategy_versions.id"),
        nullable=False,
    )
    strategy_version_id = Column(
        "strategy_version_public_id", String(64), nullable=False
    )
    approval_ref_id = Column(
        "approval_id",
        Uuid(as_uuid=True),
        ForeignKey("approval_requests.id"),
        nullable=False,
        unique=True,
    )
    approval_id = Column("approval_public_id", String(40), nullable=False, unique=True)
    job_id = Column(String(48), ForeignKey("jobs.job_id"), nullable=False, unique=True)
    result_artifact_id = Column("result_artifact_public_id", String(48), nullable=False)
    provenance_id = Column("provenance_public_id", String(48), nullable=False)
    result_artifact_ref_id = Column(
        "result_artifact_id",
        Uuid(as_uuid=True),
        ForeignKey("artifacts.id"),
        nullable=False,
    )
    provenance_ref_id = Column(
        "provenance_id",
        Uuid(as_uuid=True),
        ForeignKey("provenance_records.id"),
        nullable=False,
    )
    exposed_by_job_ref_id = Column(
        "exposed_by_job_id",
        Uuid(as_uuid=True),
        ForeignKey("jobs.id"),
        nullable=False,
    )
    exposure_count = Column(Integer, nullable=False, default=1)
    holdout_period = Column(String, nullable=False)
    contaminated_for_future_versions = Column(Boolean, nullable=False, default=True)
    result_sha256 = Column(String(64), nullable=False)
    period = Column(Text, nullable=False)
    result = Column(Text, nullable=False)
    exposed_at = Column(DateTime(timezone=True), nullable=False)
    contamination = Column(Boolean, nullable=False, default=False)
    __mapper_args__ = {"primary_key": [id]}


class RuntimeHeartbeat(Base):
    __tablename__ = "runtime_heartbeats"
    component = Column(String, primary_key=True)
    instance_id = Column(String, primary_key=True)
    queue_name = Column(String)
    occurred_at = Column(DateTime(timezone=True), nullable=False, index=True)


def _install_sqlite_immutability_guards() -> None:
    for model in (Audit, HoldoutExposureRow, SnapshotRow, SnapshotPartitionRow):
        for action in ("UPDATE", "DELETE"):
            event.listen(
                model.__table__,
                "after_create",
                DDL(
                    f"CREATE TRIGGER qf_{model.__tablename__}_{action.lower()}_immutable "
                    f"BEFORE {action} ON {model.__tablename__} BEGIN SELECT RAISE(ABORT, "
                    "'immutable evidence cannot be changed'); END"
                ).execute_if(dialect="sqlite"),
            )
    event.listen(
        Event.__table__,
        "after_create",
        DDL(
            "CREATE TRIGGER qf_domain_events_update_immutable BEFORE UPDATE ON domain_events "
            "BEGIN SELECT RAISE(ABORT, 'immutable evidence cannot be changed'); END"
        ).execute_if(dialect="sqlite"),
    )
    for action in ("UPDATE", "DELETE"):
        event.listen(
            Record.__table__,
            "after_create",
            DDL(
                f"CREATE TRIGGER qf_records_{action.lower()}_immutable "
                f"BEFORE {action} ON records "
                "WHEN OLD.kind IN ('artifact', 'provenance') BEGIN "
                "SELECT RAISE(ABORT, 'immutable record cannot be changed'); END"
            ).execute_if(dialect="sqlite"),
        )
    event.listen(
        ValidationRow.__table__,
        "after_create",
        DDL(
            "CREATE TRIGGER qf_validations_holdout_transition BEFORE UPDATE OF "
            "holdout_state, exposure_count ON validations WHEN NOT ("
            "NEW.holdout_state = OLD.holdout_state OR "
            "(OLD.holdout_state = 'LOCKED' AND NEW.holdout_state = 'APPROVAL_PENDING') OR "
            "(OLD.holdout_state = 'APPROVAL_PENDING' AND NEW.holdout_state IN ('LOCKED', 'UNLOCKED')) OR "
            "(OLD.holdout_state = 'UNLOCKED' AND NEW.holdout_state = 'RUNNING') OR "
            "(OLD.holdout_state = 'RUNNING' AND NEW.holdout_state = 'EXPOSED') OR "
            "NEW.holdout_state = 'FAILED') BEGIN SELECT RAISE(ABORT, "
            "'invalid holdout state transition'); END"
        ).execute_if(dialect="sqlite"),
    )
    event.listen(
        ValidationRow.__table__,
        "after_create",
        DDL(
            "CREATE TRIGGER qf_validations_holdout_binding BEFORE UPDATE OF "
            "holdout_state, exposure_count ON validations WHEN "
            "(NEW.exposure_count != CASE WHEN NEW.holdout_state = 'EXPOSED' THEN 1 ELSE 0 END) OR "
            "(NEW.holdout_state = 'APPROVAL_PENDING' AND NOT EXISTS (SELECT 1 FROM "
            "approval_requests a WHERE a.validation_id = OLD.id AND a.status = 'PENDING')) OR "
            "(NEW.holdout_state IN ('UNLOCKED', 'RUNNING') AND NOT EXISTS (SELECT 1 FROM "
            "approval_requests a WHERE a.validation_id = OLD.id AND a.status = 'APPROVED')) OR "
            "(NEW.holdout_state = 'EXPOSED' AND NOT EXISTS (SELECT 1 FROM "
            "holdout_exposures e WHERE e.validation_id = OLD.id AND "
            "e.strategy_version_public_id = OLD.strategy_version_id)) BEGIN SELECT RAISE(ABORT, "
            "'holdout state lacks durable evidence'); END"
        ).execute_if(dialect="sqlite"),
    )
    event.listen(
        Event.__table__,
        "after_create",
        DDL(
            "CREATE TRIGGER qf_domain_events_delete_immutable BEFORE DELETE ON domain_events "
            "WHEN OLD.expires_at > CURRENT_TIMESTAMP BEGIN SELECT RAISE(ABORT, "
            "'unexpired event cannot be deleted'); END"
        ).execute_if(dialect="sqlite"),
    )
    event.listen(
        StrategyVersionRow.__table__,
        "after_create",
        DDL(
            "CREATE TRIGGER qf_strategy_versions_delete_immutable BEFORE DELETE "
            "ON strategy_versions WHEN OLD.state != 'CANDIDATE' BEGIN "
            "SELECT RAISE(ABORT, 'non-candidate strategy version cannot be deleted'); END"
        ).execute_if(dialect="sqlite"),
    )
    event.listen(
        StrategyVersionRow.__table__,
        "after_create",
        DDL(
            "CREATE TRIGGER qf_strategy_versions_update_immutable BEFORE UPDATE "
            "ON strategy_versions WHEN "
            "(OLD.state != 'CANDIDATE' AND ("
            "NEW.strategy_id != OLD.strategy_id OR NEW.version != OLD.version OR "
            "NEW.spec_sha256 != OLD.spec_sha256 OR NEW.frozen_at != OLD.frozen_at OR "
            "COALESCE(NEW.workspace_id, '') != COALESCE(OLD.workspace_id, '') OR "
            "(NEW.state = OLD.state AND NEW.detail != OLD.detail))) OR NOT ("
            "NEW.state = OLD.state OR "
            "(OLD.state = 'CANDIDATE' AND NEW.state = 'FROZEN') OR "
            "(OLD.state = 'FROZEN' AND NEW.state = 'VALIDATING') OR "
            "(OLD.state = 'VALIDATING' AND NEW.state IN ('VALIDATED', 'REJECTED')) OR "
            "(OLD.state = 'VALIDATED' AND NEW.state IN ('PAPER', 'RETIRED')) OR "
            "(OLD.state = 'PAPER' AND NEW.state = 'RETIRED')) BEGIN "
            "SELECT RAISE(ABORT, 'illegal or mutable strategy transition'); END"
        ).execute_if(dialect="sqlite"),
    )
    for action in ("UPDATE", "DELETE"):
        event.listen(
            ExperimentRow.__table__,
            "after_create",
            DDL(
                f"CREATE TRIGGER qf_{ExperimentRow.__tablename__}_{action.lower()}_immutable "
                f"BEFORE {action} ON {ExperimentRow.__tablename__} WHEN OLD.immutable = 1 BEGIN "
                "SELECT RAISE(ABORT, 'completed experiment cannot be changed'); END"
            ).execute_if(dialect="sqlite"),
        )
        event.listen(
            ApprovalRow.__table__,
            "after_create",
            DDL(
                f"CREATE TRIGGER qf_{ApprovalRow.__tablename__}_{action.lower()}_immutable "
                f"BEFORE {action} ON {ApprovalRow.__tablename__} WHEN OLD.status != 'PENDING' BEGIN "
                "SELECT RAISE(ABORT, 'terminal approval cannot be changed'); END"
            ).execute_if(dialect="sqlite"),
        )


_install_sqlite_immutability_guards()


class AgentConfigRow(Base):
    __tablename__ = "agent_configs"
    internal_id = Column("id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(String, nullable=False, default="system")
    role = Column("role_key", String(64), nullable=False)
    enabled = Column(Boolean, nullable=False, default=True)
    revision = Column(BigInteger, nullable=False, default=1)
    model_provider = Column(String, nullable=False, default="unconfigured")
    model_name = Column(String, nullable=False, default="unconfigured")
    runtime_profile = Column(String, nullable=False, default="DEFAULT")
    tool_timeout_seconds = Column(Integer, nullable=False, default=30)
    max_steps_override = Column(Integer)
    max_tool_calls_override = Column(Integer)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    __mapper_args__ = {"primary_key": [workspace_id, role]}


class AgentRunRow(Base):
    __tablename__ = "agent_runs"
    internal_id = Column("id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = Column("agent_run_id", String(48), nullable=False, unique=True)
    workspace_id = Column(String, index=True)
    role = Column("agent_role", String(64), nullable=False)
    status = Column(String, nullable=False)
    checkpoint = Column(Text)
    checkpoint_thread_id = Column(String(128))
    pending_resume_token_hash = Column(String(64))
    resume_fencing_token = Column(Integer, nullable=False, default=0)
    revision = Column(Integer, nullable=False, default=1)
    agent_version = Column(String, nullable=False, default="1.0")
    model_provider = Column(String, nullable=False, default="unconfigured")
    model_name = Column(String, nullable=False, default="unconfigured")
    research_ref_id = Column(
        "research_id", Uuid(as_uuid=True), ForeignKey("research_cases.id")
    )
    research_id = Column("research_public_id", String(40))
    object_type = Column(String)
    object_id = Column(String)
    object_version = Column(Integer)
    object_revision = Column(BigInteger)
    objective = Column(Text, nullable=False, default="")
    decision_summary = Column(Text)
    next_action = Column(Text)
    root_agent_run_ref_id = Column(
        "root_agent_run_id", Uuid(as_uuid=True), ForeignKey("agent_runs.id"), index=True
    )
    root_agent_run_id = Column("root_agent_run_public_id", String(48), index=True)
    parent_agent_run_ref_id = Column(
        "parent_agent_run_id",
        Uuid(as_uuid=True),
        ForeignKey("agent_runs.id"),
        index=True,
    )
    parent_agent_run_id = Column("parent_agent_run_public_id", String(48), index=True)
    context_sha256 = Column(String(64), nullable=False, default="0" * 64)
    model_call_count = Column(Integer, nullable=False, default=0)
    input_tokens = Column(BigInteger, nullable=False, default=0)
    output_tokens = Column(BigInteger, nullable=False, default=0)
    tool_call_count = Column(Integer, nullable=False, default=0)
    step_count = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    __table_args__ = (
        Index(
            "uq_agent_runs_checkpoint_thread_id",
            "checkpoint_thread_id",
            unique=True,
        ),
    )
    __mapper_args__ = {"primary_key": [id]}


class ToolCallRow(Base):
    __tablename__ = "tool_calls"
    internal_id = Column("id", Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id = Column("tool_call_id", String(48), nullable=False, unique=True)
    workspace_id = Column(String, index=True)
    agent_run_ref_id = Column(
        "agent_run_id",
        Uuid(as_uuid=True),
        ForeignKey("agent_runs.id"),
        nullable=False,
        index=True,
    )
    agent_run_id = Column("agent_run_public_id", String(48), nullable=False, index=True)
    tool_name = Column(String, nullable=False)
    tool_version = Column(String, nullable=False)
    status = Column(String, nullable=False)
    input_payload = Column(Text, nullable=False, default="{}")
    input_sha256 = Column(String(64), nullable=False)
    semantic_scope = Column(String, nullable=False, default="")
    objective = Column(Text)
    research_ref_id = Column(
        "research_id", Uuid(as_uuid=True), ForeignKey("research_cases.id")
    )
    research_id = Column("research_public_id", String(40))
    experiment_ref_id = Column(
        "experiment_id", Uuid(as_uuid=True), ForeignKey("experiments.id")
    )
    experiment_id = Column("experiment_public_id", String(48))
    job_ref_id = Column("job_id", Uuid(as_uuid=True), ForeignKey("jobs.id"), index=True)
    job_id = Column("job_public_id", String(48), index=True)
    policy_version_ref = Column(String, nullable=False)
    result_summary = Column(Text)
    output_artifact_ref_id = Column(
        "output_artifact_id", Uuid(as_uuid=True), ForeignKey("artifacts.id")
    )
    output_artifact_id = Column("output_artifact_public_id", String(48))
    warnings = Column(Text, nullable=False, default="[]")
    provenance = Column(Text)
    started_at = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    finished_at = Column(DateTime(timezone=True))
    duration_ms = Column(BigInteger)
    __table_args__ = (
        Index(
            "uq_tool_calls_active_semantic",
            "workspace_id",
            "semantic_scope",
            "tool_name",
            "input_sha256",
            unique=True,
            sqlite_where=text("status IN ('RUNNING', 'SUCCESS')"),
            postgresql_where=text("status IN ('RUNNING', 'SUCCESS')"),
        ),
    )
    __mapper_args__ = {"primary_key": [id]}


def _public_row(
    session: Session, model: Any, public_id: str | None, workspace_id: str | None
) -> Any | None:
    if not public_id:
        return None
    for candidate in session.new:
        if (
            isinstance(candidate, model)
            and getattr(candidate, "id", None) == public_id
            and getattr(candidate, "workspace_id", None) == workspace_id
        ):
            return candidate
    return session.execute(
        select(model).where(model.id == public_id, model.workspace_id == workspace_id)
    ).scalar_one_or_none()


def _detail_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


@event.listens_for(Session, "before_flush")
def _resolve_section14_internal_refs(
    session: Session, _flush_context: Any, _instances: Any
) -> None:
    """Resolve public compatibility references to canonical UUID foreign keys."""

    with session.no_autoflush:
        for row in session.new:
            if hasattr(row, "workspace_id") and row.workspace_id is not None:
                row.workspace_id = canonical_workspace_id(row.workspace_id)
            if isinstance(row, Workspace):
                row.id = canonical_workspace_id(row.id)
            if hasattr(row, "internal_id") and row.internal_id is None:
                row.internal_id = uuid.uuid4()
        for row in tuple(session.new) + tuple(session.dirty):
            workspace_id = cast(str | None, getattr(row, "workspace_id", None))
            if isinstance(row, ResearchRow) and row.research_policy_ref_id is None:
                workspace_id = row.workspace_id or session.info.get("workspace_id")
                row.workspace_id = workspace_id
                policy = (
                    session.query(ResearchPolicyVersionRow)
                    .filter_by(
                        **({"workspace_id": workspace_id} if workspace_id else {})
                    )
                    .filter_by(policy_family="research")
                    .filter_by(status="ACTIVE")
                    .first()
                )
                if policy is not None:
                    row.workspace_id = row.workspace_id or policy.workspace_id
                    row.research_policy_ref_id = policy.internal_id
            elif isinstance(row, ExperimentRow):
                experiment_refs = cast(_ExperimentReferenceFields, row)
                research = _public_row(
                    session,
                    ResearchRow,
                    _as_optional_str(row.research_id),
                    workspace_id,
                )
                if research is not None:
                    row.research_ref_id = research.internal_id
                source = _public_row(
                    session,
                    ExperimentRow,
                    _as_optional_str(row.source_experiment_id),
                    workspace_id,
                )
                if source is not None:
                    row.source_experiment_ref_id = source.internal_id
                detail = _json_loads(row.detail)
                snapshot_table = Base.metadata.tables["dataset_snapshots"]
                experiment_refs.data_snapshot_ref_id = session.execute(
                    select(snapshot_table.c.id).where(
                        snapshot_table.c.snapshot_id == detail["data_snapshot_id"],
                        snapshot_table.c.workspace_id == workspace_id,
                    )
                ).scalar_one_or_none()
                cost = (
                    session.query(CostModelVersionRow)
                    .filter_by(
                        workspace_id=row.workspace_id,
                        cost_model_id=detail["cost_model_id"],
                    )
                    .one_or_none()
                )
                if cost is not None:
                    row.cost_model_ref_id = cost.internal_id
                policy = (
                    session.query(ResearchPolicyVersionRow)
                    .filter_by(
                        workspace_id=row.workspace_id,
                        policy_family="research",
                        status="ACTIVE",
                    )
                    .first()
                )
                if policy is not None:
                    row.research_policy_ref_id = policy.internal_id
            elif isinstance(row, StrategyVersionRow):
                strategy = _public_row(
                    session,
                    StrategyRow,
                    _as_optional_str(row.strategy_id),
                    workspace_id,
                )
                if strategy is not None:
                    row.strategy_ref_id = strategy.internal_id
                detail = _json_loads(row.detail)
                cost_model_id = detail.get("cost_model_id")
                cost_query = session.query(CostModelVersionRow).filter_by(
                    workspace_id=row.workspace_id
                )
                cost = (
                    cost_query.filter_by(cost_model_id=cost_model_id).one_or_none()
                    if cost_model_id
                    else cost_query.filter_by(status="ACTIVE").first()
                )
                if cost is not None:
                    row.cost_model_ref_id = cost.internal_id
                row.research_period_range = detail.get("research_period")
                row.validation_period_range = detail.get("validation_period")
                row.holdout_period_range = detail.get("holdout_period")
            elif isinstance(row, ApprovalRow):
                approval_timestamps = cast(_ApprovalDetailFields, row)
                detail = _json_loads(row.detail)
                subject = _as_json_object(detail.get("subject", {}))
                requester = _as_json_object(detail.get("requester", {}))
                approval_timestamps.approval_type = _as_str(
                    detail.get("type", _as_str(row.approval_type))
                )
                approval_timestamps.subject_hash = _as_str(
                    subject.get("sha256", _as_str(row.subject_sha256))
                )
                approval_timestamps.requested_by_type = _as_str(
                    requester.get("type", "SYSTEM")
                )
                approval_timestamps.requested_by_id = _as_str(
                    requester.get("id", "system")
                )
                approval_timestamps.reason = _as_str(detail.get("reason", ""))
                approval_timestamps.prerequisites = detail.get("prerequisites", [])
                approval_timestamps.risk_summary = detail.get("risk_summary", {})
                approval_timestamps.effects = detail.get("effects", [])
                approval_timestamps.requested_at = _detail_datetime(
                    detail.get("requested_at")
                ) or datetime.now(UTC)
                approval_timestamps.decided_at = _detail_datetime(
                    detail.get("decided_at")
                )
                approval_timestamps.decision_reason = _as_optional_str(
                    detail.get("decision_reason")
                )
                approval_timestamps.decided_by = _as_optional_str(
                    detail.get("decided_by")
                )
            elif isinstance(row, HoldoutExposureRow):
                holdout_refs = cast(_HoldoutReferenceFields, row)
                strategy = _public_row(
                    session,
                    StrategyVersionRow,
                    _as_optional_str(row.strategy_version_id),
                    workspace_id,
                )
                if strategy is not None:
                    row.strategy_version_ref_id = strategy.internal_id
                approval = _public_row(
                    session,
                    ApprovalRow,
                    _as_optional_str(row.approval_id),
                    workspace_id,
                )
                if approval is not None:
                    row.approval_ref_id = approval.internal_id
                validation_runs = Base.metadata.tables["validation_runs"]
                holdout_refs.validation_run_ref_id = session.execute(
                    select(validation_runs.c.id).where(
                        validation_runs.c.validation_id == row.validation_id,
                        validation_runs.c.workspace_id == workspace_id,
                    )
                ).scalar_one_or_none()
                artifact = (
                    session.query(ArtifactRow)
                    .filter_by(
                        artifact_id=row.result_artifact_id,
                        workspace_id=workspace_id,
                    )
                    .one_or_none()
                )
                if artifact is not None:
                    row.result_artifact_ref_id = artifact.id
                provenance_records = Base.metadata.tables["provenance_records"]
                holdout_refs.provenance_ref_id = session.execute(
                    select(provenance_records.c.id).where(
                        provenance_records.c.provenance_id == row.provenance_id,
                        provenance_records.c.workspace_id == workspace_id,
                    )
                ).scalar_one_or_none()
                exposed_by_job = _public_row(
                    session, JobRow, _as_optional_str(row.job_id), workspace_id
                )
                if exposed_by_job is not None:
                    row.exposed_by_job_ref_id = exposed_by_job.internal_id
                holdout_refs.exposure_count = max(1, _as_int(row.exposure_count or 1))
                row.holdout_period = row.period
                holdout_refs.contaminated_for_future_versions = True
            elif isinstance(row, AgentRunRow):
                research = _public_row(
                    session,
                    ResearchRow,
                    _as_optional_str(row.research_id),
                    workspace_id,
                )
                if research is not None:
                    row.research_ref_id = research.internal_id
                root = _public_row(
                    session,
                    AgentRunRow,
                    _as_optional_str(row.root_agent_run_id),
                    workspace_id,
                )
                if root is not None:
                    row.root_agent_run_ref_id = root.internal_id
                parent = _public_row(
                    session,
                    AgentRunRow,
                    _as_optional_str(row.parent_agent_run_id),
                    workspace_id,
                )
                if parent is not None:
                    row.parent_agent_run_ref_id = parent.internal_id
            elif isinstance(row, ToolCallRow):
                run = _public_row(
                    session,
                    AgentRunRow,
                    _as_optional_str(row.agent_run_id),
                    workspace_id,
                )
                if run is not None:
                    row.agent_run_ref_id = run.internal_id
                research = _public_row(
                    session,
                    ResearchRow,
                    _as_optional_str(row.research_id),
                    workspace_id,
                )
                if research is not None:
                    row.research_ref_id = research.internal_id
                experiment = _public_row(
                    session,
                    ExperimentRow,
                    _as_optional_str(row.experiment_id),
                    workspace_id,
                )
                if experiment is not None:
                    row.experiment_ref_id = experiment.internal_id
                job_row = _public_row(
                    session, JobRow, _as_optional_str(row.job_id), workspace_id
                )
                if job_row is not None:
                    row.job_ref_id = job_row.internal_id
                if row.output_artifact_id:
                    artifact = (
                        session.query(ArtifactRow)
                        .filter_by(
                            artifact_id=row.output_artifact_id,
                            workspace_id=workspace_id,
                        )
                        .one_or_none()
                    )
                    if artifact is not None:
                        row.output_artifact_ref_id = artifact.id
            elif isinstance(row, JobDependencyRow):
                job_row = _public_row(
                    session, JobRow, _as_optional_str(row.job_id), workspace_id
                )
                dependency = _public_row(
                    session,
                    JobRow,
                    _as_optional_str(row.depends_on_job_id),
                    workspace_id,
                )
                if job_row is not None:
                    row.job_internal_id = job_row.internal_id
                    row.workspace_id = job_row.workspace_id
                if dependency is not None:
                    row.depends_on_job_internal_id = dependency.internal_id


augment_section14_metadata(Base.metadata)


# Schema creation is explicitly test-only. Durable environments are Alembic-only.
if os.getenv("QF_ALLOW_TEST_SCHEMA_BOOTSTRAP") == "1":
    if ENVIRONMENT != "test" or not DB_URL.startswith("sqlite"):
        raise RuntimeError("test schema bootstrap is allowed only for SQLite tests")
    logger.warning(
        "test-only SQLite schema bootstrap enabled; Alembic is authoritative"
    )
    Base.metadata.create_all(engine)
app = FastAPI(
    title="QuantFoundry Core API",
    version="1.0.0-p0",
    openapi_url="/api/v1/openapi.json",
    docs_url=None,
)
app.router.route_class = CanonicalRoute


ROLES = [
    "RESEARCH_DIRECTOR",
    "FACTOR_SCIENTIST",
    "STRATEGY_SCIENTIST",
    "PORTFOLIO_ANALYST",
    "RED_TEAM_RESEARCHER",
    "PERFORMANCE_ANALYST",
]
ENGINE_VERSIONS = {
    "qf-factor-v1": "1.0.0",
    "qf-simulation-v1": "1.0.0",
    "qf-validation-v1": "1.0.0",
}
DEFAULT_AGENT_PROVIDER = os.getenv("QF_AGENT_PROVIDER", "unconfigured")
DEFAULT_AGENT_MODEL = os.getenv("QF_AGENT_MODEL", "unconfigured")


def require_engine(engine_key: str, engine_version: str, expected_key: str) -> None:
    if engine_key != expected_key or ENGINE_VERSIONS.get(engine_key) != engine_version:
        raise problem(
            422, "INVALID_REQUEST", "unsupported deterministic engine/version"
        )


def require_cost_model(cost_model_id: str) -> None:
    try:
        load_cost_model(cost_model_id)
    except EngineInputError as error:
        raise problem(422, "INVALID_REQUEST", str(error)) from error


def resolve_research_policy(
    s: Session,
    workspace_id: str,
    requested_policy_id: str | None,
) -> ResearchPolicyVersionRow:
    if requested_policy_id is not None:
        row = s.execute(
            select(ResearchPolicyVersionRow).where(
                ResearchPolicyVersionRow.workspace_id == workspace_id,
                ResearchPolicyVersionRow.policy_id == requested_policy_id,
                ResearchPolicyVersionRow.policy_family == "research",
                ResearchPolicyVersionRow.status == "ACTIVE",
            )
        ).scalar_one_or_none()
        if row is None:
            raise problem(422, "INVALID_REQUEST", "research policy is not active")
        return row
    binding = s.get(SetupBindingRow, workspace_id)
    if binding is not None:
        bound = s.get(ResearchPolicyVersionRow, binding.research_policy_version_id)
        if (
            bound is not None
            and bound.workspace_id == workspace_id
            and bound.policy_family == "research"
            and bound.status == "ACTIVE"
        ):
            return bound
    active = (
        s.execute(
            select(ResearchPolicyVersionRow).where(
                ResearchPolicyVersionRow.workspace_id == workspace_id,
                ResearchPolicyVersionRow.policy_family == "research",
                ResearchPolicyVersionRow.status == "ACTIVE",
            )
        )
        .scalars()
        .all()
    )
    if len(active) != 1:
        raise problem(
            422,
            "INVALID_REQUEST",
            "research policy cannot be resolved unambiguously",
        )
    return active[0]


def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@dataclass(frozen=True)
class Actor:
    id: str
    workspace_id: str
    role: str
    request_id: str


def _configured_test_actor(token: str, request_id: str) -> Actor | None:
    """Test-only token issuer, opt-in through an explicit test environment."""
    if ENVIRONMENT != "test":
        return None
    configured = json.loads(os.getenv("QF_TEST_AUTH_TOKENS", "{}"))
    value = configured.get(token)
    if not isinstance(value, dict):
        return None
    actor_id, workspace_id, role = (
        value.get("actor_id"),
        value.get("workspace_id"),
        value.get("role"),
    )
    if not all(
        isinstance(item, str) and item for item in (actor_id, workspace_id, role)
    ):
        return None
    return Actor(
        _as_str(actor_id),
        canonical_workspace_id(_as_str(workspace_id)),
        _as_str(role),
        request_id,
    )


def _session_is_active(row: SessionToken, now: datetime) -> bool:
    expires_at = row.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return row.revoked_at is None and expires_at > now


bearer = HTTPBearer(auto_error=False, scheme_name="bearerAuth")


def auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer),
    s: Session = Depends(db),
) -> Actor:
    preauthenticated = getattr(request.state, "actor", None)
    if isinstance(preauthenticated, Actor):
        return preauthenticated
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise problem(401, "UNAUTHENTICATED", "Bearer authentication required")
    token = credentials.credentials.strip()
    if not token:
        raise problem(401, "UNAUTHENTICATED", "Bearer token is empty")
    request_id = getattr(request.state, "request_id", new_id("REQ"))
    test_actor = _configured_test_actor(token, request_id)
    if test_actor is not None:
        return test_actor
    digest = hashlib.sha256(token.encode()).hexdigest()
    row = s.get(SessionToken, digest)
    now = datetime.now(UTC)
    if row is None or not _session_is_active(row, now):
        raise problem(401, "UNAUTHENTICATED", "Bearer token is invalid or expired")
    user = s.get(User, row.actor_id)
    workspace = s.get(Workspace, row.workspace_id)
    if (
        user is None
        or workspace is None
        or (user.role == "OWNER" and workspace.owner_id != user.id)
    ):
        raise problem(401, "UNAUTHENTICATED", "Bearer session is no longer valid")
    actor = Actor(
        _as_str(user.id), _as_str(workspace.id), _as_str(user.role), request_id
    )
    return actor


def require_owner(actor: Actor = Depends(auth)) -> Actor:
    if actor.role != "OWNER":
        raise problem(403, "PERMISSION_DENIED", "Owner authority required")
    return actor


@app.middleware("http")
async def authenticate_before_request_validation(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-ID") or new_id("REQ")
    if not request.url.path.startswith("/api/v1") or request.url.path in {
        "/api/v1/system/health",
        "/api/v1/openapi.json",
    }:
        return await call_next(request)
    authorization = request.headers.get("Authorization", "")
    if (
        not authorization.startswith("Bearer ")
        or not authorization.removeprefix("Bearer ").strip()
    ):
        return JSONResponse(
            problem_payload(
                401, "UNAUTHENTICATED", request, "Bearer authentication required"
            ),
            status_code=401,
            media_type="application/problem+json",
        )
    token = authorization.removeprefix("Bearer ").strip()
    actor = _configured_test_actor(token, request.state.request_id)
    if actor is None:
        session = SessionLocal()
        try:
            digest = hashlib.sha256(token.encode()).hexdigest()
            row = session.get(SessionToken, digest)
            now = datetime.now(UTC)
            if row is not None and _session_is_active(row, now):
                user = session.get(User, row.actor_id)
                workspace = session.get(Workspace, row.workspace_id)
                if (
                    user is not None
                    and workspace is not None
                    and (user.role != "OWNER" or workspace.owner_id == user.id)
                ):
                    actor = Actor(
                        _as_str(user.id),
                        _as_str(workspace.id),
                        _as_str(user.role),
                        request.state.request_id,
                    )
        finally:
            session.close()
    if actor is None:
        return JSONResponse(
            problem_payload(
                401, "UNAUTHENTICATED", request, "Bearer token is invalid or expired"
            ),
            status_code=401,
            media_type="application/problem+json",
        )
    if actor.role != "OWNER":
        return JSONResponse(
            problem_payload(
                403, "PERMISSION_DENIED", request, "Owner authority required"
            ),
            status_code=403,
            media_type="application/problem+json",
        )
    request.state.actor = actor
    return await call_next(request)


def problem(status: int, code: str, detail: str | None = None):
    return __import__("fastapi").HTTPException(
        status_code=status,
        detail={
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
    )


def problem_payload(
    status: int,
    code: str,
    request: Request,
    detail: str | None = None,
    *,
    field_errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "type": f"https://quantfoundry.local/problems/{code.lower().replace('_', '-')}",
        "title": code,
        "status": status,
        "code": code,
        "detail": detail,
        "instance": str(request.url.path),
        "request_id": getattr(request.state, "request_id", new_id("REQ")),
        "retryable": False,
        "field_errors": field_errors or [],
        "context": {},
    }


def invalid_request_response(request: Request, error: Exception) -> JSONResponse:
    field = getattr(error, "json_path", "$") or "$"
    return JSONResponse(
        problem_payload(
            422,
            "INVALID_REQUEST",
            request,
            str(error),
            field_errors=[
                {"field": field, "message": str(error), "code": "INVALID_REQUEST"}
            ],
        ),
        status_code=422,
        media_type="application/problem+json",
    )


@app.exception_handler(__import__("fastapi").HTTPException)
async def errors(request: Request, e):
    detail = e.detail if isinstance(e.detail, dict) else {}
    code = detail.get("code", "INTERNAL_ERROR")
    if (
        code
        not in canonical_openapi()["components"]["schemas"]["CanonicalErrorCode"][
            "enum"
        ]
    ):
        code = "INTERNAL_ERROR"
    payload: dict[str, Any] = {
        "type": f"https://quantfoundry.local/problems/{code.lower().replace('_', '-')}",
        "title": str(detail.get("title") or code),
        "status": e.status_code,
        "code": code,
        "detail": detail.get("detail"),
        "instance": str(request.url.path),
        "request_id": getattr(request.state, "request_id", new_id("REQ")),
        "retryable": bool(detail.get("retryable", False)),
        "field_errors": detail.get("field_errors", []),
        "context": detail.get("context", {}),
    }
    return JSONResponse(
        payload, status_code=e.status_code, media_type="application/problem+json"
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error(request: Request, error: RequestValidationError):
    return invalid_request_response(request, error)


@app.exception_handler(Exception)
async def unexpected_error(request: Request, _: Exception):
    """No validation, persistence or handler exception may escape as HTML."""
    payload: dict[str, Any] = {
        "type": "https://quantfoundry.local/problems/internal-error",
        "title": "INTERNAL_ERROR",
        "status": 500,
        "code": "INTERNAL_ERROR",
        "detail": None,
        "instance": str(request.url.path),
        "request_id": getattr(request.state, "request_id", new_id("REQ")),
        "retryable": False,
        "field_errors": [],
        "context": {},
    }
    return JSONResponse(payload, status_code=500, media_type="application/problem+json")


def etag(r: Record):
    return f'W/"{r.record_key}:{r.revision}"'


def body(r):
    return json.loads(r.body)


def new_id(prefix: str) -> str:
    aliases = {"MEM": "memo", "HEXP": "holdout_exposure"}
    kind = aliases.get(prefix)
    if kind is None:
        kind = next(
            (key for key, value in PUBLIC_ID_PREFIXES.items() if value == prefix), None
        )
    if kind is not None:
        return new_public_id(kind)
    return f"{prefix}-{uuid.uuid4()}"


def content_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def wire_datetime(value: datetime) -> str:
    """Serialize DB timestamps as explicit UTC even when SQLite drops tzinfo."""

    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return aware.isoformat().replace("+00:00", "Z")


def create_provenance(
    s: Session,
    *,
    input_value: Any,
    output_sha256: str,
    engine_name: str,
    engine_version: str = "1.0.0",
    adapter: dict[str, str] | None = None,
    data_snapshot_ids: list[str] | None = None,
    experiment_id: str | None = None,
    source_experiment_id: str | None = None,
    tool_call_id: str | None = None,
    policies: list[dict[str, Any]] | None = None,
    strategy: dict[str, Any] | None = None,
    factors: list[dict[str, Any]] | None = None,
    cost_model: dict[str, Any] | None = None,
    parameters_sha256: str | None = None,
) -> dict[str, str]:
    provenance_id = new_id("PROV")
    detail = validated_payload(
        "Provenance",
        {
            "provenance_id": provenance_id,
            "schema_version": 1,
            "experiment_id": experiment_id,
            "source_experiment_id": source_experiment_id,
            "tool_call_id": tool_call_id,
            "data_snapshot_ids": data_snapshot_ids or [],
            "engine": {"name": engine_name, "version": engine_version},
            "adapter": adapter,
            "code": {
                "commit": GIT_COMMIT,
                "build_id": BUILD_ID,
            },
            "policies": policies or [],
            "strategy": strategy,
            "factors": factors or [],
            "cost_model": cost_model,
            "parameters_sha256": parameters_sha256,
            "input_sha256": content_hash(input_value),
            "output_sha256": output_sha256,
            "calculated_at": NOW(),
        },
    )
    save(s, "provenance", detail, provenance_id)
    provenance_table = Base.metadata.tables.get("provenance_records")
    if provenance_table is not None:
        calculated_at = _detail_datetime(detail["calculated_at"])
        values = {
            "id": uuid.uuid4(),
            "workspace_id": canonical_workspace_id(
                cast(str | None, s.info.get("workspace_id")) or "system"
            ),
            "provenance_id": provenance_id,
            "schema_version": detail["schema_version"],
            "experiment_id": detail.get("experiment_id"),
            "source_experiment_id": detail.get("source_experiment_id"),
            "tool_call_id": detail.get("tool_call_id"),
            "data_snapshot_ids": detail["data_snapshot_ids"],
            "engine_name": detail["engine"]["name"],
            "engine_version": detail["engine"]["version"],
            "adapter_name": (detail.get("adapter") or {}).get("name"),
            "adapter_version": (detail.get("adapter") or {}).get("version"),
            "code_commit": detail["code"]["commit"],
            "build_id": detail["code"]["build_id"],
            "policy_refs": detail["policies"],
            "strategy_ref": detail.get("strategy"),
            "factor_refs": detail["factors"],
            "cost_model_ref": detail.get("cost_model"),
            "parameters_sha256": detail.get("parameters_sha256"),
            "input_sha256": detail["input_sha256"],
            "output_sha256": detail["output_sha256"],
            "calculated_at": calculated_at,
            "created_at": datetime.now(UTC),
        }
        s.execute(
            provenance_table.insert().values(
                **{
                    key: value
                    for key, value in values.items()
                    if key in provenance_table.c
                }
            )
        )
    return {"provenance_id": provenance_id}


def save(
    s: Session,
    kind: str,
    data: dict[str, Any],
    id: str,
    *,
    event_type: str | None = None,
) -> Record:
    now = datetime.now(UTC)
    r = Record(
        workspace_id=cast(str | None, s.info.get("workspace_id")),
        record_key=id,
        kind=kind,
        body=json.dumps(data),
        created_at=now,
        updated_at=now,
    )
    s.add(r)
    s.flush()
    if event_type is not None:
        emit(s, kind, _as_str(r.record_key), 1, event_type)
    return r


def get(s: Session, kind: str, id: str, *, workspace_id: str) -> Record:
    r = s.execute(
        select(Record).where(
            Record.workspace_id == workspace_id,
            Record.record_key == id,
        )
    ).scalar_one_or_none()
    if not r or r.kind != kind:
        raise problem(404, "RESOURCE_NOT_FOUND", f"{kind} not found")
    return r


def require_workspace(row: Any, actor: Actor) -> Any:
    if getattr(row, "workspace_id", None) != actor.workspace_id:
        raise problem(403, "PERMISSION_DENIED", "resource belongs to another workspace")
    return row


def owned(s: Session, model: Any, identifier: str, actor: Actor, label: str) -> Any:
    row = s.execute(
        select(model).where(
            model.id == identifier,
            model.workspace_id == actor.workspace_id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise problem(404, "RESOURCE_NOT_FOUND", f"{label} not found")
    return row


def emit(
    s: Session,
    kind: str,
    id: str,
    rev: int,
    event_type: str,
    *,
    payload: dict[str, Any] | None = None,
    job_id: str | None = None,
    agent_run_id: str | None = None,
    tool_call_id: str | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    request_id: str | None = None,
    actor_id: str | None = None,
    workspace_id: str | None = None,
    object_version: int | None = None,
    object_revision: int | None = None,
    audit_summary: dict[str, Any] | None = None,
    detail_artifact_id: uuid.UUID | None = None,
) -> str:
    now = datetime.now(UTC)
    effective_actor_id = actor_id or cast(str, s.info.get("actor_id", "system"))
    effective_workspace_id = workspace_id or cast(
        str | None, s.info.get("workspace_id")
    )
    chain_workspace = canonical_workspace_id(effective_workspace_id or "system")
    effective_request_id = (
        request_id
        or cast(str | None, s.info.get("request_id"))
        or correlation_id
        or new_id("REQ")
    )
    event_id = new_id("EVT")
    effective_object_revision = object_revision if object_revision is not None else rev
    if kind == "strategy_version" and object_version is None:
        raise RuntimeError("strategy_version events require an explicit object_version")
    if kind in {"settings", "provider_connection", "agent_config"}:
        object_version = None
    raw_payload = payload if payload is not None else {}
    try:
        canonical_event_type = validate_event_type(event_type)
    except EventValidationError:
        logger.error(
            "non-canonical event type replaced with system.resync_required: %r",
            event_type,
        )
        canonical_event_type = "system.resync_required"
        event_payload = safe_resync_payload()
        kind = "event_stream"
        id = event_id
        object_version = None
    else:
        event_payload = validate_event_payload(raw_payload)
    validate_sse_envelope(
        {
            "schema_version": 1,
            "event_id": event_id,
            "sequence": 1,
            "event_type": canonical_event_type,
            "occurred_at": now.isoformat(),
            "object_type": kind,
            "object_id": id,
            "object_version": object_version,
            "object_revision": effective_object_revision,
            "request_id": effective_request_id,
            "job_id": job_id,
            "agent_run_id": agent_run_id,
            "tool_call_id": tool_call_id,
            "payload": event_payload,
        }
    )
    if s.get_bind().dialect.name == "postgresql":
        s.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:workspace_id))"),
            {"workspace_id": chain_workspace},
        )
    watermark = s.execute(
        select(EventStreamWatermark)
        .where(EventStreamWatermark.workspace_id == chain_workspace)
        .with_for_update()
    ).scalar_one_or_none()
    if watermark is None:
        next_sequence = 1
        watermark = EventStreamWatermark(
            workspace_id=chain_workspace,
            last_sequence=next_sequence,
            expired_through_sequence=0,
        )
        s.add(watermark)
    else:
        next_sequence = _as_int(watermark.last_sequence) + 1
        cast(_WatermarkFields, watermark).last_sequence = next_sequence
    event = Event(
        sequence=next_sequence,
        event_id=event_id,
        workspace_id=chain_workspace,
        actor_id=effective_actor_id,
        event_type=canonical_event_type,
        object_type=kind,
        object_id=id,
        object_version=object_version,
        object_revision=effective_object_revision,
        revision=effective_object_revision,
        payload=json.dumps(event_payload),
        request_id=effective_request_id,
        correlation_id=correlation_id,
        causation_id=causation_id,
        job_id=job_id,
        agent_run_id=agent_run_id,
        tool_call_id=tool_call_id,
        occurred_at=now,
        expires_at=now + timedelta(days=7),
    )
    s.add(event)
    head = s.execute(
        select(AuditChainHead)
        .where(AuditChainHead.workspace_id == chain_workspace)
        .with_for_update()
    ).scalar_one_or_none()
    previous_sha256 = head.event_sha256 if head is not None else None
    audit_payload = {
        "event_id": event_id,
        "object_version": object_version,
        "object_revision": effective_object_revision,
        "correlation_id": correlation_id,
        "causation_id": causation_id,
        "job_id": job_id,
        "agent_run_id": agent_run_id,
        "tool_call_id": tool_call_id,
    }
    event_sha256 = content_hash(
        {
            "previous_sha256": previous_sha256,
            "actor_id": effective_actor_id,
            "action": canonical_event_type,
            "object_type": kind,
            "object_id": id,
            "payload": audit_payload,
            "occurred_at": now.isoformat(),
        }
    )
    if head is None:
        head = AuditChainHead(
            workspace_id=chain_workspace,
            event_sha256=event_sha256,
            revision=1,
        )
        s.add(head)
    else:
        head_fields = cast(_AuditChainHeadFields, head)
        head_fields.event_sha256 = event_sha256
        head_fields.revision = _as_int(head.revision) + 1
    s.add(
        Audit(
            id=new_id("AUD"),
            actor_type=("SYSTEM" if effective_actor_id == "system" else "OWNER"),
            actor_id=effective_actor_id,
            workspace_id=chain_workspace,
            sequence=next_sequence,
            request_id=effective_request_id,
            action=canonical_event_type,
            object_type=kind,
            object_id=id,
            object_version=object_version,
            object_revision=effective_object_revision,
            result="SUCCESS",
            payload=json.dumps(
                audit_summary if audit_summary is not None else audit_payload
            ),
            detail_artifact_id=detail_artifact_id,
            previous_sha256=previous_sha256,
            event_sha256=event_sha256,
            occurred_at=now,
        )
    )
    s.flush()
    return event_id
    assert event.sequence is not None
    s.flush()


def idem(
    s: Session,
    actor: Actor,
    key: str | None,
    request: dict[str, Any],
    path: str,
    fn: Any,
    *,
    method: str = "POST",
):
    s.info["actor_id"] = actor.id
    s.info["workspace_id"] = actor.workspace_id
    s.info["request_id"] = actor.request_id
    return execute_idempotent(
        s,
        Idempotency,
        key,
        request,
        path,
        fn,
        problem,
        actor_id=actor.id,
        workspace_id=actor.workspace_id,
        method=method,
    )


def cap(
    action: str,
    allowed: bool = True,
    reason: str | None = None,
    *,
    visibility: str = "SHOW",
    idempotency_required: bool = False,
    if_match_required: bool = False,
    result_mode: str = "IMMEDIATE",
    danger_level: str = "NORMAL",
    requires_confirmation: bool = False,
) -> dict[str, Any]:
    return {
        "action": action,
        "visibility": visibility,
        "allowed": allowed,
        "reason_code": reason,
        "reason_detail": None,
        "requires_confirmation": requires_confirmation,
        "idempotency_required": idempotency_required,
        "if_match_required": if_match_required,
        "result_mode": result_mode,
        "danger_level": danger_level,
    }


def strategy_action_capabilities(
    lifecycle_state: str, *, completed_backtest: bool = False
) -> list[dict[str, Any]]:
    if lifecycle_state == "CANDIDATE":
        return [
            cap(
                "run_fast_backtest",
                idempotency_required=True,
                result_mode="JOB",
                danger_level="STATE_CHANGE",
            ),
            cap(
                "freeze",
                allowed=completed_backtest,
                reason=(
                    None
                    if completed_backtest
                    else "VALIDATION_PREREQUISITES_INCOMPLETE"
                ),
                idempotency_required=True,
                if_match_required=True,
                danger_level="IRREVERSIBLE",
                requires_confirmation=True,
            ),
        ]
    if lifecycle_state == "FROZEN":
        return [
            cap(
                "start_validation",
                idempotency_required=True,
                result_mode="JOB",
                danger_level="STATE_CHANGE",
            )
        ]
    return []


def validation_action_capabilities(
    status: str,
    result: str | None,
    holdout_state: str,
    *,
    prerequisites_ready: bool = False,
) -> list[dict[str, Any]]:
    if status in {"QUEUED", "RUNNING"}:
        return [
            cap(
                "request_holdout_approval",
                allowed=False,
                reason="VALIDATION_IN_PROGRESS",
                idempotency_required=True,
                if_match_required=True,
                danger_level="STATE_CHANGE",
            )
        ]
    if status == "WAITING_HOLDOUT" and result == "PASS" and holdout_state == "LOCKED":
        return [
            cap(
                "request_holdout_approval",
                allowed=prerequisites_ready,
                reason=(
                    None if prerequisites_ready else "HOLDOUT_PREREQUISITES_INCOMPLETE"
                ),
                idempotency_required=True,
                if_match_required=True,
                danger_level="STATE_CHANGE",
            )
        ]
    return []


def job(
    s: Session,
    typ: str,
    ref: dict[str, Any] | None = None,
    *,
    input_payload: dict[str, Any] | None = None,
    queue_name: str | None = None,
    priority: int = 100,
    retry_safe: bool = True,
    max_attempts: int = 3,
) -> dict[str, Any]:
    job_id = new_id("JOB")
    queued_at = NOW()
    queued_at_dt = datetime.fromisoformat(queued_at.replace("Z", "+00:00"))
    effective_input = input_payload or {}
    actor_id = cast(str | None, s.info.get("actor_id"))
    workspace_id = cast(str | None, s.info.get("workspace_id"))
    selected_queue = queue_name or (
        "agent" if typ in {"RESEARCH_START", "AGENT_RUN", "AGENT_RESUME"} else "core"
    )
    progress = {
        "mode": "NONE",
        "completed_units": None,
        "total_units": None,
        "unit": None,
        "percent": None,
        "current_step_key": None,
        "current_step_label": None,
    }
    j = validated_payload(
        "JobDetail",
        {
            "job_id": job_id,
            "job_type": typ,
            "status": "QUEUED",
            "progress": progress,
            "error_code": None,
            "result_ref": None,
            "revision": 1,
            "queued_at": queued_at,
            "started_at": None,
            "finished_at": None,
            "last_updated_at": queued_at,
        },
    )
    s.add(
        JobRow(
            id=job_id,
            workspace_id=workspace_id,
            job_type=typ,
            status="QUEUED",
            revision=1,
            payload=json.dumps(j),
            input_payload=json.dumps(effective_input),
            payload_sha256=content_hash(effective_input),
            queue_name=selected_queue,
            priority=priority,
            attempt=0,
            max_attempts=max_attempts,
            fencing_token=0,
            retry_safe=retry_safe,
            queued_at=queued_at_dt,
            created_by_type="USER" if actor_id else "SYSTEM",
            created_by_id=actor_id or "system",
            correlation_id=job_id,
            request_id=cast(str | None, s.info.get("request_id")),
        )
    )
    s.flush()
    emit(
        s,
        "job",
        job_id,
        1,
        "job.updated",
        payload={"state": "QUEUED", "status": "QUEUED", "progress_mode": "NONE"},
        job_id=job_id,
        correlation_id=job_id,
        request_id=cast(str | None, s.info.get("request_id")),
    )
    return validated_payload(
        "JobAccepted",
        {
            "job_id": job_id,
            "status": "QUEUED",
            "progress": progress,
            "resource_ref": ref,
            "created_at": j["queued_at"],
        },
    )


@app.get("/api/v1/system/health")
def health(s: Session = Depends(db)):
    """Probe every local P0 dependency; never claim health from constants."""
    states = probe_health(s, JobRow, Event, RuntimeHeartbeat)
    if any(value == "UNAVAILABLE" for value in states.values()):
        raise problem(503, "SERVICE_DEGRADED", "one or more health probes failed")
    status = (
        "HEALTHY"
        if all(value == "HEALTHY" for value in states.values())
        else "DEGRADED"
    )
    return {"status": status, **states, "checked_at": NOW()}


@app.get("/api/v1/setup/status")
def setup_status(actor: Actor = Depends(require_owner), s: Session = Depends(db)):
    x = s.execute(
        select(Record).where(
            Record.workspace_id == actor.workspace_id,
            Record.record_key == "SETTINGS-DEFAULT",
        )
    ).scalar_one_or_none()
    if x is not None and (x.kind != "settings" or x.workspace_id != actor.workspace_id):
        x = None
    try:
        settings = body(x) if x else None
    except json.JSONDecodeError, TypeError:
        settings = None
        x = None
    binding = s.get(SetupBindingRow, actor.workspace_id) if x is not None else None
    if binding is not None and (
        x is None or binding.settings_record_id != x.record_key
    ):
        binding = None
    connection_id = binding.ai_connection_id if binding is not None else None
    connection = (
        s.get(ModelProviderConnectionRow, connection_id)
        if isinstance(connection_id, str)
        else None
    )
    active_connection_id = None
    if connection is not None:
        expires_at = connection.expires_at
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if (
            connection.workspace_id == actor.workspace_id
            and connection.owner_actor_id == actor.id
            and connection.kind == "AI"
            and connection.validation_state == "SUCCESS"
            and connection.status == "ACTIVE"
            and _connection_credential_is_authentic(connection)
            and (expires_at is None or expires_at > datetime.now(UTC))
            and settings is not None
            and settings.get("ai_connection_id") == connection.id
        ):
            active_connection_id = connection.id

    research_policy = (
        s.get(ResearchPolicyVersionRow, binding.research_policy_version_id)
        if binding is not None
        else None
    )
    active_research_policy_id = (
        research_policy.policy_id
        if research_policy is not None
        and research_policy.workspace_id == actor.workspace_id
        and research_policy.policy_family == "research"
        and research_policy.status == "ACTIVE"
        and settings is not None
        and settings.get("research_policy_id") == research_policy.policy_id
        else None
    )
    risk_policy = (
        s.get(RiskPolicyVersionRow, binding.risk_policy_version_id)
        if binding is not None
        else None
    )
    active_risk_policy_id = (
        risk_policy.policy_id
        if risk_policy is not None
        and risk_policy.workspace_id == actor.workspace_id
        and risk_policy.status == "ACTIVE"
        and settings is not None
        and settings.get("risk_policy_id") == risk_policy.policy_id
        else None
    )
    cost_model = (
        s.get(CostModelVersionRow, binding.cost_model_version_id)
        if binding is not None
        else None
    )
    active_cost_model_id = (
        cost_model.cost_model_id
        if cost_model is not None
        and cost_model.workspace_id == actor.workspace_id
        and cost_model.status == "ACTIVE"
        and settings is not None
        and settings.get("cost_model_id") == cost_model.cost_model_id
        else None
    )
    data_provider_id = settings.get("default_data_provider_id") if settings else None
    data_connection = (
        s.get(ModelProviderConnectionRow, binding.data_connection_id)
        if binding is not None and binding.data_connection_id is not None
        else None
    )
    data_expires_at = (
        data_connection.expires_at if data_connection is not None else None
    )
    if data_expires_at is not None and data_expires_at.tzinfo is None:
        data_expires_at = data_expires_at.replace(tzinfo=UTC)
    configured_data_provider = bool(
        data_connection is not None
        and data_connection.workspace_id == actor.workspace_id
        and data_connection.owner_actor_id == actor.id
        and data_connection.kind == "DATA"
        and data_connection.provider_id == data_provider_id
        and data_connection.validation_state == "SUCCESS"
        and data_connection.status == "ACTIVE"
        and _connection_credential_is_authentic(data_connection)
        and (data_expires_at is None or data_expires_at > datetime.now(UTC))
    )
    completed = bool(
        x
        and active_connection_id
        and active_research_policy_id
        and active_risk_policy_id
        and active_cost_model_id
    )
    if active_connection_id is None:
        fallback_step = "AI_PROVIDER"
    elif active_cost_model_id is None:
        fallback_step = "RESEARCH_DEFAULTS"
    elif active_research_policy_id is None or active_risk_policy_id is None:
        fallback_step = "RESEARCH_CONSTITUTION"
    else:
        fallback_step = None
    return validated_payload(
        "SetupStatus",
        {
            "completed": completed,
            "owner_session_ready": True,
            "ai_provider_configured": active_connection_id is not None,
            "ai_connection_id": active_connection_id,
            "data_provider_configured": configured_data_provider,
            "research_policy_active": active_research_policy_id is not None,
            "research_policy_id": active_research_policy_id,
            "risk_policy_active": active_risk_policy_id is not None,
            "risk_policy_id": active_risk_policy_id,
            "cost_model_active": active_cost_model_id is not None,
            "cost_model_id": active_cost_model_id,
            "fallback_step": fallback_step,
        },
    )


@app.post("/api/v1/setup/complete")
def setup_complete(
    data: SetupCompleteRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    payload = data.model_dump(mode="json", exclude_unset=True)

    def f():
        connection = s.execute(
            select(ModelProviderConnectionRow)
            .where(
                ModelProviderConnectionRow.id == payload["ai_connection_id"],
                ModelProviderConnectionRow.workspace_id == actor.workspace_id,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if connection is None or connection.validation_state != "SUCCESS":
            raise problem(404, "RESOURCE_NOT_FOUND", "AI connection is missing")
        expires_at = connection.expires_at
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if (
            connection.status != "VALIDATED"
            or expires_at is None
            or expires_at <= datetime.now(UTC)
        ):
            raise problem(
                409,
                "CONNECTION_VALIDATION_EXPIRED",
                "AI connection expired or consumed",
            )
        if connection.kind != "AI":
            raise problem(422, "CONNECTION_KIND_MISMATCH", "AI connection required")
        if not _connection_credential_is_authentic(connection):
            raise problem(
                409,
                "CONNECTION_VALIDATION_EXPIRED",
                "AI connection credential is unavailable",
            )
        if (
            connection.owner_actor_id != actor.id
            or connection.workspace_id != actor.workspace_id
        ):
            raise problem(
                403,
                "PERMISSION_DENIED",
                "connection belongs to another actor/workspace",
            )
        research_policy = s.execute(
            select(ResearchPolicyVersionRow)
            .where(
                ResearchPolicyVersionRow.workspace_id == actor.workspace_id,
                ResearchPolicyVersionRow.policy_id == payload["research_policy_id"],
                ResearchPolicyVersionRow.policy_family == "research",
                ResearchPolicyVersionRow.status == "ACTIVE",
            )
            .with_for_update()
        ).scalar_one_or_none()
        risk_policy = s.execute(
            select(RiskPolicyVersionRow)
            .where(
                RiskPolicyVersionRow.workspace_id == actor.workspace_id,
                RiskPolicyVersionRow.policy_id == payload["risk_policy_id"],
                RiskPolicyVersionRow.status == "ACTIVE",
            )
            .with_for_update()
        ).scalar_one_or_none()
        cost_model = s.execute(
            select(CostModelVersionRow)
            .where(
                CostModelVersionRow.workspace_id == actor.workspace_id,
                CostModelVersionRow.cost_model_id == payload["cost_model_id"],
                CostModelVersionRow.status == "ACTIVE",
            )
            .with_for_update()
        ).scalar_one_or_none()
        if research_policy is None or risk_policy is None or cost_model is None:
            raise problem(
                422,
                "INVALID_REQUEST",
                "setup policy/cost references are invalid",
            )
        try:
            require_cost_model(payload["cost_model_id"])
        except HTTPException as error:
            raise problem(
                422,
                "INVALID_REQUEST",
                "setup policy/cost references are invalid",
            ) from error
        data_provider_id = payload.get("default_data_provider_id")
        data_connection = None
        if data_provider_id is not None:
            candidates = (
                s.execute(
                    select(ModelProviderConnectionRow)
                    .where(
                        ModelProviderConnectionRow.workspace_id == actor.workspace_id,
                        ModelProviderConnectionRow.owner_actor_id == actor.id,
                        ModelProviderConnectionRow.provider_id == data_provider_id,
                        ModelProviderConnectionRow.kind == "DATA",
                        ModelProviderConnectionRow.validation_state == "SUCCESS",
                        ModelProviderConnectionRow.status.in_(("VALIDATED", "ACTIVE")),
                    )
                    .order_by(ModelProviderConnectionRow.validated_at.desc())
                    .with_for_update()
                )
                .scalars()
                .all()
            )
            now = datetime.now(UTC)
            for candidate in candidates:
                candidate_expiry = candidate.expires_at
                if candidate_expiry is not None and candidate_expiry.tzinfo is None:
                    candidate_expiry = candidate_expiry.replace(tzinfo=UTC)
                if candidate_expiry is None or candidate_expiry > now:
                    if _connection_credential_is_authentic(candidate):
                        data_connection = candidate
                        break
            if data_connection is None:
                raise problem(
                    422,
                    "INVALID_REQUEST",
                    "data provider has no active validated connection",
                )
        settings_id = "SETTINGS-DEFAULT"
        settings_alias = settings_id
        app_settings = Base.metadata.tables["app_settings"]
        persisted_settings = (
            s.execute(
                select(app_settings)
                .where(
                    app_settings.c.workspace_id == actor.workspace_id,
                    app_settings.c.public_id == settings_alias,
                )
                .with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        settings_row = s.execute(
            select(Record)
            .where(
                Record.record_key == settings_id,
                Record.workspace_id == actor.workspace_id,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if settings_row is not None and (
            settings_row.kind != "settings"
            or settings_row.workspace_id != actor.workspace_id
        ):
            raise problem(409, "RESOURCE_CONFLICT", "settings identity is occupied")
        revision = (
            int(persisted_settings["revision"]) + 1
            if persisted_settings is not None
            else 1
        )
        if settings_row is not None and settings_row.revision + 1 != revision:
            raise problem(409, "RESOURCE_CONFLICT", "settings mirrors diverged")
        if settings_row is not None:
            try:
                created_at = body(settings_row)["created_at"]
            except (json.JSONDecodeError, KeyError, TypeError) as error:
                raise problem(
                    409, "RESOURCE_CONFLICT", "existing settings are invalid"
                ) from error
        else:
            created_at = NOW()
        d = validated_payload(
            "SettingsDetail",
            {
                "settings_id": settings_alias,
                "revision": revision,
                **payload,
                "default_data_provider_id": payload.get("default_data_provider_id"),
                "default_research_start": payload.get("default_research_start"),
                "created_at": created_at,
                "updated_at": NOW(),
            },
        )
        timestamp = datetime.now(UTC)
        default_provider_internal_id = None
        if data_provider_id is not None:
            providers = Base.metadata.tables["data_providers"]
            default_provider_internal_id = s.execute(
                select(providers.c.id).where(
                    providers.c.workspace_id == actor.workspace_id,
                    providers.c.provider_id == data_provider_id,
                )
            ).scalar_one_or_none()
            if default_provider_internal_id is None:
                raise problem(
                    422,
                    "INVALID_REQUEST",
                    "default data provider has no workspace-scoped provider row",
                )
        settings_values = {
            "workspace_id": actor.workspace_id,
            "public_id": settings_alias,
            "revision": revision,
            "language": payload["language"],
            "timezone": payload["timezone"],
            "base_currency": payload["base_currency"],
            "number_format_locale": payload["number_format_locale"],
            "ai_connection_id": uuid.UUID(str(connection.id)),
            "default_data_provider_id": default_provider_internal_id,
            "default_benchmark": payload["default_benchmark"],
            "default_frequency": payload["default_frequency"],
            "default_research_start": (
                date.fromisoformat(payload["default_research_start"])
                if payload.get("default_research_start")
                else None
            ),
            "initial_paper_capital": payload["initial_paper_capital"],
            "active_research_policy_id": research_policy.internal_id,
            "active_risk_policy_id": risk_policy.internal_id,
            "active_cost_model_id": cost_model.internal_id,
            "updated_at": timestamp,
        }
        if persisted_settings is None:
            s.execute(
                app_settings.insert().values(
                    id=uuid.uuid4(),
                    created_at=timestamp,
                    **settings_values,
                )
            )
        else:
            s.execute(
                app_settings.update()
                .where(
                    app_settings.c.id == persisted_settings["id"],
                    app_settings.c.workspace_id == actor.workspace_id,
                    app_settings.c.revision == persisted_settings["revision"],
                )
                .values(**settings_values)
            )
        if settings_row is None:
            settings_row = save(
                s,
                "settings",
                d,
                settings_id,
            )
            emit(
                s,
                "settings",
                settings_alias,
                revision,
                "setup.completed",
                payload={"state": "COMPLETED", "status": "COMPLETED"},
            )
        else:
            settings_row.revision = revision
            settings_row.body = json.dumps(d)
            settings_row.updated_at = timestamp
            emit(
                s,
                "settings",
                settings_alias,
                revision,
                "setup.completed",
                payload={"state": "COMPLETED", "status": "COMPLETED"},
            )
        setup_binding = s.execute(
            select(SetupBindingRow)
            .where(SetupBindingRow.workspace_id == actor.workspace_id)
            .with_for_update()
        ).scalar_one_or_none()
        if setup_binding is None:
            setup_binding = SetupBindingRow(
                workspace_id=actor.workspace_id,
                settings_record_id=settings_row.record_key,
                ai_connection_id=connection.id,
                data_connection_id=(
                    data_connection.id if data_connection is not None else None
                ),
                research_policy_version_id=research_policy.id,
                risk_policy_version_id=risk_policy.id,
                cost_model_version_id=cost_model.id,
                revision=1,
                created_at=timestamp,
                updated_at=timestamp,
            )
            s.add(setup_binding)
        else:
            setup_binding.settings_record_id = settings_row.record_key
            setup_binding.ai_connection_id = connection.id
            setup_binding.data_connection_id = (
                data_connection.id if data_connection is not None else None
            )
            setup_binding.research_policy_version_id = research_policy.id
            setup_binding.risk_policy_version_id = risk_policy.id
            setup_binding.cost_model_version_id = cost_model.id
            setup_binding.revision += 1
            setup_binding.updated_at = timestamp
        connection.status = "ACTIVE"
        connection.consumed_at = timestamp
        connection.expires_at = None
        if data_connection is not None:
            data_connection.status = "ACTIVE"
            data_connection.consumed_at = timestamp
            data_connection.expires_at = None
        return 200, d

    return idem(s, actor, idempotency_key, payload, "/setup/complete", f)


def setup_provider_catalog() -> list[dict[str, Any]]:
    providers: list[dict[str, Any]] = []
    if ENVIRONMENT == "test" and encryption_is_configured():
        providers.append(
            {
                "provider_id": "TEST_AI",
                "display_name": "Deterministic Test AI",
                "kind": "AI",
                "connection_test_supported": True,
                "models": [
                    {"model_name": "test-model", "connection_test_supported": True}
                ],
                "data_capabilities": [],
            }
        )
    if (
        ENVIRONMENT != "production"
        and os.getenv("QF_ENABLE_LOCAL_DETERMINISTIC_PROVIDER") == "1"
        and encryption_is_configured()
    ):
        providers.append(
            {
                "provider_id": "LOCAL_DETERMINISTIC_DATA",
                "display_name": "Local deterministic CSV/Parquet adapter",
                "kind": "DATA",
                "connection_test_supported": True,
                "models": [],
                "data_capabilities": [local_data_capability()],
            }
        )
    base_url = os.getenv("QF_OPENAI_BASE_URL", "").rstrip("/")
    model_names = list(
        dict.fromkeys(
            name.strip()
            for name in os.getenv("QF_OPENAI_MODELS", "").split(",")
            if name.strip()
        )
    )
    if base_url and model_names and encryption_is_configured():
        providers.append(
            {
                "provider_id": "OPENAI_COMPATIBLE",
                "display_name": os.getenv(
                    "QF_OPENAI_DISPLAY_NAME", "OpenAI-compatible provider"
                ),
                "kind": "AI",
                "connection_test_supported": True,
                "models": [
                    {"model_name": name, "connection_test_supported": True}
                    for name in model_names
                ],
                "data_capabilities": [],
            }
        )
    return providers


def _connection_credential_is_authentic(
    connection: ModelProviderConnectionRow,
) -> bool:
    aad = credential_aad(
        connection_id=connection.id,
        workspace_id=connection.workspace_id,
        actor_id=connection.owner_actor_id,
        provider_id=connection.provider_id,
        model_name=connection.model_name,
    )
    try:
        credential = decrypt_credential(
            connection.ciphertext,
            connection.nonce,
            connection.key_id,
            aad=aad,
        )
    except CredentialConfigurationError:
        return False
    return bool(credential)


def _validate_provider_credential(
    configured: dict[str, Any], payload: dict[str, Any]
) -> bool:
    credential = payload["credential"]
    provider_id = configured["provider_id"]
    if provider_id == "TEST_AI":
        return ENVIRONMENT == "test" and hmac.compare_digest(
            credential,
            os.getenv("QF_TEST_PROVIDER_CREDENTIAL", "valid-test-credential"),
        )
    if provider_id == "LOCAL_DETERMINISTIC_DATA":
        configured_credential = os.getenv("QF_LOCAL_DATA_CREDENTIAL", "")
        return bool(
            ENVIRONMENT != "production"
            and os.getenv("QF_ENABLE_LOCAL_DETERMINISTIC_PROVIDER") == "1"
            and len(configured_credential) >= 20
            and hmac.compare_digest(credential, configured_credential)
        )
    if provider_id != "OPENAI_COMPATIBLE":
        return False
    base_url = os.getenv("QF_OPENAI_BASE_URL", "").rstrip("/")
    try:
        timeout = max(
            1.0,
            min(
                30.0,
                float(os.getenv("QF_OPENAI_VALIDATION_TIMEOUT_SECONDS", "5")),
            ),
        )
    except ValueError:
        return False
    try:
        response = httpx.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {credential}"},
            timeout=timeout,
        )
        response.raise_for_status()
        available_models = {
            item["id"]
            for item in response.json()["data"]
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
    except httpx.HTTPError, KeyError, TypeError, ValueError:
        return False
    return payload.get("model_name") in available_models


@app.get("/api/v1/setup/capabilities")
def setup_capabilities(_: Actor = Depends(require_owner)):
    return {"providers": setup_provider_catalog(), "server_checked_at": NOW()}


@app.post("/api/v1/setup/provider-connections/validate")
def validate_setup_provider_connection(
    data: SetupProviderConnectionValidationRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    payload = data.model_dump(mode="json", exclude_unset=True)

    def operation():
        configured = next(
            (
                provider
                for provider in setup_provider_catalog()
                if provider["provider_id"] == payload["provider_id"]
            ),
            None,
        )
        configured_models = (
            {model["model_name"] for model in configured["models"]}
            if configured is not None
            else set()
        )
        selection_valid = bool(
            configured is not None
            and configured["kind"] == payload["kind"]
            and (
                payload.get("model_name") in configured_models
                if payload["kind"] == "AI"
                else payload.get("model_name") is None
            )
        )
        valid = bool(
            selection_valid
            and configured is not None
            and _validate_provider_credential(configured, payload)
        )
        checked_at = NOW()
        if not valid:
            return 200, validated_payload(
                "SetupProviderConnectionValidationResult",
                {
                    "provider_id": payload["provider_id"],
                    "kind": payload["kind"],
                    "state": "FAILED",
                    "detail": (
                        "Provider credential validation failed"
                        if selection_valid
                        else "Provider or model selection is invalid"
                    ),
                    "error_code": (
                        "CREDENTIAL_INVALID"
                        if selection_valid
                        else (
                            "CREDENTIAL_NOT_CONFIGURED"
                            if configured is None
                            else "INVALID_REQUEST"
                        )
                    ),
                    "data_capabilities": [],
                    "checked_at": checked_at,
                },
            )
        assert configured is not None
        connection_id = str(uuid.uuid4())
        validated_at = datetime.now(UTC)
        expires_at = validated_at + timedelta(minutes=10)
        connection_model_name = payload.get("model_name") or payload["provider_id"]
        aad = credential_aad(
            connection_id=connection_id,
            workspace_id=actor.workspace_id,
            actor_id=actor.id,
            provider_id=payload["provider_id"],
            model_name=connection_model_name,
        )
        try:
            ciphertext, nonce, key_id = encrypt_credential(
                payload["credential"], aad=aad
            )
        except CredentialConfigurationError:
            return 200, validated_payload(
                "SetupProviderConnectionValidationResult",
                {
                    "provider_id": payload["provider_id"],
                    "kind": payload["kind"],
                    "state": "FAILED",
                    "detail": "Provider credential storage is unavailable",
                    "error_code": "CREDENTIAL_NOT_CONFIGURED",
                    "data_capabilities": [],
                    "checked_at": checked_at,
                },
            )
        s.add(
            ModelProviderConnectionRow(
                id=connection_id,
                workspace_id=actor.workspace_id,
                owner_actor_id=actor.id,
                provider_id=payload["provider_id"],
                kind=payload["kind"],
                model_name=connection_model_name,
                ciphertext=ciphertext,
                nonce=nonce,
                key_id=key_id,
                validation_state="SUCCESS",
                status="VALIDATED",
                validated_at=validated_at,
                expires_at=expires_at,
            )
        )
        if payload["kind"] == "DATA":
            providers = Base.metadata.tables["data_providers"]
            provider_internal_id = s.execute(
                select(providers.c.id).where(
                    providers.c.workspace_id == actor.workspace_id,
                    providers.c.provider_id == payload["provider_id"],
                )
            ).scalar_one_or_none()
            provider_values = {
                "adapter_key": payload["provider_id"].lower(),
                "display_name": configured["display_name"],
                "status": "CONNECTED",
                "config": {"capabilities": configured["data_capabilities"]},
                "last_tested_at": validated_at,
                "last_success_at": validated_at,
                "last_error_code": None,
                "updated_at": validated_at,
            }
            if provider_internal_id is None:
                s.execute(
                    providers.insert().values(
                        id=uuid.uuid4(),
                        workspace_id=actor.workspace_id,
                        provider_id=payload["provider_id"],
                        is_default=False,
                        credential_ref=None,
                        revision=1,
                        created_at=validated_at,
                        **provider_values,
                    )
                )
            else:
                s.execute(
                    providers.update()
                    .where(
                        providers.c.id == provider_internal_id,
                        providers.c.workspace_id == actor.workspace_id,
                    )
                    .values(
                        revision=providers.c.revision + 1,
                        **provider_values,
                    )
                )
        s.flush()
        emit(
            s,
            "provider_connection",
            connection_id,
            1,
            "data.provider.updated",
            payload={"state": "VALIDATED", "status": "VALIDATED"},
        )
        return 200, validated_payload(
            "SetupProviderConnectionValidationResult",
            {
                "connection_id": connection_id,
                "provider_id": payload["provider_id"],
                "kind": payload["kind"],
                "state": "SUCCESS",
                "detail": None,
                "data_capabilities": configured["data_capabilities"],
                "checked_at": checked_at,
            },
        )

    try:
        fingerprint = credential_fingerprint(payload["credential"])
    except CredentialConfigurationError:
        fingerprint = "credential-key-unavailable"
    redacted = {
        **{key: value for key, value in payload.items() if key != "credential"},
        "credential_fingerprint": fingerprint,
    }
    return idem(
        s,
        actor,
        idempotency_key,
        redacted,
        "/setup/provider-connections/validate",
        operation,
    )


@app.get("/api/v1/overview")
def overview(actor: Actor = Depends(require_owner), s: Session = Depends(db)):
    as_of = NOW()
    progress = {
        "mode": "NONE",
        "completed_units": None,
        "total_units": None,
        "unit": None,
        "percent": None,
        "current_step_key": None,
        "current_step_label": None,
    }
    research_rows = (
        s.query(ResearchRow).filter_by(workspace_id=actor.workspace_id).all()
    )
    active_research = []
    for row in research_rows:
        detail = _json_loads(row.detail)
        if not detail or row.status in {"COMPLETED", "ARCHIVED"}:
            continue
        active_research.append(
            {
                "research_id": row.id,
                "title": row.title,
                "status": row.status,
                "evidence_status": detail["evidence_status"],
                "progress": progress,
                "current_agent": None,
                "revision": row.revision,
                "action_capabilities": detail["action_capabilities"],
                "updated_at": detail["updated_at"],
            }
        )
    states = {
        state: 0
        for state in ("CANDIDATE", "FROZEN", "VALIDATING", "VALIDATED", "PAPER")
    }
    for strategy_row in (
        s.query(StrategyVersionRow).filter_by(workspace_id=actor.workspace_id).all()
    ):
        strategy_state = cast(str, strategy_row.state)
        if strategy_state in states:
            states[strategy_state] += 1
    settings = (
        s.query(Record)
        .filter_by(kind="settings", workspace_id=actor.workspace_id)
        .first()
    )
    currency = body(settings).get("base_currency", "USD") if settings else "USD"
    revision = 1 + sum(row.revision for row in research_rows) + sum(states.values())
    payload = {
        "as_of": as_of,
        "revision": revision,
        "needs_attention": [],
        "active_research": active_research,
        "strategy_pipeline": {key.lower(): value for key, value in states.items()},
        "paper_summary": {
            "active_count": 0,
            "total_nav": None,
            "currency": currency,
            "daily_return": None,
            "mtd_return": None,
            "since_start_return": None,
            "benchmark_since_start_return": None,
            "as_of_date": None,
            "provenance": None,
        },
        "paper_performance_chart": None,
        "recent_findings": [],
        "agent_activity": [],
        "data_health": {
            "state": "HEALTHY",
            "blocker_count": 0,
            "warning_count": 0,
            "checked_at": as_of,
            "action_capabilities": [],
        },
        "provenance": [],
        "action_capabilities": [cap("create_research")],
    }
    return JSONResponse(payload, headers={"ETag": f'W/"overview:{revision}"'})


@app.get("/api/v1/data/capabilities")
def capabilities(_: Actor = Depends(require_owner)):
    return (
        [local_data_capability()]
        if ENVIRONMENT == "test"
        or os.getenv("QF_ENABLE_LOCAL_DETERMINISTIC_PROVIDER") == "1"
        else []
    )


def local_data_capability() -> dict[str, Any]:
    return validated_payload(
        "DataCapability",
        {
            "capability_id": "CAP-00000000-0000-4000-8000-000000000001",
            "provider_id": "LOCAL_DETERMINISTIC_DATA",
            "capability_key": "prices",
            "state": "SUPPORTED",
            "asset_classes": ["EQUITY"],
            "frequencies": ["DAILY"],
            "coverage": {"start": None, "end": None},
            "point_in_time": {
                "supported": True,
                "available_from": None,
                "semantics": "available_at <= requested as_of_time",
            },
            "fields": ["close", "benchmark_close"],
            "limitations": [
                {
                    "code": "LOCAL_NON_PRODUCTION",
                    "detail": "Controlled CSV/Parquet adapter; disabled in production unless explicitly enabled",
                }
            ],
            "checked_at": NOW(),
        },
    )


@app.post("/api/v1/data/capabilities/evaluate")
def evaluate(data: CapabilityEvaluationRequest, _: Actor = Depends(require_owner)):
    payload = data.model_dump(mode="json", exclude_unset=True)
    enabled = (
        ENVIRONMENT == "test"
        or os.getenv("QF_ENABLE_LOCAL_DETERMINISTIC_PROVIDER") == "1"
    )
    evaluations = []
    for index, requirement in enumerate(payload["requirements"]):
        supported = (
            enabled
            and requirement["capability_key"] == "prices"
            and requirement["asset_class"] == "EQUITY"
            and requirement.get("frequency") in {None, "DAILY"}
            and set(requirement["fields"]).issubset({"close", "benchmark_close"})
        )
        evaluations.append(
            {
                "requirement_index": index,
                "state": "SUPPORTED" if supported else "UNAVAILABLE",
                "provider_id": "LOCAL_DETERMINISTIC_DATA" if supported else None,
                "reason_code": None if supported else "DATA_CAPABILITY_MISSING",
                "available_from": None,
            }
        )
    all_supported = all(item["state"] == "SUPPORTED" for item in evaluations)
    return {
        "overall_state": "SUPPORTED" if all_supported else "BLOCKED",
        "requirements": evaluations,
        "action_capabilities": [
            cap(
                "continue",
                all_supported,
                None if all_supported else "DATA_CAPABILITY_MISSING",
            )
        ],
    }


@app.post("/api/v1/data/datasets/{dataset_id}/validate", status_code=202)
def validate_dataset(
    dataset_id: DatasetId,
    data: DatasetValidationRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    payload = data.model_dump(mode="json", exclude_unset=True)

    def operation():
        source = s.get(DataSource, (dataset_id, actor.workspace_id))
        if source is None:
            source = DataSource(
                id=dataset_id,
                workspace_id=actor.workspace_id,
                provider_id="LOCAL_DETERMINISTIC_DATA",
                status="ACTIVE",
                revision=1,
            )
            s.add(source)
        elif source.status not in {"ACTIVE", "VALID", "INVALID"}:
            raise problem(409, "DATA_QUALITY_BLOCKED", "dataset is not validatable")
        accepted = job(
            s,
            "DATASET_VALIDATE",
            {"type": "dataset", "id": dataset_id, "version": None, "revision": 1},
            input_payload={"dataset_id": dataset_id, **payload},
        )
        return 202, accepted

    return idem(
        s,
        actor,
        idempotency_key,
        payload,
        f"/data/datasets/{dataset_id}/validate",
        operation,
    )


@app.post("/api/v1/data/datasets/{dataset_id}/snapshots", status_code=202)
def snapshot(
    dataset_id: DatasetId,
    data: SnapshotCreateRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    payload = data.model_dump(mode="json", exclude_unset=True)

    def f():
        source = s.get(DataSource, (dataset_id, actor.workspace_id))
        if source is None or source.status != "VALID":
            raise problem(
                409,
                "DATA_QUALITY_BLOCKED",
                "workspace-owned validated dataset is required",
            )
        fingerprint = content_hash(
            {"dataset_id": dataset_id, "snapshot_request": payload}
        )
        try:
            bundle = load_dataset(dataset_id)
            public_rows, holdout_rows = snapshot_rows(
                bundle,
                payload["coverage_start"],
                payload["coverage_end"],
                payload["as_of_time"],
            )
        except EngineInputError as error:
            raise problem(409, "DATA_QUALITY_BLOCKED", str(error)) from error
        content_sha256 = snapshot_content_sha256(
            dataset_id, bundle, public_rows, holdout_rows
        )
        existing = (
            s.query(SnapshotRow)
            .filter_by(
                dataset_id=dataset_id,
                content_sha256=content_sha256,
                workspace_id=actor.workspace_id,
            )
            .first()
        )
        snapshot_id = existing.id if existing is not None else new_id("DS")
        accepted = job(
            s,
            "SNAPSHOT_CREATE",
            {"type": "snapshot", "id": snapshot_id, "version": None, "revision": 1},
            input_payload={
                "dataset_id": dataset_id,
                "snapshot_id": snapshot_id,
                "request_sha256": fingerprint,
                "expected_content_sha256": content_sha256,
                **payload,
            },
        )
        return 202, accepted

    return idem(
        s,
        actor,
        idempotency_key,
        payload,
        f"/data/datasets/{dataset_id}/snapshots",
        f,
    )


@app.get("/api/v1/data/snapshots/{snapshot_id}")
def get_snapshot(
    snapshot_id: SnapshotId,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    r = owned(s, SnapshotRow, snapshot_id, actor, "snapshot")
    return JSONResponse(
        _json_loads(r.detail), headers={"ETag": f'"{r.content_sha256}"'}
    )


@app.get("/api/v1/research")
def list_research(actor: Actor = Depends(require_owner), s: Session = Depends(db)):
    items = []
    for row in s.query(ResearchRow).filter_by(workspace_id=actor.workspace_id).all():
        detail = _json_loads(row.detail)
        items.append(
            {
                key: detail[key]
                for key in (
                    "research_id",
                    "title",
                    "status",
                    "evidence_status",
                    "current_revision_no",
                    "revision",
                    "updated_at",
                )
            }
        )
    return {
        "items": items,
        "page": {"next_cursor": None, "has_more": False},
    }


@app.post("/api/v1/research", status_code=201)
def create_research(
    data: ResearchCreateRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    payload = data.model_dump(mode="json", exclude_unset=True)

    def f():
        research_policy = resolve_research_policy(
            s, actor.workspace_id, payload.get("research_policy_id")
        )
        i = new_id("RSCH")
        created_at = NOW()
        created_date = created_at[:10]
        brief_without_hash = {
            "revision_no": 1,
            "question": payload["original_user_prompt"],
            "hypothesis": None,
            "economic_rationale": None,
            "supporting_evidence_definition": None,
            "disconfirming_evidence_definition": None,
            "universe": {
                "asset_class": "UNSPECIFIED",
                "symbols": [],
                "universe_id": None,
            },
            "benchmark": "",
            "period": {"start": created_date, "end": created_date},
            "frequency": "DAILY",
        }
        empty_page = {"items": [], "page": {"next_cursor": None, "has_more": False}}
        d = validated_payload(
            "ResearchDetail",
            {
                "research_id": i,
                "title": payload["title"],
                "original_user_prompt": payload["original_user_prompt"],
                "normalized_question": None,
                "research_policy_id": research_policy.policy_id,
                "status": "DRAFT",
                "evidence_status": "INSUFFICIENT",
                "current_revision_no": 1,
                "active_plan_version": None,
                "director_agent_version": None,
                "current_agent_run_id": None,
                "current_job_id": None,
                "overview": {
                    "brief": {
                        **brief_without_hash,
                        "content_sha256": content_hash(brief_without_hash),
                    },
                    "current_conclusion": None,
                    "progress": [],
                    "latest_evidence": [],
                    "current_agent_work": None,
                },
                "plan": None,
                "timeline": empty_page,
                "experiments": empty_page,
                "evidence": empty_page,
                "artifacts": empty_page,
                "audit": empty_page,
                "revision": 1,
                "action_capabilities": [cap("start")],
                "created_at": created_at,
                "updated_at": created_at,
                "completed_at": None,
            },
        )
        s.add(
            ResearchRow(
                id=i,
                workspace_id=actor.workspace_id,
                status="DRAFT",
                revision=1,
                title=d["title"],
                research_policy_ref_id=research_policy.internal_id,
                detail=json.dumps(d),
            )
        )
        emit(
            s,
            "research",
            i,
            1,
            "research.created",
            payload={"state": "DRAFT", "status": "DRAFT"},
        )
        return 201, d

    return idem(s, actor, idempotency_key, payload, "/research", f)


@app.get("/api/v1/research/{research_id}")
def read_research(
    research_id: ResearchId,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    r = owned(s, ResearchRow, research_id, actor, "research")
    return JSONResponse(
        json.loads(r.detail), headers={"ETag": f'W/"{r.id}:{r.revision}"'}
    )


@app.post("/api/v1/research/{research_id}/start", status_code=202)
def start_research(
    research_id: ResearchId,
    data: ResearchStartRequest,
    idempotency_key: IdempotencyKey,
    if_match: IfMatch,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    payload = data.model_dump(mode="json", exclude_unset=True)

    def f():
        research = s.execute(
            select(ResearchRow)
            .where(
                ResearchRow.id == research_id,
                ResearchRow.workspace_id == actor.workspace_id,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if research is None:
            raise problem(404, "RESOURCE_NOT_FOUND", "research not found")
        require_workspace(research, actor)
        if if_match != f'W/"{research_id}:{research.revision}"':
            raise problem(412, "REVISION_MISMATCH", "research ETag does not match")
        if payload["research_revision_no"] != research.revision:
            raise problem(409, "RESEARCH_NOT_MUTABLE", "research revision changed")
        cfg = s.get(AgentConfigRow, (actor.workspace_id, "RESEARCH_DIRECTOR"))
        now = datetime.now(UTC)
        if cfg is None:
            cfg = AgentConfigRow(
                workspace_id=actor.workspace_id,
                role="RESEARCH_DIRECTOR",
                enabled=True,
                revision=1,
                model_provider=DEFAULT_AGENT_PROVIDER,
                model_name=DEFAULT_AGENT_MODEL,
                runtime_profile="DEFAULT",
                tool_timeout_seconds=30,
                created_at=now,
                updated_at=now,
            )
            s.add(cfg)
            s.flush()
        if not cfg.enabled:
            raise problem(409, "AGENT_DISABLED")
        run_id = new_id("ARUN")
        s.add(
            AgentRunRow(
                id=run_id,
                workspace_id=actor.workspace_id,
                role="RESEARCH_DIRECTOR",
                status="QUEUED",
                checkpoint=json.dumps({"research_id": research_id}),
                checkpoint_thread_id=f"agent:{run_id}",
                revision=1,
                research_id=research_id,
                object_type="research",
                object_id=research_id,
                objective="Start research",
                context_sha256=hashlib.sha256(research_id.encode()).hexdigest(),
                created_at=now,
                model_provider=cfg.model_provider,
                model_name=cfg.model_name,
                agent_version="1.0",
            )
        )
        s.flush()
        accepted = job(
            s,
            "RESEARCH_START",
            {"type": "agent_run", "id": run_id, "version": None, "revision": 1},
            input_payload={
                "research_id": research_id,
                "agent_run_id": run_id,
                **payload,
            },
            queue_name="agent",
        )
        detail = json.loads(research.detail)
        detail["current_agent_run_id"] = run_id
        detail["current_job_id"] = accepted["job_id"]
        detail["status"] = "RUNNING"
        detail["updated_at"] = NOW()
        research.status = "RUNNING"
        research.revision += 1
        detail["revision"] = research.revision
        research.detail = json.dumps(detail)
        emit(
            s,
            "research",
            research_id,
            research.revision,
            "research.updated",
            payload={"state": "RUNNING", "status": "RUNNING"},
        )
        return 202, accepted

    return idem(s, actor, idempotency_key, payload, f"/research/{research_id}/start", f)


@app.post("/api/v1/experiments", status_code=202)
def create_experiment(
    data: ExperimentCreateRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    payload = data.model_dump(mode="json", exclude_unset=True)

    def f():
        research = owned(s, ResearchRow, payload["research_id"], actor, "research")
        if research.revision != payload["research_revision_no"]:
            raise problem(409, "REVISION_MISMATCH", "research revision changed")
        snapshot_row = owned(
            s, SnapshotRow, payload["data_snapshot_id"], actor, "snapshot"
        )
        if not snapshot_row.immutable:
            raise problem(409, "DATA_SNAPSHOT_MISSING", "immutable snapshot required")
        expected_engine = {
            "FACTOR_ANALYSIS": "qf-factor-v1",
            "FAST_BACKTEST": "qf-simulation-v1",
            "PARAMETER_SENSITIVITY": "qf-simulation-v1",
            "DATA_VALIDATION": "qf-validation-v1",
            "STRICT_VALIDATION": "qf-validation-v1",
        }[payload["experiment_type"]]
        require_engine(
            payload["engine_key"], payload["engine_version"], expected_engine
        )
        require_cost_model(payload["cost_model_id"])
        if payload["experiment_type"] == "FACTOR_ANALYSIS":
            factor = s.execute(
                select(FactorRow).where(
                    FactorRow.id == payload.get("factor_id"),
                    FactorRow.workspace_id == actor.workspace_id,
                )
            ).scalar_one_or_none()
            if factor is None or payload.get("factor_version") != 1:
                raise problem(409, "RESOURCE_CONFLICT", "factor version required")
        if payload["experiment_type"] in {"FAST_BACKTEST", "PARAMETER_SENSITIVITY"}:
            strategy = (
                s.query(StrategyVersionRow)
                .filter_by(
                    strategy_id=payload.get("strategy_id"),
                    version=payload.get("strategy_version"),
                    workspace_id=actor.workspace_id,
                )
                .one_or_none()
            )
            if strategy is None:
                raise problem(409, "RESOURCE_CONFLICT", "strategy version required")
        experiment_id = new_id("EXP")
        accepted = job(
            s,
            "EXPERIMENT",
            {"type": "experiment", "id": experiment_id, "version": None, "revision": 1},
            input_payload={"experiment_id": experiment_id, **payload},
        )
        detail = validated_payload(
            "ExperimentDetail",
            {
                "experiment_id": experiment_id,
                "research_id": payload["research_id"],
                "parent_experiment_id": None,
                "source_experiment_id": None,
                "research_revision_no": payload["research_revision_no"],
                "objective": payload["objective"],
                "hypothesis": payload["hypothesis"],
                "experiment_type": payload["experiment_type"],
                "data_snapshot_id": payload["data_snapshot_id"],
                "cost_model_id": payload["cost_model_id"],
                "parameters": payload["parameters"],
                "parameters_sha256": hashlib.sha256(
                    json.dumps(payload["parameters"], sort_keys=True).encode()
                ).hexdigest(),
                "search_space": [],
                "search_configuration": None,
                "search_result": {
                    "state": "NOT_APPLICABLE",
                    "evaluated_count": 0,
                    "selected_parameters": [],
                    "selected_metric": None,
                    "result_ref": None,
                    "failure_code": None,
                },
                "metrics": [],
                "artifacts": [],
                "job_id": accepted["job_id"],
                "status": "QUEUED",
                "validity_state": "PENDING",
                "factor_ref": (
                    {
                        "id": payload["factor_id"],
                        "version": payload["factor_version"],
                    }
                    if payload.get("factor_id") and payload.get("factor_version")
                    else None
                ),
                "strategy_ref": (
                    {
                        "id": payload["strategy_id"],
                        "version": payload["strategy_version"],
                    }
                    if payload.get("strategy_id") and payload.get("strategy_version")
                    else None
                ),
                "engine": {
                    "name": payload["engine_key"],
                    "version": payload["engine_version"],
                },
                "adapter": None,
                "code_version": BUILD_ID,
                "provenance": None,
                "action_capabilities": [],
                "started_at": None,
                "finished_at": None,
                "created_at": NOW(),
                "invalidated_at": None,
                "invalid_reason_code": None,
                "invalid_reason_detail": None,
            },
        )
        s.add(
            ExperimentRow(
                id=experiment_id,
                workspace_id=actor.workspace_id,
                research_id=payload["research_id"],
                source_experiment_id=None,
                immutable=False,
                revision=1,
                detail=json.dumps(detail),
            )
        )
        emit(
            s,
            "experiment",
            experiment_id,
            1,
            "experiment.created",
            payload={"state": "QUEUED", "status": "QUEUED"},
        )
        return 202, accepted

    return idem(s, actor, idempotency_key, payload, "/experiments", f)


@app.post("/api/v1/factors", status_code=201)
def create_factor(
    data: FactorCreateRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    payload = data.model_dump(mode="json", exclude_unset=True)

    def f():
        owned(s, ResearchRow, payload["research_id"], actor, "research")
        factor_id = new_id("FAC")
        created_at = NOW()
        detail = validated_payload(
            "FactorDetail",
            {
                "factor_id": factor_id,
                "name": payload["name"],
                "category": payload["category"],
                "description": payload["description"],
                "economic_rationale": payload["economic_rationale"],
                "formula": payload["formula"],
                "universe": payload["universe"],
                "frequency": payload["frequency"],
                "current_version": 1,
                "status": "DRAFT",
                "definition_sha256": hashlib.sha256(
                    json.dumps(payload, sort_keys=True).encode()
                ).hexdigest(),
                "revision": 1,
                "action_capabilities": [cap("analyze")],
                "created_at": created_at,
                "updated_at": created_at,
            },
        )
        s.add(
            FactorRow(
                id=factor_id,
                workspace_id=actor.workspace_id,
                research_id=payload["research_id"],
                revision=1,
                detail=json.dumps(detail),
            )
        )
        emit(
            s,
            "factor",
            factor_id,
            1,
            "factor.updated",
            payload={"state": "DRAFT", "status": "DRAFT"},
        )
        return 201, detail

    return idem(s, actor, idempotency_key, payload, "/factors", f)


@app.post("/api/v1/strategies", status_code=201)
def create_strategy(
    data: StrategyCreateRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    payload = data.model_dump(mode="json", exclude_unset=True)

    def f():
        owned(s, ResearchRow, payload["research_id"], actor, "research")
        require_cost_model(payload["cost_model_id"])
        for signal in payload["signals"]:
            factor = s.execute(
                select(FactorRow).where(
                    FactorRow.id == signal["factor_id"],
                    FactorRow.workspace_id == actor.workspace_id,
                )
            ).scalar_one_or_none()
            if factor is None or signal["factor_version"] != 1:
                raise problem(
                    409, "RESOURCE_CONFLICT", "strategy factor version missing"
                )
        strategy_id = new_id("STRAT")
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        detail = validated_payload(
            "StrategyVersionDetail",
            {
                "strategy_id": strategy_id,
                "name": payload["name"],
                "thesis": payload["thesis"],
                "universe": payload["universe"],
                "signals": payload["signals"],
                "rules": payload["rules"],
                "cost_model_id": payload["cost_model_id"],
                "benchmark": payload["benchmark"],
                "research_period": payload["research_period"],
                "validation_period": payload["validation_period"],
                "holdout_period": payload["holdout_period"],
                "known_failure_modes": payload["known_failure_modes"],
                "version": 1,
                "lifecycle_state": "CANDIDATE",
                "is_frozen": False,
                "spec_sha256": digest,
                "specification": {
                    "thesis": payload["thesis"],
                    "universe": payload["universe"],
                    "signals": payload["signals"],
                    "rules": payload["rules"],
                    "cost_model_id": payload["cost_model_id"],
                    "benchmark": payload["benchmark"],
                    "research_period": payload["research_period"],
                    "validation_period": payload["validation_period"],
                    "holdout_period": payload["holdout_period"],
                    "known_failure_modes": payload["known_failure_modes"],
                    "spec_sha256": digest,
                },
                "latest_backtest": {
                    "state": "EMPTY",
                    "result": None,
                    "metrics": [],
                    "chart": None,
                },
                "validation_summary": None,
                "artifacts": [],
                "provenance": [],
                "frozen_at": None,
                "frozen_by": None,
                "revision": 1,
                "action_capabilities": strategy_action_capabilities("CANDIDATE"),
                "created_at": NOW(),
            },
        )
        s.add(
            StrategyRow(
                id=strategy_id,
                workspace_id=actor.workspace_id,
                research_id=payload["research_id"],
                revision=1,
                detail=json.dumps(detail),
            )
        )
        s.add(
            StrategyVersionRow(
                id=new_id("SV"),
                workspace_id=actor.workspace_id,
                strategy_id=strategy_id,
                version=1,
                state="CANDIDATE",
                spec_sha256=digest,
                revision=1,
                detail=json.dumps(detail),
            )
        )
        emit(
            s,
            "strategy_version",
            strategy_id,
            1,
            "strategy.created",
            payload={"state": "DRAFT", "status": "DRAFT"},
            object_version=1,
        )
        return 201, detail

    return idem(s, actor, idempotency_key, payload, "/strategies", f)


@app.get("/api/v1/strategies/{strategy_id}/versions/{version}")
def get_strategy_version(
    strategy_id: StrategyId,
    version: Version,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    row = (
        s.query(StrategyVersionRow)
        .filter_by(
            strategy_id=strategy_id,
            version=version,
            workspace_id=actor.workspace_id,
        )
        .first()
    )
    if row is None:
        raise problem(404, "RESOURCE_NOT_FOUND", "strategy version not found")
    require_workspace(row, actor)
    return JSONResponse(
        strategy_version_payload(s, row),
        headers={"ETag": f'W/"{strategy_id}:{row.revision}"'},
    )


@app.get("/api/v1/strategies/{strategy_id}/current-version")
def get_current_strategy_version(
    strategy_id: StrategyId,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    row = (
        s.query(StrategyVersionRow)
        .filter_by(strategy_id=strategy_id, workspace_id=actor.workspace_id)
        .order_by(StrategyVersionRow.version.desc())
        .first()
    )
    if row is None:
        raise problem(404, "RESOURCE_NOT_FOUND", "strategy not found")
    require_workspace(row, actor)
    location = f"/api/v1/strategies/{strategy_id}/versions/{row.version}"
    return JSONResponse(
        strategy_version_payload(s, row),
        headers={
            "ETag": f'W/"{strategy_id}:{row.revision}"',
            "Content-Location": location,
        },
    )


@app.get("/api/v1/experiments/{experiment_id}")
def get_experiment(
    experiment_id: ExperimentId,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    row = owned(s, ExperimentRow, experiment_id, actor, "experiment")
    return JSONResponse(
        _json_loads(row.detail), headers={"ETag": f'W/"{row.id}:{row.revision}"'}
    )


def _reproducible_source(
    s: Session, source: ExperimentRow, actor: Actor
) -> tuple[dict[str, Any], dict[str, Any]]:
    detail = _json_loads(source.detail)
    if not source.immutable:
        raise problem(409, "EXPERIMENT_IMMUTABLE", "source experiment is not immutable")
    if detail.get("status") != "COMPLETED" or detail.get("validity_state") != "VALID":
        raise problem(409, "EXPERIMENT_INVALID", "source experiment is not valid")
    capability = next(
        (
            item
            for item in _as_json_objects(detail.get("action_capabilities", []))
            if item.get("action") == "reproduce"
        ),
        None,
    )
    provenance = detail.get("provenance")
    required_values = (
        detail.get("data_snapshot_id"),
        detail.get("parameters_sha256"),
        detail.get("engine"),
        detail.get("code_version"),
        detail.get("cost_model_id"),
        provenance,
    )
    if (
        capability is None
        or capability.get("visibility") != "SHOW"
        or not capability.get("allowed")
        or any(value is None for value in required_values)
        or not isinstance(provenance, dict)
    ):
        raise problem(
            422, "NON_REPRODUCIBLE", "source reproducibility contract is incomplete"
        )
    provenance_id = provenance.get("provenance_id")
    provenance_row = s.execute(
        select(Record).where(
            Record.workspace_id == actor.workspace_id,
            Record.record_key == provenance_id,
        )
    ).scalar_one_or_none()
    if (
        not isinstance(provenance_id, str)
        or provenance_row is None
        or provenance_row.kind != "provenance"
        or _json_loads(provenance_row.body) != provenance
        or provenance.get("experiment_id") != source.id
        or (
            provenance.get("source_experiment_id") is not None
            and provenance.get("source_experiment_id")
            != detail.get("source_experiment_id")
        )
    ):
        raise problem(422, "NON_REPRODUCIBLE", "source provenance is unavailable")
    require_workspace(provenance_row, actor)
    parameters_sha256 = hashlib.sha256(
        json.dumps(detail.get("parameters"), sort_keys=True).encode()
    ).hexdigest()
    if parameters_sha256 != detail["parameters_sha256"]:
        raise problem(422, "NON_REPRODUCIBLE", "source parameters hash is invalid")
    snapshot_row = s.execute(
        select(SnapshotRow).where(
            SnapshotRow.id == detail["data_snapshot_id"],
            SnapshotRow.workspace_id == actor.workspace_id,
        )
    ).scalar_one_or_none()
    if snapshot_row is None or not snapshot_row.immutable:
        raise problem(422, "NON_REPRODUCIBLE", "source snapshot is unavailable")
    try:
        require_cost_model(_as_str(detail["cost_model_id"]))
    except HTTPException as error:
        raise problem(
            422, "NON_REPRODUCIBLE", "source cost model is unavailable"
        ) from error
    return detail, provenance


@app.post(
    "/api/v1/experiments/{experiment_id}/reproduce",
    status_code=202,
)
def reproduce_experiment(
    experiment_id: ExperimentId,
    data: ExperimentReproduceRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    payload = data.model_dump(mode="json", exclude_unset=True)

    def operation():
        source = s.execute(
            select(ExperimentRow)
            .where(
                ExperimentRow.id == experiment_id,
                ExperimentRow.workspace_id == actor.workspace_id,
            )
            .with_for_update()
        ).scalar_one_or_none()
        if source is None:
            raise problem(404, "RESOURCE_NOT_FOUND", "source experiment not found")
        require_workspace(source, actor)
        source_detail, source_provenance = _reproducible_source(s, source, actor)
        mode = payload.get("mode", "EXACT")
        engine = dict(source_detail["engine"])
        adapter = (
            dict(source_detail["adapter"])
            if isinstance(source_detail.get("adapter"), dict)
            else None
        )
        code_version = source_detail["code_version"]
        if mode == "CONTROLLED_OVERRIDE":
            overrides = payload["execution_overrides"]
            if "engine_version" in overrides:
                engine["version"] = overrides["engine_version"]
            if "adapter_version" in overrides:
                if adapter is None:
                    raise problem(
                        422,
                        "NON_REPRODUCIBLE",
                        "source has no adapter version to override",
                    )
                adapter["version"] = overrides["adapter_version"]
            if "code_version" in overrides:
                code_version = overrides["code_version"]
        if ENGINE_VERSIONS.get(engine["name"]) != engine["version"]:
            raise problem(422, "NON_REPRODUCIBLE", "engine version is unavailable")
        if code_version != BUILD_ID:
            raise problem(422, "NON_REPRODUCIBLE", "code version is unavailable")
        snapshot = s.execute(
            select(SnapshotRow).where(
                SnapshotRow.id == source_detail["data_snapshot_id"],
                SnapshotRow.workspace_id == actor.workspace_id,
            )
        ).scalar_one_or_none()
        if snapshot is None:
            raise problem(422, "NON_REPRODUCIBLE", "source snapshot is unavailable")
        snapshot_detail = json.loads(snapshot.detail)
        snapshot_adapter = snapshot_detail["provider_metadata"]
        if adapter is not None and (
            adapter["name"] != snapshot_adapter["adapter_key"]
            or adapter["version"] != snapshot_adapter["adapter_version"]
        ):
            raise problem(422, "NON_REPRODUCIBLE", "adapter version is unavailable")

        child_id = new_id("EXP")
        accepted = job(
            s,
            "EXPERIMENT_REPRODUCE",
            {"type": "experiment", "id": child_id, "version": None, "revision": 1},
            input_payload={
                "experiment_id": child_id,
                "source_experiment_id": source.id,
                "source_provenance_id": source_provenance["provenance_id"],
                "source_output_sha256": source_provenance["output_sha256"],
                "reproduce_mode": mode,
                "execution_overrides": payload.get("execution_overrides", {}),
                "reason": payload.get("reason"),
            },
        )
        child_detail = dict(source_detail)
        child_detail.update(
            {
                "experiment_id": child_id,
                "parent_experiment_id": None,
                "source_experiment_id": source.id,
                "status": "QUEUED",
                "validity_state": "PENDING",
                "engine": engine,
                "adapter": adapter,
                "code_version": code_version,
                "job_id": accepted["job_id"],
                "provenance": None,
                "action_capabilities": [],
                "started_at": None,
                "finished_at": None,
                "created_at": NOW(),
                "invalidated_at": None,
                "invalid_reason_code": None,
                "invalid_reason_detail": None,
            }
        )
        child_detail = validated_payload("ExperimentDetail", child_detail)
        s.add(
            ExperimentRow(
                id=child_id,
                workspace_id=actor.workspace_id,
                research_id=source.research_id,
                source_experiment_id=source.id,
                immutable=False,
                revision=1,
                detail=json.dumps(child_detail),
            )
        )
        emit(
            s,
            "experiment",
            child_id,
            1,
            "experiment.created",
            payload={"state": "QUEUED", "status": "QUEUED"},
            job_id=accepted["job_id"],
        )
        response = validated_payload(
            "ExperimentReproduceAccepted",
            {
                "job_id": accepted["job_id"],
                "status": accepted["status"],
                "progress": accepted["progress"],
                "resource_ref": {
                    "type": "experiment",
                    "id": child_id,
                    "version": None,
                    "revision": 1,
                },
                "source_experiment_id": source.id,
                "source_provenance": {
                    "provenance_id": source_provenance["provenance_id"]
                },
                "reproduce_mode": mode,
                "created_at": accepted["created_at"],
            },
        )
        return 202, response

    return idem(
        s,
        actor,
        idempotency_key,
        payload,
        f"/experiments/{experiment_id}/reproduce",
        operation,
    )


@app.post("/api/v1/factors/{factor_id}/analyses", status_code=202)
def factor_analysis(
    factor_id: FactorId,
    data: FactorAnalysisRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    payload = data.model_dump(mode="json", exclude_unset=True)

    def operation():
        factor = s.execute(
            select(FactorRow).where(
                FactorRow.id == factor_id,
                FactorRow.workspace_id == actor.workspace_id,
            )
        ).scalar_one_or_none()
        if factor is None or payload["factor_version"] != 1:
            raise problem(404, "RESOURCE_NOT_FOUND", "factor not found")
        require_workspace(factor, actor)
        snapshot_row = owned(s, SnapshotRow, payload["snapshot_id"], actor, "snapshot")
        if not snapshot_row.immutable:
            raise problem(409, "DATA_SNAPSHOT_MISSING", "immutable snapshot required")
        return 202, job(
            s,
            "FACTOR_ANALYSIS",
            {"type": "factor", "id": factor_id, "version": None, "revision": 1},
            input_payload={"factor_id": factor_id, **payload},
        )

    return idem(
        s,
        actor,
        idempotency_key,
        payload,
        f"/factors/{factor_id}/analyses",
        operation,
    )


@app.post(
    "/api/v1/strategies/{strategy_id}/versions/{version}/backtests", status_code=202
)
def backtest(
    strategy_id: StrategyId,
    version: Version,
    data: BacktestRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    payload = data.model_dump(mode="json", exclude_unset=True)

    def operation():
        row = (
            s.query(StrategyVersionRow)
            .filter_by(
                strategy_id=strategy_id,
                version=version,
                workspace_id=actor.workspace_id,
            )
            .first()
        )
        if row is None:
            raise problem(404, "RESOURCE_NOT_FOUND", "strategy version not found")
        require_workspace(row, actor)
        if row.state != "CANDIDATE":
            raise problem(409, "STRATEGY_VERSION_FROZEN")
        snapshot_row = owned(s, SnapshotRow, payload["snapshot_id"], actor, "snapshot")
        if not snapshot_row.immutable:
            raise problem(409, "DATA_SNAPSHOT_MISSING", "immutable snapshot required")
        require_engine(
            payload["engine_key"], payload["engine_version"], "qf-simulation-v1"
        )
        require_cost_model(payload["cost_model_id"])
        return 202, job(
            s,
            "FAST_BACKTEST",
            {
                "type": "strategy",
                "id": strategy_id,
                "version": version,
                "revision": row.revision,
            },
            input_payload={
                "strategy_id": strategy_id,
                "strategy_version": version,
                "strategy_version_id": row.id,
                "strategy_spec_sha256": row.spec_sha256,
                **payload,
            },
        )

    return idem(
        s,
        actor,
        idempotency_key,
        payload,
        f"/strategies/{strategy_id}/versions/{version}/backtests",
        operation,
    )


def has_completed_backtest(s: Session, strategy: StrategyVersionRow) -> bool:
    rows = (
        s.query(JobRow)
        .filter_by(
            job_type="FAST_BACKTEST",
            status="COMPLETED",
            workspace_id=strategy.workspace_id,
        )
        .all()
    )
    return any(
        _json_loads(candidate.input_payload).get("strategy_id") == strategy.strategy_id
        and _json_loads(candidate.input_payload).get("strategy_version")
        == strategy.version
        and _json_loads(candidate.input_payload).get("strategy_version_id")
        == strategy.id
        and _json_loads(candidate.input_payload).get("strategy_spec_sha256")
        == strategy.spec_sha256
        and bool(candidate.result_ref)
        for candidate in rows
    )


def strategy_version_payload(
    s: Session, strategy: StrategyVersionRow
) -> dict[str, Any]:
    detail = _json_loads(strategy.detail)
    detail.update(
        {
            "lifecycle_state": _as_str(strategy.state),
            "revision": _as_int(strategy.revision),
            "action_capabilities": cast(
                list[JsonValue],
                strategy_action_capabilities(
                    _as_str(strategy.state),
                    completed_backtest=(
                        has_completed_backtest(s, strategy)
                        if strategy.state == "CANDIDATE"
                        else False
                    ),
                ),
            ),
        }
    )
    return validated_payload("StrategyVersionDetail", detail)


@app.post("/api/v1/strategies/{strategy_id}/versions/{version}/freeze")
def freeze(
    strategy_id: StrategyId,
    version: Version,
    data: FreezeStrategyRequest,
    if_match: IfMatch,
    idempotency_key: IdempotencyKey,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    payload = data.model_dump(mode="json", exclude_unset=True)

    def f():
        r = (
            s.query(StrategyVersionRow)
            .filter_by(
                strategy_id=strategy_id,
                version=version,
                workspace_id=actor.workspace_id,
            )
            .with_for_update()
            .one_or_none()
        )
        if not r:
            raise problem(404, "RESOURCE_NOT_FOUND", "strategy version not found")
        require_workspace(r, actor)
        d = json.loads(r.detail)
        if r.state != "CANDIDATE":
            raise problem(409, "STRATEGY_VERSION_FROZEN")
        if not if_match:
            raise problem(428, "PRECONDITION_REQUIRED")
        if if_match != f'W/"{strategy_id}:{r.revision}"':
            raise problem(412, "REVISION_MISMATCH")
        if payload["expected_spec_sha256"] != r.spec_sha256:
            raise problem(409, "STRATEGY_VERSION_MISMATCH")
        if not has_completed_backtest(s, r):
            raise problem(
                409,
                "VALIDATION_PREREQUISITES_INCOMPLETE",
                "completed deterministic fast backtest required",
            )
        r.state = "FROZEN"
        r.frozen_at = datetime.now(UTC)
        r.revision += 1
        d.update(
            {
                "lifecycle_state": "FROZEN",
                "is_frozen": True,
                "frozen_at": NOW(),
                "frozen_by": actor.id,
                "revision": r.revision,
                "action_capabilities": strategy_action_capabilities("FROZEN"),
            }
        )
        d = validated_payload("StrategyVersionDetail", d)
        r.detail = json.dumps(d)
        emit(
            s,
            "strategy_version",
            strategy_id,
            r.revision,
            "strategy.updated",
            payload={"state": "FROZEN", "status": "FROZEN"},
            object_version=version,
        )
        return 200, d

    return idem(
        s,
        actor,
        idempotency_key,
        payload,
        f"/strategies/{strategy_id}/versions/{version}/freeze",
        f,
    )


@app.post("/api/v1/validations", status_code=202)
def validation(
    data: ValidationCreateRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    payload = data.model_dump(mode="json", exclude_unset=True)

    def f():
        policy = s.execute(
            select(ResearchPolicyVersionRow).where(
                ResearchPolicyVersionRow.workspace_id == actor.workspace_id,
                ResearchPolicyVersionRow.policy_id == payload["policy_id"],
                ResearchPolicyVersionRow.policy_family == "validation",
                ResearchPolicyVersionRow.status == "ACTIVE",
            )
        ).scalar_one_or_none()
        if policy is None:
            raise problem(422, "INVALID_REQUEST", "validation policy is invalid")
        try:
            load_validation_policy(policy.policy_id)
        except EngineInputError as error:
            raise problem(
                422, "INVALID_REQUEST", "validation policy is invalid"
            ) from error
        version = (
            s.query(StrategyVersionRow)
            .filter_by(
                strategy_id=payload["strategy_id"],
                version=payload["strategy_version"],
                workspace_id=actor.workspace_id,
            )
            .first()
        )
        if version is None:
            raise problem(409, "STRATEGY_NOT_FROZEN")
        if version.state != "FROZEN":
            raise problem(409, "STRATEGY_NOT_FROZEN")
        require_engine(
            payload["strict_engine_key"],
            payload["strict_engine_version"],
            "qf-validation-v1",
        )
        if not has_completed_backtest(s, version):
            raise problem(
                409,
                "VALIDATION_PREREQUISITES_INCOMPLETE",
                "completed deterministic fast backtest required",
            )
        version.state = "VALIDATING"
        version.revision += 1
        version_detail = json.loads(version.detail)
        version_detail.update(
            {
                "lifecycle_state": "VALIDATING",
                "revision": version.revision,
                "action_capabilities": strategy_action_capabilities("VALIDATING"),
            }
        )
        version.detail = json.dumps(
            validated_payload("StrategyVersionDetail", version_detail)
        )
        emit(
            s,
            "strategy_version",
            version.strategy_id,
            version.revision,
            "strategy.updated",
            payload={"state": "VALIDATING", "status": "VALIDATING"},
            object_version=version.version,
        )
        i = new_id("VAL")
        accepted = job(
            s,
            "VALIDATION",
            {"type": "validation", "id": i, "version": None, "revision": 1},
            input_payload={"validation_id": i, **payload},
        )
        created_at = NOW()
        d = validated_payload(
            "ValidationDetail",
            {
                "validation_id": i,
                "strategy": {
                    "id": payload["strategy_id"],
                    "version": payload["strategy_version"],
                },
                "policy_id": payload["policy_id"],
                "strict_engine": {
                    "name": payload["strict_engine_key"],
                    "version": payload["strict_engine_version"],
                },
                "status": "QUEUED",
                "result": None,
                "test_suite_version": payload["test_suite_version"],
                "tests": [],
                "warnings": [],
                "failures": [],
                "holdout_state": "LOCKED",
                "red_team_run_id": None,
                "job_id": accepted["job_id"],
                "revision": 1,
                "action_capabilities": validation_action_capabilities(
                    "QUEUED", None, "LOCKED"
                ),
                "started_at": None,
                "finished_at": None,
                "created_at": created_at,
            },
        )
        s.add(
            ValidationRow(
                id=i,
                workspace_id=actor.workspace_id,
                strategy_version_id=version.id,
                status="QUEUED",
                holdout_state="LOCKED",
                exposure_count=0,
                revision=1,
                detail=json.dumps(d),
            )
        )
        emit(
            s,
            "validation",
            i,
            1,
            "validation.created",
            payload={"state": "QUEUED", "status": "QUEUED"},
        )
        return 202, accepted

    return idem(s, actor, idempotency_key, payload, "/validations", f)


@app.get("/api/v1/validations/{validation_id}")
def get_validation(
    validation_id: ValidationId,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    row = owned(s, ValidationRow, validation_id, actor, "validation")
    return JSONResponse(
        validation_payload(s, row),
        headers={"ETag": f'W/"{row.id}:{row.revision}"'},
    )


@app.get("/api/v1/validations/{validation_id}/holdout")
def holdout_gate(
    validation_id: ValidationId,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    r = owned(s, ValidationRow, validation_id, actor, "validation")
    validation_detail = validation_payload(s, r)
    strategy = s.execute(
        select(StrategyVersionRow).where(
            StrategyVersionRow.id == r.strategy_version_id,
            StrategyVersionRow.workspace_id == r.workspace_id,
        )
    ).scalar_one_or_none()
    if strategy is None:
        raise problem(500, "INTERNAL_ERROR", "validation strategy version is missing")
    require_workspace(strategy, actor)
    strategy_detail = _json_loads(strategy.detail)
    approval = (
        s.query(ApprovalRow)
        .filter_by(validation_id=validation_id, workspace_id=actor.workspace_id)
        .order_by(ApprovalRow.requested_at.desc(), ApprovalRow.id.desc())
        .first()
    )
    approval_summary = None
    if approval is not None:
        require_workspace(approval, actor)
        approval_summary = validated_payload(
            "ApprovalSummary",
            {
                "approval_id": approval.id,
                "status": approval.status,
                "revision": approval.revision,
            },
        )
    return JSONResponse(
        validated_payload(
            "HoldoutGate",
            {
                "validation_id": validation_id,
                "state": r.holdout_state,
                "exposure_count": r.exposure_count,
                "period": strategy_detail["holdout_period"],
                "approval": approval_summary,
                "action_capabilities": [
                    cap(
                        "run_holdout",
                        r.holdout_state == "UNLOCKED",
                        "HOLDOUT_APPROVAL_REQUIRED",
                    )
                ],
                "revision": r.revision,
                "validation": {
                    **validation_detail,
                    "holdout_state": r.holdout_state,
                    "revision": r.revision,
                },
            },
        ),
        headers={"ETag": f'W/"{r.id}:{r.revision}"'},
    )


def approval_prerequisites(
    s: Session, validation: ValidationRow, strategy: StrategyVersionRow
) -> list[dict[str, str]]:
    exposure_exists = (
        s.query(HoldoutExposureRow.id)
        .filter_by(
            validation_id=validation.id,
            workspace_id=validation.workspace_id,
        )
        .first()
        is not None
    )
    return [
        {
            "key": "strategy_frozen",
            "state": "PASS" if strategy.state == "VALIDATED" else "FAIL",
            "detail": "Strategy passed strict validation",
        },
        {
            "key": "holdout_not_exposed",
            "state": (
                "PASS"
                if validation.exposure_count == 0 and not exposure_exists
                else "FAIL"
            ),
            "detail": "No prior holdout exposure exists",
        },
        {
            "key": "validation_bound",
            "state": (
                "PASS"
                if validation.strategy_version_id == strategy.id
                and validation.holdout_state in {"LOCKED", "APPROVAL_PENDING"}
                and validation.status in {"WAITING_HOLDOUT", "COMPLETED"}
                and _json_loads(validation.detail).get("result") == "PASS"
                else "FAIL"
            ),
            "detail": "Completed validation and strategy revision are bound",
        },
    ]


def validation_payload(s: Session, validation: ValidationRow) -> dict[str, Any]:
    detail = _json_loads(validation.detail)
    strategy = s.execute(
        select(StrategyVersionRow).where(
            StrategyVersionRow.id == validation.strategy_version_id,
            StrategyVersionRow.workspace_id == validation.workspace_id,
        )
    ).scalar_one_or_none()
    prerequisites_ready = False
    if strategy is not None and strategy.workspace_id == validation.workspace_id:
        prerequisites_ready = all(
            item["state"] == "PASS"
            for item in approval_prerequisites(s, validation, strategy)
        )
    detail.update(
        {
            "status": _as_str(validation.status),
            "holdout_state": _as_str(validation.holdout_state),
            "revision": _as_int(validation.revision),
            "action_capabilities": cast(
                list[JsonValue],
                validation_action_capabilities(
                    _as_str(validation.status),
                    _as_optional_str(detail.get("result")),
                    _as_str(validation.holdout_state),
                    prerequisites_ready=prerequisites_ready,
                ),
            ),
        }
    )
    return validated_payload("ValidationDetail", detail)


@app.post(
    "/api/v1/validations/{validation_id}/holdout-approval-requests", status_code=201
)
def request_approval(
    validation_id: ValidationId,
    data: HoldoutApprovalRequest,
    idempotency_key: IdempotencyKey,
    if_match: IfMatch,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    payload = data.model_dump(mode="json", exclude_unset=True)

    def f():
        validation_row = (
            s.query(ValidationRow)
            .filter_by(id=validation_id, workspace_id=actor.workspace_id)
            .with_for_update()
            .one_or_none()
        )
        if not validation_row:
            raise problem(404, "RESOURCE_NOT_FOUND", "validation not found")
        require_workspace(validation_row, actor)
        if not if_match:
            raise problem(428, "PRECONDITION_REQUIRED", "If-Match required")
        if if_match != f'W/"{validation_id}:{validation_row.revision}"':
            raise problem(412, "REVISION_MISMATCH", "validation ETag does not match")
        if validation_row.holdout_state != "LOCKED":
            raise problem(409, "HOLDOUT_LOCKED")
        strategy = (
            s.query(StrategyVersionRow)
            .filter_by(
                id=validation_row.strategy_version_id,
                workspace_id=actor.workspace_id,
            )
            .with_for_update()
            .one_or_none()
        )
        if strategy is None:
            raise problem(404, "RESOURCE_NOT_FOUND", "strategy version not found")
        require_workspace(strategy, actor)
        validation_row.revision += 1
        prerequisites = approval_prerequisites(s, validation_row, strategy)
        if any(item["state"] != "PASS" for item in prerequisites):
            raise problem(409, "HOLDOUT_PREREQUISITES_INCOMPLETE")
        prerequisites_sha256 = content_hash(prerequisites)
        i = new_id("APR")
        subject_sha256 = content_hash(
            {
                "subject_type": "validation",
                "subject_id": validation_id,
                "subject_version": strategy.version,
                "subject_revision": validation_row.revision,
                "strategy_version_id": strategy.id,
                "strategy_spec_sha256": strategy.spec_sha256,
                "prerequisites_sha256": prerequisites_sha256,
            }
        )
        d = validated_payload(
            "ApprovalDetail",
            {
                "approval_id": i,
                "type": "HOLDOUT_UNLOCK",
                "subject": {
                    "type": "VALIDATION",
                    "id": validation_id,
                    "version": strategy.version,
                    "revision": validation_row.revision,
                    "sha256": subject_sha256,
                },
                "requester": {"type": "OWNER", "id": actor.id},
                "status": "PENDING",
                "reason": payload["reason"],
                "prerequisites": prerequisites,
                "risk_summary": {"risk_level": "HIGH", "warning_codes": []},
                "effects": [
                    {
                        "code": "HOLDOUT_UNLOCK",
                        "detail": "Allows one controlled holdout run",
                    }
                ],
                "revision": 1,
                "requested_at": NOW(),
                "decided_at": None,
                "action_capabilities": [cap("approve")],
            },
        )
        approval_row = ApprovalRow(
            id=i,
            workspace_id=actor.workspace_id,
            validation_id=validation_id,
            status="PENDING",
            subject_sha256=subject_sha256,
            subject_type="VALIDATION",
            subject_id=validation_id,
            subject_version=strategy.version,
            subject_revision=validation_row.revision,
            subject_spec_sha256=strategy.spec_sha256,
            prerequisites_sha256=prerequisites_sha256,
            revision=1,
            detail=json.dumps(d),
        )
        s.add(approval_row)
        s.flush([approval_row])
        validation_row.holdout_state = "APPROVAL_PENDING"
        emit(
            s,
            "approval",
            i,
            1,
            "approval.created",
            payload={"state": "PENDING", "status": "PENDING"},
        )
        return 201, d

    return idem(
        s,
        actor,
        idempotency_key,
        payload,
        f"/validations/{validation_id}/holdout-approval-requests",
        f,
    )


@app.post("/api/v1/validations/{validation_id}/holdout-runs", status_code=202)
def holdout_run(
    validation_id: ValidationId,
    data: HoldoutRunRequest,
    idempotency_key: IdempotencyKey,
    if_match: IfMatch,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    payload = data.model_dump(mode="json", exclude_unset=True)

    def f():
        validation_row = (
            s.query(ValidationRow)
            .filter_by(id=validation_id, workspace_id=actor.workspace_id)
            .with_for_update()
            .one_or_none()
        )
        if validation_row is None:
            raise problem(404, "RESOURCE_NOT_FOUND", "validation not found")
        require_workspace(validation_row, actor)
        if not if_match:
            raise problem(428, "PRECONDITION_REQUIRED", "If-Match required")
        if if_match != f'W/"{validation_id}:{validation_row.revision}"':
            raise problem(412, "REVISION_MISMATCH", "validation ETag does not match")
        approval = (
            s.query(ApprovalRow)
            .filter_by(id=payload["approval_id"], workspace_id=actor.workspace_id)
            .with_for_update()
            .one_or_none()
        )
        if (
            not approval
            or approval.validation_id != validation_id
            or approval.status != "APPROVED"
        ):
            raise problem(403, "HOLDOUT_APPROVAL_REQUIRED")
        require_workspace(approval, actor)
        if validation_row.holdout_state != "UNLOCKED":
            raise problem(409, "HOLDOUT_LOCKED")
        validation_row.holdout_state = "RUNNING"
        validation_row.revision += 1
        emit(
            s,
            "validation",
            validation_id,
            validation_row.revision,
            "validation.holdout.updated",
            payload={"state": "RUNNING", "status": "RUNNING"},
        )
        return 202, job(
            s,
            "HOLDOUT_RUN",
            {
                "type": "validation",
                "id": validation_id,
                "version": None,
                "revision": validation_row.revision,
            },
            input_payload={
                "validation_id": validation_id,
                "approval_id": approval.id,
                **payload,
            },
            retry_safe=False,
            max_attempts=1,
        )

    return idem(
        s,
        actor,
        idempotency_key,
        payload,
        f"/validations/{validation_id}/holdout-runs",
        f,
    )


@app.get("/api/v1/validations/{validation_id}/holdout/result")
def holdout_result(
    validation_id: ValidationId,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    row = owned(s, ValidationRow, validation_id, actor, "validation")
    if row.holdout_state != "EXPOSED":
        raise problem(403, "HOLDOUT_RESULT_FORBIDDEN")
    exposure = (
        s.query(HoldoutExposureRow)
        .filter_by(validation_id=validation_id, workspace_id=actor.workspace_id)
        .one_or_none()
    )
    if exposure is None:
        raise problem(404, "RESOURCE_NOT_FOUND", "holdout result not found")
    result = _json_loads(exposure.result)
    return JSONResponse(
        validated_payload("HoldoutResult", result),
        headers={"ETag": f'W/"{row.id}:{row.revision}"'},
    )


@app.post("/api/v1/memos", status_code=202)
def generate_memo(
    data: MemoGenerateRequest,
    idempotency_key: IdempotencyKey,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    payload = data.model_dump(mode="json", exclude_unset=True)

    def operation():
        version = (
            s.query(StrategyVersionRow)
            .filter_by(
                strategy_id=payload["strategy_id"],
                version=payload["strategy_version"],
                workspace_id=actor.workspace_id,
            )
            .first()
        )
        if version is None:
            raise problem(404, "RESOURCE_NOT_FOUND", "strategy version not found")
        require_workspace(version, actor)
        memo_id = new_id("MEM")
        accepted = job(
            s,
            "MEMO_GENERATE",
            {"type": "memo", "id": memo_id, "version": None, "revision": 1},
            input_payload={"memo_id": memo_id, **payload},
        )
        return 202, accepted

    return idem(s, actor, idempotency_key, payload, "/memos", operation)


@app.get("/api/v1/memos/{memo_id}")
def get_memo(
    memo_id: MemoId,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    record = get(s, "memo", memo_id, workspace_id=actor.workspace_id)
    require_workspace(record, actor)
    return JSONResponse(
        body(record), headers={"ETag": f'W/"{record.record_key}:{record.revision}"'}
    )


@app.get("/api/v1/memos/{memo_id}/export", response_class=Response)
def export_memo(
    memo_id: MemoId,
    format: Literal["MARKDOWN"] = Query(...),
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    if format != "MARKDOWN":
        raise problem(422, "INVALID_REQUEST", "only MARKDOWN export is supported")
    record = get(s, "memo", memo_id, workspace_id=actor.workspace_id)
    require_workspace(record, actor)
    detail = body(record)
    markdown = f"# Investment Memo {memo_id}\n\n" + "\n\n".join(
        f"## {section['title']}\n\n{section['content']}"
        for section in detail["sections"]
    )
    return Response(
        markdown,
        media_type="text/markdown",
        headers={
            "ETag": f'W/"{record.id}:{record.revision}"',
            "Content-Disposition": f'attachment; filename="{memo_id}.md"',
        },
    )


@app.get("/api/v1/approvals")
def list_approvals(actor: Actor = Depends(require_owner), s: Session = Depends(db)):
    items = []
    for row in (
        s.query(ApprovalRow)
        .filter_by(workspace_id=actor.workspace_id)
        .order_by(ApprovalRow.id)
        .all()
    ):
        detail = _json_loads(row.detail)
        items.append(
            {
                key: detail[key]
                for key in (
                    "approval_id",
                    "type",
                    "subject",
                    "requester",
                    "reason",
                    "status",
                    "requested_at",
                    "decided_at",
                    "revision",
                    "action_capabilities",
                )
            }
        )
    return {"items": items, "page": {"next_cursor": None, "has_more": False}}


@app.get("/api/v1/approvals/{approval_id}")
def read_approval(
    approval_id: ApprovalId,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    r = owned(s, ApprovalRow, approval_id, actor, "approval")
    return JSONResponse(
        json.loads(r.detail), headers={"ETag": f'W/"{r.id}:{r.revision}"'}
    )


def decide(
    approval_id: str,
    data: dict[str, Any],
    if_match: str | None,
    s: Session,
    status: str,
    path: str,
    actor: Actor,
) -> tuple[int, dict[str, Any]]:
    r = (
        s.query(ApprovalRow)
        .filter_by(id=approval_id, workspace_id=actor.workspace_id)
        .with_for_update()
        .one_or_none()
    )
    if not r:
        raise problem(404, "RESOURCE_NOT_FOUND", "approval not found")
    if r.status != "PENDING":
        raise problem(409, "APPROVAL_ALREADY_RESOLVED")
    if not if_match:
        raise problem(428, "PRECONDITION_REQUIRED")
    if if_match != f'W/"{r.id}:{r.revision}"':
        raise problem(412, "REVISION_MISMATCH")
    validation_row = (
        s.query(ValidationRow)
        .filter_by(id=r.validation_id, workspace_id=actor.workspace_id)
        .with_for_update()
        .one_or_none()
    )
    strategy = (
        s.query(StrategyVersionRow)
        .filter_by(
            id=validation_row.strategy_version_id,
            workspace_id=actor.workspace_id,
        )
        .with_for_update()
        .one_or_none()
        if validation_row is not None
        else None
    )
    detail = _json_loads(r.detail)
    prerequisites = (
        approval_prerequisites(s, validation_row, strategy)
        if validation_row is not None and strategy is not None
        else []
    )
    current_subject_sha256 = content_hash(
        {
            "subject_type": "validation",
            "subject_id": r.validation_id,
            "subject_version": strategy.version if strategy else None,
            "subject_revision": validation_row.revision if validation_row else None,
            "strategy_version_id": strategy.id if strategy else None,
            "strategy_spec_sha256": strategy.spec_sha256 if strategy else None,
            "prerequisites_sha256": content_hash(prerequisites),
        }
    )
    acknowledged = data.get("acknowledged_subject_sha256")
    stale = (
        validation_row is None
        or strategy is None
        or strategy.state != "VALIDATED"
        or validation_row.holdout_state != "APPROVAL_PENDING"
        or validation_row.revision != r.subject_revision
        or strategy.version != r.subject_version
        or strategy.spec_sha256 != r.subject_spec_sha256
        or content_hash(prerequisites) != r.prerequisites_sha256
        or any(item["state"] != "PASS" for item in prerequisites)
        or current_subject_sha256 != r.subject_sha256
        or bool(acknowledged and acknowledged != r.subject_sha256)
    )
    if stale:
        approval_fields = cast(_ApprovalMutationFields, r)
        approval_fields.status = "STALE"
        approval_fields.revision = _as_int(r.revision) + 1
        detail.update(
            {"status": "STALE", "decided_at": NOW(), "revision": _as_int(r.revision)}
        )
        approval_fields.detail = json.dumps(detail)
        s.flush([r])
        if validation_row is not None:
            validation_fields = cast(_ValidationMutationFields, validation_row)
            validation_fields.holdout_state = "LOCKED"
            validation_fields.revision = _as_int(validation_row.revision) + 1
        emit(
            s,
            "approval",
            _as_str(r.id),
            _as_int(r.revision),
            "approval.updated",
            payload={"state": "STALE", "status": "STALE"},
        )
        return 409, {
            "type": "https://quantfoundry.local/problems/approval-stale",
            "title": "APPROVAL_STALE",
            "status": 409,
            "code": "APPROVAL_STALE",
            "detail": "Approval subject or mandatory prerequisites changed",
            "instance": f"/api/v1{path}",
            "request_id": actor.request_id,
            "retryable": False,
            "field_errors": [],
            "context": {},
        }
    approval_fields = cast(_ApprovalMutationFields, r)
    approval_fields.status = status
    approval_fields.revision = _as_int(r.revision) + 1
    d = detail
    d.update({"status": status, "decided_at": NOW(), "revision": _as_int(r.revision)})
    approval_fields.detail = json.dumps(d)
    s.flush([r])
    if validation_row:
        validation_fields = cast(_ValidationMutationFields, validation_row)
        validation_fields.holdout_state = (
            "UNLOCKED" if status == "APPROVED" else "LOCKED"
        )
        validation_fields.revision = _as_int(validation_row.revision) + 1
    emit(
        s,
        "approval",
        _as_str(r.id),
        _as_int(r.revision),
        "approval.updated",
        payload={"state": status, "status": status},
    )
    return 200, validated_payload(
        "ApprovalDecisionResult",
        {
            "approval": d,
            "subject_ref": {
                "type": "validation",
                "id": r.validation_id,
                "version": None,
                "revision": validation_row.revision if validation_row else 1,
            },
            "next_job": None,
        },
    )


@app.post("/api/v1/approvals/{approval_id}/approve")
def approve(
    approval_id: ApprovalId,
    data: ApprovalDecisionRequest,
    if_match: IfMatch,
    idempotency_key: IdempotencyKey,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    data = data.model_dump(mode="json", exclude_unset=True)
    return idem(
        s,
        actor,
        idempotency_key,
        data,
        f"/approvals/{approval_id}/approve",
        lambda: decide(
            approval_id,
            data,
            if_match,
            s,
            "APPROVED",
            f"/approvals/{approval_id}/approve",
            actor,
        ),
    )


@app.post("/api/v1/approvals/{approval_id}/reject")
def reject(
    approval_id: ApprovalId,
    data: ApprovalRejectRequest,
    if_match: IfMatch,
    idempotency_key: IdempotencyKey,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    data = data.model_dump(mode="json", exclude_unset=True)
    return idem(
        s,
        actor,
        idempotency_key,
        data,
        f"/approvals/{approval_id}/reject",
        lambda: decide(
            approval_id,
            data,
            if_match,
            s,
            "REJECTED",
            f"/approvals/{approval_id}/reject",
            actor,
        ),
    )


@app.get("/api/v1/agents")
def agents(actor: Actor = Depends(require_owner), s: Session = Depends(db)):
    return [
        agent_config_payload(
            s.get(AgentConfigRow, (actor.workspace_id, role))
            or default_agent_config(role)
        )
        for role in ROLES
    ]


def default_agent_config(role: str):
    now = datetime.now(UTC)
    return SimpleNamespace(
        role=role,
        enabled=True,
        model_provider=DEFAULT_AGENT_PROVIDER,
        model_name=DEFAULT_AGENT_MODEL,
        runtime_profile="DEFAULT",
        tool_timeout_seconds=30,
        max_steps_override=None,
        max_tool_calls_override=None,
        revision=1,
        created_at=now,
        updated_at=now,
    )


def agent_config_payload(row):
    return {
        "role_key": row.role,
        "enabled": row.enabled,
        "model_provider": row.model_provider,
        "model_name": row.model_name,
        "runtime_profile": row.runtime_profile,
        "tool_timeout_seconds": row.tool_timeout_seconds,
        "max_steps_override": row.max_steps_override,
        "max_tool_calls_override": row.max_tool_calls_override,
        "revision": row.revision,
        "action_capabilities": [cap("update_config")],
        "created_at": wire_datetime(row.created_at),
        "updated_at": wire_datetime(row.updated_at),
    }


@app.get("/api/v1/agents/{role}/config")
def get_agent_config(
    role: AgentRole,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    if role not in ROLES:
        raise problem(404, "RESOURCE_NOT_FOUND", "agent role not found")
    row = s.get(AgentConfigRow, (actor.workspace_id, role)) or default_agent_config(
        role
    )
    return JSONResponse(
        agent_config_payload(row),
        headers={"ETag": f'W/"agent:{role}:{row.revision}"'},
    )


@app.put("/api/v1/agents/{role}/config")
def agent_config(
    role: AgentRole,
    data: AgentConfigUpdate,
    if_match: IfMatch,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    s.info.update(
        {
            "actor_id": actor.id,
            "workspace_id": actor.workspace_id,
            "request_id": actor.request_id,
        }
    )
    payload = data.model_dump(mode="json", exclude_unset=True)
    if role not in ROLES:
        raise problem(404, "RESOURCE_NOT_FOUND")
    if not if_match:
        raise problem(428, "PRECONDITION_REQUIRED")
    row = s.get(AgentConfigRow, (actor.workspace_id, role)) or AgentConfigRow(
        workspace_id=actor.workspace_id,
        role=role,
        enabled=True,
        revision=1,
        model_provider=DEFAULT_AGENT_PROVIDER,
        model_name=DEFAULT_AGENT_MODEL,
        runtime_profile="DEFAULT",
        tool_timeout_seconds=30,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    s.add(row)
    if if_match != f'W/"agent:{role}:{row.revision}"':
        raise problem(412, "REVISION_MISMATCH")
    row.enabled = payload.get("enabled", row.enabled)
    row.model_provider = payload.get("model_provider", row.model_provider)
    row.model_name = payload.get("model_name", row.model_name)
    row.runtime_profile = payload.get("runtime_profile", row.runtime_profile)
    row.tool_timeout_seconds = payload.get(
        "tool_timeout_seconds", row.tool_timeout_seconds
    )
    row.max_steps_override = payload.get("max_steps_override", row.max_steps_override)
    row.max_tool_calls_override = payload.get(
        "max_tool_calls_override", row.max_tool_calls_override
    )
    config_fields = cast(_AgentConfigMutationFields, row)
    config_fields.revision = _as_int(row.revision) + 1
    config_fields.updated_at = datetime.now(UTC)
    response_payload = validated_payload("AgentConfig", agent_config_payload(row))
    emit(
        s,
        "agent_config",
        role,
        _as_int(row.revision),
        "notification.updated",
        payload={"state": "UPDATED", "status": "UPDATED"},
    )
    s.commit()
    return JSONResponse(
        response_payload, headers={"ETag": f'W/"agent:{role}:{row.revision}"'}
    )


@app.get("/api/v1/jobs/{job_id}")
def read_job(
    job_id: JobId,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    r = owned(s, JobRow, job_id, actor, "job")
    return JSONResponse(
        json.loads(r.payload), headers={"ETag": f'W/"{r.id}:{r.revision}"'}
    )


@app.get("/api/v1/agent-runs/{agent_run_id}")
def agent_run(
    agent_run_id: AgentRunId,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    r = owned(s, AgentRunRow, agent_run_id, actor, "agent run")
    return {
        "agent_run_id": r.id,
        "agent_role": r.role,
        "agent_version": r.agent_version,
        "model_provider": r.model_provider,
        "model_name": r.model_name,
        "research_id": r.research_id,
        "object_type": r.object_type,
        "object_id": r.object_id,
        "object_version": r.object_version,
        "object_revision": r.object_revision,
        "objective": r.objective,
        "status": r.status,
        "decision_summary": r.decision_summary,
        "next_action": json.loads(r.next_action) if r.next_action else None,
        "root_agent_run_id": r.root_agent_run_id,
        "parent_agent_run_id": r.parent_agent_run_id,
        "context_sha256": r.context_sha256,
        "model_call_count": r.model_call_count,
        "input_tokens": r.input_tokens,
        "output_tokens": r.output_tokens,
        "tool_call_count": r.tool_call_count,
        "step_count": r.step_count,
        "started_at": wire_datetime(r.started_at) if r.started_at else None,
        "ended_at": wire_datetime(r.ended_at) if r.ended_at else None,
        "created_at": wire_datetime(r.created_at),
    }


@app.get("/api/v1/tool-calls/{tool_call_id}")
def tool_call(
    tool_call_id: ToolCallId,
    actor: Actor = Depends(require_owner),
    s: Session = Depends(db),
):
    r = owned(s, ToolCallRow, tool_call_id, actor, "tool call")
    return {
        "tool_call_id": r.id,
        "agent_run_id": r.agent_run_id,
        "tool_name": r.tool_name,
        "tool_version": r.tool_version,
        "objective": r.objective,
        "research_id": r.research_id,
        "experiment_id": r.experiment_id,
        "job_id": r.job_id,
        "input_sha256": r.input_sha256,
        "policy_version_ref": r.policy_version_ref,
        "status": r.status,
        "result_summary": json.loads(r.result_summary) if r.result_summary else None,
        "output_artifact_id": r.output_artifact_id,
        "warnings": json.loads(r.warnings),
        "provenance": json.loads(r.provenance) if r.provenance else None,
        "started_at": wire_datetime(r.started_at),
        "finished_at": wire_datetime(r.finished_at) if r.finished_at else None,
        "duration_ms": r.duration_ms,
    }


@app.get("/api/v1/events/stream", response_class=StreamingResponse)
def stream(
    last_event_id: LastEventId = None,
    actor: Actor = Depends(require_owner),
):
    return StreamingResponse(
        durable_event_stream(
            SessionLocal,
            Event,
            last_event_id,
            lambda data: validated_payload("SseEnvelope", data),
            NOW,
            workspace_id=actor.workspace_id,
            watermark_model=EventStreamWatermark,
        ),
        media_type="text/event-stream",
    )


def _configure_contract_routes() -> None:
    specification = canonical_openapi()

    def resolved_response(response: dict[str, Any]) -> dict[str, Any]:
        if "$ref" not in response:
            return response
        return specification["components"]["responses"][
            response["$ref"].rsplit("/", 1)[-1]
        ]

    for route in app.routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/v1"):
            continue
        canonical_path = route.path.removeprefix("/api/v1")
        methods = [
            method.lower()
            for method in route.methods or set()
            if method.lower() in {"get", "post", "put"}
        ]
        if len(methods) != 1:
            continue
        operation = specification["paths"][canonical_path][methods[0]]
        route.operation_id = operation["operationId"]
        success_status = str(route.status_code or 200)
        success = resolved_response(operation["responses"][success_status])
        reference = (
            success.get("content", {})
            .get("application/json", {})
            .get("schema", {})
            .get("$ref")
        )
        if reference:
            response_model = SCHEMA_MODELS[reference.rsplit("/", 1)[-1]]
            route.response_model = response_model
            route.response_field = create_model_field(
                name=f"Response_{operation['operationId']}",
                type_=response_model,
                mode="serialization",
            )
        configured_responses: dict[int | str, dict[str, Any]] = {}
        for status, raw_declared in operation["responses"].items():
            declared = resolved_response(raw_declared)
            if status == success_status:
                if declared.get("headers") or "application/json" not in declared.get(
                    "content", {}
                ):
                    configured_responses[int(status)] = {
                        "description": declared["description"],
                        **(
                            {"headers": declared["headers"]}
                            if declared.get("headers")
                            else {}
                        ),
                        **(
                            {"content": declared["content"]}
                            if "application/json" not in declared.get("content", {})
                            else {}
                        ),
                    }
                continue
            configured_responses[int(status)] = {
                "description": declared["description"],
                "content": {
                    "application/problem+json": {
                        "schema": {"$ref": "#/components/schemas/ApiProblem"}
                    }
                },
                **({"headers": declared["headers"]} if declared.get("headers") else {}),
            }
        route.responses = configured_responses


_configure_contract_routes()


def application_openapi() -> dict[str, Any]:
    if app.openapi_schema is not None:
        return app.openapi_schema
    specification = canonical_openapi()
    generated = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version="3.1.0",
        routes=app.routes,
    )
    generated["paths"] = {
        path.removeprefix("/api/v1"): operations
        for path, operations in generated["paths"].items()
        if path.startswith("/api/v1")
    }
    generated["security"] = specification["security"]
    generated["paths"]["/system/health"]["get"]["security"] = []
    path_parameter_models = {
        "dataset_id": "dataset",
        "snapshot_id": "snapshot",
        "research_id": "research",
        "experiment_id": "experiment",
        "factor_id": "factor",
        "strategy_id": "strategy",
        "validation_id": "validation",
        "memo_id": "memo",
        "approval_id": "approval",
        "agent_run_id": "agent_run",
        "tool_call_id": "tool_call",
        "job_id": "job",
    }
    for path, methods in generated["paths"].items():
        for method, operation in methods.items():
            if not isinstance(operation, dict) or "responses" not in operation:
                continue
            declared = specification["paths"][path][method]["responses"]
            canonical_parameters = specification["paths"][path][method].get(
                "parameters", []
            )
            required_headers = {
                (
                    specification["components"]["parameters"][
                        raw["$ref"].rsplit("/", 1)[-1]
                    ]
                    if "$ref" in raw
                    else raw
                )["name"].lower()
                for raw in canonical_parameters
                if (
                    specification["components"]["parameters"][
                        raw["$ref"].rsplit("/", 1)[-1]
                    ]
                    if "$ref" in raw
                    else raw
                ).get("in")
                == "header"
                and (
                    specification["components"]["parameters"][
                        raw["$ref"].rsplit("/", 1)[-1]
                    ]
                    if "$ref" in raw
                    else raw
                ).get("required")
            }
            for parameter in operation.get("parameters", []):
                id_kind = path_parameter_models.get(parameter.get("name", ""))
                if parameter.get("in") == "path" and id_kind is not None:
                    parameter["schema"] = public_id_json_schema(id_kind)
                if (
                    parameter.get("in") == "header"
                    and parameter.get("name", "").lower() in required_headers
                ):
                    parameter["required"] = True
                    schema = parameter.get("schema", {})
                    branches = schema.get("anyOf")
                    if isinstance(branches, list):
                        non_null = [
                            branch
                            for branch in branches
                            if branch.get("type") != "null"
                        ]
                        if len(non_null) == 1:
                            parameter["schema"] = non_null[0]
            for status in list(operation["responses"]):
                if status not in declared:
                    del operation["responses"][status]
    # FastAPI emits every request/response model attached to a route. Add only
    # referenced leaf models that FastAPI cannot discover through external
    # JSON-Schema refs; never replace the generated runtime document/spec.
    runtime_schemas = generated.setdefault("components", {}).setdefault("schemas", {})
    model_schemas = application_schemas()
    # FastAPI expands private helper classes used inside generated unions.  The
    # public runtime surface is the closed set of independently generated
    # component models, with their helper definitions already inlined.
    runtime_schemas.clear()
    runtime_schemas.update(model_schemas)
    generated["info"] = specification["info"]
    generated["servers"] = specification.get("servers", [])
    app.openapi_schema = generated
    return generated


object.__setattr__(app, "openapi", application_openapi)
