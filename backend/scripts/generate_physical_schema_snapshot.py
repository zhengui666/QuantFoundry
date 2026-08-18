"""Generate immutable Alembic physical-schema snapshots."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
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
_IMPLICIT_SERIAL_DEFAULT = re.compile(
    r"^nextval\('(?P<sequence>(?:[^']|'')+)'::regclass\)$"
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
    if isinstance(effective, postgresql.JSON):
        return {"name": "json"}
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
        return {"name": "timestamptz" if effective.timezone else "timestamp"}
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
        return {"name": "jsonb" if name != "json" else "json"}
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


def _canonical_sql(value: str, column: Any) -> str:
    rendered = re.sub(r"\s+", " ", value).strip()
    while rendered.startswith("(") and rendered.endswith(")"):
        depth = 0
        quote: str | None = None
        closes_at_end = True
        for index, char in enumerate(rendered):
            if quote is not None:
                if char == quote and rendered[index - 1] != "\\":
                    quote = None
                continue
            if char in "'\"":
                quote = char
            elif char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0 and index != len(rendered) - 1:
                    closes_at_end = False
                    break
        if not closes_at_end or depth != 0:
            break
        rendered = rendered[1:-1].strip()
    type_name = _type_spec(column.type)["name"]
    casts = {
        "varchar": r"character varying|varchar|text",
        "char": r"character|bpchar|char",
        "integer": r"integer|int4",
        "bigint": r"bigint|int8",
        "smallint": r"smallint|int2",
        "numeric": r"numeric",
        "boolean": r"boolean|bool",
        "date": r"date",
        "timestamptz": r"timestamp\s+with\s+time\s+zone|timestamptz",
    }.get(type_name)
    if casts:
        rendered = re.sub(
            rf"::(?:pg_catalog\.)?(?:{casts})(?=\s|\)|$)",
            "",
            rendered,
            flags=re.IGNORECASE,
        )
    return rendered


def _server_default_spec(column: Any, *, reflected: bool = False) -> str | None:
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
    if server_default_arg is not None and _autoincrement_spec(
        column, reflected=reflected
    ):
        rendered = str(server_default_arg).strip()
        match = _IMPLICIT_SERIAL_DEFAULT.fullmatch(rendered)
        if match is not None:
            sequence = match.group("sequence").split(".")[-1].replace('"', "")
            if sequence == f"{column.table.name}_{column.name}_seq":
                return None
    return (
        _canonical_sql(str(server_default_arg), column)
        if server_default_arg is not None
        else None
    )


def _generation_spec(column: Any) -> dict[str, Any] | None:
    computed = getattr(column, "computed", None)
    if computed is None:
        return None
    return {
        "sqltext": str(
            computed.sqltext.compile(
                dialect=postgresql.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        ).strip(),
        "persisted": True if getattr(computed, "persisted", None) is None else computed.persisted,
    }


def _identity_spec(column: Any) -> dict[str, Any] | None:
    identity = getattr(column, "identity", None)
    if identity is None:
        return None
    type_name = _type_spec(column.type)["name"]
    limits = {
        "smallint": (-32768, 32767),
        "integer": (-2147483648, 2147483647),
        "bigint": (-9223372036854775808, 9223372036854775807),
    }.get(type_name)
    increment = getattr(identity, "increment", None)
    if increment is None:
        increment = 1
    minimum, maximum = limits or (None, None)
    minvalue = getattr(identity, "minvalue", None)
    maxvalue = getattr(identity, "maxvalue", None)
    if minvalue is None:
        minvalue = minimum if increment < 0 else 1
    if maxvalue is None:
        maxvalue = maximum if increment > 0 else -1
    start = getattr(identity, "start", None)
    if start is None:
        start = minvalue if increment > 0 else maxvalue
    cache = getattr(identity, "cache", None)
    return {
        "always": bool(getattr(identity, "always", False)),
        "start": start,
        "increment": increment,
        "minvalue": minvalue,
        "maxvalue": maxvalue,
        "cycle": bool(getattr(identity, "cycle", False)),
        "cache": 1 if cache is None else cache,
    }


def _autoincrement_spec(column: Any, *, reflected: bool = False) -> bool:
    table = column.table
    if reflected:
        server_default = getattr(column, "server_default", None)
        default = getattr(server_default, "arg", None)
        return bool(
            getattr(column, "identity", None) is not None
            or (
                default is not None
                and _IMPLICIT_SERIAL_DEFAULT.fullmatch(str(default).strip()) is not None
            )
        )
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


def _compiled_sql(expression: Any) -> str:
    return str(
        expression.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    ).strip()


def snapshot(metadata: MetaData, *, reflected: bool = False) -> dict[str, Any]:
    from quantfoundry.contracts.events.locator import (
        POSTGRES_LOCATOR_CONTRACT_SHA256,
        POSTGRES_LOCATOR_HELPERS,
        locator_truth_table,
    )

    tables: list[dict[str, Any]] = []
    seen_tables: set[tuple[str, str]] = set()
    for table in sorted(
        metadata.tables.values(), key=lambda item: (item.schema or "public", item.name)
    ):
        if table.name == "alembic_version" or table.schema not in {None, "public"}:
            continue
        schema = table.schema or "public"
        identity = (schema, table.name)
        if identity in seen_tables:
            raise ValueError(
                f"duplicate physical table identity: {schema}.{table.name}"
            )
        seen_tables.add(identity)
        columns = []
        for column in table.columns:
            columns.append(
                {
                    "name": column.name,
                    "type": _type_spec(column.type),
                    "nullable": column.nullable,
                    "primary_key": column.primary_key,
                    "autoincrement": _autoincrement_spec(column, reflected=reflected),
                    "server_default": _server_default_spec(column, reflected=reflected),
                    "generation": _generation_spec(column),
                    "identity": _identity_spec(column),
                }
            )
        unique_constraints = sorted(
            [
                {
                    "name": constraint.name,
                    "columns": [column.name for column in constraint.columns],
                    "deferrable": constraint.deferrable,
                    "initially": constraint.initially,
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
                    "onupdate": constraint.onupdate,
                    "deferrable": constraint.deferrable,
                    "initially": constraint.initially,
                    "match": constraint.match,
                }
                for constraint in table.foreign_key_constraints
            ],
            key=lambda item: (item["name"] or "", item["columns"]),
        )
        checks = sorted(
            [
                {"name": constraint.name, "sql": _compiled_sql(constraint.sqltext)}
                for constraint in table.constraints
                if isinstance(constraint, CheckConstraint)
            ],
            key=lambda item: (item["name"] or "", item["sql"]),
        )
        indexes = []
        for index in sorted(
            table.indexes,
            key=lambda item: (
                item.name or "",
                tuple(str(expression) for expression in item.expressions),
                bool(item.unique),
            ),
        ):
            where = index.dialect_options["postgresql"].get("where")
            include = index.dialect_options["postgresql"].get("include") or []
            method = index.dialect_options["postgresql"].get("using") or "btree"
            postgres_options = index.dialect_options["postgresql"]
            operator_classes = postgres_options.get("ops") or {}
            indexes.append(
                {
                    "name": index.name,
                    "unique": index.unique,
                    "method": method,
                    "keys": [
                        _index_key_spec(expression) for expression in index.expressions
                    ],
                    "include": list(include),
                    "where": _compiled_sql(where) if where is not None else None,
                    "operator_classes": sorted(
                        (str(key), str(value))
                        for key, value in operator_classes.items()
                    ),
                    "nulls_not_distinct": postgres_options.get("nulls_not_distinct"),
                    "with": postgres_options.get("with"),
                    "tablespace": postgres_options.get("tablespace"),
                }
            )
        tables.append(
            {
                "schema": schema,
                "name": table.name,
                "primary_key": [column.name for column in table.primary_key.columns],
                "primary_key_constraint": {
                    "name": table.primary_key.name,
                    "deferrable": table.primary_key.deferrable,
                    "initially": table.primary_key.initially,
                },
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
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--orm", action="store_true")
    source.add_argument("--database-url", default=os.getenv("QF_DATABASE_URL"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if bool(args.orm) == bool(args.database_url):
        parser.error("provide exactly one of --orm or --database-url/QF_DATABASE_URL")
    if args.orm:
        from quantfoundry.api.app import Base

        metadata = Base.metadata
    else:
        engine = create_engine(args.database_url)
        try:
            metadata = MetaData()
            metadata.reflect(bind=engine)
            if engine.dialect.name != "postgresql":
                raise ValueError("--database-url must target PostgreSQL")
            from scripts.schema_manifest_check import _check_postgres_helpers
            from quantfoundry.contracts.events.locator import (
                POSTGRES_LOCATOR_CONTRACT_SHA256,
                POSTGRES_LOCATOR_HELPERS,
                locator_truth_table,
            )

            helper_contract = {
                "sha256": POSTGRES_LOCATOR_CONTRACT_SHA256,
                "functions": list(POSTGRES_LOCATOR_HELPERS),
                "truth_table": locator_truth_table(),
            }
            errors = _check_postgres_helpers(args.database_url, helper_contract)
            if errors:
                raise RuntimeError(
                    "database locator helper contract mismatch: "
                    + "; ".join(errors[:5])
                )
        finally:
            engine.dispose()
    value = snapshot(metadata, reflected=not args.orm)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=args.output.parent,
            prefix=f".{args.output.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, args.output)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(
        f"wrote {value['table_count']} tables/{value['column_count']} columns "
        f"to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
