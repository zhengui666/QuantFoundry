"""Closed 21-branch object-locator validation shared by API and storage."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from pydantic import ValidationError

from quantfoundry.contracts.openapi.generated_api_models import (
    EventPayload,
    JobResultRef,
    NextAction,
)
from quantfoundry.domain.value_objects.public_ids import PUBLIC_ID_PATTERNS

LOCATOR_FIELDS = ("object_type", "object_id", "object_version", "object_revision")
JOB_RESULT_REF_FIELDS = frozenset((*LOCATOR_FIELDS, "artifact_id"))
NEXT_ACTION_FIELDS = frozenset(("action", *LOCATOR_FIELDS))

LOCATOR_CHECK_SQL = (
    "qf_event_locator_quartet_valid("
    "object_type, object_id, object_version, object_revision, {allow_null})"
)
JOB_RESULT_REF_CHECK_SQL = """result_ref IS NULL OR (
jsonb_typeof(result_ref) = 'object'
AND result_ref ?& ARRAY['object_type','object_id','object_version','object_revision','artifact_id']
AND result_ref - ARRAY['object_type','object_id','object_version','object_revision','artifact_id'] = '{}'::jsonb
AND qf_event_locator_json_valid(result_ref, true)
AND qf_nullable_public_id_json_valid(result_ref->'artifact_id', 'ART')
)"""
NEXT_ACTION_CHECK_SQL = """next_action IS NULL OR (
jsonb_typeof(next_action) = 'object'
AND next_action ?& ARRAY['action','object_type','object_id','object_version','object_revision']
AND next_action - ARRAY['action','object_type','object_id','object_version','object_revision'] = '{}'::jsonb
AND jsonb_typeof(next_action->'action') = 'string'
AND qf_event_locator_json_valid(next_action, true)
)"""

_ORDINARY_LOCATORS = {
    "job": "job",
    "research": "research",
    "conclusion": "conclusion",
    "experiment": "experiment",
    "factor": "factor",
    "validation": "validation",
    "approval": "approval",
    "paper": "paper",
    "paper_run": "paper_run",
    "review": "performance_review",
    "capability": "capability",
    "snapshot": "snapshot",
    "agent_run": "agent_run",
    "tool_call": "tool_call",
    "memo": "memo",
    "notification": "notification",
}
_AGENT_ROLES = (
    "RESEARCH_DIRECTOR",
    "FACTOR_SCIENTIST",
    "STRATEGY_SCIENTIST",
    "PORTFOLIO_ANALYST",
    "RED_TEAM_RESEARCHER",
    "PERFORMANCE_ANALYST",
)


def _postgres_locator_function_sql() -> str:
    ordinary = "\n".join(
        "        WHEN object_type_value = "
        f"'{object_type}' THEN object_id_value ~ "
        f"'{PUBLIC_ID_PATTERNS[kind]}' AND "
        "(object_version_value IS NULL OR object_version_value >= 1) AND "
        "(object_revision_value IS NULL OR object_revision_value >= 1)"
        for object_type, kind in _ORDINARY_LOCATORS.items()
    )
    roles = ", ".join(f"'{role}'" for role in _AGENT_ROLES)
    return f"""
CREATE OR REPLACE FUNCTION qf_event_locator_quartet_valid(
    object_type_value text,
    object_id_value text,
    object_version_value integer,
    object_revision_value bigint,
    allow_null boolean
) RETURNS boolean
LANGUAGE plpgsql IMMUTABLE
AS $qf$
BEGIN
    IF object_type_value IS NULL AND object_id_value IS NULL
       AND object_version_value IS NULL AND object_revision_value IS NULL THEN
        RETURN COALESCE(allow_null, false);
    END IF;
    IF object_type_value IS NULL OR object_id_value IS NULL THEN
        RETURN false;
    END IF;
    RETURN COALESCE(CASE
{ordinary}
        WHEN object_type_value = 'strategy_version' THEN
            object_id_value ~ '{PUBLIC_ID_PATTERNS["strategy"]}'
            AND object_version_value >= 1 AND object_revision_value >= 1
        WHEN object_type_value = 'settings' THEN
            object_id_value = 'SETTINGS-DEFAULT'
            AND object_version_value IS NULL AND object_revision_value >= 1
        WHEN object_type_value = 'provider_connection' THEN
            object_id_value ~ '^[0-9a-f]{{8}}-[0-9a-f]{{4}}-4[0-9a-f]{{3}}-[89ab][0-9a-f]{{3}}-[0-9a-f]{{12}}$'
            AND object_version_value IS NULL AND object_revision_value >= 1
        WHEN object_type_value = 'agent_config' THEN
            object_id_value IN ({roles})
            AND object_version_value IS NULL AND object_revision_value >= 1
        WHEN object_type_value = 'event_stream' THEN
            object_id_value ~ '{PUBLIC_ID_PATTERNS["domain_event"]}'
            AND object_version_value IS NULL AND object_revision_value >= 1
        ELSE false
    END, false);
