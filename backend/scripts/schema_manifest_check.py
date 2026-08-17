"""Independently verify section-14 document, ORM, database, and Alembic state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import CheckConstraint, MetaData, create_engine, text
from sqlalchemy.dialects import postgresql

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantfoundry.contracts.events.locator import (
    JOB_RESULT_REF_CHECK_SQL,
    LOCATOR_CHECK_SQL,
    NEXT_ACTION_CHECK_SQL,
    POSTGRES_LOCATOR_CONTRACT_SHA256,
    POSTGRES_LOCATOR_HELPERS,
    locator_truth_table,
)
from quantfoundry.infrastructure.db.schema import MANIFEST_PATH, load_manifest
from scripts.generate_physical_schema_snapshot import (
    _autoincrement_spec,
    _index_key_spec,
)
from scripts.generate_physical_schema_snapshot import (
    snapshot as physical_snapshot,
)
from scripts.generate_schema_manifest import DEFAULT_DOCUMENT, extract_manifest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PHYSICAL_PATH = BACKEND_ROOT / "alembic/versions/0016_section14_physical.json"
_TYPE_ARGS = re.compile(r"^(varchar|char|numeric)\((\d+)(?:,(\d+))?\)$")
_FK = re.compile(r"FK\s+([a-z0-9_]+)\(([^)]+)\)", re.IGNORECASE)
_COMPOSITE_FK = re.compile(
    r"FK\s*\(([^)]+)\)\s*(?:->|→)\s*([a-z0-9_]+)\(([^)]+)\)",
    re.IGNORECASE,
)
_APPROVED_INTERNAL_DATABASE_TABLES = frozenset({"alembic_version"})
_SQLITE_CLOSED_CHECKS = {
    "ck_agent_runs_locator_quartet": LOCATOR_CHECK_SQL.format(allow_null="1"),
    "ck_notifications_locator_quartet": LOCATOR_CHECK_SQL.format(allow_null="1"),
    "ck_domain_events_locator_quartet": LOCATOR_CHECK_SQL.format(allow_null="0"),
    "ck_audit_events_locator_quartet": LOCATOR_CHECK_SQL.format(allow_null="0"),
    "ck_jobs_result_ref_closed": (
        "result_ref IS NULL OR qf_job_result_ref_valid(result_ref)"
    ),
    "ck_agent_runs_next_action_closed": (
        "next_action IS NULL OR qf_next_action_valid(next_action)"
    ),
}
_DOCUMENTED_NAMED_CHECKS = frozenset(
    {
        ("agent_runs", "ck_agent_runs_locator_quartet"),
        ("agent_runs", "ck_agent_runs_next_action_closed"),
        ("audit_events", "ck_audit_events_locator_quartet"),
        ("domain_events", "ck_domain_events_locator_quartet"),
        ("jobs", "ck_jobs_result_ref_closed"),
        ("notifications", "ck_notifications_locator_quartet"),
        ("records", "ck_records_kind_record_key"),
        ("setup_bindings", "ck_setup_bindings_settings_record_id"),
    }
)
_DOCUMENTED_CLOSED_CHECK_SQL = {
    ("agent_runs", "ck_agent_runs_locator_quartet"): LOCATOR_CHECK_SQL.format(
        allow_null="TRUE"
    ),
    ("agent_runs", "ck_agent_runs_next_action_closed"): NEXT_ACTION_CHECK_SQL,
    ("audit_events", "ck_audit_events_locator_quartet"): LOCATOR_CHECK_SQL.format(
        allow_null="FALSE"
    ),
    ("domain_events", "ck_domain_events_locator_quartet"): LOCATOR_CHECK_SQL.format(
        allow_null="FALSE"
    ),
    ("jobs", "ck_jobs_result_ref_closed"): JOB_RESULT_REF_CHECK_SQL,
    ("notifications", "ck_notifications_locator_quartet"): LOCATOR_CHECK_SQL.format(
        allow_null="TRUE"
    ),
}


def _manifest_named_checks(manifest: dict[str, Any]) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for table in manifest["tables"]:
        for column in table.get("columns", []):
            result.update(
                (table["name"], name)
                for name in re.findall(
                    r"CHECK\s+`([^`]+)`", column.get("constraints", ""), re.I
                )
            )
    return result


def _expected_type(value: str, dialect: str) -> tuple[Any, ...]:
    match = _TYPE_ARGS.fullmatch(value)
    if match:
        name, first, second = match.groups()
        if name == "numeric":
            return name, int(first), int(second or 0)
        return name, int(first)
    if dialect == "sqlite" and value == "daterange":
        return ("varchar", None)
    return (value,)


def _actual_type(value: Any, dialect: str) -> tuple[Any, ...]:
    if value.__class__.__name__ == "WorkspaceScopeId":
        return ("uuid",) if dialect == "postgresql" else ("char", 32)
    if value.__class__.__name__ == "DateRangeCompat":
        return ("daterange",) if dialect == "postgresql" else ("varchar", None)
    if value.__class__.__name__ == "JSONTextCompat":
        return ("jsonb",)
    if isinstance(value, postgresql.JSONB):
        return ("jsonb",)
    if isinstance(value, postgresql.DATERANGE):
        return ("daterange",)
    if isinstance(value, postgresql.TIMESTAMP):
        return ("timestamptz",) if value.timezone else ("timestamp",)
    name = value.__class__.__name__.lower()
    aliases = {
        "biginteger": "bigint",
        "smallinteger": "smallint",
        "datetime": "timestamptz" if getattr(value, "timezone", False) else "timestamp",
        "uuid": "uuid",
        "largebinary": "bytea",
        "json": "json" if dialect == "postgresql" else "jsonb",
        "text": "text",
        "date": "date",
        "boolean": "boolean",
        "integer": "integer",
        "string": "varchar",
        "varchar": "varchar",
        "char": "char",
        "numeric": "numeric",
    }
    normalized = aliases.get(name, name)
    if normalized in {"varchar", "char"}:
        return normalized, getattr(value, "length", None)
    if normalized == "numeric":
        return (
            normalized,
            getattr(value, "precision", None),
            getattr(value, "scale", None),
        )
    return (normalized,)


def _type_matches(expected: str, actual: Any, dialect: str) -> bool:
    wanted = _expected_type(expected, dialect)
    got = _actual_type(actual, dialect)
    if (
        dialect == "sqlite"
        and expected == "uuid"
        and got
        in {
            ("char", 32),
            ("varchar", 32),
        }
    ):
        return True
    if (
        dialect == "sqlite"
        and expected == "bytea"
        and got[0]
        in {
            "blob",
            "largebinary",
            "bytea",
        }
    ):
        return True
    if dialect == "sqlite" and expected == "bigint" and got == ("integer",):
        return True
    if (
        dialect == "sqlite"
        and wanted[0] in {"varchar", "char"}
        and got[0]
        in {
            "varchar",
            "text",
        }
    ):
        return wanted[1:] == got[1:] or got[1:] == (None,)
    # SQLAlchemy represents an unbounded String as VARCHAR with length=None;
    # the frozen manifest writes that contract as plain ``varchar``/``char``.
    if wanted in {("varchar",), ("char",)} and got[:1] == wanted:
        return got[1:] == (None,)
    return wanted == got


def _expected_foreign_keys(
    table_spec: dict[str, Any],
    manifest_tables: Mapping[str, dict[str, Any]] | set[str],
) -> set[tuple[tuple[str, ...], tuple[str, ...]]]:
    result: set[tuple[tuple[str, ...], tuple[str, ...]]] = set()
    table_columns = {column["name"] for column in table_spec["columns"]}
    table_specs = manifest_tables if isinstance(manifest_tables, Mapping) else {}
    for column in table_spec["columns"]:
        constraints = column["constraints"]
        composite = _COMPOSITE_FK.search(constraints)
        if composite is not None:
            local = tuple(item.strip() for item in composite.group(1).split(","))
            target = composite.group(2)
            remote = tuple(
                f"{target}.{item.strip()}" for item in composite.group(3).split(",")
            )
            result.add((local, remote))
            continue
        match = _FK.search(constraints)
        if match is None:
            continue
        target, target_column = match.group(1), match.group(2).strip()
        target_spec = table_specs.get(target)
        target_columns = (
            {item["name"] for item in target_spec["columns"]}
            if target_spec is not None
            else set()
        )
        scoped = (
            column["name"] != "workspace_id"
            and "workspace_id" in table_columns
            and "workspace_id" in target_columns
        )
        local = ("workspace_id", column["name"]) if scoped else (column["name"],)
        remote = (
            (f"{target}.workspace_id", f"{target}.{target_column}")
            if scoped
            else (f"{target}.{target_column}",)
        )
        result.add((local, remote))
    return result


def _constraint_shapes(
    table: Any,
) -> tuple[
    set[tuple[str | None, tuple[str, ...]]],
    set[
        tuple[
            str | None,
            tuple[str, ...],
            tuple[str, ...],
            str | None,
        ]
    ],
    set[
        tuple[
            str | None,
            str,
            tuple[tuple[str | None, str, str, str], ...],
            tuple[str, ...],
            bool,
            str | None,
        ]
    ],
    dict[str, str],
]:
    unique: set[tuple[str | None, tuple[str, ...]]] = {
        (
            cast(str | None, constraint.name),
            tuple(str(column.name) for column in constraint.columns),
        )
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    foreign_keys: set[
        tuple[str | None, tuple[str, ...], tuple[str, ...], str | None]
    ] = {
        (
            cast(str | None, constraint.name),
            tuple(str(element.parent.name) for element in constraint.elements),
            tuple(str(element.target_fullname) for element in constraint.elements),
            cast(str | None, constraint.ondelete),
        )
        for constraint in table.foreign_key_constraints
    }
    indexes: set[
        tuple[
            str | None,
            str,
            tuple[tuple[str | None, str, str, str], ...],
            tuple[str, ...],
            bool,
            str | None,
        ]
    ] = {
        (
            cast(str | None, index.name),
            str(index.dialect_options["postgresql"].get("using") or "btree"),
            tuple(
                _index_key_tuple(_index_key_spec(expression))
                for expression in index.expressions
            ),
            tuple(
                str(item)
                for item in index.dialect_options["postgresql"].get("include") or ()
            ),
            bool(index.unique),
            (
                str(index.dialect_options["postgresql"].get("where"))
                if index.dialect_options["postgresql"].get("where") is not None
                else str(index.dialect_options["sqlite"].get("where"))
                if index.dialect_options["sqlite"].get("where") is not None
                else None
            ),
        )
        for index in table.indexes
    }
    checks = {
        str(constraint.name): str(constraint.sqltext)
        for constraint in table.constraints
        if isinstance(constraint, CheckConstraint)
    }
    return unique, foreign_keys, indexes, checks


def _column_default_signature(column: Any) -> str | None:
    server_default = getattr(column, "server_default", None)
    arg = getattr(server_default, "arg", None) if server_default is not None else None
    return str(arg) if arg is not None else None


def _column_generation_signature(column: Any) -> dict[str, Any] | None:
    computed = getattr(column, "computed", None)
    if computed is None:
        return None
    return {
        "sqltext": str(computed.sqltext),
        "persisted": getattr(computed, "persisted", None),
    }


def _column_identity_signature(column: Any) -> dict[str, Any] | None:
    identity = getattr(column, "identity", None)
    if identity is None:
        return None
    return {
        "always": getattr(identity, "always", None),
        "start": getattr(identity, "start", None),
        "increment": getattr(identity, "increment", None),
        "minvalue": getattr(identity, "minvalue", None),
        "maxvalue": getattr(identity, "maxvalue", None),
        "cycle": getattr(identity, "cycle", None),
        "cache": getattr(identity, "cache", None),
    }


def _column_autoincrement_signature(column: Any) -> bool:
    return _autoincrement_spec(column)


def _index_key_tuple(
    item: Mapping[str, Any],
) -> tuple[str | None, str, str, str]:
    direction = str(item.get("direction") or "ASC").upper()
    nulls = item.get("nulls") or ("LAST" if direction == "ASC" else "FIRST")
    return (
        str(item["column"]) if item.get("column") is not None else None,
        str(item["expression"]),
        direction,
        str(nulls).upper(),
    )


def _legacy_index_key(value: str) -> dict[str, str]:
    match = re.fullmatch(
        r"(?P<base>.*?)(?:\s+(?P<direction>ASC|DESC))?"
        r"(?:\s+NULLS\s+(?P<nulls>FIRST|LAST))?$",
        value.strip(),
        re.IGNORECASE,
    )
    if match is None:
        raise RuntimeError(f"unclassified legacy index key {value!r}")
    expression = match.group("base").strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expression):
        raise RuntimeError(
            f"legacy index expression lacks structured signature: {value!r}"
        )
    direction = (match.group("direction") or "ASC").upper()
    return {
        "column": expression,
        "expression": expression,
        "direction": direction,
        "nulls": (
            match.group("nulls") or ("LAST" if direction == "ASC" else "FIRST")
        ).upper(),
    }


def _index_keys(index: Mapping[str, Any]) -> list[dict[str, Any]]:
    if "keys" in index:
        return [dict(item) for item in index["keys"]]
    if "columns" in index:
        return [_legacy_index_key(str(item)) for item in index["columns"]]
    raise RuntimeError(f"index {index.get('name')!r} has no keys or columns")


def _postgres_generated_constraint_name(
    kind: str, table_name: str, columns: tuple[str, ...]
) -> str:
    if not columns:
        raise RuntimeError(f"anonymous {kind} on {table_name} has no columns")
    suffix = {"uq": "key", "fk": "fkey"}.get(kind)
    if suffix is None:
        raise RuntimeError(f"anonymous {kind} on {table_name} has no name policy")
    name = f"{table_name}_{'_'.join(columns)}_{suffix}"
    if len(name.encode()) > 63:
        raise RuntimeError(
            f"anonymous {kind} name requires PostgreSQL truncation policy: {name}"
        )
    return name


def _expected_constraint_name(
    kind: str,
    table_name: str,
    columns: tuple[str, ...],
    name: str | None,
    label: str,
) -> str | None:
    if name is not None or label != "database":
        return name
    return _postgres_generated_constraint_name(kind, table_name, columns)


def _physical_contract(
    manifest: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    value = json.loads(PHYSICAL_PATH.read_text(encoding="utf-8"))
    if (
        value.get("table_count") != 63
        or value.get("column_count") != 967
        or sum(len(table["checks"]) for table in value["tables"]) != 191
    ):
        raise RuntimeError("physical schema is not canonical 63/967/191")
    documented = _manifest_named_checks(manifest)
    if documented != _DOCUMENTED_NAMED_CHECKS:
        raise RuntimeError(
            "section-14 manifest named CHECK set is not canonical: "
            f"expected={sorted(_DOCUMENTED_NAMED_CHECKS)} actual={sorted(documented)}"
        )
    helper_contract = value.get("locator_helper_contract")
    expected_helper_contract = {
        "sha256": POSTGRES_LOCATOR_CONTRACT_SHA256,
        "functions": list(POSTGRES_LOCATOR_HELPERS),
        "truth_table": locator_truth_table(),
    }
    if helper_contract != expected_helper_contract:
        raise RuntimeError(
            "physical locator helper contract disagrees with generated document rules"
        )
    helper_sql = "\n".join(
        str(function["sql"]) for function in helper_contract["functions"]
    )
    if hashlib.sha256(helper_sql.encode()).hexdigest() != helper_contract["sha256"]:
        raise RuntimeError("physical locator helper contract hash is invalid")
    if (
        len(helper_contract["truth_table"]["valid"]) != 69
        or len(helper_contract["truth_table"]["invalid"]) != 76
    ):
        raise RuntimeError("physical locator truth table is not canonical 69/76")
    contract = {table["name"]: table for table in value["tables"]}
    manifest_specs = {table["name"]: table for table in manifest["tables"]}
    for table_spec in manifest["tables"]:
        table_name = table_spec["name"]
        expected_foreign_keys = _expected_foreign_keys(table_spec, manifest_specs)
        actual_foreign_keys = {
            (tuple(item["columns"]), tuple(item["targets"]))
            for item in contract[table_name]["foreign_keys"]
        }
        if expected_foreign_keys != actual_foreign_keys:
            raise RuntimeError(
                "section-14 manifest/physical foreign-key mismatch "
                f"for {table_name}: "
                f"missing={sorted(expected_foreign_keys - actual_foreign_keys)} "
                f"unexpected={sorted(actual_foreign_keys - expected_foreign_keys)}"
            )
    for (table_name, check_name), sql in _DOCUMENTED_CLOSED_CHECK_SQL.items():
        physical = {
            str(check["name"]): str(check["sql"])
            for check in contract[table_name]["checks"]
        }
        if _normalized_check(physical.get(check_name, "")) != _normalized_check(sql):
            raise RuntimeError(
                f"physical schema disagrees with documented CHECK {check_name}"
            )
    return contract, helper_contract


def _normalized_helper_body(sql: str) -> str:
    match = re.search(r"AS \$qf\$\s*(.*?)\s*\$qf\$;?\s*$", sql, re.DOTALL)
    if match is None:
        raise RuntimeError("locator helper SQL lacks the canonical $qf$ body")
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _check_postgres_helpers(
    database_url: str, helper_contract: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT p.proname, oidvectortypes(p.proargtypes), p.provolatile, "
                    "l.lanname, p.prorettype::regtype::text, p.prosrc, "
                    "obj_description(p.oid, 'pg_proc') "
                    "FROM pg_proc p "
                    "JOIN pg_namespace n ON n.oid=p.pronamespace "
                    "JOIN pg_language l ON l.oid=p.prolang "
                    "WHERE n.nspname=current_schema() AND p.proname = ANY(:names)"
                ),
                {
                    "names": [
                        str(function["name"])
                        for function in helper_contract["functions"]
                    ]
                },
            ).all()
            actual = {(str(row[0]), str(row[1])): row for row in rows}
            expected_comment = f"qf-contract-sha256:{helper_contract['sha256']}"
            for function in helper_contract["functions"]:
                name = str(function["name"])
                row = actual.get((name, str(function["identity_arguments"])))
                if row is None:
                    errors.append(f"database:missing-helper:{name}")
                    continue
                if str(row[1]) != str(function["identity_arguments"]):
                    errors.append(
                        f"database:helper-arguments:{name}:"
                        f"expected={function['identity_arguments']}:actual={row[1]}"
                    )
                if row[2] != "i" or row[3] != "plpgsql" or row[4] != "boolean":
                    errors.append(
                        f"database:helper-signature:{name}:"
                        f"volatility={row[2]}:language={row[3]}:returns={row[4]}"
                    )
                expected_body = _normalized_helper_body(str(function["sql"]))
                actual_body = re.sub(r"\s+", " ", str(row[5])).strip()
                if actual_body != expected_body:
                    errors.append(f"database:helper-body:{name}")
                if row[6] != expected_comment:
                    errors.append(
                        f"database:helper-contract-hash:{name}:"
                        f"expected={expected_comment}:actual={row[6]}"
                    )

            call = text(
                "SELECT qf_event_locator_quartet_valid("
                ":object_type,:object_id,:object_version,:object_revision,FALSE)"
            )
            json_call = text(
                "SELECT qf_event_locator_json_valid(CAST(:value AS jsonb),FALSE)"
            )
            for expected, label in ((True, "valid"), (False, "invalid")):
                for index, locator in enumerate(helper_contract["truth_table"][label]):
                    result = connection.execute(call, locator).scalar_one()
                    if result is not expected:
                        errors.append(
                            f"database:helper-truth:{label}:{index}:actual={result!r}"
                        )
                    json_result = connection.execute(
                        json_call, {"value": json.dumps(locator, separators=(",", ":"))}
                    ).scalar_one()
                    if json_result is not expected:
                        errors.append(
                            "database:json-helper-truth:"
                            f"{label}:{index}:actual={json_result!r}"
                        )
            optional_null = {
                "object_type": None,
                "object_id": None,
                "object_version": None,
                "object_revision": None,
            }
            optional_result = connection.execute(
                text(
                    "SELECT qf_event_locator_quartet_valid("
                    ":object_type,:object_id,:object_version,:object_revision,TRUE)"
                ),
                optional_null,
            ).scalar_one()
            if optional_result is not True:
                errors.append(
                    f"database:helper-truth:optional-null:actual={optional_result!r}"
                )
            nullable_id_cases = (
                (None, "ART", False),
                ("null", "ART", True),
                (json.dumps("ART-550e8400-e29b-41d4-a716-446655440000"), "ART", True),
                (json.dumps("JOB-550e8400-e29b-41d4-a716-446655440000"), "ART", False),
                ("true", "ART", False),
                (json.dumps("ART-550e8400-e29b-41d4-a716-446655440000"), None, False),
            )
            for index, (value, prefix, expected) in enumerate(nullable_id_cases):
                result = connection.execute(
                    text(
                        "SELECT qf_nullable_public_id_json_valid("
                        "CAST(:value AS jsonb),:prefix)"
                    ),
                    {"value": value, "prefix": prefix},
                ).scalar_one()
                if result is not expected:
                    errors.append(
                        "database:nullable-public-id-helper-truth:"
                        f"{index}:actual={result!r}"
                    )
    finally:
        engine.dispose()
    return errors


def _normalized_sql_layout(value: str) -> str:
    output: list[str] = []
    index = 0
    pending_space = False
    while index < len(value):
        char = value[index]
        if char.isspace():
            pending_space = True
            index += 1
            continue
        dollar = re.match(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$", value[index:])
        if char in {"'", '"'} or dollar is not None:
            if pending_space and output:
                output.append(" ")
            pending_space = False
            delimiter = dollar.group(0) if dollar is not None else char
            end = index + len(delimiter)
            while end < len(value):
                if value.startswith(delimiter, end):
                    if delimiter in {"'", '"'} and value.startswith(delimiter * 2, end):
                        end += 2
                        continue
                    end += len(delimiter)
                    break
                end += 1
            if end > len(value) or not value.startswith(
                delimiter, end - len(delimiter)
            ):
                raise RuntimeError("unterminated quoted SQL token")
            output.append(value[index:end])
            index = end
            continue
        if pending_space and output:
            output.append(" ")
        pending_space = False
        output.append(char)
        index += 1
    return "".join(output).strip()


def _has_single_wrapping_parentheses(value: str) -> bool:
    if not (value.startswith("(") and value.endswith(")")):
        return False
    depth = 0
    index = 0
    while index < len(value):
        char = value[index]
        if char in {"'", '"'}:
            delimiter = char
            index += 1
            while index < len(value):
                if value[index] == delimiter:
                    if index + 1 < len(value) and value[index + 1] == delimiter:
                        index += 2
                        continue
                    break
                index += 1
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0 and index != len(value) - 1:
                return False
            if depth < 0:
                return False
        index += 1
    return depth == 0


def _normalized_check(value: str) -> str:
    result = _normalized_sql_layout(value)
    while _has_single_wrapping_parentheses(result):
        result = result[1:-1].strip()
    return result


def _check_metadata(
    manifest: dict[str, Any],
    metadata: MetaData,
    dialect: str,
    label: str,
    physical_contract: dict[str, dict[str, Any]],
    parsed_expected_checks: dict[tuple[str, str], str] | None = None,
    parsed_actual_checks: dict[tuple[str, str], str] | None = None,
    parsed_expected_indexes: dict[tuple[str, str], str] | None = None,
    parsed_actual_indexes: dict[tuple[str, str], str] | None = None,
) -> list[str]:
    errors: list[str] = []
    manifest_names = {table["name"] for table in manifest["tables"]}
    allowed_internal = (
        _APPROVED_INTERNAL_DATABASE_TABLES if label == "database" else frozenset()
    )
    for table_name in sorted(set(metadata.tables) - manifest_names - allowed_internal):
        errors.append(f"{label}:unexpected-table:{table_name}")
    for table_spec in manifest["tables"]:
        table_name = table_spec["name"]
        table = metadata.tables.get(table_name)
        if table is None:
            errors.append(f"{label}:missing-table:{table_name}")
            continue
        expected_columns = {column["name"] for column in table_spec["columns"]}
        for name in sorted(set(table.c.keys()) - expected_columns):
            errors.append(f"{label}:unexpected-column:{table_name}.{name}")
        for column_spec in table_spec["columns"]:
            name = column_spec["name"]
            if name not in table.c:
                errors.append(f"{label}:missing-column:{table_name}.{name}")
                continue
            column = table.c[name]
            if not _type_matches(column_spec["postgres_type"], column.type, dialect):
                errors.append(
                    f"{label}:type:{table_name}.{name}:"
                    f"expected={column_spec['postgres_type']}:actual={column.type}"
                )
            if column.nullable != column_spec["nullable"]:
                errors.append(
                    f"{label}:nullable:{table_name}.{name}:"
                    f"expected={column_spec['nullable']}:actual={column.nullable}"
                )
        physical_table = physical_contract[table_name]
        physical_columns = {item["name"]: item for item in physical_table["columns"]}
        for name, physical_column in physical_columns.items():
            if name not in table.c:
                errors.append(f"{label}:missing-physical-column:{table_name}.{name}")
                continue
            column = table.c[name]
            actual_default = _column_default_signature(column)
            if actual_default != physical_column.get("server_default"):
                errors.append(
                    f"{label}:default:{table_name}.{name}:"
                    f"expected={physical_column.get('server_default')}:actual={actual_default}"
                )
            actual_generation = _column_generation_signature(column)
            if actual_generation != physical_column.get("generation"):
                errors.append(
                    f"{label}:generation:{table_name}.{name}:"
                    f"expected={physical_column.get('generation')}:actual={actual_generation}"
                )
            actual_identity = _column_identity_signature(column)
            if actual_identity != physical_column.get("identity"):
                errors.append(
                    f"{label}:identity:{table_name}.{name}:"
                    f"expected={physical_column.get('identity')}:actual={actual_identity}"
                )
            actual_autoincrement = _column_autoincrement_signature(column)
            if actual_autoincrement != bool(physical_column["autoincrement"]):
                errors.append(
                    f"{label}:autoincrement:{table_name}.{name}:"
                    f"expected={physical_column['autoincrement']}:actual={actual_autoincrement}"
                )
        expected_pk = tuple(physical_table["primary_key"])
        actual_pk = tuple(column.name for column in table.primary_key.columns)
        if actual_pk != expected_pk:
            errors.append(
                f"{label}:primary-key:{table_name}:"
                f"expected={expected_pk}:actual={actual_pk}"
            )
        expected_unique = {
            (
                _expected_constraint_name(
                    "uq",
                    table_name,
                    tuple(constraint["columns"]),
                    constraint["name"],
                    label,
                ),
                tuple(constraint["columns"]),
            )
            for constraint in physical_table["unique_constraints"]
        }
        expected_foreign_keys = {
            (
                _expected_constraint_name(
                    "fk",
                    table_name,
                    tuple(constraint["columns"]),
                    constraint["name"],
                    label,
                ),
                tuple(constraint["columns"]),
                tuple(constraint["targets"]),
                constraint["ondelete"],
            )
            for constraint in physical_table["foreign_keys"]
        }
        expected_indexes = {
            (
                index["name"],
                str(index.get("method") or "btree").lower(),
                tuple(_index_key_tuple(item) for item in _index_keys(index)),
                tuple(index.get("include") or ()),
                bool(index["unique"]),
                (parsed_expected_indexes or {}).get(
                    (table_name, index["name"]), index["where"]
                ),
            )
            for index in physical_table["indexes"]
        }
        actual_unique, actual_foreign_keys, actual_indexes, actual_checks = (
            _constraint_shapes(table)
        )
        actual_indexes = {
            (
                name,
                method,
                keys,
                include,
                unique,
                (parsed_actual_indexes or {}).get((table_name, str(name)), where),
            )
            for name, method, keys, include, unique, where in actual_indexes
        }
        for unique_shape in sorted(expected_unique - actual_unique):
            errors.append(f"{label}:missing-unique:{table_name}:{unique_shape}")
        for unique_shape in sorted(actual_unique - expected_unique):
            errors.append(f"{label}:unexpected-unique:{table_name}:{unique_shape}")
        for foreign_key_shape in sorted(expected_foreign_keys - actual_foreign_keys):
            errors.append(
                f"{label}:missing-foreign-key:{table_name}:{foreign_key_shape}"
            )
        for foreign_key_shape in sorted(actual_foreign_keys - expected_foreign_keys):
            errors.append(
                f"{label}:unexpected-foreign-key:{table_name}:{foreign_key_shape}"
            )
        for index_shape in sorted(expected_indexes - actual_indexes):
            errors.append(f"{label}:missing-index:{table_name}:{index_shape}")
        for index_shape in sorted(actual_indexes - expected_indexes):
            errors.append(f"{label}:unexpected-index:{table_name}:{index_shape}")
        expected_checks = {
            str(constraint["name"]): str(constraint["sql"])
            for constraint in physical_table["checks"]
        }
        for key, sql in _DOCUMENTED_CLOSED_CHECK_SQL.items():
            documented_table, name = key
            if documented_table == table_name:
                expected_checks[name] = sql
        if dialect == "sqlite" and label == "database":
            for name, sql in _SQLITE_CLOSED_CHECKS.items():
                if name in expected_checks:
                    expected_checks[name] = sql
        for name in sorted(set(expected_checks) - set(actual_checks)):
            errors.append(f"{label}:missing-check:{table_name}:{name}")
        for name in sorted(set(actual_checks) - set(expected_checks)):
            errors.append(f"{label}:unexpected-check:{table_name}:{name}")
        for name in sorted(set(expected_checks) & set(actual_checks)):
            expected_sql = _normalized_check(
                (parsed_expected_checks or {}).get(
                    (table_name, name), expected_checks[name]
                )
            )
            actual_sql = _normalized_check(
                (parsed_actual_checks or {}).get(
                    (table_name, name), actual_checks[name]
                )
            )
            if expected_sql != actual_sql:
                errors.append(
                    f"{label}:check-sql:{table_name}:{name}:"
                    f"expected={expected_sql}:actual={actual_sql}"
                )
    return errors


def _database_metadata(database_url: str) -> tuple[MetaData, str]:
    engine = create_engine(database_url)
    try:
        metadata = MetaData()
        metadata.reflect(bind=engine)
        return metadata, engine.dialect.name
    finally:
        engine.dispose()


def _postgres_parsed_expected_checks(
    database_url: str, physical_contract: dict[str, dict[str, Any]]
) -> dict[tuple[str, str], str]:
    """Round-trip expected expressions through PostgreSQL's own parser."""

    engine = create_engine(database_url)
    result: dict[tuple[str, str], str] = {}
    try:
        with engine.connect() as connection:
            preparer = connection.dialect.identifier_preparer
            transaction = connection.begin()
            try:
                for offset, (table_name, table) in enumerate(
                    sorted(physical_contract.items())
                ):
                    temporary = f"qf_check_contract_{offset}"
                    connection.execute(
                        text(
                            f"CREATE TEMP TABLE {preparer.quote(temporary)} "
                            f"(LIKE {preparer.quote(table_name)} INCLUDING GENERATED)"
                        )
                    )
                    for check_offset, check in enumerate(table["checks"]):
                        temporary_constraint = f"qf_check_{offset}_{check_offset}"
                        connection.execute(
                            text(
                                f"ALTER TABLE {preparer.quote(temporary)} ADD "
                                f"CONSTRAINT {preparer.quote(temporary_constraint)} "
                                f"CHECK ({check['sql']}) NOT VALID"
                            )
                        )
                        parsed = connection.execute(
                            text(
                                "SELECT pg_get_expr(c.conbin, c.conrelid) "
                                "FROM pg_constraint c "
                                "WHERE c.conrelid = to_regclass(:table_name) "
                                "AND c.conname = :constraint_name"
                            ),
                            {
                                "table_name": f"pg_temp.{temporary}",
                                "constraint_name": temporary_constraint,
                            },
                        ).scalar_one()
                        result[(table_name, str(check["name"]))] = str(parsed)
                transaction.rollback()
            except Exception:
                transaction.rollback()
                raise
    finally:
        engine.dispose()
    return result


