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
    for raw_segment in value["$ref"].removeprefix("#/").split("/"):
        segment = raw_segment.replace("~1", "/").replace("~0", "~")
        current = current[segment]
    return current


def normalized_fragment(document: dict[str, Any], value: Any) -> Any:
    if isinstance(value, dict) and "$ref" in value:
        target = resolve(document, value)
        siblings = {key: item for key, item in value.items() if key != "$ref"}
        value = {**target, **siblings}
    if isinstance(value, dict):
        return {
            key: normalized_fragment(document, item)
            for key, item in sorted(value.items())
        }
    if isinstance(value, list):
        return [normalized_fragment(document, item) for item in value]
    return value


def normalized_schema(
    document: dict[str, Any], schema: Any, active_refs: frozenset[str] = frozenset()
) -> Any:
    """Normalize equivalent OpenAPI/Pydantic JSON-Schema representations."""

    if isinstance(schema, list):
        return [normalized_schema(document, item, active_refs) for item in schema]
    if not isinstance(schema, dict):
        return schema
    if "$ref" in schema:
        reference = str(schema["$ref"])
        if reference in active_refs:
            return {"$recursive_ref": reference}
        target = resolve(document, schema)
        siblings = {key: value for key, value in schema.items() if key != "$ref"}
        if siblings:
            return normalized_schema(
                document,
                {"allOf": [target, siblings]},
                active_refs | {reference},
            )
        return normalized_schema(document, target, active_refs | {reference})
    result = deepcopy(schema)
    result.pop("title", None)
    result.pop("description", None)
    result.pop("examples", None)
    type_value = result.get("type")
    if isinstance(type_value, list):
        type_specific_keywords = {
            "string": {"minLength", "maxLength", "pattern", "format"},
            "number": {
                "multipleOf",
                "maximum",
                "exclusiveMaximum",
                "minimum",
                "exclusiveMinimum",
            },
            "integer": {
                "multipleOf",
                "maximum",
                "exclusiveMaximum",
                "minimum",
                "exclusiveMinimum",
            },
            "array": {
                "prefixItems",
                "items",
                "contains",
                "minContains",
                "maxContains",
                "uniqueItems",
                "minItems",
                "maxItems",
            },
            "object": {
                "maxProperties",
                "minProperties",
                "required",
                "properties",
                "patternProperties",
                "additionalProperties",
                "propertyNames",
                "dependentRequired",
                "dependentSchemas",
            },
        }
        base = {key: value for key, value in result.items() if key != "type"}
        branches: list[Any] = []
        for branch_type in type_value:
            const_value = base.get("const")
            if "const" in base:
                if const_value is None:
                    compatible_types = {"null"}
                elif isinstance(const_value, bool):
                    compatible_types = {"boolean"}
                elif isinstance(const_value, (int, float)):
                    compatible_types = {"number"}
                    if isinstance(const_value, int) or const_value.is_integer():
                        compatible_types.add("integer")
                elif isinstance(const_value, str):
                    compatible_types = {"string"}
                elif isinstance(const_value, list):
                    compatible_types = {"array"}
                else:
                    compatible_types = {"object"}
                if branch_type not in compatible_types:
                    continue
            branch: dict[str, Any]
            branch = {
                key: value
                for key, value in base.items()
                if key
                not in {
                    keyword
                    for supported_type, keywords in type_specific_keywords.items()
                    if supported_type != branch_type
                    and not {supported_type, branch_type} <= {"number", "integer"}
                    for keyword in keywords
                }
            }
            if branch_type == "null":
                if base.get("const") is not None or (
                    isinstance(base.get("enum"), list) and None not in base["enum"]
                ):
                    continue
                branch["type"] = "null"
                if isinstance(branch.get("enum"), list):
                    branch["enum"] = [None]
            else:
                branch["type"] = branch_type
                if isinstance(branch.get("enum"), list):
                    branch["enum"] = [
                        item for item in branch["enum"] if item is not None
                    ]
            branches.append(normalized_schema(document, branch, active_refs))
        return {
            "union": sorted(branches, key=lambda item: json.dumps(item, sort_keys=True))
        }
    any_of = result.pop("anyOf", None)
    one_of = result.pop("oneOf", None)
    if any_of is not None:
        result["union"] = sorted(
            [normalized_schema(document, branch, active_refs) for branch in any_of],
            key=lambda item: json.dumps(item, sort_keys=True),
        )
    if one_of is not None:
        result["exclusive_union"] = sorted(
            [normalized_schema(document, branch, active_refs) for branch in one_of],
            key=lambda item: json.dumps(item, sort_keys=True),
        )
    if "union" in result:
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
    if (
        "exclusive_union" in result
        and result.get("type") == "string"
        and all(
            isinstance(branch, dict) and branch.get("type") == "string"
            for branch in result["exclusive_union"]
        )
    ):
        result.pop("type")
    for key, value in list(result.items()):
        if key in {"properties", "patternProperties", "dependentSchemas"} and isinstance(
            value, dict
        ):
            result[key] = {
                name: normalized_schema(document, child, active_refs)
                for name, child in sorted(value.items())
            }
        else:
            result[key] = normalized_schema(document, value, active_refs)
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
        outer_properties = set(result.get("properties", {}))
        if (
            disjoint
            and not outer_properties.intersection(set().union(*branch_property_sets))
            and composition_only
            and "additionalProperties" not in result
        ):
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
                values = [
                    lower_bound(item) for item in nested if isinstance(item, dict)
                ]
                return min(values) if values else 0
            return int(branch.get("minLength", 0)) if isinstance(branch, dict) else 0

        def upper_bound(branch: dict[str, Any]) -> int | None:
            nested = branch.get("union")
            if isinstance(nested, list) and nested:
                values = [
                    upper_bound(item) for item in nested if isinstance(item, dict)
                ]
                return (
                    None
                    if None in values
                    else max(cast(int, value) for value in values)
                )
            if not isinstance(branch, dict):
                return None
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
    if isinstance(result.get("required"), list):
        result["required"] = sorted(result["required"])
    if result.get("format") == "uri" and result.get("minLength") == 1:
        result.pop("minLength")
    return result


