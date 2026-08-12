"""Semantic diff between model-generated runtime OpenAPI and canonical OpenAPI."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import yaml

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.main import app  # noqa: E402

ROOT = Path(__file__).parents[2]
canonical = yaml.safe_load(
    (ROOT / "docs/后端系统技术方案/contracts/openapi-v1.yaml").read_text()
)
runtime = app.openapi()


def resolve(document: dict[str, Any], value: dict[str, Any]) -> dict[str, Any]:
    if "$ref" not in value:
        return value
    current: Any = document
    for segment in value["$ref"].removeprefix("#/").split("/"):
        current = current[segment]
    return current


def normalized_schema(document: dict[str, Any], schema: Any) -> Any:
    """Normalize equivalent OpenAPI/Pydantic JSON-Schema representations."""

    if isinstance(schema, list):
        return [normalized_schema(document, item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    if "$ref" in schema:
        return normalized_schema(document, resolve(document, schema))
    result = deepcopy(schema)
    result.pop("title", None)
    result.pop("description", None)
    result.pop("examples", None)
    if result.get("default", object()) is None:
        result.pop("default", None)
    type_value = result.get("type")
    if isinstance(type_value, list):
        base = {key: value for key, value in result.items() if key != "type"}
        branches: list[Any] = []
        for branch_type in type_value:
            branch: dict[str, Any]
            if branch_type == "null":
                branch = {"type": "null"}
            else:
                branch = {**base, "type": branch_type}
                if isinstance(branch.get("enum"), list):
                    branch["enum"] = [
                        item for item in branch["enum"] if item is not None
                    ]
            branches.append(normalized_schema(document, branch))
        return {
            "union": sorted(branches, key=lambda item: json.dumps(item, sort_keys=True))
        }
    union: list[Any] = []
    for keyword in ("oneOf", "anyOf"):
        union.extend(result.pop(keyword, []))
    if union:
        result["union"] = sorted(
            [normalized_schema(document, branch) for branch in union],
            key=lambda item: json.dumps(item, sort_keys=True),
        )
        if result.get("type") == "string" and all(
            isinstance(branch, dict)
            and (
                branch.get("type") == "string"
                or (
                    "union" in branch
                    and all(
                        isinstance(nested, dict) and nested.get("type") == "string"
                        for nested in branch["union"]
                    )
                )
            )
            for branch in result["union"]
        ):
            result.pop("type")
    for key, value in list(result.items()):
        result[key] = normalized_schema(document, value)
    branches = result.get("allOf")
    if isinstance(branches, list) and all(
        isinstance(branch, dict)
        and not any(key in branch for key in ("if", "then", "else", "oneOf", "anyOf"))
        for branch in branches
    ):
        result.pop("allOf")
        properties = dict(result.pop("properties", {}))
        required = list(result.pop("required", []))
        for branch in branches:
            properties.update(branch.get("properties", {}))
            required.extend(branch.get("required", []))
            for key, item in branch.items():
                if key not in {"properties", "required"}:
                    result[key] = item
        if properties:
            result["properties"] = properties
        if required:
            result["required"] = sorted(set(required))
    if "union" in result:
        string_branches = [
            branch
            for branch in result["union"]
            if isinstance(branch, dict)
            and (
                branch.get("type") == "string" or isinstance(branch.get("union"), list)
            )
        ]

        def lower_bound(branch: dict[str, Any]) -> int:
            nested = branch.get("union")
            if isinstance(nested, list) and nested:
                return min(lower_bound(item) for item in nested)
            return int(branch.get("minLength", 0))

        def upper_bound(branch: dict[str, Any]) -> int | None:
            nested = branch.get("union")
            if isinstance(nested, list) and nested:
                values = [upper_bound(item) for item in nested]
                return (
                    None
                    if None in values
                    else max(cast(int, value) for value in values)
                )
            value = branch.get("maxLength")
            return int(value) if value is not None else None

        if len(string_branches) == len(result["union"]):
            minimum = result.get("minLength")
            if minimum is not None and all(
                lower_bound(branch) >= minimum for branch in string_branches
            ):
                result.pop("minLength")
            maximum = result.get("maxLength")
            upper_bounds = [upper_bound(branch) for branch in string_branches]
            if maximum is not None and all(
                bound is not None and bound <= maximum for bound in upper_bounds
            ):
                result.pop("maxLength")
        if set(result) == {"union"}:
            flattened: list[Any] = []
            for branch in result["union"]:
                if isinstance(branch, dict) and set(branch) == {"union"}:
                    flattened.extend(branch["union"])
                else:
                    flattened.append(branch)
            result["union"] = sorted(
                flattened, key=lambda item: json.dumps(item, sort_keys=True)
            )
    if result.get("items") == {}:
        result.pop("items")
    if "enum" in result:
        result["enum"] = sorted(result["enum"], key=str)
        result.pop("type", None)
    if "const" in result:
        result.pop("type", None)
    if "required" in result:
        result["required"] = sorted(result["required"])
    if result.get("format") in {"int32", "int64"}:
        result.pop("format")
    if (
        result.get("format") in {"uri", "uri-reference"}
        and result.get("minLength") == 1
    ):
        result.pop("minLength")
    return result


def normalized_parameters(
    document: dict[str, Any], operation: dict[str, Any]
) -> list[Any]:
    values = []
    for raw in operation.get("parameters", []):
        parameter = resolve(document, raw)
        schema = normalized_schema(document, parameter["schema"])
        if not parameter.get("required", False) and isinstance(schema, dict):
            non_null = [
                branch
                for branch in schema.get("union", [])
                if branch != {"type": "null"}
            ]
            if len(non_null) == 1:
                schema = non_null[0]
        values.append(
            (
                parameter["in"],
                parameter["name"].lower(),
                parameter.get("required", False),
                schema,
            )
        )
    return sorted(values, key=lambda value: (value[0], value[1]))


def normalized_security(value: Any) -> Any:
    if value is None:
        return None
    return [{key.lower(): scopes for key, scopes in item.items()} for item in value]


errors: list[str] = []
methods = {"get", "post", "put", "patch", "delete"}
canonical_operations = {
    (path, method): operation
    for path, path_item in canonical["paths"].items()
    for method, operation in path_item.items()
    if method in methods
}
runtime_operations = {
    (path, method): operation
    for path, path_item in runtime["paths"].items()
    for method, operation in path_item.items()
    if method in methods
}
if canonical_operations.keys() != runtime_operations.keys():
    errors.append("path/method set differs")

for key, expected in canonical_operations.items():
    actual = runtime_operations.get(key)
    if actual is None:
        continue
    label = f"{key[1].upper()} {key[0]}"
    if actual.get("operationId") != expected.get("operationId"):
        errors.append(f"{label}: operationId")
    if normalized_parameters(canonical, expected) != normalized_parameters(
        runtime, actual
    ):
        errors.append(f"{label}: parameters")
    expected_body = (
        expected.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    actual_body = (
        actual.get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("schema")
    )
    if expected_body != actual_body:
        errors.append(f"{label}: request body schema")
    if set(expected["responses"]) != set(actual["responses"]):
        errors.append(f"{label}: response statuses")
    for status, raw_expected_response in expected["responses"].items():
        expected_response = resolve(canonical, raw_expected_response)
        actual_response = actual["responses"].get(status, {})
        if set(expected_response.get("content", {})) != set(
            actual_response.get("content", {})
        ):
            errors.append(f"{label}: response {status} content types")
        if {name.lower() for name in expected_response.get("headers", {})} != {
            name.lower() for name in actual_response.get("headers", {})
        }:
            errors.append(f"{label}: response {status} headers")
        for media_type, expected_media in expected_response.get("content", {}).items():
            actual_media = actual_response.get("content", {}).get(media_type, {})
            if expected_media.get("schema") != actual_media.get("schema"):
                errors.append(f"{label}: response {status} {media_type} schema")
    expected_security = expected.get("security", canonical.get("security"))
    actual_security = actual.get("security", runtime.get("security"))
    if normalized_security(expected_security) != normalized_security(actual_security):
        errors.append(f"{label}: security")

canonical_schemas = canonical["components"]["schemas"]
runtime_schemas = runtime.get("components", {}).get("schemas", {})
for schema_name, canonical_schema in canonical_schemas.items():
    runtime_schema = runtime_schemas.get(schema_name)
    if runtime_schema is None or normalized_schema(
        canonical, canonical_schema
    ) != normalized_schema(runtime, runtime_schema):
        errors.append(f"component schema differs: {schema_name}")

expected_operation_count = canonical["info"]["x-quantfoundry-operation-count"]
expected_error_count = len(canonical_schemas["CanonicalErrorCode"]["enum"])
expected_schema_count = len(canonical_schemas)
if expected_operation_count != 45:
    errors.append("canonical operation metadata is not the approved 45")
if expected_error_count != 65:
    errors.append("canonical error count is not the approved 65")
if expected_schema_count != 162:
    errors.append("canonical schema count is not the approved 162")
if len(runtime_schemas) != expected_schema_count:
    errors.append("runtime schema count differs from canonical")
if len(runtime_schemas["CanonicalErrorCode"]["enum"]) != expected_error_count:
    errors.append("runtime canonical error count differs from canonical")
if len(runtime_operations) != expected_operation_count:
    errors.append("runtime operation count differs from canonical metadata")

if errors:
    raise SystemExit("Runtime semantic contract drift:\n- " + "\n- ".join(errors))
print(
    f"OK: {expected_operation_count} operations, {expected_error_count} errors, "
    f"{expected_schema_count} application-model schemas semantically match"
)