def _postgres_actual_checks(database_url: str) -> dict[tuple[str, str], str]:
    """Read real checks through the same PostgreSQL deparser used for expectations."""

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT t.relname, c.conname, "
                    "pg_get_expr(c.conbin, c.conrelid) "
                    "FROM pg_constraint c "
                    "JOIN pg_class t ON t.oid = c.conrelid "
                    "JOIN pg_namespace n ON n.oid = t.relnamespace "
                    "WHERE c.contype = 'c' "
                    "AND n.nspname = current_schema()"
                )
            )
            return {
                (str(table_name), str(constraint_name)): str(expression)
                for table_name, constraint_name, expression in rows
            }
    finally:
        engine.dispose()


def _postgres_parsed_expected_indexes(
    database_url: str, physical_contract: dict[str, dict[str, Any]]
) -> dict[tuple[str, str], str]:
    """Round-trip expected partial-index predicates through PostgreSQL."""

    engine = create_engine(database_url)
    result: dict[tuple[str, str], str] = {}
    try:
        with engine.connect() as connection:
            preparer = connection.dialect.identifier_preparer
            transaction = connection.begin()
            try:
                for offset, (table_name, table) in enumerate(
                    sorted(physical_contract.items())
                ):
                    indexes = [item for item in table["indexes"] if item["where"]]
                    if not indexes:
                        continue
                    temporary = f"qf_index_contract_{offset}"
                    connection.execute(
                        text(
                            f"CREATE TEMP TABLE {preparer.quote(temporary)} "
                            f"(LIKE {preparer.quote(table_name)} INCLUDING GENERATED)"
                        )
                    )
                    for index_offset, index in enumerate(indexes):
                        temporary_index = f"qf_index_{offset}_{index_offset}"
                        columns = ", ".join(
                            preparer.quote(str(key["column"]))
                            if key.get("column")
                            else str(key["expression"])
                            for key in _index_keys(index)
                        )
                        connection.execute(
                            text(
                                f"CREATE {'UNIQUE ' if index['unique'] else ''}INDEX "
                                f"{preparer.quote(temporary_index)} ON "
                                f"{preparer.quote(temporary)} ({columns}) "
                                f"WHERE {index['where']}"
                            )
                        )
                        parsed = connection.execute(
                            text(
                                "SELECT pg_get_expr(i.indpred, i.indrelid) "
                                "FROM pg_index i "
                                "JOIN pg_class c ON c.oid=i.indexrelid "
                                "JOIN pg_namespace n ON n.oid=c.relnamespace "
                                "WHERE c.relname=:index_name "
                                "AND n.oid=pg_my_temp_schema()"
                            ),
                            {"index_name": temporary_index},
                        ).scalar_one()
                        result[(table_name, str(index["name"]))] = str(parsed)
                transaction.rollback()
            except Exception:
                transaction.rollback()
                raise
    finally:
        engine.dispose()
    return result


