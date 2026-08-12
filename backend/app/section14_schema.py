"""Backend Design section 14 physical-schema definitions.

The committed JSON manifest is the independent fact source.  This module maps
that frozen contract to SQLAlchemy metadata; it does not inspect application
models to decide what the contract should contain.
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from psycopg.types.range import Range
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
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import TypeDecorator

from app.locator_contract import (
    JOB_RESULT_REF_CHECK_SQL,
    LOCATOR_CHECK_SQL,
    NEXT_ACTION_CHECK_SQL,
)
from app.public_ids import PUBLIC_ID_PREFIXES

MANIFEST_PATH = Path(__file__).resolve().parents[1] / "schema/section14_manifest.json"
_TYPE_WITH_ARGS = re.compile(r"^(varchar|char|numeric)\((\d+)(?:,(\d+))?\)$")
_FK = re.compile(r"FK\s+([a-z0-9_]+)\(([^)]+)\)", re.IGNORECASE)
_COMPOSITE_FK = re.compile(
    r"FK\s*\(([^)]+)\)\s*(?:->|→)\s*([a-z0-9_]+)\(([^)]+)\)",
    re.IGNORECASE,
)
_UNIQUE_COLUMNS = re.compile(r"UNIQUE\(([^)]+)\)", re.IGNORECASE)
_CHECK_IN = re.compile(r"CHECK (?:in )?([A-Z][A-Z0-9_|]+)$")
_NON_BASELINE_AUTO_CHECKS = frozenset(
    {
        "ck_agent_runs_resume_fencing_token_valid",
        "ck_agent_runs_revision_valid",
        "ck_artifacts_publication_state_valid",
        "ck_audit_chain_heads_revision_valid",
        "ck_data_snapshots_dataset_id_valid",
        "ck_data_snapshots_id_valid",
        "ck_data_sources_id_valid",
        "ck_data_sources_revision_valid",
        "ck_data_sources_status_valid",
        "ck_event_stream_watermarks_last_sequence_valid",
        "ck_experiments_revision_valid",
        "ck_jobs_fencing_token_valid",
        "ck_jobs_resume_fencing_token_valid",
        "ck_model_provider_connections_kind_valid",
        "ck_model_provider_connections_status_valid",
        "ck_records_revision_valid",
        "ck_research_cases_status_valid",
        "ck_setup_bindings_revision_valid",
        "ck_snapshot_partitions_artifact_id_valid",
        "ck_snapshot_partitions_row_count_valid",
        "ck_strategies_status_valid",
        "ck_strategy_versions_state_valid",
        "ck_users_revision_valid",
        "ck_users_role_valid",
        "ck_validations_exposure_count_valid",
        "ck_validations_holdout_state_valid",
        "ck_validations_id_valid",
        "ck_validations_revision_valid",
        "ck_validations_status_valid",
        "ck_workspaces_revision_valid",
        "ck_paper_scheduler_states_scheduler_status_valid",
        "ck_paper_scheduler_states_revision_valid",
    }
)
_OBJECT_TYPE_TO_PUBLIC_ID_KIND = {
    "research_policy": "research_policy",
    "risk_policy": "risk_policy",
    "cost_model": "cost_model",
    "credential": "credential",
    "capability": "capability",
    "dataset": "dataset",
    "snapshot": "snapshot",
    "data_quality_run": "quality_run",
    "data_quality_issue": "quality_issue",
    "research": "research",
    "evidence": "evidence",
    "conclusion": "conclusion",
    "experiment": "experiment",
    "factor": "factor",
    "strategy": "strategy",
    "validation": "validation",
    "exposure": "holdout_exposure",
    "red_team_run": "red_team_run",
    "portfolio": "portfolio",
    "memo": "memo",
    "approval": "approval",
    "paper": "paper",
    "paper_run": "paper_run",
    "paper_order": "paper_order",
    "paper_fill": "paper_fill",
    "review": "performance_review",
    "agent_run": "agent_run",
    "tool_call": "tool_call",
    "job": "job",
    "domain_event": "domain_event",
    "audit_event": "audit_event",
    "artifact": "artifact",
    "notification": "notification",
    "provenance": "provenance",
}
_LEGACY_PUBLIC_ID_COLUMNS = {
    "research_id": "RSCH",
    "experiment_id": "EXP",
    "factor_id": "FAC",
    "strategy_id": "STRAT",
    "validation_id": "VAL",
    "approval_id": "APR",
    "memo_id": "MEMO",
    "paper_id": "PAPER",
    "paper_run_id": "PRUN",
    "agent_run_id": "ARUN",
    "tool_call_id": "TCALL",
    "job_id": "JOB",
    "event_id": "EVT",
    "audit_id": "AUD",
    "artifact_id": "ART",
    "notification_id": "NOTIF",
    "provenance_id": "PROV",
    "snapshot_id": "DS",
    "data_snapshot_id": "DS",
    "dataset_id": "DSSET",
    "cost_model_id": "COST",
    "research_public_id": "RSCH",
    "root_agent_run_public_id": "ARUN",
    "parent_agent_run_public_id": "ARUN",
    "source_experiment_public_id": "EXP",
    "approval_public_id": "APR",
    "result_artifact_public_id": "ART",
    "provenance_public_id": "PROV",
    "job_public_id": "JOB",
    "depends_on_job_public_id": "JOB",
    "strategy_public_id": "STRAT",
    "agent_run_public_id": "ARUN",
    "experiment_public_id": "EXP",
    "output_artifact_public_id": "ART",
}


class JSONTextCompat(TypeDecorator[str]):
    """JSONB on PostgreSQL while preserving legacy string-facing handlers."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB(none_as_null=True))
        return dialect.type_descriptor(JSON(none_as_null=True))

    def process_bind_param(self, value: Any, _dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            return json.loads(value)
        return value

    def process_result_value(self, value: Any, _dialect: Any) -> Any:
        if value is None or isinstance(value, str):
            return value
        return json.dumps(value, separators=(",", ":"), sort_keys=True)


class ContractCheckConstraint(CheckConstraint):
    """Canonical PostgreSQL CHECK with an equivalent SQLite predicate."""

    inherit_cache = True

    def __init__(self, sqltext: str, *, sqlite_sql: str, name: str) -> None:
        super().__init__(sqltext, name=name)
        self.sqlite_sql = sqlite_sql


@compiles(ContractCheckConstraint, "sqlite")
def _compile_sqlite_contract_check(
    constraint: ContractCheckConstraint, compiler: Any, **_: Any
) -> str:
    name = compiler.preparer.format_constraint(constraint)
    return f"CONSTRAINT {name} CHECK ({constraint.sqlite_sql})"


class DateRangeCompat(TypeDecorator[Any]):
    """Native PostgreSQL daterange with JSON-compatible SQLite values."""

    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(DATERANGE())
        return dialect.type_descriptor(String())

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, str):
            if not value:
                return None
            if value.startswith("{"):
                value = json.loads(value)
        if isinstance(value, dict):
            start = date.fromisoformat(value["start"])
            end = date.fromisoformat(value["end"])
            if dialect.name == "postgresql":
                return Range(start, end, bounds="[]")
            return json.dumps(value, separators=(",", ":"), sort_keys=True)
        return value

    def process_result_value(self, value: Any, _dialect: Any) -> Any:
        if isinstance(value, Range):
            return {
                "start": value.lower.isoformat() if value.lower is not None else None,
                "end": value.upper.isoformat() if value.upper is not None else None,
            }
        if isinstance(value, str) and value.startswith("{"):
            return json.loads(value)
        return value


