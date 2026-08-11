"""Independent typed Pydantic models generated from the committed API contract."""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel

from app import generated_api_models as generated

SetupCompleteRequest = generated.SetupCompleteRequest
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

SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    name: cast(type[BaseModel], getattr(generated, name))
    for name in generated.SCHEMA_NAMES
}
for _model in SCHEMA_MODELS.values():
    _model.model_rebuild()


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
    return {name: schemas[name] for name in generated.SCHEMA_NAMES}


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
