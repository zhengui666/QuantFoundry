"""Load expected physical-schema artifacts from immutable Alembic snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import (
    CHAR,
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Computed,
    Date,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
    Uuid,
    literal_column,
    text,
)
from sqlalchemy.dialects.postgresql import DATERANGE, JSONB
from sqlalchemy.sql.elements import ColumnElement, TextClause

from quantfoundry.contracts.events.locator import LOCATOR_CHECK_SQL
from quantfoundry.infrastructure.db.schema import ContractCheckConstraint

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


def _type(spec: dict[str, Any]) -> Any:
    name = spec["name"]
    if name == "varchar":
        return String(spec.get("length"))
    if name == "char":
        return CHAR(spec.get("length"))
    if name == "numeric":
        return Numeric(spec.get("precision"), spec.get("scale"))
    if name == "uuid":
        return Uuid(as_uuid=True)
    if name == "bigint":
        return BigInteger()
    if name == "smallint":
        return SmallInteger()
    if name == "integer":
        return Integer()
    if name == "boolean":
        return Boolean()
    if name == "date":
        return Date()
    if name == "timestamptz":
        return DateTime(timezone=True)
    if name == "text":
        return Text()
    if name == "jsonb":
        return JSON(none_as_null=True).with_variant(
            JSONB(none_as_null=True), "postgresql"
        )
    if name == "bytea":
        return LargeBinary()
    if name == "daterange":
        return String().with_variant(DATERANGE(), "postgresql")
    raise ValueError(f"unsupported frozen type {name}")


def load_physical_metadata(
    path: Path,
    *,
    include_checks: bool = True,
    include_sqlite_null_ordering: bool = True,
    include_server_defaults: bool = True,
    sqlite_compatibility: bool = True,
) -> MetaData:
    value = json.loads(path.read_text(encoding="utf-8"))
    metadata = MetaData()
    specs = {table["name"]: table for table in value["tables"]}

    def table_key(table_spec: dict[str, Any]) -> str:
        schema = table_spec.get("schema")
        if sqlite_compatibility:
            return table_spec["name"]
        return f"{schema}.{table_spec['name']}" if schema else table_spec["name"]

    def target_name(target: str) -> str:
        if sqlite_compatibility:
            return target
        table_name, column_name = target.rsplit(".", 1)
        target_spec = specs.get(table_name)
        schema = target_spec.get("schema") if target_spec else None
        return f"{schema}.{target}" if schema else target

    for table_spec in value["tables"]:
        columns = []
        primary_key = table_spec.get("primary_key") or [
            column["name"] for column in table_spec["columns"] if column["primary_key"]
        ]
        primary_count = len(primary_key)
        for column in table_spec["columns"]:
            column_type = _type(column["type"])
            if (
                column["autoincrement"]
                and column["name"] in primary_key
                and primary_count == 1
                and column["type"]["name"] == "bigint"
            ):
                column_type = BigInteger().with_variant(Integer(), "sqlite")
            generation = column.get("generation")
            identity = column.get("identity")
            if generation is not None and identity is not None:
                raise ValueError(
                    f"{table_spec['name']}.{column['name']} cannot be both generated and identity"
                )
            schema_items: list[Any] = []
            if generation is not None:
                schema_items.append(
                    Computed(
                        generation["sqltext"], persisted=generation.get("persisted")
                    )
                )
            if identity is not None:
                identity_options = {
                    key: value
                    for key, value in identity.items()
                    if key != "always" and value is not None
                }
                schema_items.append(
                    Identity(always=bool(identity.get("always")), **identity_options)
                )
            columns.append(
                Column(
                    column["name"],
                    column_type,
                    *schema_items,
                    nullable=column["nullable"],
                    primary_key=(
                        column["primary_key"]
                        if not table_spec.get("primary_key")
                        else False
                    ),
                    autoincrement=column["autoincrement"],
                    server_default=(
                        literal_column(column["server_default"])
                        if not schema_items
                        and include_server_defaults
                        and column["server_default"] is not None
                        else None
                    ),
                )
            )
        table_schema = None if sqlite_compatibility else table_spec.get("schema")
        table = Table(table_spec["name"], metadata, *columns, schema=table_schema)
        if table_spec.get("primary_key"):
            primary_key_spec = table_spec.get("primary_key_constraint") or {}
            table.append_constraint(
                PrimaryKeyConstraint(
                    *(table.c[name] for name in primary_key),
                    name=primary_key_spec.get("name"),
                    deferrable=primary_key_spec.get("deferrable"),
                    initially=primary_key_spec.get("initially"),
                )
            )
    for _table_name, table_spec in specs.items():
        table = metadata.tables[table_key(table_spec)]
        for constraint in table_spec["unique_constraints"]:
            name = constraint["name"]
            table.append_constraint(
                UniqueConstraint(
                    *constraint["columns"],
                    name=name[:63] if name is not None else None,
                    deferrable=constraint.get("deferrable"),
                    initially=constraint.get("initially"),
                )
            )
        if include_checks:
            for constraint in table_spec["checks"]:
                name = constraint["name"]
                if name in _SQLITE_CLOSED_CHECKS:
                    if not isinstance(name, str):
                        raise ValueError("closed CHECK must have a canonical name")
                    table.append_constraint(
                        ContractCheckConstraint(
                            constraint["sql"],
                            sqlite_sql=_SQLITE_CLOSED_CHECKS[name],
                            name=name[:63],
                        )
                    )
                else:
                    table.append_constraint(
                        CheckConstraint(
                            constraint["sql"],
                            name=name[:63] if name is not None else None,
                        )
                    )
        for constraint in table_spec["foreign_keys"]:
            name = constraint["name"]
            table.append_constraint(
                ForeignKeyConstraint(
                    constraint["columns"],
                    [target_name(target) for target in constraint["targets"]],
                    name=name[:63] if name is not None else None,
                    ondelete=constraint.get("ondelete"),
                    onupdate=constraint.get("onupdate"),
                    deferrable=constraint.get("deferrable"),
                    initially=constraint.get("initially"),
                    match=constraint.get("match"),
                    use_alter=True,
                )
            )
        for index in table_spec["indexes"]:
            expressions: list[ColumnElement[Any] | TextClause] = []
            if "keys" in index:
                for item in index["keys"]:
                    column_name = item.get("column")
                    if isinstance(column_name, str) and column_name in table.c:
                        expression: ColumnElement[Any] = table.c[column_name]
                    else:
                        expression = literal_column(str(item["expression"]))
                    direction = str(item.get("direction") or "ASC").upper()
                    nulls = item.get("nulls")
                    if direction == "DESC":
                        expression = expression.desc()
                    elif direction == "ASC":
                        expression = expression.asc()
                    else:
                        raise ValueError(
                            f"unsupported index direction {direction!r} on {index['name']}"
                        )
                    if not include_sqlite_null_ordering:
                        # SQLite rejects PostgreSQL's NULLS FIRST/LAST index syntax.
                        nulls = None
                    if nulls == "FIRST":
                        expression = expression.nulls_first()
                    elif nulls == "LAST":
                        expression = expression.nulls_last()
                    elif nulls is not None:
                        raise ValueError(
                            f"unsupported index NULLS direction {nulls!r} on {index['name']}"
                        )
                    expressions.append(expression)
            else:
                expressions = [table.c[name] for name in index["columns"]]
            Index(
                index["name"],
                *expressions,
                unique=index["unique"],
                postgresql_using=index.get("method"),
                postgresql_include=index.get("include"),
                postgresql_where=text(index["where"]) if index["where"] else None,
                postgresql_ops=dict(index.get("operator_classes") or []),
                postgresql_nulls_not_distinct=index.get("nulls_not_distinct"),
                postgresql_with=index.get("with") or {},
                postgresql_tablespace=index.get("tablespace"),
                sqlite_where=(text(index["where"]) if index["where"] else None),
            )
    return metadata