def strict_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            strict_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(
            strict_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return left == right


def normalized_header(document: dict[str, Any], value: Any) -> Any:
    if not isinstance(value, dict):
        return normalized_fragment(document, value)
    value = resolve(document, value)
    return {
        key: normalized_schema(document, item)
        if key == "schema"
        else {
            media_type: {
                **{
                    field: normalized_fragment(document, field_value)
                    for field, field_value in media.items()
                    if field != "schema"
                },
                **(
                    {"schema": normalized_schema(document, media.get("schema"))}
                    if "schema" in media
                    else {}
                ),
            }
            for media_type, media in item.items()
        }
        if key == "content" and isinstance(item, dict)
        else normalized_fragment(document, item)
        for key, item in sorted(value.items())
    }


def effective_servers(
    document: dict[str, Any], path_item: dict[str, Any], operation: dict[str, Any]
) -> Any:
    if "servers" in operation:
        return operation["servers"]
    if "servers" in path_item:
        return path_item["servers"]
    return document.get("servers", [])


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
                parameter.get("deprecated", False),
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
    return sorted(
        [{key: sorted(scopes) for key, scopes in item.items()} for item in value],
        key=lambda item: json.dumps(item, sort_keys=True),
    )


def normalized_encoding(media: dict[str, Any]) -> str:
    return json.dumps(media.get("encoding", {}), sort_keys=True, separators=(",", ":"))


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
    if not strict_equal(
        normalized_parameters(canonical, expected, canonical["paths"][key[0]]),
        normalized_parameters(runtime, actual, runtime["paths"][key[0]]),
    ):
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
        if not strict_equal(
            normalized_schema(canonical, expected_media.get("schema")),
            normalized_schema(runtime, actual_media.get("schema")),
        ):
            errors.append(f"{label}: request body {media_type} schema")
        if normalized_encoding(expected_media) != normalized_encoding(actual_media):
            errors.append(f"{label}: request body {media_type} encoding")
    if set(expected["responses"]) != set(actual["responses"]):
        errors.append(f"{label}: response statuses")
    for status, raw_expected_response in expected["responses"].items():
        expected_response = resolve(canonical, raw_expected_response)
        actual_response = resolve(runtime, actual["responses"].get(status, {}))
        if set(expected_response.get("content", {})) != set(
            actual_response.get("content", {})
        ):
            errors.append(f"{label}: response {status} content types")
        expected_headers = {
            name.lower(): normalized_header(canonical, header)
            for name, header in expected_response.get("headers", {}).items()
        }
        actual_headers = {
            name.lower(): normalized_header(runtime, header)
            for name, header in actual_response.get("headers", {}).items()
        }
        if expected_headers != actual_headers:
            errors.append(f"{label}: response {status} headers")
        for media_type, expected_media in expected_response.get("content", {}).items():
            actual_media = actual_response.get("content", {}).get(media_type, {})
            if not strict_equal(
                normalized_schema(canonical, expected_media.get("schema")),
                normalized_schema(runtime, actual_media.get("schema")),
            ):
                errors.append(f"{label}: response {status} {media_type} schema")
            if normalized_encoding(expected_media) != normalized_encoding(actual_media):
                errors.append(f"{label}: response {status} {media_type} encoding")
        if not strict_equal(
            normalized_fragment(canonical, expected_response.get("links", {})),
            normalized_fragment(runtime, actual_response.get("links", {})),
        ):
            errors.append(f"{label}: response {status} links")
    if expected.get("deprecated", False) != actual.get("deprecated", False):
        errors.append(f"{label}: deprecated")
    if not strict_equal(
        normalized_fragment(
            canonical,
            effective_servers(canonical, canonical["paths"][key[0]], expected),
        ),
        normalized_fragment(
            runtime, effective_servers(runtime, runtime["paths"][key[0]], actual)
        ),
    ):
        errors.append(f"{label}: servers")
    if not strict_equal(
        normalized_fragment(canonical, expected.get("callbacks", {})),
        normalized_fragment(runtime, actual.get("callbacks", {})),
    ):
        errors.append(f"{label}: callbacks")
    expected_security = expected.get("security", canonical.get("security"))
    actual_security = actual.get("security", runtime.get("security"))
    if not strict_equal(
        normalized_security(expected_security), normalized_security(actual_security)
    ):
        errors.append(f"{label}: security")

canonical_schemas = canonical["components"]["schemas"]
runtime_schemas = runtime.get("components", {}).get("schemas", {})
for schema_name, canonical_schema in canonical_schemas.items():
    runtime_schema = runtime_schemas.get(schema_name)
    if runtime_schema is None or not strict_equal(
        normalized_schema(canonical, canonical_schema),
        normalized_schema(runtime, runtime_schema),
    ):
        errors.append(f"component schema differs: {schema_name}")

expected_operation_count = canonical["info"]["x-quantfoundry-operation-count"]
expected_error_count = canonical["info"]["x-quantfoundry-error-count"]
expected_schema_count = canonical["info"]["x-quantfoundry-schema-count"]
if expected_operation_count != len(canonical_operations):
    errors.append("canonical operation metadata differs from canonical paths")
canonical_security_schemes = canonical.get("components", {}).get("securitySchemes", {})
runtime_security_schemes = runtime.get("components", {}).get("securitySchemes", {})
if not strict_equal(
    normalized_schema(canonical, canonical_security_schemes),
    normalized_schema(runtime, runtime_security_schemes),
):
    errors.append("security schemes differ")
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