def _postgres_actual_indexes(database_url: str) -> dict[tuple[str, str], str]:
    """Read partial predicates through PostgreSQL's canonical deparser."""

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT t.relname, c.relname, pg_get_expr(i.indpred, i.indrelid) "
                    "FROM pg_index i "
                    "JOIN pg_class t ON t.oid=i.indrelid "
                    "JOIN pg_class c ON c.oid=i.indexrelid "
                    "JOIN pg_namespace n ON n.oid=t.relnamespace "
                    "WHERE i.indpred IS NOT NULL AND n.nspname=current_schema()"
                )
            )
            return {
                (str(table_name), str(index_name)): str(expression)
                for table_name, index_name, expression in rows
            }
    finally:
        engine.dispose()


def _normalized_physical_snapshot(
    value: dict[str, Any],
    *,
    parsed_checks: Mapping[tuple[str, str], str],
    parsed_indexes: Mapping[tuple[str, str], str],
) -> dict[str, Any]:
    """Canonicalize only catalog renderings; retain every physical signature."""

    normalized = deepcopy(value)
    for table in normalized["tables"]:
        table_name = str(table["name"])
        for column in table.get("columns", []):
            column.setdefault("generation", None)
            column.setdefault("identity", None)
        for kind, prefix in (("unique_constraints", "uq"), ("foreign_keys", "fk")):
            for constraint in table[kind]:
                if constraint["name"] is None:
                    constraint["name"] = _postgres_generated_constraint_name(
                        prefix, table_name, tuple(constraint["columns"])
                    )
        for constraint in table["checks"]:
            name = constraint["name"]
            if name is None:
                raise RuntimeError(
                    f"anonymous CHECK on {table_name} lacks canonical name policy"
                )
            constraint["sql"] = parsed_checks.get((table_name, name), constraint["sql"])
        for index in table["indexes"]:
            name = str(index["name"])
            index["method"] = str(index.get("method") or "btree").lower()
            index["include"] = list(index.get("include") or ())
            index["keys"] = [
                {
                    "column": key[0],
                    "expression": key[1],
                    "direction": key[2],
                    "nulls": key[3],
                }
                for key in (_index_key_tuple(item) for item in _index_keys(index))
            ]
            index.pop("columns", None)
            index["where"] = parsed_indexes.get((table_name, name), index["where"])
        for kind in ("unique_constraints", "foreign_keys", "checks", "indexes"):
            table[kind].sort(
                key=lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True)
            )
    return normalized


