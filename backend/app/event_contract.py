"""Closed, generated SSE event-contract boundary."""

from __future__ import annotations

from typing import Any, cast

from pydantic import ValidationError

from app.generated_api_models import EventPayload, EventType, SseEnvelope


def _event_type_values() -> tuple[str, ...]:
    schema = EventType.model_json_schema(mode="validation")
    values = schema.get("enum")
    if not isinstance(values, list) or not all(
        isinstance(value, str) for value in values
    ):
        raise RuntimeError("generated EventType is not a closed string enum")
    return tuple(cast(list[str], values))


EVENT_TYPES = _event_type_values()
if len(EVENT_TYPES) != 31 or len(set(EVENT_TYPES)) != 31:
    raise RuntimeError("generated EventType must contain exactly 31 unique members")


def _event_object_types() -> dict[str, str]:
    """Derive the 31 event-to-locator branches from the generated model."""

    result: dict[str, str] = {}
    schema = SseEnvelope.model_json_schema(mode="validation")
    for rule in schema.get("allOf", []):
        if not isinstance(rule, dict):
            continue
        condition = rule.get("if", {}).get("properties", {}).get("event_type", {})
        locator = rule.get("then", {}).get("properties", {}).get("object_type", {})
        if not isinstance(condition, dict) or not isinstance(locator, dict):
            continue
        object_type = locator.get("const")
        if not isinstance(object_type, str):
            continue
        values = (
            [condition["const"]]
            if isinstance(condition.get("const"), str)
            else condition.get("enum", [])
        )
        for value in values:
            if isinstance(value, str):
                result[value] = object_type
    if set(result) != set(EVENT_TYPES):
        raise RuntimeError("generated SSE event/object mapping is incomplete")
    return result


EVENT_OBJECT_TYPES = _event_object_types()

EVENT_TYPE_CHECK_SQL = (
    "event_type IN ("
    + ", ".join("'" + value.replace("'", "''") + "'" for value in EVENT_TYPES)
    + ")"
)


def validate_event_type(value: str) -> str:
    return EventType.model_validate(value).root


def validate_event_payload(value: dict[str, Any]) -> dict[str, Any]:
    return EventPayload.model_validate(value).model_dump(
        mode="json", exclude_unset=True
    )


def validate_sse_envelope(value: dict[str, Any]) -> dict[str, Any]:
    return SseEnvelope.model_validate(value).model_dump(mode="json", exclude_unset=True)


def safe_resync_payload(sequence: int | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {
        "state": "RESYNC_REQUIRED",
        "status": None,
    }
    if sequence is not None:
        value["resync_from_sequence"] = max(1, sequence)
    return validate_event_payload(value)


__all__ = [
    "EVENT_TYPES",
    "EVENT_TYPE_CHECK_SQL",
    "EVENT_OBJECT_TYPES",
    "ValidationError",
    "safe_resync_payload",
    "validate_event_payload",
    "validate_event_type",
    "validate_sse_envelope",
]