_WORKSPACE_NAMESPACE = uuid.UUID("f3e9ad1f-c2ce-4aa5-b218-b72e86d0f504")


def canonical_workspace_id(value: Any) -> str:
    """Return the internal UUID for UUID or deterministic local/bootstrap aliases."""

    if isinstance(value, uuid.UUID):
        return str(value)
    text_value = str(value)
    try:
        return str(uuid.UUID(text_value))
    except ValueError:
        return str(uuid.uuid5(_WORKSPACE_NAMESPACE, text_value))


class WorkspaceScopeId(TypeDecorator[str]):
    """UUID storage with deterministic compatibility for governed local aliases."""

    impl = Uuid(as_uuid=False)
    cache_ok = True

    def process_bind_param(self, value: Any, _dialect: Any) -> str | None:
        if value is None:
            return None
        return canonical_workspace_id(value)

    def process_result_value(self, value: Any, _dialect: Any) -> str | None:
        if value is None:
            return None
        return str(value)


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def sqlalchemy_type(pg_type: str, *, string_compatible_json: bool = False) -> Any:
    match = _TYPE_WITH_ARGS.fullmatch(pg_type)
    if match:
        kind, first, second = match.groups()
        if kind == "varchar":
            return String(int(first))
        if kind == "char":
            return CHAR(int(first))
        return Numeric(int(first), int(second or 0))
    return {
        "uuid": Uuid(as_uuid=True),
        "bigint": BigInteger(),
        "integer": Integer(),
        "smallint": SmallInteger(),
        "boolean": Boolean(),
        "date": Date(),
        "daterange": DateRangeCompat(),
        "timestamptz": DateTime(timezone=True),
        "text": Text(),
        "jsonb": JSONTextCompat()
        if string_compatible_json
        else JSON().with_variant(JSONB(), "postgresql"),
        "bytea": LargeBinary(),
    }[pg_type]


