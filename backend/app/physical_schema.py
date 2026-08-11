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
    Date,
    DateTime,
    ForeignKeyConstraint,
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
    text,
)
from sqlalchemy.dialects.postgresql import DATERANGE, JSONB
from sqlalchemy.sql.elements import ColumnElement, TextClause

from app.locator_contract import LOCATOR_CHECK_SQL
from app.section14_schema import ContractCheckConstraint

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
    include_sqlite_partial_indexes: bool = True,
    include_server_defaults: bool = True,
) -> MetaData:
    value = json.loads(path.read_text(encoding="utf-8"))
    metadata = MetaData()
    specs = {table["name"]: table for table in value["tables"]}
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
            columns.append(
                Column(
                    column["name"],
                    column_type,
                    nullable=column["nullable"],
                    primary_key=(
                        column["primary_key"]
                        if not table_spec.get("primary_key")
                        else False
                    ),
                    autoincrement=column["autoincrement"],
                    server_default=(
                        text(column["server_default"])
                        if include_server_defaults
                        and column["server_default"] is not None
                        else None
                    ),
                )
            )
        table = Table(table_spec["name"], metadata, *columns)
        if table_spec.get("primary_key"):
            table.append_constraint(
                PrimaryKeyConstraint(
                    *(table.c[name] for name in primary_key),
                    name=f"pk_{table_spec['name']}",
                )
            )
    for table_name, table_spec in specs.items():
        table = metadata.tables[table_name]
        for offset, constraint in enumerate(table_spec["unique_constraints"]):
            name = constraint["name"] or f"uq_{table_name}_frozen_{offset}"
            table.append_constraint(
                UniqueConstraint(*constraint["columns"], name=name[:63])
            )
        if include_checks:
            for offset, constraint in enumerate(table_spec["checks"]):
                name = constraint["name"] or f"ck_{table_name}_frozen_{offset}"
                if name in _SQLITE_CLOSED_CHECKS:
                    table.append_constraint(
                        ContractCheckConstraint(
                            constraint["sql"],
                            sqlite_sql=_SQLITE_CLOSED_CHECKS[name],
                            name=name[:63],
                        )
                    )
                else:
                    table.append_constraint(
                        CheckConstraint(constraint["sql"], name=name[:63])
                    )
        for offset, constraint in enumerate(table_spec["foreign_keys"]):
            name = constraint["name"] or f"fk_{table_name}_frozen_{offset}"
            table.append_constraint(
                ForeignKeyConstraint(
                    constraint["columns"],
                    constraint["targets"],
                    name=name[:63],
                    ondelete=constraint["ondelete"],
                    use_alter=True,
                )
            )
        for index in table_spec["indexes"]:
            expressions: list[ColumnElement[Any] | TextClause] = []
            if "keys" in index:
                for item in index["keys"]:
                    column_name = item.get("column")
                    if isinstance(column_name, str) and column_name in table.c:
                        expressions.append(table.c[column_name])
                    else:
                        expressions.append(text(str(item["expression"])))
            else:
                expressions = [table.c[name] for name in index["columns"]]
            Index(
                index["name"],
                *expressions,
                unique=index["unique"],
                postgresql_using=index.get("method"),
                postgresql_include=index.get("include"),
                postgresql_where=text(index["where"]) if index["where"] else None,
                sqlite_where=(
                    text(index["where"])
                    if index["where"] and include_sqlite_partial_indexes
                    else None
                ),
            )
    return metadata