EXCEPTION WHEN OTHERS THEN
    RETURN false;
END;
$qf$;
""".strip()


POSTGRES_LOCATOR_FUNCTION_SQL = _postgres_locator_function_sql()
POSTGRES_LOCATOR_JSON_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION qf_event_locator_json_valid(value jsonb, allow_null boolean)
RETURNS boolean
LANGUAGE plpgsql IMMUTABLE
AS $qf$
DECLARE
    object_type_value text;
    object_id_value text;
    object_version_value integer;
    object_revision_value bigint;
BEGIN
    IF value IS NULL
       OR jsonb_typeof(value) IS DISTINCT FROM 'object'
       OR (value ?& ARRAY['object_type','object_id','object_version','object_revision']) IS NOT TRUE THEN
        RETURN false;
    END IF;
    IF COALESCE(jsonb_typeof(value->'object_type'), '') NOT IN ('string', 'null')
       OR COALESCE(jsonb_typeof(value->'object_id'), '') NOT IN ('string', 'null')
       OR COALESCE(jsonb_typeof(value->'object_version'), '') NOT IN ('number', 'null')
       OR COALESCE(jsonb_typeof(value->'object_revision'), '') NOT IN ('number', 'null') THEN
        RETURN false;
    END IF;
    IF jsonb_typeof(value->'object_version') = 'number'
       AND (value->>'object_version') !~ '^-?[0-9]+$' THEN
        RETURN false;
    END IF;
    IF jsonb_typeof(value->'object_revision') = 'number'
       AND (value->>'object_revision') !~ '^-?[0-9]+$' THEN
        RETURN false;
    END IF;
    object_type_value := CASE WHEN jsonb_typeof(value->'object_type') = 'null'
        THEN NULL ELSE value->>'object_type' END;
    object_id_value := CASE WHEN jsonb_typeof(value->'object_id') = 'null'
        THEN NULL ELSE value->>'object_id' END;
    object_version_value := CASE WHEN jsonb_typeof(value->'object_version') = 'null'
        THEN NULL ELSE (value->>'object_version')::integer END;
    object_revision_value := CASE WHEN jsonb_typeof(value->'object_revision') = 'null'
        THEN NULL ELSE (value->>'object_revision')::bigint END;
    RETURN COALESCE(qf_event_locator_quartet_valid(
        object_type_value, object_id_value, object_version_value,
        object_revision_value, allow_null
    ), false);
EXCEPTION WHEN OTHERS THEN
    RETURN false;
END;
$qf$;
""".strip()
POSTGRES_NULLABLE_PUBLIC_ID_FUNCTION_SQL = f"""
CREATE OR REPLACE FUNCTION qf_nullable_public_id_json_valid(value jsonb, prefix text)
RETURNS boolean
LANGUAGE plpgsql IMMUTABLE
AS $qf$
BEGIN
    IF value IS NULL THEN
        RETURN false;
    END IF;
    IF jsonb_typeof(value) IS NOT DISTINCT FROM 'null' THEN
        RETURN true;
    END IF;
    IF jsonb_typeof(value) IS DISTINCT FROM 'string' THEN
        RETURN false;
    END IF;
    RETURN COALESCE(CASE prefix
        WHEN 'ART' THEN value #>> '{{}}' ~ '{PUBLIC_ID_PATTERNS["artifact"]}'
        ELSE false
    END, false);
EXCEPTION WHEN OTHERS THEN
    RETURN false;
END;
$qf$;
""".strip()
POSTGRES_LOCATOR_CONTRACT_SHA256 = hashlib.sha256(
    "\n".join(
        (
            POSTGRES_LOCATOR_FUNCTION_SQL,
            POSTGRES_LOCATOR_JSON_FUNCTION_SQL,
            POSTGRES_NULLABLE_PUBLIC_ID_FUNCTION_SQL,
        )
    ).encode()
).hexdigest()