def _existing_contract_type(current: Any, pg_type: str) -> Any:
    """Preserve compatibility decorators only when PostgreSQL type stays exact."""

    if pg_type == "uuid" and isinstance(current, Uuid):
        return current
    if pg_type == "jsonb" and isinstance(current, Text):
        return JSONTextCompat()
    if pg_type == "bigint" and isinstance(current, BigInteger):
        return current
    if pg_type == "smallint" and isinstance(current, SmallInteger):
        return current
    if pg_type == "integer" and type(current) is Integer:
        return current
    if pg_type == "boolean" and isinstance(current, Boolean):
        return current
    if pg_type == "date" and type(current) is Date:
        return current
    if pg_type == "timestamptz" and isinstance(current, DateTime) and current.timezone:
        return current
    return sqlalchemy_type(
        pg_type,
        string_compatible_json=pg_type == "jsonb" and isinstance(current, Text),
    )


def _default_value(column: dict[str, Any]) -> Any:
    raw = column["default"]
    pg_type = column["postgres_type"]
    constraints = column["constraints"]
    if raw in {"NULL", "-"} and column["nullable"]:
        return None
    if raw in {"uuidv7()", "identity"} or pg_type == "uuid":
        return uuid.uuid4
    if raw == "now()" or pg_type == "timestamptz":
        return lambda: datetime.now(UTC)
    if pg_type == "date":
        return date(1970, 1, 1)
    if pg_type == "daterange":
        return None
    if pg_type == "jsonb":
        return list if raw == "[]" else dict
    if pg_type == "boolean":
        return raw.lower() != "false"
    if pg_type in {"integer", "bigint", "smallint"}:
        try:
            return int(raw)
        except ValueError:
            return 1 if "> 0" in constraints or ">0" in constraints else 0
    if pg_type.startswith("numeric"):
        try:
            return Decimal(raw)
        except InvalidOperation:
            return (
                Decimal("1")
                if "> 0" in constraints or ">0" in constraints
                else Decimal("0")
            )
    if pg_type == "bytea":
        return b""
    if raw.startswith("'") and raw.endswith("'"):
        return raw[1:-1]
    if raw not in {"", "-"}:
        return raw
    return ""


def _constraint_name(table: str, suffix: str) -> str:
    value = re.sub(r"[^a-z0-9_]+", "_", suffix.lower()).strip("_")
    return f"ck_{table}_{value}"[:63]