def _short_exact_value(value: Any) -> str:
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True)
    if len(rendered) <= 240:
        return rendered
    digest = hashlib.sha256(rendered.encode()).hexdigest()
    return f"sha256={digest}:bytes={len(rendered.encode())}"


def _exact_tree_diff(expected: Any, actual: Any, path: str = "$") -> list[str]:
    if isinstance(expected, dict) and isinstance(actual, dict):
        errors: list[str] = []
        for key in sorted(set(expected) - set(actual)):
            errors.append(f"{path}.{key}:missing")
        for key in sorted(set(actual) - set(expected)):
            errors.append(f"{path}.{key}:unexpected")
        for key in sorted(set(expected) & set(actual)):
            errors.extend(_exact_tree_diff(expected[key], actual[key], f"{path}.{key}"))
        return errors
    if isinstance(expected, list) and isinstance(actual, list):
        errors = []
        if len(expected) != len(actual):
            errors.append(
                f"{path}:length:expected={len(expected)}:actual={len(actual)}"
            )
        for offset, (expected_item, actual_item) in enumerate(
            zip(expected, actual, strict=False)
        ):
            errors.extend(
                _exact_tree_diff(expected_item, actual_item, f"{path}[{offset}]")
            )
        return errors
    if type(expected) is not type(actual) or expected != actual:
        return [
            f"{path}:expected={_short_exact_value(expected)}:"
            f"actual={_short_exact_value(actual)}"
        ]
    return []


