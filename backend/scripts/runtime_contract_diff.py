"""Semantic diff between model-generated runtime OpenAPI and canonical OpenAPI."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import yaml

BACKEND_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(BACKEND_ROOT / "src"))
sys.path.insert(1, str(BACKEND_ROOT))

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
        isinstance(branch, dict) for branch in branches
    ):
        branch_property_sets = [
            set(branch.get("properties", {})) for branch in branches
        ]
        disjoint = sum(map(len, branch_property_sets)) == len(
            set().union(*branch_property_sets)
        )
        composition_only = all(
            set(branch) <= {"properties", "required"} for branch in branches
        )
        if disjoint and composition_only:
            result.pop("allOf")
            properties = dict(result.pop("properties", {}))
            required = list(result.pop("required", []))
            for branch in branches:
                properties.update(branch.get("properties", {}))
                required.extend(branch.get("required", []))
            if properties:
                result["properties"] = properties
            if required:
                result["required"] = sorted(set(required))
        else:
            result["allOf"] = sorted(
                branches, key=lambda item: json.dumps(item, sort_keys=True)
            )
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
    if isinstance(result.get("required"), list):
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
    document: dict[str, Any],
    operation: dict[str, Any],
    path_item: dict[str, Any] | None = None,
) -> list[Any]:
    values = []
    effective: dict[tuple[str, str], Any] = {}
    for raw in (path_item or {}).get("parameters", []):
        parameter = resolve(document, raw)
        effective[(parameter["name"], parameter["in"])] = parameter
    for raw in operation.get("parameters", []):
        parameter = resolve(document, raw)
        effective[(parameter["name"], parameter["in"])] = parameter
    for parameter in effective.values():
        location = parameter["in"]
        schema = normalized_schema(document, parameter.get("schema"))
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
                location,
                parameter["name"].lower()
                if location == "header"
                else parameter["name"],
                parameter.get("required", False),
                parameter.get(
                    "style", "simple" if location in {"path", "header"} else "form"
                ),
                parameter.get(
                    "explode",
                    parameter.get(
                        "style", "simple" if location in {"path", "header"} else "form"
                    )
                    == "form",
                ),
                parameter.get("allowReserved", False),
                parameter.get("allowEmptyValue", False),
                schema,
                tuple(
                    sorted(
                        (
                            media_type,
                            normalized_schema(document, media.get("schema")),
                        )
                        for media_type, media in parameter.get("content", {}).items()
                    )
                ),
            )
        )
    return sorted(values, key=lambda value: (value[0], value[1]))


def normalized_security(value: Any) -> Any:
    if value is None:
        return None
    return [{key.lower(): scopes for key, scopes in item.items()} for item in value]


errors: list[str] = []
methods = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
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
    if normalized_parameters(
        canonical, expected, canonical["paths"][key[0]]
    ) != normalized_parameters(runtime, actual, runtime["paths"][key[0]]):
        errors.append(f"{label}: parameters")
    expected_request = resolve(canonical, expected.get("requestBody", {}))
    actual_request = resolve(runtime, actual.get("requestBody", {}))
    if expected_request.get("required", False) != actual_request.get("required", False):
        errors.append(f"{label}: request body required")
    expected_content = expected_request.get("content", {})
    actual_content = actual_request.get("content", {})
    if set(expected_content) != set(actual_content):
        errors.append(f"{label}: request body content types")
    for media_type, expected_media in expected_content.items():
        actual_media = actual_content.get(media_type, {})
        if normalized_schema(
            canonical, expected_media.get("schema")
        ) != normalized_schema(runtime, actual_media.get("schema")):
            errors.append(f"{label}: request body {media_type} schema")
    if set(expected["responses"]) != set(actual["responses"]):
        errors.append(f"{label}: response statuses")
    for status, raw_expected_response in expected["responses"].items():
        expected_response = resolve(canonical, raw_expected_response)
        actual_response = actual["responses"].get(status, {})
        if set(expected_response.get("content", {})) != set(
            actual_response.get("content", {})
        ):
            errors.append(f"{label}: response {status} content types")
        expected_headers = {
            name.lower(): normalized_schema(canonical, resolve(canonical, header))
            for name, header in expected_response.get("headers", {}).items()
        }
        actual_headers = {
            name.lower(): normalized_schema(runtime, resolve(runtime, header))
            for name, header in actual_response.get("headers", {}).items()
        }
        if expected_headers != actual_headers:
            errors.append(f"{label}: response {status} headers")
        for media_type, expected_media in expected_response.get("content", {}).items():
            actual_media = actual_response.get("content", {}).get(media_type, {})
            if normalized_schema(
                canonical, expected_media.get("schema")
            ) != normalized_schema(runtime, actual_media.get("schema")):
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
expected_error_count = canonical["info"]["x-quantfoundry-error-count"]
expected_schema_count = canonical["info"]["x-quantfoundry-schema-count"]
if expected_operation_count != len(canonical_operations):
    errors.append("canonical operation metadata differs from canonical paths")
canonical_error_schema = canonical_schemas.get("CanonicalErrorCode")
canonical_error_enum = (
    canonical_error_schema.get("enum")
    if isinstance(canonical_error_schema, dict)
    else None
)
if not isinstance(canonical_error_enum, list):
    errors.append("canonical error enum is missing or malformed")
elif expected_error_count != len(canonical_error_enum):
    errors.append("canonical error metadata differs from canonical enum")
if expected_schema_count != len(canonical_schemas):
    errors.append("canonical schema metadata differs from canonical components")
if len(runtime_schemas) != expected_schema_count:
    errors.append("runtime schema count differs from canonical")
runtime_error_schema = runtime_schemas.get("CanonicalErrorCode")
runtime_error_enum = (
    runtime_error_schema.get("enum") if isinstance(runtime_error_schema, dict) else None
)
if (
    not isinstance(runtime_error_enum, list)
    or len(runtime_error_enum) != expected_error_count
):
    errors.append("runtime canonical error count differs from canonical")
if len(runtime_operations) != expected_operation_count:
    errors.append("runtime operation count differs from canonical metadata")

if errors:
    raise SystemExit("Runtime semantic contract drift:\n- " + "\n- ".join(errors))
print(
    f"OK: {expected_operation_count} operations, {expected_error_count} errors, "
    f"{expected_schema_count} application-model schemas semantically match"
)
