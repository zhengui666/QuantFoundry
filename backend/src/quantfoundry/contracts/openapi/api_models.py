"""Independent typed Pydantic models generated from the committed API contract."""

from __future__ import annotations

from typing import Any, Literal, cast
from urllib.parse import urlsplit

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from quantfoundry.contracts.openapi import generated_api_models as generated

SetupProviderConnectionValidationRequest = (
    generated.SetupProviderConnectionValidationRequest
)
CapabilityEvaluationRequest = generated.CapabilityEvaluationRequest
DatasetValidationRequest = generated.DatasetValidationRequest
SnapshotCreateRequest = generated.SnapshotCreateRequest
ResearchCreateRequest = generated.ResearchCreateRequest
ResearchStartRequest = generated.ResearchStartRequest
ExperimentCreateRequest = generated.ExperimentCreateRequest
ExperimentReproduceRequest = generated.ExperimentReproduceRequest
FactorCreateRequest = generated.FactorCreateRequest
FactorAnalysisRequest = generated.FactorAnalysisRequest
StrategyCreateRequest = generated.StrategyCreateRequest
BacktestRequest = generated.BacktestRequest
FreezeStrategyRequest = generated.FreezeStrategyRequest
ValidationCreateRequest = generated.ValidationCreateRequest
HoldoutApprovalRequest = generated.HoldoutApprovalRequest
HoldoutRunRequest = generated.HoldoutRunRequest
MemoGenerateRequest = generated.MemoGenerateRequest
ApprovalDecisionRequest = generated.ApprovalDecisionRequest
ApprovalRejectRequest = generated.ApprovalRejectRequest
AgentConfigUpdate = generated.AgentConfigUpdate


class SetupCompleteRequest(BaseModel):
    """UX-001 completes setup by activating a validated control-plane revision."""

    model_config = ConfigDict(extra="forbid")
    configuration_revision: int = Field(..., ge=1)


class LiveConnectorValidationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connection_id: str = Field(
        ..., min_length=1, max_length=80, pattern=r"^[A-Za-z0-9._-]+$"
    )
    endpoint: str = Field(..., min_length=1, max_length=2048)
    key_id: str = Field(..., min_length=1, max_length=160)
    credential: str = Field(
        ..., min_length=1, max_length=16384, json_schema_extra={"writeOnly": True}
    )
    expected_account_id: str | None = Field(default=None, min_length=1, max_length=160)

    @field_validator("endpoint")
    @classmethod
    def require_https_endpoint(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username
            or parsed.password
        ):
            raise ValueError(
                "endpoint must be an HTTPS URL without embedded credentials"
            )
        return value.rstrip("/")


class LiveConnectorValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    connection_id: str = Field(..., min_length=1, max_length=80)
    state: Literal["SUCCESS", "FAILED"]
    error_code: str | None
    connector_id: str | None
    protocol_version: str | None
    capabilities_hash: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    account_ids: list[str]
    assets: list[
        Literal[
            "EQUITY", "FUTURE", "OPTION", "FX_SPOT", "CRYPTO_SPOT", "CRYPTO_PERPETUAL"
        ]
    ]
    checked_at: AwareDatetime


SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    name: cast(type[BaseModel], SetupCompleteRequest)
    if name == "SetupCompleteRequest"
    else cast(type[BaseModel], getattr(generated, name))
    for name in generated.SCHEMA_NAMES
}
SCHEMA_MODELS.update(
    {
        "LiveConnectorValidationRequest": LiveConnectorValidationRequest,
        "LiveConnectorValidationResult": LiveConnectorValidationResult,
    }
)
for _model in SCHEMA_MODELS.values():
    _model.model_rebuild()
try:
    from app import generated_api_models as _ux_models

    for _name in (
        "GeneralAccessKeyLoginRequest",
        "GeneralAccessKeyMetadata",
        "GeneralAccessKeyList",
        "GeneralAccessKeyCreateRequest",
        "GeneralAccessKeyRenameRequest",
        "GeneralAccessKeyIssued",
        "OwnerSessionView",
        "SessionBootstrapResponse",
        "ConfigurationCatalog",
        "ConfigurationCatalogEntry",
        "ConfigurationValueWrite",
        "ConfigurationValueView",
        "ConfigurationCandidateRequest",
        "ConfigurationCandidate",
        "ConfigurationConsumerState",
        "ConfigurationActive",
        "ConfigurationValidationResult",
        "ConfigurationActivateRequest",
        "ConfigurationRollbackRequest",
        "DatabaseConnectionCandidate",
        "DatabaseConnectionCandidateRequest",
        "DatabaseConnectionStatus",
        "DatabaseConnectionCheck",
        "DatabaseConnectionValidationResult",
        "ApiProblem",
        "CanonicalErrorCode",
        "FieldError",
        "ProblemContext",
    ):
        SCHEMA_MODELS[_name] = cast(type[BaseModel], getattr(_ux_models, _name))
except ImportError:
    pass


def validate_schema(name: str, value: Any) -> Any:
    """Validate using the independent generated model; never load canonical YAML."""

    return (
        SCHEMA_MODELS[name]
        .model_validate(value)
        .model_dump(mode="json", exclude_unset=True)
    )


def application_schemas() -> dict[str, dict[str, Any]]:
    """Return JSON Schema generated solely from application Pydantic models."""

    def inline(value: Any, definitions: dict[str, Any], stack: frozenset[str]) -> Any:
        if isinstance(value, list):
            return [inline(item, definitions, stack) for item in value]
        if not isinstance(value, dict):
            return value
        reference = value.get("$ref")
        if isinstance(reference, str):
            name = reference.rsplit("/", 1)[-1]
            if name in definitions and name not in stack:
                return inline(definitions[name], definitions, stack | {name})
        return {
            key: inline(item, definitions, stack)
            for key, item in value.items()
            if key != "$defs"
        }

    schemas: dict[str, dict[str, Any]] = {}
    for name, model in SCHEMA_MODELS.items():
        schema = model.model_json_schema(
            ref_template="#/components/schemas/{model}", mode="validation"
        )
        definitions = schema.pop("$defs", {})
        schemas[name] = cast(dict[str, Any], inline(schema, definitions, frozenset()))
    return schemas


__all__ = [
    "AgentConfigUpdate",
    "ApprovalDecisionRequest",
    "ApprovalRejectRequest",
    "BacktestRequest",
    "CapabilityEvaluationRequest",
    "DatasetValidationRequest",
    "ExperimentCreateRequest",
    "ExperimentReproduceRequest",
    "FactorAnalysisRequest",
    "FactorCreateRequest",
    "FreezeStrategyRequest",
    "HoldoutApprovalRequest",
    "HoldoutRunRequest",
    "MemoGenerateRequest",
    "LiveConnectorValidationRequest",
    "LiveConnectorValidationResult",
    "ResearchCreateRequest",
    "ResearchStartRequest",
    "SCHEMA_MODELS",
    "SetupCompleteRequest",
    "SetupProviderConnectionValidationRequest",
    "SnapshotCreateRequest",
    "StrategyCreateRequest",
    "ValidationCreateRequest",
    "application_schemas",
    "validate_schema",
]