def _physical_snapshot_exact_errors(
    expected: dict[str, Any],
    metadata: MetaData,
    *,
    parsed_expected_checks: Mapping[tuple[str, str], str],
    parsed_actual_checks: Mapping[tuple[str, str], str],
    parsed_expected_indexes: Mapping[tuple[str, str], str],
    parsed_actual_indexes: Mapping[tuple[str, str], str],
) -> list[str]:
    # Match the persisted snapshot boundary so SQLAlchemy quoted-name/string
    # subclasses cannot create a false deep diff after JSON serialization.
    actual = json.loads(json.dumps(physical_snapshot(metadata), sort_keys=True))
    normalized_expected = _normalized_physical_snapshot(
        expected,
        parsed_checks=parsed_expected_checks,
        parsed_indexes=parsed_expected_indexes,
    )
    normalized_actual = _normalized_physical_snapshot(
        actual,
        parsed_checks=parsed_actual_checks,
        parsed_indexes=parsed_actual_indexes,
    )
    return [
        f"database:physical-snapshot-exact:{item}"
        for item in _exact_tree_diff(normalized_expected, normalized_actual)
    ]


def _alembic_revisions(database_url: str) -> tuple[str | None, str | None]:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    expected = ScriptDirectory.from_config(config).get_current_head()
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            actual = MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()
    return expected, actual


