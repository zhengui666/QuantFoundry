"""Fail-closed checks for the UX-001 D1 machine contract bundle."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = ROOT / "docs/后端系统技术方案/contracts"
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
REGISTRY_DATA_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "$schema",
        "title",
        "schema_version",
        "contract_stage",
        "additionalProperties",
        "required",
        "properties",
        "tools",
    ],
    "properties": {
        "$schema": {"type": "string", "format": "uri"},
        "title": {"type": "string", "minLength": 1},
        "schema_version": {"const": 1},
        "contract_stage": {"const": "P0_P0_5_EXECUTABLE"},
        "additionalProperties": {"const": False},
        "required": {"type": "array", "minItems": 1, "items": {"type": "string"}},
        "properties": {"type": "object"},
        "tools": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "name",
                    "version",
                    "input_schema",
                    "output_schema",
                    "allowed_agent_roles",
                    "idempotency_class",
                    "side_effect_class",
                    "execution_mode",
                    "timeout_seconds",
                    "requires_policy_checks",
                    "requires_snapshot",
                ],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "version": {"type": "string", "pattern": r"^1\.0$"},
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"},
                    "allowed_agent_roles": {
                        "type": "array",
                        "minItems": 1,
                        "uniqueItems": True,
                        "items": {
                            "enum": [
                                "RESEARCH_DIRECTOR",
                                "FACTOR_SCIENTIST",
                                "STRATEGY_SCIENTIST",
                                "PORTFOLIO_ANALYST",
                                "RED_TEAM_RESEARCHER",
                                "PERFORMANCE_ANALYST",
                            ]
                        },
                    },
                    "idempotency_class": {
                        "enum": [
                            "READ_ONLY",
                            "IDEMPOTENT",
                            "NATURAL_KEY",
                            "NON_IDEMPOTENT",
                        ]
                    },
                    "side_effect_class": {
                        "enum": [
                            "NONE",
                            "CREATE_RESEARCH_OBJECT",
                            "LIFECYCLE_MUTATION",
                            "APPROVAL_REQUEST",
                            "CAPITAL_GATE",
                        ]
                    },
                    "execution_mode": {"enum": ["SYNC", "JOB"]},
                    "timeout_seconds": {"type": "integer", "minimum": 1},
                    "requires_policy_checks": {
                        "type": "array",
                        "uniqueItems": True,
                        "items": {"type": "string"},
                    },
                    "requires_snapshot": {"type": "boolean"},
                },
            },
        },
    },
}


def load(name: str) -> dict:
    value = yaml.safe_load((CONTRACT_ROOT / name).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{name} must contain an object")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _resolve_local(document: dict[str, Any], reference: str, location: str) -> Any:
    if not reference.startswith("#/"):
        raise AssertionError(f"{location}: external OpenAPI reference is not allowed")
    current: Any = document
    try:
        for raw_segment in reference[2:].split("/"):
            segment = raw_segment.replace("~1", "/").replace("~0", "~")
            current = current[segment]
    except (KeyError, IndexError, TypeError) as error:
        raise AssertionError(f"{location}: unresolved OpenAPI reference {reference}") from error
    return current


def validate_openapi_document(document: dict[str, Any]) -> None:
    require(
        isinstance(document.get("openapi"), str)
        and document["openapi"].startswith("3.1."),
        "OpenAPI document must declare 3.1.x",
    )
    require(
        isinstance(document.get("info"), dict)
        and isinstance(document["info"].get("title"), str)
        and isinstance(document["info"].get("version"), str),
        "OpenAPI info is incomplete",
    )
    require(isinstance(document.get("paths"), dict), "OpenAPI paths are malformed")
    require(
        isinstance(document.get("components"), dict),
        "OpenAPI components are malformed",
    )

    def walk(value: Any, location: str, active: frozenset[str] = frozenset()) -> None:
        if isinstance(value, dict):
            reference = value.get("$ref")
            if isinstance(reference, str) and reference not in active:
                walk(
                    _resolve_local(document, reference, location),
                    f"{location} -> {reference}",
                    active | {reference},
                )
            for key, child in value.items():
                walk(child, f"{location}.{key}", active)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{location}[{index}]", active)

    walk(document, "root")
    for path, path_item in document["paths"].items():
        require(path.startswith("/"), f"OpenAPI path is invalid: {path}")
        require(isinstance(path_item, dict), f"OpenAPI path item is invalid: {path}")
        for method in HTTP_METHODS:
            if method not in path_item:
                continue
            operation = path_item[method]
            require(
                isinstance(operation, dict),
                f"{method.upper()} {path} is not an object",
            )
            require(
                isinstance(operation.get("operationId"), str)
                and operation["operationId"].strip(),
                f"{method.upper()} {path} has no operationId",
            )
            require(
                isinstance(operation.get("responses"), dict)
                and bool(operation["responses"]),
                f"{method.upper()} {path} has no responses",
            )


def main() -> int:
    openapi = load("openapi-v1.yaml")
    catalog = load("configuration-catalog-v1.yaml")
    bootstrap = load("bootstrap-control-v1.yaml")
    matrix = load("ux001-d1-test-matrix.yaml")
    registry = load("tools/v1-p0.yaml")
    validate_openapi_document(openapi)
    registry_errors = sorted(
        Draft202012Validator(REGISTRY_DATA_SCHEMA).iter_errors(registry),
        key=lambda error: list(error.path),
    )
    require(
        not registry_errors,
        "semantic tool registry schema validation failed: "
        + "; ".join(error.message for error in registry_errors[:3]),
    )
    for name, schema in openapi["components"]["schemas"].items():
        try:
            Draft202012Validator.check_schema(schema)
        except Exception as error:
            raise AssertionError(f"invalid OpenAPI schema: {name}") from error
    required_entry_fields = {
        "key",
        "group",
        "schema_version",
        "scope",
        "sensitivity",
        "apply_mode",
        "consumers",
        "dependencies",
        "schema",
        "validator",
        "safe_range",
    }
    require(isinstance(catalog.get("entries"), list), "catalog entries are malformed")
    for entry in catalog["entries"]:
        require(
            isinstance(entry, dict) and required_entry_fields <= set(entry),
            "catalog entry fields are incomplete",
        )
        try:
            Draft202012Validator.check_schema(entry["schema"])
        except Exception as error:
            raise AssertionError(
                f"invalid configuration schema: {entry['key']}"
            ) from error

    operations = sum(
        1
        for path_item in openapi["paths"].values()
        for method in path_item
        if method in HTTP_METHODS
    )
    schemas = len(openapi["components"]["schemas"])
    errors = len(openapi["components"]["schemas"]["CanonicalErrorCode"]["enum"])
    expected = openapi["info"]
    require(
        all(
            document.get("schema_version") == "UX001_D1_R1"
            for document in (catalog, bootstrap, matrix)
        ),
        "schema version mismatch",
    )
    require(
        expected["x-quantfoundry-contract-revision"] == "UX001_D1_R1",
        "unexpected contract revision",
    )
    require(
        operations == expected["x-quantfoundry-operation-count"] == 66,
        "operation count mismatch",
    )
    require(
        schemas == expected["x-quantfoundry-schema-count"] == 188,
        "schema count mismatch",
    )
    require(
        errors == expected["x-quantfoundry-error-count"] == 75, "error count mismatch"
    )
    require(
        "cookieSession" in openapi["components"]["securitySchemes"],
        "cookieSession is missing",
    )
    require(
        "bearerAuth" not in openapi["components"]["securitySchemes"],
        "bearerAuth must not be present",
    )

    require(catalog["status"] == "FROZEN", "catalog is not frozen")
    require(catalog["scope"] == "INSTALLATION", "catalog scope is invalid")
    keys = [entry["key"] for entry in catalog["entries"]]
    require(keys and len(keys) == len(set(keys)), "catalog keys are not unique")
    require(
        all(entry["scope"] == "INSTALLATION" for entry in catalog["entries"]),
        "catalog entry scope is invalid",
    )
    require(
        expected["x-quantfoundry-configuration-catalog-version"]
        == catalog["catalog_version"],
        "catalog version mismatch",
    )
    require(
        expected["x-quantfoundry-configuration-entry-count"] == len(keys) == 16,
        "catalog entry count mismatch",
    )

    require(
        bootstrap["status"] == "TARGET_SCHEMA_FROZEN", "bootstrap schema is not frozen"
    )
    require(
        bootstrap["authority"]["physical_source"].startswith("SQLAlchemy"),
        "bootstrap authority is invalid",
    )
    require(len(bootstrap["relations"]) == 11, "bootstrap relation count mismatch")
    require(
        bootstrap["domain_transition"]["target_status"] == "TARGET_TRANSITION_FROZEN",
        "domain transition is not frozen",
    )

    require(matrix["status"] == "FROZEN", "test matrix is not frozen")
    tools = registry.get("tools")
    require(isinstance(tools, list), "semantic tool registry is malformed")
    tool_identities = [(tool["name"], tool["version"]) for tool in tools]
    require(
        len(tool_identities) == len(set(tool_identities)),
        "semantic tool identities are not unique",
    )
    require(
        matrix["counts"]
        == {
            "operations": 66,
            "schemas": 188,
            "errors": 75,
            "semantic_tools": len(tools),
        },
        "test matrix counts mismatch",
    )
    require(len(tools) == 13, "semantic tool registry count mismatch")
    operation_ids = []
    for path, path_item in openapi["paths"].items():
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue
            require(
                isinstance(operation, dict), f"{method.upper()} {path} is not an object"
            )
            operation_id = operation.get("operationId")
            require(
                isinstance(operation_id, str) and operation_id.strip(),
                f"{method.upper()} {path} has no operationId",
            )
            operation_ids.append(operation_id)
    require(
        len(operation_ids) == len(set(operation_ids)), "operation IDs are not unique"
    )
    operation_ids = set(operation_ids)
    matrix_operation_id_list = [
        operation_id
        for family in matrix["families"]
        for operation_id in family.get("operations", [])
    ]
    require(
        len(matrix_operation_id_list) == len(set(matrix_operation_id_list)),
        "test matrix operation assignments are not unique",
    )
    matrix_operation_ids = set(matrix_operation_id_list)
    require(
        matrix_operation_ids == operation_ids,
        "test matrix operation coverage does not exactly match OpenAPI",
    )
    for tool in tools:
        try:
            Draft202012Validator.check_schema(tool["input_schema"])
            Draft202012Validator.check_schema(tool["output_schema"])
        except Exception as error:
            raise AssertionError(
                f"invalid semantic tool schema: {tool.get('name')}"
            ) from error
    print("OK: UX-001 D1 machine contract bundle is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