POSTGRES_LOCATOR_HELPERS = (
    {
        "name": "qf_event_locator_quartet_valid",
        "identity_arguments": "text, text, integer, bigint, boolean",
        "sql": POSTGRES_LOCATOR_FUNCTION_SQL,
    },
    {
        "name": "qf_event_locator_json_valid",
        "identity_arguments": "jsonb, boolean",
        "sql": POSTGRES_LOCATOR_JSON_FUNCTION_SQL,
    },
    {
        "name": "qf_nullable_public_id_json_valid",
        "identity_arguments": "jsonb, text",
        "sql": POSTGRES_NULLABLE_PUBLIC_ID_FUNCTION_SQL,
    },
)


def locator_truth_table() -> dict[str, list[dict[str, str | int | None]]]:
    """Build the canonical 69/76 mandatory-locator oracle from generated rules."""

    cases: list[dict[str, str | int | None]] = []
    for rule in EventPayload.model_json_schema(mode="validation").get("allOf", []):
        object_type = (
            rule.get("if", {}).get("properties", {}).get("object_type", {}).get("const")
        )
        if not isinstance(object_type, str):
            continue
        properties = rule.get("then", {}).get("properties", {})
        object_id_schema = properties.get("object_id", {})
        examples = object_id_schema.get("examples", [])
        if examples:
            object_id = examples[-1]
        elif isinstance(object_id_schema.get("const"), str):
            object_id = object_id_schema["const"]
        elif object_id_schema.get("enum"):
            object_id = object_id_schema["enum"][0]
        else:
            object_id = "550e8400-e29b-41d4-a716-446655440000"
        cases.append(
            {
                "object_type": object_type,
                "object_id": object_id,
                "object_version": (
                    1
                    if properties.get("object_version", {}).get("minimum") == 1
                    else None
                ),
                "object_revision": (
                    1
                    if properties.get("object_revision", {}).get("minimum") == 1
                    else None
                ),
            }
        )
    if len(cases) != 21:
        raise RuntimeError(f"locator contract requires 21 branches, got {len(cases)}")
    special_types = {
        "strategy_version",
        "settings",
        "provider_connection",
        "agent_config",
        "event_stream",
    }
    ordinary = [row for row in cases if row["object_type"] not in special_types]
    if len(ordinary) != 16:
        raise RuntimeError(
            f"locator contract requires 16 ordinary branches, got {len(ordinary)}"
        )
    valid = [dict(row) for row in cases]
    valid.extend(
        {**row, "object_version": version, "object_revision": revision}
        for row in ordinary
        for version, revision in ((1, None), (None, 1), (1, 1))
    )
    invalid: list[dict[str, str | int | None]] = [
        {
            "object_type": None,
            "object_id": cases[0]["object_id"],
            "object_version": None,
            "object_revision": None,
        },
        {
            "object_type": "unknown",
            "object_id": cases[0]["object_id"],
            "object_version": None,
            "object_revision": None,
        },
        {
            "object_type": None,
            "object_id": None,
            "object_version": None,
            "object_revision": None,
        },
    ]
    invalid.extend(
        {**row, "object_id": cases[(index + 1) % len(cases)]["object_id"]}
        for index, row in enumerate(cases)
    )
    invalid.extend({**row, "object_version": 0} for row in cases)
    invalid.extend({**row, "object_revision": 0} for row in cases)
    invalid.extend(
        {**row, "object_version": None}
        for row in cases
        if row["object_type"] == "strategy_version"
    )
    invalid.extend(
        {**row, "object_revision": None}
        for row in cases
        if row["object_type"] in special_types
    )
    invalid.extend(
        {**row, "object_version": 1}
        for row in cases
        if row["object_type"]
        in {"settings", "provider_connection", "agent_config", "event_stream"}
    )
    if len(valid) != 69 or len(invalid) != 76:
        raise RuntimeError(
            f"locator truth table must be 69/76, got {len(valid)}/{len(invalid)}"
        )
    return {"valid": valid, "invalid": invalid}


