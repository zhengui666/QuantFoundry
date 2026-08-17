"""Fail-closed checks for the UX-001 D1 machine contract bundle."""

from __future__ import annotations

from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = ROOT / "docs/后端系统技术方案/contracts"
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}


def load(name: str) -> dict:
    value = yaml.safe_load((CONTRACT_ROOT / name).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"{name} must contain an object")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    openapi = load("openapi-v1.yaml")
    catalog = load("configuration-catalog-v1.yaml")
    bootstrap = load("bootstrap-control-v1.yaml")
    matrix = load("ux001-d1-test-matrix.yaml")
    registry = load("tools/v1-p0.yaml")
    registry_errors = sorted(
        Draft202012Validator(registry).iter_errors(registry),
        key=lambda error: list(error.path),
    )
    require(
        not registry_errors,
        "semantic tool registry schema validation failed: "
        + "; ".join(error.message for error in registry_errors[:3]),
    )

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
    require(
        all(required_entry_fields <= set(entry) for entry in catalog["entries"]),
        "catalog entry fields are incomplete",
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
    tool_identities = {
        (tool.get("name"), tool.get("version"))
        for tool in tools
        if isinstance(tool, dict)
    }
    require(len(tools) == len(tool_identities), "semantic tool identities are not unique")
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
            require(isinstance(operation, dict), f"{method.upper()} {path} is not an object")
            operation_id = operation.get("operationId")
            require(
                isinstance(operation_id, str) and operation_id.strip(),
                f"{method.upper()} {path} has no operationId",
            )
            operation_ids.append(operation_id)
    require(len(operation_ids) == len(set(operation_ids)), "operation IDs are not unique")
    operation_ids = set(operation_ids)
    matrix_operation_ids = {
        operation_id
        for family in matrix["families"]
        for operation_id in family.get("operations", [])
    }
    require(
        matrix_operation_ids == operation_ids,
        "test matrix operation coverage does not exactly match OpenAPI",
    )
    print("OK: UX-001 D1 machine contract bundle is internally consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