def check(database_url: str | None, *, orm: bool = True) -> dict[str, Any]:
    manifest = load_manifest()
    current = extract_manifest(DEFAULT_DOCUMENT)
    errors: list[str] = []
    physical_contract, helper_contract = _physical_contract(manifest)
    if current != manifest:
        errors.append("document:frozen-manifest-drift")
    orm_table_count: int | None = None
    if orm:
        from quantfoundry.api.app import Base

        orm_table_count = len(Base.metadata.tables)
        orm_dialect = (
            "postgresql" if database_url and "postgresql" in database_url else "sqlite"
        )
        errors.extend(
            _check_metadata(
                manifest, Base.metadata, orm_dialect, "orm", physical_contract
            )
        )
    database_table_count: int | None = None
    database_catalog_table_count: int | None = None
    database_internal_tables: list[str] | None = None
    expected_revision: str | None = None
    actual_revision: str | None = None
    physical_snapshot_exact: bool | None = None
    if database_url:
        database_metadata, dialect = _database_metadata(database_url)
        database_catalog_table_count = len(database_metadata.tables)
        database_internal_tables = sorted(
            set(database_metadata.tables) & _APPROVED_INTERNAL_DATABASE_TABLES
        )
        database_table_count = database_catalog_table_count - len(
            database_internal_tables
        )
        parsed_expected_checks = (
            _postgres_parsed_expected_checks(database_url, physical_contract)
            if dialect == "postgresql"
            else None
        )
        parsed_actual_checks = (
            _postgres_actual_checks(database_url) if dialect == "postgresql" else None
        )
        parsed_expected_indexes = (
            _postgres_parsed_expected_indexes(database_url, physical_contract)
            if dialect == "postgresql"
            else None
        )
        parsed_actual_indexes = (
            _postgres_actual_indexes(database_url) if dialect == "postgresql" else None
        )
        errors.extend(
            _check_metadata(
                manifest,
                database_metadata,
                dialect,
                "database",
                physical_contract,
                parsed_expected_checks,
                parsed_actual_checks,
                parsed_expected_indexes,
                parsed_actual_indexes,
            )
        )
        if dialect == "postgresql":
            physical_errors = _physical_snapshot_exact_errors(
                json.loads(PHYSICAL_PATH.read_text(encoding="utf-8")),
                database_metadata,
                parsed_expected_checks=parsed_expected_checks or {},
                parsed_actual_checks=parsed_actual_checks or {},
                parsed_expected_indexes=parsed_expected_indexes or {},
                parsed_actual_indexes=parsed_actual_indexes or {},
            )
            physical_snapshot_exact = not physical_errors
            errors.extend(physical_errors)
            errors.extend(_check_postgres_helpers(database_url, helper_contract))
        expected_revision, actual_revision = _alembic_revisions(database_url)
        if expected_revision != actual_revision:
            errors.append(
                f"alembic:revision:expected={expected_revision}:actual={actual_revision}"
            )
    return {
        "ok": not errors,
        "manifest_path": str(MANIFEST_PATH),
        "manifest_tables": manifest["table_count"],
        "manifest_columns": manifest["column_count"],
        "locator_helper_sha256": helper_contract["sha256"],
        "orm_tables": orm_table_count,
        "database_tables": database_table_count,
        "database_catalog_tables": database_catalog_table_count,
        "database_internal_tables": database_internal_tables,
        "physical_snapshot_exact": physical_snapshot_exact,
        "alembic_expected": expected_revision,
        "alembic_actual": actual_revision,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv("QF_DATABASE_URL"))
    parser.add_argument("--no-orm", action="store_true")
    args = parser.parse_args()
    result = check(args.database_url, orm=not args.no_orm)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
