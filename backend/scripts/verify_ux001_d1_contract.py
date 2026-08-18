"""Fail-closed checks for the UX-001 D1 machine contract bundle."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from fastapi.openapi.models import OpenAPI
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_ROOT = ROOT / "docs/后端系统技术方案/contracts"
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options", "trace"}
EXPECTED_BOOTSTRAP_RELATIONS = {
    "bootstrap_state",
    "general_access_keys",
    "owner_sessions",
    "configuration_catalog",
    "configuration_revisions",
    "configuration_values",
    "active_configuration",
    "configuration_consumer_states",
    "domain_database_connection_revisions",
    "bootstrap_audit_events",
    "control_idempotency_records",
}
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


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_unique_mapping(loader: yaml.SafeLoader, node: yaml.MappingNode, deep: bool = False) -> dict:
    loader.flatten_mapping(node)
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        require(key not in mapping, f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def load(name: str) -> dict:
    value = yaml.load(
        (CONTRACT_ROOT / name).read_text(encoding="utf-8"),
        Loader=_UniqueKeyLoader,
    )
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


def _resolved_path_item(
    document: dict[str, Any], path: str, value: dict[str, Any]
) -> dict[str, Any]:
    reference = value.get("$ref")
    if not isinstance(reference, str):
        return value
    target = _resolve_local(document, reference, f"{path}.$ref")
    require(isinstance(target, dict), f"{path}: referenced path item is malformed")
    return {**target, **{key: child for key, child in value.items() if key != "$ref"}}


def validate_openapi_document(document: dict[str, Any]) -> None:
    try:
        OpenAPI.model_validate(document)
    except Exception as error:
        raise AssertionError("OpenAPI structural validation failed") from error
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
    security_schemes = document["components"].get("securitySchemes")
    require(
        isinstance(security_schemes, dict)
        and set(security_schemes) == {"cookieSession", "csrfHeader"}
        and security_schemes["cookieSession"].get("type") == "apiKey"
        and security_schemes["cookieSession"].get("in") == "cookie"
        and security_schemes["csrfHeader"].get("type") == "apiKey"
        and security_schemes["csrfHeader"].get("in") == "header",
        "OpenAPI security schemes are not the closed session contract",
    )
    require(document.get("security") == [{"cookieSession": []}], "global OpenAPI security is invalid")
    security_rules = document.get("x-quantfoundry-security-rules")
    require(
        security_rules == {
            "public-operations": ["/system/health", "/auth/login"],
            "protected-read": ["cookieSession"],
            "protected-mutation": ["cookieSession", "csrfHeader"],
            "protected-mutation-origin": "REQUIRED",
            "protected-mutation-fetch-metadata": "REQUIRED",
        },
        "OpenAPI security rules are incomplete",
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
    for path, raw_path_item in document["paths"].items():
        require(path.startswith("/"), f"OpenAPI path is invalid: {path}")
        require(isinstance(raw_path_item, dict), f"OpenAPI path item is invalid: {path}")
        path_item = _resolved_path_item(document, path, raw_path_item)
        require(
            set(path_item) <= {"$ref", "summary", "description", "servers", "parameters", *HTTP_METHODS},
            f"{path}: unknown path-item fields",
        )
        if "parameters" in path_item:
            require(isinstance(path_item["parameters"], list), f"{path}: parameters must be a list")
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
            known_operation_fields = {
                "tags",
                "summary",
                "description",
                "externalDocs",
                "operationId",
                "parameters",
                "requestBody",
                "responses",
                "callbacks",
                "deprecated",
                "security",
                "servers",
            }
            require(
                all(key in known_operation_fields or key.startswith("x-") for key in operation),
                f"{method.upper()} {path} has unknown operation fields",
            )
            template_names = set(re.findall(r"\{([^{}]+)\}", path))
            all_parameters = [*path_item.get("parameters", []), *operation.get("parameters", [])]
            resolved_parameters = []
            for parameter in all_parameters:
                resolved_parameter = (
                    _resolve_local(
                        document, parameter["$ref"], f"{method.upper()} {path} parameter"
                    )
                    if isinstance(parameter, dict) and "$ref" in parameter
                    else parameter
                )
                resolved_parameters.append(resolved_parameter)
            path_parameters = [
                parameter
                for parameter in resolved_parameters
                if isinstance(parameter, dict) and parameter.get("in") == "path"
            ]
            require(
                len({(p.get("name"), p.get("in")) for p in resolved_parameters})
                == len(resolved_parameters),
                f"{method.upper()} {path} has duplicate parameters",
            )
            require(
                {parameter.get("name") for parameter in path_parameters} == template_names
                and all(parameter.get("required") is True for parameter in path_parameters),
                f"{method.upper()} {path} path parameters do not match the URI template",
            )
            if "requestBody" in operation:
                request_body = operation["requestBody"]
                if isinstance(request_body, dict) and "$ref" in request_body:
                    request_body = _resolve_local(document, request_body["$ref"], f"{method.upper()} {path} requestBody")
                require(
                    isinstance(request_body, dict)
                    and isinstance(request_body.get("content"), dict)
                    and bool(request_body["content"]),
                    f"{method.upper()} {path} requestBody content is invalid",
                )
                for media_type, media in request_body["content"].items():
                    require(
                        isinstance(media, dict)
                        and any(key in media for key in ("schema", "example", "examples")),
                        f"{method.upper()} {path} requestBody media type {media_type} is incomplete",
                    )
            for response_code, response in operation["responses"].items():
                require(
                    isinstance(response, dict),
                    f"{method.upper()} {path} {response_code} is not an object",
                )
                resolved_response = (
                    _resolve_local(
                        document,
                        response["$ref"],
                        f"{method.upper()} {path} {response_code}",
                    )
                    if "$ref" in response
                    else response
                )
                require(
                    isinstance(resolved_response, dict)
                    and isinstance(resolved_response.get("description"), str),
                    f"{method.upper()} {path} {response_code} is not a valid response",
                )
                if "content" in resolved_response:
                    require(
                        isinstance(resolved_response["content"], dict)
                        and bool(resolved_response["content"]),
                        f"{method.upper()} {path} {response_code} content is invalid",
                    )
                    for media_type, media in resolved_response["content"].items():
                        require(
                            isinstance(media, dict)
                            and any(key in media for key in ("schema", "example", "examples")),
                            f"{method.upper()} {path} response media type {media_type} is incomplete",
                        )
            parameters = operation.get("parameters", [])
            require(
                isinstance(parameters, list),
                f"{method.upper()} {path}: parameters must be a list",
            )
            for parameter in [*path_item.get("parameters", []), *parameters]:
                resolved_parameter = (
                    _resolve_local(
                        document, parameter["$ref"], f"{method.upper()} {path} parameter"
                    )
                    if isinstance(parameter, dict) and "$ref" in parameter
                    else parameter
                )
                require(
                    isinstance(resolved_parameter, dict)
                    and isinstance(resolved_parameter.get("name"), str)
                    and resolved_parameter.get("in") in {"query", "header", "path", "cookie"}
                    and ("schema" in resolved_parameter) != ("content" in resolved_parameter),
                    f"{method.upper()} {path} has an invalid parameter",
                )
            expected_security = (
                []
                if path in {"/system/health", "/auth/login"}
                else [{"cookieSession": [], "csrfHeader": []}]
                if method in {"post", "put", "patch", "delete"}
                else [{"cookieSession": []}]
            )
            require(
                operation.get("security", document["security"]) == expected_security,
                f"{method.upper()} {path} has an invalid security requirement",
            )


def validate_configuration_catalog(catalog: dict[str, Any]) -> None:
    require(
        set(catalog)
        == {"schema_version", "catalog_version", "status", "authority", "scope", "description", "entries"},
        "configuration catalog top-level fields are not closed",
    )
    require(catalog["schema_version"] == "UX001_D1_R1", "catalog schema version is invalid")
    require(isinstance(catalog["authority"], str) and catalog["authority"], "catalog authority is invalid")
    require(isinstance(catalog["description"], str) and catalog["description"], "catalog description is invalid")
    allowed_entry_fields = {
        "key", "group", "schema_version", "scope", "sensitivity", "apply_mode",
        "consumers", "dependencies", "schema", "validator", "safe_range",
    }
    allowed_modes = {"LIVE_NEW_WORK", "DRAIN_RELOAD", "RESTART_REQUIRED", "SECURITY_IMMEDIATE"}
    entries = catalog["entries"]
    require(isinstance(entries, list) and entries, "catalog entries are malformed")
    keys = {entry.get("key") for entry in entries if isinstance(entry, dict)}
    for entry in entries:
        require(isinstance(entry, dict) and set(entry) == allowed_entry_fields, "catalog entry fields are not closed")
        require(isinstance(entry["key"], str) and re.fullmatch(r"[a-z][a-z0-9]*(\.[a-z0-9_-]+)+", entry["key"]), "catalog key is invalid")
        require(entry["schema_version"] == 1 and entry["scope"] == "INSTALLATION", f"catalog entry {entry['key']} metadata is invalid")
        require(entry["sensitivity"] in {"PUBLIC", "MASKED", "SECRET"} and entry["apply_mode"] in allowed_modes, f"catalog entry {entry['key']} enum is invalid")
        require(isinstance(entry["group"], str) and entry["group"], f"catalog entry {entry['key']} group is invalid")
        require(isinstance(entry["consumers"], list) and len(entry["consumers"]) == len(set(entry["consumers"])), f"catalog entry {entry['key']} consumers are invalid")
        require(all(isinstance(value, str) and value for value in entry["consumers"]), f"catalog entry {entry['key']} consumers are invalid")
        require(isinstance(entry["dependencies"], list) and len(entry["dependencies"]) == len(set(entry["dependencies"])), f"catalog entry {entry['key']} dependencies are invalid")
        require(all(isinstance(value, str) and value in keys for value in entry["dependencies"]), f"catalog entry {entry['key']} has an unknown dependency")
        require(isinstance(entry["validator"], str) and entry["validator"], f"catalog entry {entry['key']} validator is invalid")
        require(isinstance(entry["safe_range"], dict), f"catalog entry {entry['key']} safe_range is invalid")
        try:
            Draft202012Validator.check_schema(entry["schema"])
        except Exception as error:
            raise AssertionError(f"invalid configuration schema: {entry['key']}") from error
    edges = {entry["key"]: entry["dependencies"] for entry in entries}
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(key: str) -> None:
        require(key not in visiting, f"catalog dependency cycle at {key}")
        if key in visited:
            return
        visiting.add(key)
        for dependency in edges[key]:
            visit(dependency)
        visiting.remove(key)
        visited.add(key)
    for key in edges:
        visit(key)


def validate_bootstrap_schema(bootstrap: dict[str, Any]) -> None:
    require(
        set(bootstrap)
        == {"schema_version", "status", "authority", "storage", "field_types", "relations", "indexes", "domain_transition"},
        "bootstrap schema top-level fields are not closed",
    )
    require(bootstrap["schema_version"] == "UX001_D1_R1", "bootstrap schema version is invalid")
    require(
        set(bootstrap["authority"])
        == {"logical_source", "physical_source", "generated_outputs", "plaintext_secret_storage", "file_env_cli_fallback", "root_of_trust"},
        "bootstrap authority fields are incomplete",
    )
    require(isinstance(bootstrap["authority"]["generated_outputs"], list), "bootstrap generated outputs are invalid")
    require(set(bootstrap["storage"]) == {"control_db", "domain_db", "dual_write_or_fallback"}, "bootstrap storage fields are incomplete")
    require(set(bootstrap["storage"]["control_db"]) == {"product_role", "domain_outage_behavior"}, "control DB storage contract is incomplete")
    require(set(bootstrap["storage"]["domain_db"]) == {"product_role", "connection_authority"}, "domain DB storage contract is incomplete")
    require(set(bootstrap["field_types"]) == {"id", "revision", "timestamp", "json", "hash", "ciphertext"}, "bootstrap field type catalog is incomplete")
    relations = bootstrap["relations"]
    require(isinstance(relations, dict), "bootstrap relations are malformed")
    allowed_field_fields = {"type", "const", "values", "min", "min_length", "max_length", "pattern", "nullable", "references", "sensitivity"}
    allowed_types = {"text", "int64", "revision", "timestamp", "enum", "json", "bytes", "hash", "ciphertext"}
    for relation_name, relation in relations.items():
        require(isinstance(relation, dict), f"bootstrap relation {relation_name} is malformed")
        require(set(relation) <= {"cardinality", "primary_key", "unique_key", "fields", "checks", "indexes"}, f"bootstrap relation {relation_name} has unknown fields")
        fields = relation.get("fields")
        require(isinstance(fields, dict) and fields, f"bootstrap relation {relation_name} fields are malformed")
        for field_name, field in fields.items():
            require(isinstance(field, dict) and set(field) <= allowed_field_fields, f"bootstrap field {relation_name}.{field_name} has unknown fields")
            require(field.get("type") in allowed_types and isinstance(field.get("nullable"), bool), f"bootstrap field {relation_name}.{field_name} is malformed")
            if "values" in field:
                require(field["type"] == "enum" and isinstance(field["values"], list) and field["values"], f"bootstrap enum {relation_name}.{field_name} is malformed")
            if "references" in field:
                target_relation, separator, target_field = field["references"].partition(".")
                require(separator and target_relation in relations and target_field in relations[target_relation]["fields"], f"bootstrap reference {relation_name}.{field_name} is invalid")
        for key_name in ("primary_key", "unique_key"):
            if key_name in relation:
                require(isinstance(relation[key_name], list) and relation[key_name] and all(value in fields for value in relation[key_name]), f"bootstrap {relation_name} {key_name} is invalid")
        require(isinstance(relation.get("checks"), list) and all(isinstance(value, str) and value for value in relation["checks"]), f"bootstrap relation {relation_name} checks are invalid")
        if "indexes" in relation:
            require(isinstance(relation["indexes"], list) and all(isinstance(value, str) and value in fields for value in relation["indexes"]), f"bootstrap relation {relation_name} indexes are invalid")
    for index in bootstrap["indexes"]:
        require(isinstance(index, dict) and set(index) == {"relation", "columns"} and index["relation"] in relations, "bootstrap index is malformed")
        require(isinstance(index["columns"], list) and index["columns"] and all(value in relations[index["relation"]]["fields"] for value in index["columns"]), "bootstrap index columns are invalid")


def main() -> int:
    openapi = load("openapi-v1.yaml")
    catalog = load("configuration-catalog-v1.yaml")
    bootstrap = load("bootstrap-control-v1.yaml")
    matrix = load("ux001-d1-test-matrix.yaml")
    registry = load("tools/v1-p0.yaml")
    validate_openapi_document(openapi)
    validate_configuration_catalog(catalog)
    validate_bootstrap_schema(bootstrap)
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
        for path, raw_path_item in openapi["paths"].items()
        for method in _resolved_path_item(openapi, path, raw_path_item)
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
    relations = bootstrap.get("relations")
    require(
        isinstance(relations, dict)
        and set(relations) == EXPECTED_BOOTSTRAP_RELATIONS,
        "bootstrap relation set mismatch",
    )
    for relation_name, relation in relations.items():
        require(
            isinstance(relation, dict)
            and relation.get("cardinality") in {"exactly_one", "many"}
            and isinstance(relation.get("primary_key"), list)
            and relation["primary_key"]
            and isinstance(relation.get("fields"), dict)
            and isinstance(relation.get("checks"), list)
            and all(isinstance(check, str) and check for check in relation["checks"]),
            f"bootstrap relation {relation_name} is malformed",
        )
        fields = relation["fields"]
        for field_name, field in fields.items():
            require(
                isinstance(field, dict)
                and isinstance(field.get("type"), str)
                and isinstance(field.get("nullable"), bool),
                f"bootstrap field {relation_name}.{field_name} is malformed",
            )
        require(
            all(field_name in fields for field_name in relation["primary_key"]),
            f"bootstrap relation {relation_name} primary key is not declared",
        )
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
    for path, raw_path_item in openapi["paths"].items():
        path_item = _resolved_path_item(openapi, path, raw_path_item)
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