def _exact_locator_scalar_types(values: dict[str, Any]) -> bool:
    object_type = values.get("object_type")
    object_id = values.get("object_id")
    object_version = values.get("object_version")
    object_revision = values.get("object_revision")
    if object_type is not None and not isinstance(object_type, str):
        return False
    if object_id is not None and not isinstance(object_id, str):
        return False
    return all(
        value is None or (isinstance(value, int) and not isinstance(value, bool))
        for value in (object_version, object_revision)
    )


def locator_quartet_valid(
    object_type: Any,
    object_id: Any,
    object_version: Any,
    object_revision: Any,
    allow_null: Any,
) -> bool:
    values = dict(
        zip(
            LOCATOR_FIELDS,
            (object_type, object_id, object_version, object_revision),
            strict=True,
        )
    )
    if not isinstance(allow_null, bool | int) or isinstance(allow_null, float):
        return False
    if all(value is None for value in values.values()):
        return bool(allow_null)
    if not _exact_locator_scalar_types(values):
        return False
    try:
        EventPayload.model_validate(values)
    except ValidationError:
        return False
    return True


def _json_object(value: Any) -> dict[str, Any] | None:
    if isinstance(value, bytes):
        try:
            value = value.decode()
        except UnicodeDecodeError:
            return None
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return None
    return value if isinstance(value, dict) else None


def job_result_ref_valid(value: Any) -> bool:
    document = _json_object(value)
    if document is None or set(document) != JOB_RESULT_REF_FIELDS:
        return False
    if not _exact_locator_scalar_types(document):
        return False
    artifact_id = document.get("artifact_id")
    if artifact_id is not None and not isinstance(artifact_id, str):
        return False
    try:
        JobResultRef.model_validate(document)
    except ValidationError:
        return False
    return True


def next_action_valid(value: Any) -> bool:
    document = _json_object(value)
    if document is None or set(document) != NEXT_ACTION_FIELDS:
        return False
    if not isinstance(document.get("action"), str):
        return False
    if not _exact_locator_scalar_types(document):
        return False
    try:
        NextAction.model_validate(document)
    except ValidationError:
        return False
    return True


def register_sqlite_functions(dbapi_connection: Any) -> None:
    """Register deterministic fail-closed predicates used by SQLite CHECKs."""

    dbapi_connection.create_function(
        "qf_event_locator_quartet_valid",
        5,
        lambda *args: int(locator_quartet_valid(*args)),
        deterministic=True,
    )
    dbapi_connection.create_function(
        "qf_job_result_ref_valid",
        1,
        lambda value: int(job_result_ref_valid(value)),
        deterministic=True,
    )
    dbapi_connection.create_function(
        "qf_next_action_valid",
        1,
        lambda value: int(next_action_valid(value)),
        deterministic=True,
    )
    dbapi_connection.create_function("uuidv7", 0, lambda: str(uuid.uuid7()))


__all__ = [
    "JOB_RESULT_REF_CHECK_SQL",
    "LOCATOR_CHECK_SQL",
    "NEXT_ACTION_CHECK_SQL",
    "POSTGRES_LOCATOR_CONTRACT_SHA256",
    "POSTGRES_LOCATOR_FUNCTION_SQL",
    "POSTGRES_LOCATOR_HELPERS",
    "POSTGRES_LOCATOR_JSON_FUNCTION_SQL",
    "POSTGRES_NULLABLE_PUBLIC_ID_FUNCTION_SQL",
    "job_result_ref_valid",
    "locator_quartet_valid",
    "locator_truth_table",
    "next_action_valid",
    "register_sqlite_functions",
]