def _public_id_check_sql(name: str, prefix: str) -> str:
    prefix_value = f"{prefix}-"
    payload_start = len(prefix_value) + 1
    allowed_ulid = tuple("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    allowed_hex = tuple("0123456789abcdef")

    def char_in(position: int, values: tuple[str, ...]) -> str:
        literals = ",".join(f"'{value}'" for value in values)
        return f"substr({name},{position},1) IN ({literals})"

    ulid_checks = [
        f"length({name}) = {len(prefix_value) + 26}",
        f"substr({name},1,{len(prefix_value)}) = '{prefix_value}'",
        char_in(payload_start, tuple("01234567")),
    ]
    ulid_checks.extend(
        char_in(payload_start + offset, allowed_ulid) for offset in range(1, 26)
    )
    uuid_checks = [
        f"length({name}) = {len(prefix_value) + 36}",
        f"substr({name},1,{len(prefix_value)}) = '{prefix_value}'",
    ]
    for relative in range(1, 37):
        position = payload_start + relative - 1
        if relative in {9, 14, 19, 24}:
            uuid_checks.append(f"substr({name},{position},1) = '-'")
        elif relative == 15:
            uuid_checks.append(f"substr({name},{position},1) = '4'")
        elif relative == 20:
            uuid_checks.append(char_in(position, tuple("89ab")))
        else:
            uuid_checks.append(char_in(position, allowed_hex))
    return "(" + " AND ".join(ulid_checks) + ") OR (" + " AND ".join(uuid_checks) + ")"


def _typed_public_id_check_sql(
    type_column: str,
    id_column: str,
    mapping: dict[str, str],
    *,
    nullable: bool,
) -> str:
    branches = [
        f"({type_column} = '{object_type}' AND "
        f"({_public_id_check_sql(id_column, PUBLIC_ID_PREFIXES[kind])}))"
        for object_type, kind in mapping.items()
    ]
    if nullable:
        branches.insert(0, f"({type_column} IS NULL AND {id_column} IS NULL)")
    return "COALESCE((" + " OR ".join(branches) + "), FALSE)"


def _check_sql(column: dict[str, Any]) -> str | None:
    name = column["name"]
    text = re.sub(r",\s*INDEX(?:\([^)]*\))?\s*$", "", column["constraints"]).strip()
    enum = _CHECK_IN.search(text)
    if enum:
        values = ", ".join(f"'{item}'" for item in enum.group(1).split("|"))
        return f"{name} IN ({values})"
    mixed_case_enum = re.search(
        r"CHECK in ([A-Za-z][A-Za-z-]*(?:,[A-Za-z][A-Za-z-]*)+)$", text
    )
    if mixed_case_enum:
        values = ", ".join(f"'{item}'" for item in mixed_case_enum.group(1).split(","))
        return f"{name} IN ({values})"
    if "CHECK 0..1" in text:
        return f"{name} >= 0 AND {name} <= 1"
    if "CHECK > 0" in text or "CHECK >0" in text:
        return f"{name} > 0"
    if "CHECK >= 0" in text or "CHECK >=0" in text:
        return f"{name} >= 0"
    if "CHECK >=1" in text:
        return f"{name} >= 1"
    exact = re.search(r"CHECK = ([A-Z][A-Z0-9_]*)", text)
    if exact:
        return f"{name} = '{exact.group(1)}'"
    if "CHECK = false" in text:
        return f"{name} = FALSE"
    exact_id = re.search(r"CHECK exact (?:R2 DatasetId|([A-Z]+)) grammar", text)
    if exact_id:
        prefix = exact_id.group(1) or "DSSET"
        if prefix in PUBLIC_ID_PREFIXES.values():
            return _public_id_check_sql(name, prefix)
    return None


def _append_contract_constraints(
    table: Table, spec: dict[str, Any], *, workspace_scoped: bool
) -> None:
    replaced_checks = {
        "agent_runs": "ck_agent_runs_object_id_type_prefix",
        "notifications": "ck_notifications_object_id_type_prefix",
    }
    replaced_name = replaced_checks.get(table.name)
    if replaced_name is not None:
        for constraint in list(table.constraints):
            if constraint.name == replaced_name:
                table.constraints.discard(constraint)
    existing_names = {
        constraint.name for constraint in table.constraints if constraint.name
    }
    existing_foreign_keys = {
        (
            tuple(element.parent.name for element in constraint.elements),
            tuple(element.target_fullname for element in constraint.elements),
        )
        for constraint in table.foreign_key_constraints
    }
    existing_unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }
    for column in spec["columns"]:
        constraints = column["constraints"]
        check_sql = _check_sql(column)
        if check_sql:
            name = _constraint_name(table.name, f"{column['name']}_valid")
            if name not in existing_names and name not in _NON_BASELINE_AUTO_CHECKS:
                table.append_constraint(CheckConstraint(check_sql, name=name))
                existing_names.add(name)
        composite_match = _COMPOSITE_FK.search(constraints)
        plain_match = _FK.search(constraints) if composite_match is None else None
        if composite_match is not None or plain_match is not None:
            if composite_match is not None:
                local_columns = tuple(
                    item.strip() for item in composite_match.group(1).split(",")
                )
                target_name = composite_match.group(2)
                target_column_names = tuple(
                    item.strip() for item in composite_match.group(3).split(",")
                )
                target_columns = tuple(
                    f"{target_name}.{item}" for item in target_column_names
                )
            else:
                assert plain_match is not None
                target_name = plain_match.group(1)
                target_column = plain_match.group(2).strip()
                target = table.metadata.tables.get(target_name)
                scoped = (
                    column["name"] != "workspace_id"
                    and "workspace_id" in table.c
                    and target is not None
                    and "workspace_id" in target.c
                )
                local_columns = (
                    ("workspace_id", column["name"]) if scoped else (column["name"],)
                )
                target_columns = (
                    (f"{target_name}.workspace_id", f"{target_name}.{target_column}")
                    if scoped
                    else (f"{target_name}.{target_column}",)
                )
            name = f"fk_{table.name}_{column['name']}_{target_name}"[:63]
            signature = (local_columns, target_columns)
            if name not in existing_names and signature not in existing_foreign_keys:
                table.append_constraint(
                    ForeignKeyConstraint(
                        list(local_columns),
                        list(target_columns),
                        name=name,
                        use_alter=True,
                    )
                )
                existing_names.add(name)
                existing_foreign_keys.add(signature)
        unique_matches = list(_UNIQUE_COLUMNS.finditer(constraints))
        for unique_match in unique_matches:
            columns = [item.strip() for item in unique_match.group(1).split(",")]
            name = f"uq_{table.name}_{'_'.join(columns)}"[:63]
            remainder = constraints[unique_match.end() :].lstrip()
            where_match = re.match(r"WHERE\s+([a-z0-9_]+)", remainder, re.IGNORECASE)
            if where_match and all(item in table.c for item in columns):
                predicate = where_match.group(1)
                index_name = f"ux_{table.name}_{'_'.join(columns)}_{predicate}"[:63]
                if index_name not in {str(index.name) for index in table.indexes}:
                    Index(
                        index_name,
                        *(table.c[item] for item in columns),
                        unique=True,
                        sqlite_where=text(predicate),
                        postgresql_where=text(predicate),
                    )
                continue
            if (
                name not in existing_names
                and tuple(columns) not in existing_unique_columns
                and all(item in table.c for item in columns)
            ):
                table.append_constraint(UniqueConstraint(*columns, name=name))
                existing_names.add(name)
                existing_unique_columns.add(tuple(columns))
        if (
            not unique_matches
            and re.search(r"(?:^|,\s*)UNIQUE(?:,|$)", constraints)
            and "partial unique" not in constraints.lower()
        ):
            name = f"uq_{table.name}_{column['name']}"[:63]
            if (
                name not in existing_names
                and (column["name"],) not in existing_unique_columns
            ):
                table.append_constraint(UniqueConstraint(column["name"], name=name))
                existing_names.add(name)
                existing_unique_columns.add((column["name"],))
    typed_public_id_checks: dict[str, str] = {}
    if table.name == "portfolio_scenarios":
        typed_public_id_checks["baseline_ref"] = (
            "COALESCE(((baseline_type = 'EMPTY' AND baseline_ref IS NULL) OR "
            f"(baseline_type = 'SCENARIO' AND ({_public_id_check_sql('baseline_ref', 'PORT')})) OR "
            f"(baseline_type = 'PAPER' AND ({_public_id_check_sql('baseline_ref', 'PAPER')}))), FALSE)"
        )
    elif table.name == "approval_requests":
        typed_public_id_checks["subject_id"] = _typed_public_id_check_sql(
            "subject_type",
            "subject_id",
            {
                "STRATEGY_VERSION": "strategy",
                "VALIDATION": "validation",
                "PAPER": "paper",
            },
            nullable=False,
        )
    for column_name, check_sql in typed_public_id_checks.items():
        name = _constraint_name(table.name, f"{column_name}_type_prefix")
        if name not in existing_names:
            table.append_constraint(CheckConstraint(check_sql, name=name))
            existing_names.add(name)
    closed_checks: list[CheckConstraint] = []
    if table.name in {"agent_runs", "notifications"}:
        closed_checks.append(
            ContractCheckConstraint(
                LOCATOR_CHECK_SQL.format(allow_null="TRUE"),
                sqlite_sql=LOCATOR_CHECK_SQL.format(allow_null="1"),
                name=f"ck_{table.name}_locator_quartet",
            )
        )
    elif table.name in {"audit_events", "domain_events"}:
        closed_checks.append(
            ContractCheckConstraint(
                LOCATOR_CHECK_SQL.format(allow_null="FALSE"),
                sqlite_sql=LOCATOR_CHECK_SQL.format(allow_null="0"),
                name=f"ck_{table.name}_locator_quartet",
            )
        )
    if table.name == "jobs":
        closed_checks.append(
            ContractCheckConstraint(
                JOB_RESULT_REF_CHECK_SQL,
                sqlite_sql="result_ref IS NULL OR qf_job_result_ref_valid(result_ref)",
                name="ck_jobs_result_ref_closed",
            )
        )
    elif table.name == "agent_runs":
        closed_checks.append(
            ContractCheckConstraint(
                NEXT_ACTION_CHECK_SQL,
                sqlite_sql="next_action IS NULL OR qf_next_action_valid(next_action)",
                name="ck_agent_runs_next_action_closed",
            )
        )
    if table.name == "records":
        record_key_sql = (
            "COALESCE(("
            + " OR ".join(
                (
                    "(kind = 'settings' AND record_key = 'SETTINGS-DEFAULT')",
                    "(kind = 'artifact' AND "
                    f"({_public_id_check_sql('record_key', 'ART')}))",
                    "(kind = 'provenance' AND "
                    f"({_public_id_check_sql('record_key', 'PROV')}))",
                    "(kind = 'memo' AND "
                    f"({_public_id_check_sql('record_key', 'MEMO')}))",
                )
            )
            + "), FALSE)"
        )
        closed_checks.append(
            CheckConstraint(
                record_key_sql,
                name="ck_records_kind_record_key",
            )
        )
    elif table.name == "setup_bindings":
        closed_checks.append(
            CheckConstraint(
                "settings_record_id = 'SETTINGS-DEFAULT'",
                name="ck_setup_bindings_settings_record_id",
            )
        )
    for constraint in closed_checks:
        constraint_name = constraint.name
        if constraint_name is not None and constraint_name not in existing_names:
            table.append_constraint(constraint)
            existing_names.add(constraint_name)
    pk_columns: list[str] = []
    for column in spec["columns"]:
        constraints = column["constraints"]
        if constraints == "PK" or constraints.startswith("PK "):
            pk_columns.append(column["name"])
        composite = re.search(r"PK\(([^)]+)\)", constraints)
        if composite:
            pk_columns.extend(item.strip() for item in composite.group(1).split(","))
    pk_columns = list(dict.fromkeys(pk_columns))
    current_pk = [column.name for column in table.primary_key.columns]
    if pk_columns and current_pk != pk_columns:
        old_pk = table.primary_key
        table.constraints.discard(old_pk)
        for column in table.c:
            column.primary_key = column.name in pk_columns
            if len(pk_columns) > 1:
                column.autoincrement = False
        table.append_constraint(
            PrimaryKeyConstraint(
                *(table.c[name] for name in pk_columns),
                name=f"pk_{table.name}",
            )
        )

    existing_indexes = {
        str(index.name) for index in table.indexes if index.name is not None
    }
    for column in spec["columns"]:
        constraints = column["constraints"]
        if "INDEX" not in constraints:
            continue
        columns = [column["name"]]
        composite = re.search(r"INDEX\(([^)]+)\)", constraints)
        if composite:
            columns = [item.strip() for item in composite.group(1).split(",")]
        name = f"ix_{table.name}_{'_'.join(columns)}"[:63]
        if name not in existing_indexes and all(item in table.c for item in columns):
            Index(name, *(table.c[item] for item in columns))
            existing_indexes.add(name)


