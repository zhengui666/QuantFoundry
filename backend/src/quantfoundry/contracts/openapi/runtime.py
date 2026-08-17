"""Runtime access to the committed OpenAPI contract.

The contract is an assertion boundary, never a response-value generator.  A
schema must not be used to manufacture IDs, timestamps, hashes, provenance or
otherwise conceal an incomplete handler result.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any

import jsonschema
import yaml

from quantfoundry.contracts.openapi.api_models import validate_schema

_SPEC: dict[str, Any] | None = None


def canonical_openapi() -> dict[str, Any]:
    global _SPEC
    if _SPEC is None:
        resource = files("quantfoundry.contracts.openapi").joinpath("openapi-v1.yaml")
        if resource.is_file():
            _SPEC = yaml.safe_load(resource.read_text(encoding="utf-8"))
        else:
            _SPEC = yaml.safe_load(
                (
                    Path(__file__).parents[5]
                    / "docs/后端系统技术方案/contracts/openapi-v1.yaml"
                ).read_text(encoding="utf-8")
            )
    return deepcopy(_SPEC)


def now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def validate_json_schema(schema: dict[str, Any], payload: Any) -> None:
    """Validate a schema fragment against the OpenAPI component resource."""
    specification = canonical_openapi()
    root_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": "#/$target",
        "$target": schema,
        "components": specification["components"],
    }
    jsonschema.Draft202012Validator(
        root_schema, format_checker=jsonschema.FormatChecker()
    ).validate(payload)


def validated_payload(name: str, payload: Any) -> Any:
    """Validate a handler-produced payload without changing it.

    This intentionally raises on missing required fields, invalid enums,
    patterns and additional properties.  Callers must convert such failures to
    a canonical internal problem; silently normalizing is forbidden.
    """
    validate_schema(name, payload)
    return payload
