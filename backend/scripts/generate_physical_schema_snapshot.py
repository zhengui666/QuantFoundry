"""Generate immutable Alembic physical-schema snapshots."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import (
    CHAR,
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Integer,
    LargeBinary,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    create_engine,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.schema import Column as SchemaColumn

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_INDEX_SUFFIX = re.compile(
    r"^(?P<base>.*?)(?:\s+(?P<direction>ASC|DESC))?"
    r"(?:\s+NULLS\s+(?P<nulls>FIRST|LAST))?$",
    re.IGNORECASE,
)


def _type_spec(type_: Any) -> dict[str, Any]:
    effective = type_.dialect_impl(postgresql.dialect())
    if type_.__class__.__name__ == "WorkspaceScopeId":
        return {"name": "uuid"}
    if type_.__class__.__name__ == "DateRangeCompat":
        return {"name": "daterange"}
    if (
        isinstance(effective, postgresql.JSONB)
        or type_.__class__.__name__ == "JSONTextCompat"
    ):
        return {"name": "jsonb"}
    if isinstance(effective, Uuid):
        return {"name": "uuid"}
    if isinstance(effective, postgresql.DATERANGE):
        return {"name": "daterange"}
    if isinstance(effective, BigInteger):
        return {"name": "bigint"}
    if isinstance(effective, SmallInteger):
        return {"name": "smallint"}
    if isinstance(effective, Integer):
        return {"name": "integer"}
    if isinstance(effective, Boolean):
        return {"name": "boolean"}
    if isinstance(effective, DateTime):
        return {"name": "timestamptz"}
    if isinstance(effective, Date):
        return {"name": "date"}
    if isinstance(effective, Text):
        return {"name": "text"}
    if isinstance(effective, LargeBinary):
        return {"name": "bytea"}
    if isinstance(effective, Numeric):
        return {
            "name": "numeric",
            "precision": effective.precision,
            "scale": effective.scale,
        }
    if isinstance(effective, CHAR):
        return {"name": "char", "length": effective.length}
    if isinstance(effective, String):
        return {"name": "varchar", "length": effective.length}
    name = effective.__class__.__name__.lower()
    if name in {"jsonb", "json", "jsontextcompat"}:
        return {"name": "jsonb"}
    if name in {"uuid", "pguuid"}:
        return {"name": "uuid"}
    if name == "daterange":
        return {"name": "daterange"}
    aliases = {
        "biginteger": "bigint",
        "smallinteger": "smallint",
        "integer": "integer",
        "boolean": "boolean",
        "date": "date",
        "datetime": "timestamptz",
        "text": "text",
        "largebinary": "bytea",
        "bytea": "bytea",
        "numeric": "numeric",
        "string": "varchar",
        "varchar": "varchar",
        "char": "char",
    }
    normalized = aliases.get(name)
    if normalized is None:
        raise ValueError(f"unsupported physical type {type_!r}/{effective!r}")
    result: dict[str, Any] = {"name": normalized}
    if normalized in {"varchar", "char"}:
        result["length"] = getattr(effective, "length", None)
    if normalized == "numeric":
        result["precision"] = getattr(effective, "precision", None)
        result["scale"] = getattr(effective, "scale", None)
    return result


def _server_default_spec(column: Any) -> str | None:
    if getattr(column, "computed", None) is not None:
        return None
    if getattr(column, "identity", None) is not None:
        return None
    server_default = column.server_default
    server_default_arg = (
        getattr(server_default, "arg", None) if server_default is not None else None
    )
    if server_default is not None and server_default_arg is None:
        raise ValueError(
            f"unsupported server default for {column.table.name}.{column.name}"
        )
    return str(server_default_arg) if server_default_arg is not None else None


def _generation_spec(column: Any) -> dict[str, Any] | None:
    computed = getattr(column, "computed", None)
    if computed is None:
        return None
    return {
        "sqltext": str(computed.sqltext),
        "persisted": getattr(computed, "persisted", None),
    }


def _identity_spec(column: Any) -> dict[str, Any] | None:
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


def _autoincrement_spec(column: Any) -> bool:
    table = column.table
    return bool(
        column.autoincrement is True
        or (
            column.autoincrement == "auto"
            and column.primary_key
            and len(table.primary_key.columns) == 1
            and _type_spec(column.type)["name"] in {"integer", "bigint", "smallint"}
        )
    )


def _index_key_spec(expression: Any) -> dict[str, Any]:
    compiled = str(
        expression.compile(
            dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}
        )
    ).strip()
    match = _INDEX_SUFFIX.fullmatch(compiled)
    if match is None:
        raise ValueError(f"unsupported index expression rendering: {compiled}")
    element = getattr(expression, "element", expression)
    name = element.name if isinstance(element, SchemaColumn) else None
    base = match.group("base").strip()
    if isinstance(name, str):
        table_name = getattr(getattr(element, "table", None), "name", None)
        if base in {name, f"{table_name}.{name}"}:
            base = name
    direction = (match.group("direction") or "ASC").upper()
    nulls = match.group("nulls")
    return {
        "column": name if isinstance(name, str) and name else None,
        "expression": base,
        "direction": direction,
        "nulls": nulls.upper()
        if nulls
        else ("LAST" if direction == "ASC" else "FIRST"),
    }


def snapshot(metadata: MetaData) -> dict[str, Any]:
    from quantfoundry.contracts.events.locator import (
        POSTGRES_LOCATOR_CONTRACT_SHA256,
        POSTGRES_LOCATOR_HELPERS,
        locator_truth_table,
    )

    tables: list[dict[str, Any]] = []
    for table in sorted(metadata.tables.values(), key=lambda item: item.name):
        if table.name == "alembic_version" or table.schema not in {None, "public"}:
            continue
        columns = []
        for column in table.columns:
            columns.append(
                {
                    "name": column.name,
                    "type": _type_spec(column.type),
                    "nullable": column.nullable,
                    "primary_key": column.primary_key,
                    "autoincrement": _autoincrement_spec(column),
                    "server_default": _server_default_spec(column),
                    "generation": _generation_spec(column),
                    "identity": _identity_spec(column),
                }
            )
        unique_constraints = sorted(
            [
                {
                    "name": constraint.name,
                    "columns": [column.name for column in constraint.columns],
                }
                for constraint in table.constraints
                if isinstance(constraint, UniqueConstraint)
            ],
            key=lambda item: (item["name"] or "", item["columns"]),
        )
        foreign_keys = sorted(
            [
                {
                    "name": constraint.name,
                    "columns": [element.parent.name for element in constraint.elements],
                    "targets": [
                        element.target_fullname for element in constraint.elements
                    ],
                    "ondelete": constraint.ondelete,
                }
                for constraint in table.foreign_key_constraints
            ],
            key=lambda item: (item["name"] or "", item["columns"]),
        )
        checks = sorted(
            [
                {"name": constraint.name, "sql": str(constraint.sqltext)}
                for constraint in table.constraints
                if isinstance(constraint, CheckConstraint)
            ],
            key=lambda item: (item["name"] or "", item["sql"]),
        )
        indexes = []
        for index in sorted(table.indexes, key=lambda item: item.name or ""):
            where = index.dialect_options["postgresql"].get("where")
            include = index.dialect_options["postgresql"].get("include") or []
            method = index.dialect_options["postgresql"].get("using") or "btree"
            indexes.append(
                {
                    "name": index.name,
                    "unique": index.unique,
                    "method": method,
                    "keys": [
                        _index_key_spec(expression) for expression in index.expressions
                    ],
                    "include": list(include),
                    "where": str(where) if where is not None else None,
                }
            )
        tables.append(
            {
                "name": table.name,
                "primary_key": [column.name for column in table.primary_key.columns],
                "columns": columns,
                "unique_constraints": unique_constraints,
                "foreign_keys": foreign_keys,
                "checks": checks,
                "indexes": indexes,
            }
        )
    return {
        "snapshot_version": 1,
        "table_count": len(tables),
        "column_count": sum(len(table["columns"]) for table in tables),
        "locator_helper_contract": {
            "sha256": POSTGRES_LOCATOR_CONTRACT_SHA256,
            "functions": list(POSTGRES_LOCATOR_HELPERS),
            "truth_table": locator_truth_table(),
        },
        "tables": tables,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--orm", action="store_true")
    source.add_argument("--database-url", default=os.getenv("QF_DATABASE_URL"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.orm:
        from quantfoundry.api.app import Base

        metadata = Base.metadata
    else:
        engine = create_engine(args.database_url)
        try:
            metadata = MetaData()
            metadata.reflect(bind=engine)
        finally:
            engine.dispose()
    value = snapshot(metadata)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        f"wrote {value['table_count']} tables/{value['column_count']} columns "
        f"to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