def augment_section14_metadata(metadata: MetaData) -> None:
    """Make all frozen section-14 tables/columns explicit in ORM metadata."""

    manifest = load_manifest()
    specs = {table["name"]: table for table in manifest["tables"]}
    for table_name, spec in specs.items():
        table = metadata.tables.get(table_name)
        if table is None:
            table = Table(table_name, metadata)
        for column in spec["columns"]:
            name = column["name"]
            if name in table.c:
                current_type = table.c[name].type
                table.c[name].type = (
                    WorkspaceScopeId()
                    if name == "workspace_id"
                    else _existing_contract_type(current_type, column["postgres_type"])
                )
                table.c[name].nullable = column["nullable"]
                continue
            constraints = column["constraints"]
            is_primary = constraints == "PK" or constraints.startswith("PK ")
            table.append_column(
                Column(
                    name,
                    WorkspaceScopeId()
                    if name == "workspace_id"
                    else sqlalchemy_type(column["postgres_type"]),
                    primary_key=is_primary,
                    nullable=False if is_primary else column["nullable"],
                    default=None if column["nullable"] else _default_value(column),
                    info={"section14": column},
                )
            )
        formal_columns = {column["name"] for column in spec["columns"]}
        existing_check_names = {
            constraint.name for constraint in table.constraints if constraint.name
        }
        for name, prefix in _LEGACY_PUBLIC_ID_COLUMNS.items():
            if name in formal_columns or name not in table.c:
                continue
            legacy_column = table.c[name]
            if not isinstance(legacy_column.type, String):
                continue
            legacy_column.type = String(len(prefix) + 37)
            check_name = _constraint_name(table.name, f"{name}_valid")
            check_sql = _check_sql(
                {"name": name, "constraints": f"CHECK exact {prefix} grammar"}
            )
            if check_sql is not None and check_name not in existing_check_names:
                table.append_constraint(CheckConstraint(check_sql, name=check_name))
                existing_check_names.add(check_name)
    workspace_table = metadata.tables.get("workspaces")
    if workspace_table is not None:
        workspace_table.c.id.type = WorkspaceScopeId()
    for table in metadata.tables.values():
        if "workspace_id" in table.c:
            table.c.workspace_id.type = WorkspaceScopeId()
    # A workspace-owned child must never retain a one-column FK to another
    # workspace-owned aggregate.  Every such relation is reconstructed from
    # the frozen manifest as (workspace_id, id).
    formal_names = set(specs)
    for table_name in formal_names:
        table = metadata.tables[table_name]
        if "workspace_id" not in table.c:
            continue
        for constraint in list(table.foreign_key_constraints):
            local_columns = tuple(
                element.parent.name for element in constraint.elements
            )
            target_tables = {
                element.target_fullname.split(".", 1)[0]
                for element in constraint.elements
            }
            if "workspace_id" in local_columns or len(target_tables) != 1:
                continue
            target_name = next(iter(target_tables))
            target = metadata.tables.get(target_name)
            if target is None:
                continue
            if "workspace_id" not in target.c:
                continue
            table.constraints.discard(constraint)
            for element in constraint.elements:
                table.foreign_keys.discard(element)
                element.parent.foreign_keys.discard(element)
    # Constraints are appended after all targets exist, including cyclic FKs.
    for table_name, spec in specs.items():
        table = metadata.tables[table_name]
        _append_contract_constraints(
            table, spec, workspace_scoped="workspace_id" in table.c
        )


def section14_table_names() -> frozenset[str]:
    return frozenset(table["name"] for table in load_manifest()["tables"])
