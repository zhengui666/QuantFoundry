"""Rebuild the pre-release physical schema from frozen section-14 metadata.

Revision ID: 0016_section14_schema
Revises: 0015_langgraph_checkpoint
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    LargeBinary,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
    Uuid,
    inspect,
    select,
    text,
)

from alembic import op
from quantfoundry.contracts.events.event_contract import EVENT_OBJECT_TYPES
from quantfoundry.contracts.events.locator import (
    POSTGRES_LOCATOR_CONTRACT_SHA256,
    POSTGRES_LOCATOR_FUNCTION_SQL,
    POSTGRES_LOCATOR_JSON_FUNCTION_SQL,
    POSTGRES_NULLABLE_PUBLIC_ID_FUNCTION_SQL,
    job_result_ref_valid,
    locator_quartet_valid,
    next_action_valid,
    register_sqlite_functions,
)
from quantfoundry.domain.value_objects.public_ids import is_public_id
from quantfoundry.infrastructure.db.physical_schema import load_physical_metadata
from quantfoundry.infrastructure.db.schema import (
    JSONTextCompat,
    WorkspaceScopeId,
    canonical_workspace_id,
)

revision = "0016_section14_schema"
down_revision = "0015_langgraph_checkpoint"
branch_labels = None
depends_on = None

HERE = Path(__file__).resolve().parent
CURRENT = HERE / "0016_section14_physical.json"
PREVIOUS = HERE / "0016_pre_section14_physical.json"
_SOURCE_BACKUP_PREFIX = "_qf0016_source_"
_ROUNDTRIP_BACKUP_PREFIX = "_qf0016_roundtrip_"
_BACKUP_PREFIXES = (_SOURCE_BACKUP_PREFIX, _ROUNDTRIP_BACKUP_PREFIX)
_DOMAIN_LOCATOR_CHECK_NAME = "ck_domain_events_locator_quartet"
_DOMAIN_LOCATOR_CHECK_SQL = (
    "qf_event_locator_quartet_valid("
    "object_type, object_id, object_version, object_revision, FALSE)"
)
_POSTGRES_UUIDV7_COMPAT_SQL = """
CREATE OR REPLACE FUNCTION public.uuidv7()
RETURNS uuid
LANGUAGE plpgsql
VOLATILE
AS $$
DECLARE
  timestamp_hex text;
  random_hex text;
BEGIN
  timestamp_hex := lpad(
    to_hex(floor(extract(epoch FROM clock_timestamp()) * 1000)::bigint),
    12,
    '0'
  );
  random_hex := replace(gen_random_uuid()::text, '-', '');
  RETURN (
    substr(timestamp_hex, 1, 8) || '-' ||
    substr(timestamp_hex, 9, 4) || '-' ||
    '7' || substr(random_hex, 1, 3) || '-' ||
    '8' || substr(random_hex, 5, 3) || '-' ||
    substr(random_hex, 9, 12)
  )::uuid;
END;
$$
"""

_PUBLIC_PREFIXES = {
    "RP",
    "RISK",
    "COST",
    "CRED",
    "CAP",
    "DSSET",
    "DS",
    "DQ",
    "DQI",
    "RSCH",
    "EVID",
    "CONC",
    "EXP",
    "FAC",
    "STRAT",
    "VAL",
    "HOLD",
    "RT",
    "PORT",
    "MEMO",
    "APR",
    "PAPER",
    "PRUN",
    "PORD",
    "PFILL",
    "REV",
    "ARUN",
    "TCALL",
    "JOB",
    "EVT",
    "AUD",
    "ART",
    "NOTIF",
    "PROV",
}
_PUBLIC_UUID4 = re.compile(
    r"^(?P<prefix>[A-Z]+)-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


class MigrationQuarantineError(RuntimeError):
    """Fail-closed report for rows whose closed references cannot be proven."""

    def __init__(self, reports: list[dict[str, str]]):
        self.reports = reports
        summary = json.dumps(reports, sort_keys=True, separators=(",", ":"))
        super().__init__(f"0016 migration quarantine blocks activation: {summary}")


_AUTHORITY_TABLES: dict[str, tuple[tuple[str, tuple[str, ...]], ...]] = {
    "job": (("jobs", ("job_id", "id")),),
    "research": (("research_cases", ("research_id", "id")),),
    "conclusion": (("research_conclusions", ("conclusion_id", "id")),),
    "experiment": (("experiments", ("experiment_id", "id")),),
    "factor": (("factors", ("factor_id", "id")),),
    "validation": (("validations", ("validation_id", "id")),),
    "approval": (("approval_requests", ("approval_id", "id")),),
    "paper": (("paper_deployments", ("paper_id", "id")),),
    "paper_run": (("paper_daily_runs", ("paper_run_id", "run_id", "id")),),
    "review": (("performance_reviews", ("review_id", "id")),),
    "capability": (("data_capabilities", ("capability_id", "id")),),
    "snapshot": (
        ("dataset_snapshots", ("snapshot_id", "id")),
        ("data_snapshots", ("snapshot_id", "id")),
    ),
    "agent_run": (("agent_runs", ("agent_run_id", "id")),),
    "tool_call": (("tool_calls", ("tool_call_id", "id")),),
    "memo": (("investment_memos", ("memo_id", "id")),),
    "notification": (("notifications", ("notification_id", "id")),),
}

_RECORD_KINDS = {
    "job": {"job"},
    "research": {"research"},
    "conclusion": {"conclusion", "research_conclusion"},
    "experiment": {"experiment"},
    "factor": {"factor"},
    "validation": {"validation"},
    "approval": {"approval"},
    "paper": {"paper", "paper_deployment"},
    "paper_run": {"paper_run"},
    "review": {"review", "performance_review"},
    "capability": {"capability", "data_capability"},
    "snapshot": {"snapshot", "data_snapshot"},
    "agent_run": {"agent_run"},
    "tool_call": {"tool_call"},
    "memo": {"memo"},
    "notification": {"notification"},
}


def _deterministic_uuid4(namespace: str, value: Any) -> uuid.UUID:
    raw = bytearray(
        uuid.uuid5(uuid.NAMESPACE_URL, f"quantfoundry:{namespace}:{value}").bytes
    )
    raw[6] = (raw[6] & 0x0F) | 0x40
    raw[8] = (raw[8] & 0x3F) | 0x80
    return uuid.UUID(bytes=bytes(raw))


def _workspace_uuid(value: Any) -> uuid.UUID:
    try:
        return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return _deterministic_uuid4("workspace", value)


def _public_id(value: Any, default_prefix: str) -> str:
    raw = str(value or "")
    match = _PUBLIC_UUID4.fullmatch(raw)
    if match and match.group("prefix") in _PUBLIC_PREFIXES:
        return raw
    candidate = raw.split("-", 1)[0]
    prefix = candidate if candidate in _PUBLIC_PREFIXES else default_prefix
    return f"{prefix}-{_deterministic_uuid4(prefix, raw)}"


_PUBLIC_COLUMN_PREFIXES = {
    "agent_run_id": "ARUN",
    "approval_id": "APR",
    "artifact_id": "ART",
    "audit_event_id": "AUD",
    "capability_id": "CAP",
    "conclusion_id": "CONC",
    "cost_model_id": "COST",
    "credential_id": "CRED",
    "data_quality_issue_id": "DQI",
    "data_quality_run_id": "DQ",
    "dataset_id": "DSSET",
    "dataset_snapshot_id": "DS",
    "event_id": "EVT",
    "evidence_id": "EVID",
    "experiment_id": "EXP",
    "exposure_id": "HOLD",
    "factor_id": "FAC",
    "fill_id": "PFILL",
    "job_id": "JOB",
    "memo_id": "MEMO",
    "notification_id": "NOTIF",
    "order_id": "PORD",
    "paper_deployment_id": "PAPER",
    "portfolio_id": "PORT",
    "provenance_id": "PROV",
    "red_team_run_id": "RT",
    "research_id": "RSCH",
    "research_revision_id": "REV",
    "review_id": "REV",
    "run_id": "PRUN",
    "strategy_id": "STRAT",
    "tool_call_id": "TCALL",
    "validation_id": "VAL",
}

_COLUMN_ALIASES = {
    "research_policy_versions": {
        "id": "legacy_id",
        "legacy_id": "id",
    },
    "risk_policy_versions": {
        "id": "legacy_id",
        "legacy_id": "id",
    },
    "cost_model_versions": {
        "id": "legacy_id",
        "legacy_id": "id",
    },
    "research_cases": {
        "id": "research_id",
        "research_id": "id",
    },
    "experiments": {
        "id": "experiment_id",
        "experiment_id": "id",
        "research_id": "research_public_id",
        "research_public_id": "research_id",
        "source_experiment_id": "source_experiment_public_id",
        "source_experiment_public_id": "source_experiment_id",
    },
    "factors": {
        "id": "factor_id",
        "factor_id": "id",
    },
    "strategies": {
        "id": "strategy_id",
        "strategy_id": "id",
    },
    "strategy_versions": {
        "id": "legacy_id",
        "legacy_id": "id",
        "strategy_id": "strategy_public_id",
        "strategy_public_id": "strategy_id",
    },
    "approval_requests": {
        "id": "approval_id",
        "approval_id": "id",
    },
    "holdout_exposures": {
        "id": "exposure_id",
        "exposure_id": "id",
        "strategy_version_id": "strategy_version_public_id",
        "strategy_version_public_id": "strategy_version_id",
        "approval_id": "approval_public_id",
        "approval_public_id": "approval_id",
    },
    "agent_configs": {
        "role": "role_key",
        "role_key": "role",
    },
    "idempotency_records": {
        "path": "normalized_route",
        "normalized_route": "path",
        "request_hash": "request_sha256",
        "request_sha256": "request_hash",
        "status": "response_status",
        "response_status": "status",
        "response": "response_body",
        "response_body": "response",
    },
    "jobs": {
        "id": "job_id",
        "job_id": "id",
    },
    "job_dependencies": {
        "job_id": "job_public_id",
        "job_public_id": "job_id",
        "depends_on_job_id": "depends_on_job_public_id",
        "depends_on_job_public_id": "depends_on_job_id",
    },
    "tool_calls": {
        "id": "tool_call_id",
        "tool_call_id": "id",
        "agent_run_id": "agent_run_public_id",
        "agent_run_public_id": "agent_run_id",
        "research_id": "research_public_id",
        "research_public_id": "research_id",
        "experiment_id": "experiment_public_id",
        "experiment_public_id": "experiment_id",
        "job_id": "job_public_id",
        "job_public_id": "job_id",
        "output_artifact_id": "output_artifact_public_id",
        "output_artifact_public_id": "output_artifact_id",
    },
    "agent_runs": {
        "id": "agent_run_id",
        "agent_run_id": "id",
        "research_id": "research_public_id",
        "research_public_id": "research_id",
        "root_agent_run_id": "root_agent_run_public_id",
        "root_agent_run_public_id": "root_agent_run_id",
        "parent_agent_run_id": "parent_agent_run_public_id",
        "parent_agent_run_public_id": "parent_agent_run_id",
    },
}


def _is_backup_table(name: str) -> bool:
    return name.startswith(_BACKUP_PREFIXES)


def _application_table_names(bind: Any) -> list[str]:
    return sorted(
        name
        for name in inspect(bind).get_table_names(schema=None)
        if name != "alembic_version" and not _is_backup_table(name)
    )


def _quoted(bind: Any, name: str) -> str:
    return bind.dialect.identifier_preparer.quote(name)


def _drop_backup_set(bind: Any, prefix: str) -> None:
    for name in inspect(bind).get_table_names(schema=None):
        if name.startswith(prefix):
            bind.execute(text(f"DROP TABLE IF EXISTS {_quoted(bind, name)}"))


def _backup_tables(bind: Any, prefix: str, *, replace: bool) -> list[str]:
    existing = set(inspect(bind).get_table_names(schema=None))
    names = _application_table_names(bind)
    if replace:
        _drop_backup_set(bind, prefix)
        existing = set(inspect(bind).get_table_names(schema=None))
    for name in names:
        backup_name = f"{prefix}{name}"
        if backup_name in existing:
            continue
        bind.execute(
            text(
                f"CREATE TABLE {_quoted(bind, backup_name)} AS "
                f"SELECT * FROM {_quoted(bind, name)}"
            )
        )
    return names


def _backup_names(bind: Any, prefix: str) -> dict[str, str]:
    return {
        name.removeprefix(prefix): name
        for name in inspect(bind).get_table_names(schema=None)
        if name.startswith(prefix)
    }


def _read_backup_rows(bind: Any, prefix: str) -> dict[str, list[dict[str, Any]]]:
    rows: dict[str, list[dict[str, Any]]] = {}
    for source_name, backup_name in _backup_names(bind, prefix).items():
        rows[source_name] = [
            dict(row)
            for row in bind.execute(
                text(f"SELECT * FROM {_quoted(bind, backup_name)}")
            ).mappings()
        ]
    return rows


def _sqlite_source_schema(bind: Any) -> list[str]:
    """Capture the actual pre-migration SQLite DDL for failure recovery.

    The pre-0016 schema is historical and cannot be reconstructed safely from
    a later physical snapshot when an upgrade fails midway.  Preserve its DDL
    before dropping application tables so the error path restores exactly what
    was present, including columns that are intentionally absent from 0015.
    """
    rows = bind.execute(
        text(
            "SELECT type, name, sql FROM sqlite_master "
            "WHERE sql IS NOT NULL AND type IN ('table', 'index') "
            "ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END, name"
        )
    ).mappings()
    return [
        str(row["sql"])
        for row in rows
        if row["name"] not in {"sqlite_sequence", "alembic_version"}
        and not _is_backup_table(str(row["name"]))
    ]


def _restore_sqlite_source_schema(
    bind: Any, statements: list[str], source_rows: dict[str, list[dict[str, Any]]]
) -> None:
    """Rebuild the captured source schema and restore its unmodified rows."""
    for statement in statements:
        bind.execute(text(statement))
    metadata = MetaData()
    metadata.reflect(bind=bind)
    _restore_exact_source(bind, metadata, source_rows)


def _identity_seed(table_name: str, source: dict[str, Any], row_number: int) -> Any:
    for name in (
        "id",
        "public_id",
        f"{table_name.removesuffix('s')}_id",
        "event_id",
        "job_id",
    ):
        if source.get(name) is not None:
            return source[name]
    return f"{table_name}:{row_number}"


def _public_prefix(column_name: str) -> str | None:
    if column_name in _PUBLIC_COLUMN_PREFIXES:
        return _PUBLIC_COLUMN_PREFIXES[column_name]
    if column_name.endswith("_public_id"):
        return _PUBLIC_COLUMN_PREFIXES.get(
            column_name.removesuffix("_public_id") + "_id"
        )
    return None


def _json_default(column_name: str) -> Any:
    if column_name.endswith("s") or column_name in {
        "prerequisites",
        "effects",
        "signals",
        "required_dataset_refs",
    }:
        return []
    return {}


def _text_default(column_name: str, identity: Any) -> str:
    values = {
        "action": "MIGRATED",
        "action_type": "MIGRATED",
        "actor_type": "USER",
        "agent_role": "RESEARCH_AGENT",
        "base_currency": "CNY",
        "currency": "CNY",
        "direction": "LONG",
        "email": f"migration-{_deterministic_uuid4('email', identity)}@invalid.local",
        "environment": "migration",
        "event_type": "system.resync_required",
        "kind": "SYSTEM",
        "language": "zh-CN",
        "lifecycle_state": "DRAFT",
        "number_format_locale": "zh-CN",
        "policy_family": "DEFAULT",
        "requested_by_type": "USER",
        "result": "SUCCESS",
        "role": "OWNER",
        "role_key": "RESEARCH_AGENT",
        "status": "ACTIVE",
        "subject_type": "VALIDATION",
        "timezone": "UTC",
        "type": "VALIDATION",
        "validation_state": "SUCCESS",
    }
    if column_name in values:
        return values[column_name]
    if "sha256" in column_name or column_name.endswith("_hash"):
        return hashlib.sha256(str(identity).encode()).hexdigest()
    if column_name.endswith("_version"):
        return "migration-v1"
    if column_name.endswith("_key"):
        return "migration"
    return "Migrated"


def _direct_check_default(column: Any) -> str | None:
    pattern = re.compile(
        rf"^\s*{re.escape(column.name)}\s+IN\s+\((?P<values>[^)]+)\)\s*$",
        re.IGNORECASE,
    )
    for constraint in column.table.constraints:
        sqltext = getattr(constraint, "sqltext", None)
        if sqltext is None:
            continue
        match = pattern.fullmatch(str(sqltext))
        if match is None:
            continue
        values = re.findall(r"'((?:''|[^'])*)'", match.group("values"))
        if values:
            return values[0].replace("''", "'")
    return None


def _coerce_value(column: Any, value: Any, *, identity: Any) -> Any:
    if value is None:
        return None
    column_type = column.type
    prefix = _public_prefix(column.name)
    if (
        prefix is not None
        and isinstance(column_type, (String, Text))
        and isinstance(value, (str, uuid.UUID))
    ):
        return _public_id(value, prefix)
    if isinstance(column_type, WorkspaceScopeId):
        return canonical_workspace_id(value)
    if (
        column.name == "workspace_id"
        or (column.table.name == "workspaces" and column.name == "id")
    ) and isinstance(column_type, Uuid):
        return _workspace_uuid(value)
    if isinstance(column_type, Uuid):
        try:
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        except (TypeError, ValueError, AttributeError):
            if column.table.name == "records" and column.name == "id":
                # Python 3.14 provides uuid7; keep a deterministic compatible
                # fallback for the migration's supported interpreter boundary.
                uuid7 = getattr(uuid, "uuid7", None)
                return (
                    uuid7() if callable(uuid7) else _deterministic_uuid4("uuid7", value)
                )
            return _deterministic_uuid4("internal", value)
    if isinstance(column_type, JSON) or isinstance(
        getattr(column_type, "impl", None), JSON
    ):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = {"legacy_value": value}
        if isinstance(column_type, JSONTextCompat):
            return json.dumps(value, sort_keys=True, separators=(",", ":"))
        return value
    if isinstance(column_type, (String, Text)):
        if isinstance(value, (dict, list)):
            return json.dumps(value, sort_keys=True, separators=(",", ":"))
        if isinstance(value, uuid.UUID):
            return str(value)
    if isinstance(column_type, DateTime) and isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    if (
        isinstance(column_type, Date)
        and not isinstance(column_type, DateTime)
        and isinstance(value, str)
    ):
        return date.fromisoformat(value)
    if isinstance(column_type, Numeric) and not isinstance(value, Decimal):
        return Decimal(str(value))
    if isinstance(column_type, Boolean) and not isinstance(value, bool):
        return bool(value)
    if isinstance(column_type, LargeBinary) and isinstance(value, str):
        return value.encode()
    return value


def _missing_value(
    column: Any, *, table_name: str, source: dict[str, Any], row_number: int
) -> Any:
    identity = _identity_seed(table_name, source, row_number)
    prefix = _public_prefix(column.name)
    if prefix is not None and isinstance(column.type, (String, Text)):
        return _public_id(f"{table_name}:{column.name}:{identity}", prefix)
    if column.name == "workspace_id":
        return _workspace_uuid(source.get("workspace_id", "migration-workspace"))
    if isinstance(column.type, Uuid):
        related = source.get(column.name)
        return _deterministic_uuid4(
            "internal", related if related is not None else identity
        )
    if isinstance(column.type, JSON):
        return _json_default(column.name)
    if isinstance(column.type, DateTime):
        timestamp = source.get("created_at") or source.get("updated_at")
        if timestamp is not None:
            return _coerce_value(column, timestamp, identity=identity)
        return datetime(1970, 1, 1, tzinfo=UTC)
    if isinstance(column.type, Date):
        return date(1970, 1, 1)
    if isinstance(column.type, Boolean):
        return False
    if isinstance(column.type, Numeric):
        return Decimal("0")
    if isinstance(column.type, LargeBinary):
        return b""
    try:
        python_type = column.type.python_type
    except NotImplementedError:
        python_type = str
    if python_type is int:
        return (
            row_number + 1
            if column.name in {"sequence", "version", "revision", "current_revision_no"}
            else 0
        )
    if python_type is str:
        return _direct_check_default(column) or _text_default(column.name, identity)
    raise RuntimeError(f"0016 cannot derive {table_name}.{column.name}")


def _same_workspace(left: Any, right: Any) -> bool:
    return _workspace_uuid(left) == _workspace_uuid(right)


def _row_public_id(
    row: dict[str, Any], object_type: str, columns: tuple[str, ...]
) -> str | None:
    for column in columns:
        value = row.get(column)
        version = 1 if object_type == "strategy_version" else None
        revision = 1 if object_type == "strategy_version" else None
        if isinstance(value, str) and locator_quartet_valid(
            object_type, value, version, revision, False
        ):
            return value
    return None


def _ordinary_authority(
    source_rows: dict[str, list[dict[str, Any]]],
    workspace_id: Any,
    object_type: str,
    object_id: Any,
) -> list[tuple[int | None, int | None]]:
    if not isinstance(object_id, str):
        return []
    matches: list[tuple[int | None, int | None]] = []
    for table_name, columns in _AUTHORITY_TABLES[object_type]:
        for row in source_rows.get(table_name, []):
            if not _same_workspace(row.get("workspace_id"), workspace_id):
                continue
            if _row_public_id(row, object_type, columns) == object_id:
                version = row.get("version")
                revision = row.get("revision")
                matches.append(
                    (
                        version if isinstance(version, int) else None,
                        revision if isinstance(revision, int) else None,
                    )
                )
    for row in source_rows.get("records", []):
        if not _same_workspace(row.get("workspace_id"), workspace_id):
            continue
        if str(row.get("kind", "")).lower() not in _RECORD_KINDS[object_type]:
            continue
        if (
            _row_public_id(row, object_type, ("public_id", "record_key", "id"))
            == object_id
        ):
            revision = row.get("revision")
            matches.append((None, revision if isinstance(revision, int) else None))
    return list(dict.fromkeys(matches))


def _special_authority(
    source_rows: dict[str, list[dict[str, Any]]],
    workspace_id: Any,
    object_type: str,
    object_id: Any,
) -> list[tuple[int | None, int | None]]:
    matches: list[tuple[int | None, int | None]] = []
    if object_type == "settings":
        for row in source_rows.get("app_settings", []):
            if (
                _same_workspace(row.get("workspace_id"), workspace_id)
                and row.get("public_id", "SETTINGS-DEFAULT") == object_id
            ):
                matches.append((None, row.get("revision")))
        for row in source_rows.get("records", []):
            if (
                _same_workspace(row.get("workspace_id"), workspace_id)
                and row.get("kind") == "settings"
                and object_id == "SETTINGS-DEFAULT"
            ):
                matches.append((None, row.get("revision")))
    elif object_type == "provider_connection":
        for row in source_rows.get("model_provider_connections", []):
            if (
                _same_workspace(row.get("workspace_id"), workspace_id)
                and str(row.get("id")) == object_id
            ):
                revision = row.get("revision")
                matches.append((None, revision if isinstance(revision, int) else None))
    elif object_type == "agent_config":
        for row in source_rows.get("agent_configs", []):
            role = row.get("role_key", row.get("role"))
            if (
                _same_workspace(row.get("workspace_id"), workspace_id)
                and role == object_id
            ):
                matches.append((None, row.get("revision")))
    return list(dict.fromkeys(matches))


def _strategy_authority(
    source_rows: dict[str, list[dict[str, Any]]],
    workspace_id: Any,
    object_id: Any,
    object_version: Any,
) -> list[tuple[int, int]]:
    matches: list[tuple[int, int]] = []
    for row in source_rows.get("strategy_versions", []):
        if not _same_workspace(row.get("workspace_id"), workspace_id):
            continue
        public_id = _row_public_id(
            row, "strategy_version", ("strategy_public_id", "strategy_id")
        )
        version = row.get("version")
        revision = row.get("revision")
        if (
            public_id == object_id
            and isinstance(version, int)
            and isinstance(revision, int)
            and (object_version is None or object_version == version)
        ):
            matches.append((version, revision))
    return matches


def _quarantine_report(
    table_name: str, row: dict[str, Any], reason: str
) -> dict[str, str]:
    primary_key = next(
        (
            str(row[name])
            for name in ("event_id", "id", "sequence", "job_id", "notification_id")
            if row.get(name) is not None
        ),
        "unknown",
    )
    encoded = json.dumps(
        _normalized(row), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return {
        "table": table_name,
        "primary_key": primary_key,
        "reason": reason,
        "payload_sha256": hashlib.sha256(encoded).hexdigest(),
    }


def _resolve_locator(
    source_rows: dict[str, list[dict[str, Any]]],
    table_name: str,
    row: dict[str, Any],
    *,
    expected_object_type: str | None = None,
    allow_null: bool,
) -> str | None:
    values = {
        "object_type": row.get("object_type"),
        "object_id": row.get("object_id"),
        "object_version": row.get("object_version"),
        "object_revision": row.get("object_revision")
        if row.get("object_revision") is not None
        else row.get("revision")
        if table_name == "domain_events"
        else None,
    }
    if all(value is None for value in values.values()):
        return None if allow_null else "mandatory locator is absent"
    if any(values[name] is None for name in ("object_type", "object_id")):
        return "locator type/id is partially null"
    if expected_object_type == "event_stream":
        values = {
            "object_type": "event_stream",
            "object_id": row.get("event_id"),
            "object_version": None,
            "object_revision": row.get("sequence") or row.get("revision"),
        }
    elif expected_object_type is not None:
        values["object_type"] = expected_object_type
    object_type = values["object_type"]
    object_id = values["object_id"]
    workspace_id = row.get("workspace_id")
    if object_type in _AUTHORITY_TABLES:
        authority = _ordinary_authority(
            source_rows, workspace_id, str(object_type), object_id
        )
        if len(authority) != 1:
            return f"ordinary locator authority count is {len(authority)}"
    elif object_type == "strategy_version":
        strategy_authority = _strategy_authority(
            source_rows, workspace_id, object_id, values["object_version"]
        )
        if len(strategy_authority) != 1:
            return f"strategy version authority count is {len(strategy_authority)}"
        values["object_version"] = strategy_authority[0][0]
        values["object_revision"] = (
            values["object_revision"] or strategy_authority[0][1]
        )
    elif object_type in {"settings", "provider_connection", "agent_config"}:
        authority = _special_authority(
            source_rows, workspace_id, str(object_type), object_id
        )
        if len(authority) != 1:
            return f"special locator authority count is {len(authority)}"
        values["object_version"] = None
        values["object_revision"] = values["object_revision"] or authority[0][1]
    elif object_type != "event_stream":
        return "locator object_type is not closed"
    if not locator_quartet_valid(
        values["object_type"],
        values["object_id"],
        values["object_version"],
        values["object_revision"],
        allow_null,
    ):
        return "locator quartet is not canonical"
    row.update(values)
    if table_name == "domain_events":
        row["revision"] = values["object_revision"]
    return None


def _backfill_closed_storage(
    source_rows: dict[str, list[dict[str, Any]]],
) -> None:
    reports: list[dict[str, str]] = []
    record_keys: set[tuple[str, str]] = set()
    for row in source_rows.get("records", []):
        workspace_id = row.get("workspace_id")
        record_key = row.get("record_key", row.get("id"))
        kind = row.get("kind")
        valid = (kind == "settings" and record_key == "SETTINGS-DEFAULT") or (
            kind in {"artifact", "provenance", "memo"}
            and isinstance(record_key, str)
            and is_public_id(str(kind), record_key)
        )
        identity = (str(_workspace_uuid(workspace_id)), str(record_key))
        if workspace_id is None or not valid:
            reports.append(
                _quarantine_report(
                    "records", row, "record kind/key lacks canonical authority"
                )
            )
        elif identity in record_keys:
            reports.append(
                _quarantine_report(
                    "records", row, "duplicate workspace-local record key"
                )
            )
        else:
            record_keys.add(identity)
    for table_name in ("domain_events", "audit_events", "agent_runs", "notifications"):
        for row in source_rows.get(table_name, []):
            expected = (
                EVENT_OBJECT_TYPES.get(str(row.get("event_type")))
                if table_name == "domain_events"
                else None
            )
            reason = _resolve_locator(
                source_rows,
                table_name,
                row,
                expected_object_type=expected,
                allow_null=table_name in {"agent_runs", "notifications"},
            )
            if reason is not None:
                reports.append(_quarantine_report(table_name, row, reason))
    for row in source_rows.get("jobs", []):
        value = row.get("result_ref")
        if value is not None and not job_result_ref_valid(value):
            reports.append(
                _quarantine_report("jobs", row, "result_ref is not closed JobResultRef")
            )
    for row in source_rows.get("agent_runs", []):
        value = row.get("next_action")
        if value is not None and not next_action_valid(value):
            reports.append(
                _quarantine_report(
                    "agent_runs", row, "next_action is not closed NextAction"
                )
            )
    if reports:
        raise MigrationQuarantineError(reports)


def _defer_domain_locator_check(metadata: MetaData) -> Any:
    """Leave the retained-data locator check for PostgreSQL NOT VALID validation."""
    table = metadata.tables["domain_events"]
    constraint = next(
        item for item in table.constraints if item.name == _DOMAIN_LOCATOR_CHECK_NAME
    )
    table.constraints.remove(constraint)
    return constraint


def _install_and_validate_domain_locator_check() -> None:
    op.execute(
        "ALTER TABLE domain_events ADD CONSTRAINT "
        f"{_DOMAIN_LOCATOR_CHECK_NAME} CHECK ({_DOMAIN_LOCATOR_CHECK_SQL}) NOT VALID"
    )
    op.execute(
        f"ALTER TABLE domain_events VALIDATE CONSTRAINT {_DOMAIN_LOCATOR_CHECK_NAME}"
    )


def _prepare_rows(
    table: Table,
    rows: list[dict[str, Any]],
    *,
    prefer_aliases: bool = True,
) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for row_number, source in enumerate(rows):
        identity = _identity_seed(table.name, source, row_number)
        values: dict[str, Any] = {}
        for column in table.c:
            source_name = column.name
            alias = _COLUMN_ALIASES.get(table.name, {}).get(column.name)
            use_alias = (
                alias is not None and source.get(alias) is not None and prefer_aliases
            )
            if use_alias and alias is not None:
                source_name = alias
            if source_name in source and source[source_name] is not None:
                value = source[source_name]
                if prefer_aliases and column.name == "subject_id":
                    discriminator = str(
                        source.get("object_type") or source.get("subject_type") or ""
                    ).upper()
                    object_prefix = {
                        "AGENT_RUN": "ARUN",
                        "APPROVAL": "APR",
                        "ARTIFACT": "ART",
                        "DATASET": "DSSET",
                        "EXPERIMENT": "EXP",
                        "FACTOR": "FAC",
                        "JOB": "JOB",
                        "RESEARCH": "RSCH",
                        "STRATEGY": "STRAT",
                        "TOOL_CALL": "TCALL",
                        "VALIDATION": "VAL",
                    }.get(discriminator, "EVT")
                    value = _public_id(value, object_prefix)
                values[column.name] = _coerce_value(column, value, identity=identity)
            elif not column.nullable or column.primary_key:
                values[column.name] = _missing_value(
                    column,
                    table_name=table.name,
                    source=source,
                    row_number=row_number,
                )
            else:
                values[column.name] = None
        prepared.append(values)
    return prepared


def _normalized(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _normalized(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_normalized(item) for item in value]
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        parsed = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return parsed.astimezone(UTC).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, bytes):
        return value.hex()
    if all(hasattr(value, attribute) for attribute in ("lower", "upper", "bounds")):
        return {
            "lower": _normalized(value.lower),
            "upper": _normalized(value.upper),
            "bounds": value.bounds,
            "empty": bool(getattr(value, "empty", False)),
        }
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _row_digest(row: dict[str, Any], columns: set[str]) -> str:
    projected = {
        key: _normalized(value) for key, value in row.items() if key in columns
    }
    encoded = json.dumps(
        projected, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(encoded.encode()).hexdigest()


def _legacy_event_sequence_map(
    metadata: MetaData,
    source_rows: dict[str, list[dict[str, Any]]],
) -> dict[tuple[str, int], int]:
    table = metadata.tables.get("domain_events")
    if table is None or tuple(column.name for column in table.primary_key.columns) != (
        "sequence",
    ):
        return {}
    keys = {
        (str(row.get("workspace_id")), int(row["sequence"]))
        for row in source_rows.get("domain_events", [])
        if row.get("sequence") is not None
    }
    return {key: offset for offset, key in enumerate(sorted(keys), start=1)}


def _normalize_paper_deployment_statuses(
    rows: list[dict[str, Any]], *, target_is_current: bool
) -> None:
    """Translate the retired STOPPED spelling across the 0016 boundary."""
    source_status = "STOPPED" if target_is_current else "DISABLED"
    target_status = "DISABLED" if target_is_current else "STOPPED"
    for row in rows:
        if row.get("status") == source_status:
            row["status"] = target_status


def _restore_all_tables(
    bind: Any,
    metadata: MetaData,
    source_rows: dict[str, list[dict[str, Any]]],
    *,
    prefer_aliases: bool = True,
) -> None:
    source_rows = {
        name: [dict(row) for row in rows] for name, rows in source_rows.items()
    }
    # Section-14 uses UUID workspace keys.  Apply one deterministic mapping to
    # every scoped row before restoring, including legacy text-backed schemas.
    # Keep generic helper callers unchanged when no workspace authority exists.
    if "workspaces" in metadata.tables:
        for rows in source_rows.values():
            for row in rows:
                if row.get("workspace_id") is not None:
                    row["workspace_id"] = str(_workspace_uuid(row["workspace_id"]))
        for row in source_rows.get("workspaces", []):
            if row.get("id") is not None:
                row["id"] = str(_workspace_uuid(row["id"]))
    if "users" in metadata.tables and "workspaces" in metadata.tables:
        referenced_workspaces = {
            _workspace_uuid(row["workspace_id"])
            for rows in source_rows.values()
            for row in rows
            if row.get("workspace_id") is not None
        }
        existing_workspaces = {
            _workspace_uuid(row.get("id"))
            for row in source_rows.get("workspaces", [])
            if row.get("id") is not None
        }
        existing_users = {
            str(row.get("id"))
            for row in source_rows.get("users", [])
            if row.get("id") is not None
        }
        for workspace_id in sorted(
            referenced_workspaces - existing_workspaces, key=str
        ):
            owner_id = f"migration-owner:{workspace_id}"
            if owner_id not in existing_users:
                source_rows.setdefault("users", []).append(
                    {
                        "id": owner_id,
                        "email": f"migration-{workspace_id}@invalid.local",
                        "role": "OWNER",
                        "revision": 1,
                    }
                )
                existing_users.add(owner_id)
            source_rows.setdefault("workspaces", []).append(
                {
                    "id": str(workspace_id),
                    "owner_id": owner_id,
                    "name": "Migrated workspace",
                    "revision": 1,
                }
            )
    pending = set(metadata.tables)
    ordered_tables: list[Table] = []
    while pending:
        ready = sorted(
            name
            for name in pending
            if not {
                element.column.table.name
                for constraint in metadata.tables[name].foreign_key_constraints
                if all(not element.parent.nullable for element in constraint.elements)
                for element in constraint.elements
                if element.column.table.name != name
            }
            & pending
        )
        if not ready:
            ready = [sorted(pending)[0]]
        for name in ready:
            ordered_tables.append(metadata.tables[name])
            pending.remove(name)
    if bind.dialect.name == "sqlite":
        bind.execute(text("PRAGMA defer_foreign_keys = ON"))
    legacy_event_sequences = _legacy_event_sequence_map(metadata, source_rows)
    prepared_by_table: dict[str, list[dict[str, Any]]] = {}
    inserted_tables: set[str] = set()
    deferred_foreign_keys: list[
        tuple[Table, dict[str, Any], dict[str, Any], dict[str, Any]]
    ] = []
    for table in ordered_tables:
        rows = source_rows.get(table.name, [])
        prepared = _prepare_rows(table, rows, prefer_aliases=prefer_aliases)
        if legacy_event_sequences and table.name in {"domain_events", "audit_events"}:
            for source, values in zip(rows, prepared, strict=True):
                sequence = source.get("sequence")
                key = (str(source.get("workspace_id")), int(sequence or 0))
                if "sequence" in table.c and key in legacy_event_sequences:
                    values["sequence"] = legacy_event_sequences[key]
        for values in prepared:
            for constraint in table.foreign_key_constraints:
                target_tables = {
                    element.column.table.name for element in constraint.elements
                }
                if target_tables <= inserted_tables:
                    continue
                nullable_columns = [
                    element.parent.name
                    for element in constraint.elements
                    if element.parent.nullable
                    and values.get(element.parent.name) is not None
                ]
                if not nullable_columns:
                    continue
                primary_key = {
                    column.name: values[column.name]
                    for column in table.primary_key.columns
                }
                restore = {name: values[name] for name in nullable_columns}
                for name in nullable_columns:
                    values[name] = None
                deferred_foreign_keys.append((table, primary_key, restore, values))
        if prepared:
            bind.execute(table.insert(), prepared)
        prepared_by_table[table.name] = prepared
        inserted_tables.add(table.name)
    for table, primary_key, restore, prepared_row in deferred_foreign_keys:
        statement = table.update()
        for name, value in primary_key.items():
            statement = statement.where(table.c[name] == value)
        result = bind.execute(statement.values(**restore))
        if result.rowcount != 1:
            raise RuntimeError(
                f"0016 deferred foreign-key restore lost {table.name}:{primary_key}"
            )
        prepared_row.update(restore)
    if bind.dialect.name == "sqlite":
        violations = list(bind.execute(text("PRAGMA foreign_key_check")))
        if violations:
            raise RuntimeError(
                f"0016 foreign-key verification failed: {violations[:3]}"
            )
    for table in ordered_tables:
        expected = prepared_by_table[table.name]
        actual = [dict(row) for row in bind.execute(select(table)).mappings()]
        if len(actual) != len(expected):
            raise RuntimeError(
                f"0016 row-count mismatch for {table.name}: {len(expected)} != {len(actual)}"
            )
        if not expected:
            continue
        compared_columns = set.intersection(*(set(row) for row in expected))
        expected_hashes = Counter(
            _row_digest(row, compared_columns) for row in expected
        )
        actual_hashes = Counter(_row_digest(row, compared_columns) for row in actual)
        if actual_hashes != expected_hashes:
            differing_columns = [
                column
                for column in sorted(compared_columns)
                if Counter(
                    json.dumps(_normalized(row.get(column)), sort_keys=True)
                    for row in expected
                )
                != Counter(
                    json.dumps(_normalized(row.get(column)), sort_keys=True)
                    for row in actual
                )
            ]
            raise RuntimeError(
                f"0016 content-hash mismatch for {table.name}; "
                f"columns={differing_columns}"
            )


def _restore_exact_source(
    bind: Any,
    metadata: MetaData,
    source_rows: dict[str, list[dict[str, Any]]],
) -> None:
    """Restore the source snapshot byte-for-byte after a failed SQLite rebuild."""

    preparer = bind.dialect.identifier_preparer
    for table_name in metadata.tables:
        rows = source_rows.get(table_name, [])
        if not rows:
            continue
        columns = [column.name for column in metadata.tables[table_name].c]
        common = [name for name in columns if all(name in row for row in rows)]
        if not common:
            raise RuntimeError(f"0016 recovery has no columns for {table_name}")
        parameters = [
            {f"p{offset}": row[name] for offset, name in enumerate(common)}
            for row in rows
        ]
        column_sql = ", ".join(preparer.quote(name) for name in common)
        value_sql = ", ".join(f":p{offset}" for offset in range(len(common)))
        bind.execute(
            text(
                f"INSERT INTO {preparer.quote(table_name)} ({column_sql}) "
                f"VALUES ({value_sql})"
            ),
            parameters,
        )
    for table_name, rows in source_rows.items():
        if table_name not in metadata.tables:
            continue
        count = bind.execute(
            text(f"SELECT count(*) FROM {preparer.quote(table_name)}")
        ).scalar_one()
        if count != len(rows):
            raise RuntimeError(
                f"0016 recovery row-count mismatch for {table_name}: {len(rows)} != {count}"
            )


def _capture_domain_events(bind: Any) -> list[dict[str, Any]]:
    if "domain_events" not in inspect(bind).get_table_names(schema=None):
        return []
    metadata = MetaData()
    table = Table("domain_events", metadata, autoload_with=bind)
    return [
        dict(row)
        for row in bind.execute(select(table).order_by(table.c.sequence)).mappings()
    ]


def _restore_domain_events(
    bind: Any, metadata: MetaData, rows: list[dict[str, Any]]
) -> None:
    if not rows or "domain_events" not in metadata.tables:
        return
    target = metadata.tables["domain_events"]
    workspace_ids = {_workspace_uuid(row.get("workspace_id")) for row in rows}
    if "users" in metadata.tables and "workspaces" in metadata.tables:
        users = metadata.tables["users"]
        workspaces = metadata.tables["workspaces"]
        for workspace_id in sorted(workspace_ids, key=str):
            owner_id = f"migration-owner:{workspace_id}"
            bind.execute(
                users.insert().values(
                    id=owner_id,
                    email=f"migration-{workspace_id}@invalid.local",
                    role="OWNER",
                    revision=1,
                )
            )
            bind.execute(
                workspaces.insert().values(
                    id=workspace_id,
                    owner_id=owner_id,
                    name="Migrated workspace",
                    revision=1,
                )
            )
    restored: list[dict[str, Any]] = []
    for source in rows:
        values = {key: value for key, value in source.items() if key in target.c}
        if "schema_version" in target.c:
            values.setdefault("schema_version", 1)
        values["workspace_id"] = _workspace_uuid(values.get("workspace_id"))
        values["event_id"] = _public_id(values.get("event_id"), "EVT")
        values["object_id"] = _public_id(values.get("object_id"), "EVT")
        for field, prefix in (
            ("job_id", "JOB"),
            ("agent_run_id", "ARUN"),
            ("tool_call_id", "TCALL"),
        ):
            if values.get(field) is not None:
                values[field] = _public_id(values[field], prefix)
        for column in target.c:
            if (
                column.name in values
                and isinstance(column.type, JSON)
                and isinstance(values[column.name], str)
            ):
                values[column.name] = json.loads(values[column.name])
        restored.append(values)
    bind.execute(target.insert(), restored)


def _drop_application_tables() -> None:
    bind = op.get_bind()
    names = _application_table_names(bind)
    if bind.dialect.name == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION qf_validate_holdout_transition()
            RETURNS trigger AS $$
            BEGIN
              IF NOT (
                NEW.holdout_state = OLD.holdout_state OR
                (OLD.holdout_state = 'LOCKED' AND NEW.holdout_state = 'APPROVAL_PENDING') OR
                (OLD.holdout_state = 'APPROVAL_PENDING' AND NEW.holdout_state IN ('LOCKED', 'UNLOCKED')) OR
                (OLD.holdout_state = 'UNLOCKED' AND NEW.holdout_state = 'RUNNING') OR
                (OLD.holdout_state = 'RUNNING' AND NEW.holdout_state = 'EXPOSED') OR
                NEW.holdout_state = 'FAILED'
              ) THEN
                RAISE EXCEPTION 'invalid holdout state transition';
              END IF;
              IF NEW.exposure_count <> (
                CASE WHEN NEW.holdout_state = 'EXPOSED' THEN 1 ELSE 0 END
              ) THEN
                RAISE EXCEPTION 'holdout exposure count is inconsistent';
              END IF;
              IF NEW.holdout_state = 'APPROVAL_PENDING' AND NOT EXISTS (
                SELECT 1 FROM approval_requests a
                WHERE a.validation_id = OLD.id AND a.status = 'PENDING'
              ) THEN
                RAISE EXCEPTION 'holdout approval evidence is missing';
              END IF;
              IF NEW.holdout_state IN ('UNLOCKED', 'RUNNING') AND NOT EXISTS (
                SELECT 1 FROM approval_requests a
                WHERE a.validation_id = OLD.id AND a.status = 'APPROVED'
              ) THEN
                RAISE EXCEPTION 'approved holdout evidence is missing';
              END IF;
              IF NEW.holdout_state = 'EXPOSED' AND NOT EXISTS (
                SELECT 1 FROM holdout_exposures e
                WHERE e.validation_id = OLD.id
                  AND e.strategy_version_public_id = OLD.strategy_version_id
              ) THEN
                RAISE EXCEPTION 'holdout exposure evidence is missing';
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        preparer = bind.dialect.identifier_preparer
        for name in names:
            op.execute(text(f"DROP TABLE IF EXISTS {preparer.quote(name)} CASCADE"))
        return
    preparer = bind.dialect.identifier_preparer
    if bind.execute(text("PRAGMA foreign_keys")).scalar_one() == 0:
        for name in names:
            op.execute(text(f"DROP TABLE IF EXISTS {preparer.quote(name)}"))
        return
    inspector = inspect(bind)
    dependencies = {
        name: {
            foreign_key["referred_table"]
            for foreign_key in inspector.get_foreign_keys(name)
            if foreign_key.get("referred_table") in names
            and foreign_key.get("referred_table") != name
        }
        for name in names
    }
    pending = set(names)
    drop_order: list[str] = []
    while pending:
        ready = sorted(
            name
            for name in pending
            if not any(name in dependencies[other] for other in pending - {name})
        )
        if not ready:
            raise RuntimeError(
                f"0016 SQLite foreign-key cycle cannot be rebuilt safely: {sorted(pending)}"
            )
        drop_order.extend(ready)
        pending.difference_update(ready)
    for name in drop_order:
        op.execute(text(f"DROP TABLE IF EXISTS {preparer.quote(name)}"))


def _drop_sqlite_guard_triggers() -> None:
    """Free stable guard names after source tables were renamed as backups."""
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        return
    triggers = bind.execute(
        text(
            "SELECT name FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'qf_%'"
        )
    ).scalars()
    preparer = bind.dialect.identifier_preparer
    for name in triggers:
        op.execute(text(f"DROP TRIGGER IF EXISTS {preparer.quote(name)}"))


def _install_guards() -> None:
    bind = op.get_bind()
    _drop_sqlite_guard_triggers()
    if bind.dialect.name == "postgresql":
        for table in (
            "audit_events",
            "holdout_exposures",
            "data_snapshots",
            "snapshot_partitions",
        ):
            op.execute(
                f"CREATE TRIGGER qf_{table}_immutable BEFORE UPDATE OR DELETE "
                f"ON {table} FOR EACH ROW EXECUTE FUNCTION qf_reject_change()"
            )
        op.execute(
            "CREATE TRIGGER qf_domain_events_update_immutable BEFORE UPDATE ON "
            "domain_events FOR EACH ROW EXECUTE FUNCTION qf_reject_change()"
        )
        op.execute(
            "CREATE TRIGGER qf_domain_events_delete_immutable BEFORE DELETE ON "
            "domain_events FOR EACH ROW EXECUTE FUNCTION "
            "qf_reject_unexpired_event_delete()"
        )
        op.execute(
            "CREATE TRIGGER qf_strategy_versions_immutable BEFORE UPDATE OR DELETE "
            "ON strategy_versions FOR EACH ROW EXECUTE FUNCTION "
            "qf_validate_strategy_transition()"
        )
        op.execute(
            "CREATE TRIGGER qf_experiments_immutable BEFORE UPDATE OR DELETE ON "
            "experiments FOR EACH ROW EXECUTE FUNCTION "
            "qf_reject_completed_experiment_change()"
        )
        op.execute(
            "CREATE TRIGGER qf_approval_requests_immutable BEFORE UPDATE OR DELETE "
            "ON approval_requests FOR EACH ROW EXECUTE FUNCTION "
            "qf_reject_terminal_approval_change()"
        )
        op.execute(
            "CREATE TRIGGER qf_records_immutable BEFORE UPDATE OR DELETE ON records "
            "FOR EACH ROW EXECUTE FUNCTION qf_reject_immutable_record_change()"
        )
        op.execute(
            "CREATE TRIGGER qf_validations_holdout_transition BEFORE UPDATE OF "
            "holdout_state, exposure_count ON validations FOR EACH ROW EXECUTE "
            "FUNCTION qf_validate_holdout_transition()"
        )
        return
    for table in (
        "audit_events",
        "holdout_exposures",
        "data_snapshots",
        "snapshot_partitions",
    ):
        for action in ("UPDATE", "DELETE"):
            op.execute(f"DROP TRIGGER IF EXISTS qf_{table}_{action.lower()}_immutable")
            op.execute(
                f"CREATE TRIGGER qf_{table}_{action.lower()}_immutable BEFORE "
                f"{action} ON {table} BEGIN SELECT RAISE(ABORT, "
                "'immutable evidence cannot be changed'); END"
            )
    op.execute("DROP TRIGGER IF EXISTS qf_domain_events_update_immutable")
    op.execute(
        "CREATE TRIGGER qf_domain_events_update_immutable BEFORE UPDATE ON "
        "domain_events BEGIN SELECT RAISE(ABORT, "
        "'immutable evidence cannot be changed'); END"
    )
    op.execute("DROP TRIGGER IF EXISTS qf_domain_events_delete_immutable")
    op.execute(
        "CREATE TRIGGER qf_domain_events_delete_immutable BEFORE DELETE ON "
        "domain_events WHEN OLD.expires_at > CURRENT_TIMESTAMP BEGIN SELECT "
        "RAISE(ABORT, 'unexpired event cannot be deleted'); END"
    )
    op.execute("DROP TRIGGER IF EXISTS qf_validations_holdout_transition")
    op.execute(
        "CREATE TRIGGER qf_validations_holdout_transition BEFORE UPDATE OF "
        "holdout_state, exposure_count ON validations WHEN NOT ("
        "NEW.holdout_state = OLD.holdout_state OR "
        "(OLD.holdout_state = 'LOCKED' AND NEW.holdout_state = 'APPROVAL_PENDING') OR "
        "(OLD.holdout_state = 'APPROVAL_PENDING' AND NEW.holdout_state IN ('LOCKED', 'UNLOCKED')) OR "
        "(OLD.holdout_state = 'UNLOCKED' AND NEW.holdout_state = 'RUNNING') OR "
        "(OLD.holdout_state = 'RUNNING' AND NEW.holdout_state = 'EXPOSED') OR "
        "NEW.holdout_state = 'FAILED') BEGIN SELECT RAISE(ABORT, "
        "'invalid holdout state transition'); END"
    )
    op.execute("DROP TRIGGER IF EXISTS qf_validations_holdout_binding")
    op.execute(
        "CREATE TRIGGER qf_validations_holdout_binding BEFORE UPDATE OF "
        "holdout_state, exposure_count ON validations WHEN "
        "(NEW.exposure_count != CASE WHEN NEW.holdout_state = 'EXPOSED' THEN 1 ELSE 0 END) OR "
        "(NEW.holdout_state = 'APPROVAL_PENDING' AND NOT EXISTS (SELECT 1 FROM "
        "approval_requests a WHERE a.validation_id = OLD.id AND a.status = 'PENDING')) OR "
        "(NEW.holdout_state IN ('UNLOCKED', 'RUNNING') AND NOT EXISTS (SELECT 1 FROM "
        "approval_requests a WHERE a.validation_id = OLD.id AND a.status = 'APPROVED')) OR "
        "(NEW.holdout_state = 'EXPOSED' AND NOT EXISTS (SELECT 1 FROM "
        "holdout_exposures e WHERE e.validation_id = OLD.id AND "
        "e.strategy_version_public_id = OLD.strategy_version_id)) BEGIN SELECT RAISE(ABORT, "
        "'holdout state lacks durable evidence'); END"
    )


def _replace(snapshot: Path, *, guards: bool) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        register_sqlite_functions(bind.connection.driver_connection)
    target_is_current = snapshot == CURRENT
    roundtrip_preexisting = bool(_backup_names(bind, _ROUNDTRIP_BACKUP_PREFIX))
    source_schema = _sqlite_source_schema(bind) if bind.dialect.name == "sqlite" else []
    _backup_tables(bind, _SOURCE_BACKUP_PREFIX, replace=True)
    source_rows = _read_backup_rows(bind, _SOURCE_BACKUP_PREFIX)
    if not target_is_current:
        _backup_tables(bind, _ROUNDTRIP_BACKUP_PREFIX, replace=True)
    restore_rows = (
        _read_backup_rows(bind, _ROUNDTRIP_BACKUP_PREFIX)
        if target_is_current and roundtrip_preexisting
        else {name: [dict(row) for row in rows] for name, rows in source_rows.items()}
    )
    if target_is_current and not roundtrip_preexisting:
        _backfill_closed_storage(restore_rows)
    _normalize_paper_deployment_statuses(
        restore_rows.get("paper_deployments", []), target_is_current=target_is_current
    )

    def metadata_for(path: Path) -> MetaData:
        return load_physical_metadata(
            path,
            include_checks=(bind.dialect.name == "postgresql"),
            include_sqlite_partial_indexes=(bind.dialect.name == "postgresql"),
            # The frozen physical authority requires records.id to retain its
            # PostgreSQL uuidv7() default.  SQLite deliberately omits it: its
            # compatibility path supplies explicit UUID values instead.
            include_server_defaults=(bind.dialect.name == "postgresql"),
        )

    try:
        _drop_sqlite_guard_triggers()
        _drop_application_tables()
        if bind.dialect.name == "postgresql" and target_is_current:
            if (bind.dialect.server_version_info or ()) < (18, 0):
                bind.execute(text(_POSTGRES_UUIDV7_COMPAT_SQL))
            for statement in (
                POSTGRES_LOCATOR_FUNCTION_SQL,
                POSTGRES_LOCATOR_JSON_FUNCTION_SQL,
                POSTGRES_NULLABLE_PUBLIC_ID_FUNCTION_SQL,
            ):
                bind.execute(text(statement))
            contract_comment = f"qf-contract-sha256:{POSTGRES_LOCATOR_CONTRACT_SHA256}"
            bind.execute(
                text(
                    "COMMENT ON FUNCTION qf_event_locator_quartet_valid("
                    "text,text,integer,bigint,boolean) IS "
                    f"'{contract_comment}'"
                )
            )
            bind.execute(
                text(
                    "COMMENT ON FUNCTION qf_event_locator_json_valid(jsonb,boolean) "
                    f"IS '{contract_comment}'"
                )
            )
            bind.execute(
                text(
                    "COMMENT ON FUNCTION qf_nullable_public_id_json_valid(jsonb,text) "
                    f"IS '{contract_comment}'"
                )
            )
        metadata = metadata_for(snapshot)
        deferred_domain_locator_check = None
        if bind.dialect.name == "postgresql" and target_is_current:
            deferred_domain_locator_check = _defer_domain_locator_check(metadata)
        try:
            metadata.create_all(bind=bind)
        finally:
            if deferred_domain_locator_check is not None:
                metadata.tables["domain_events"].constraints.add(
                    deferred_domain_locator_check
                )
        _restore_all_tables(
            bind,
            metadata,
            restore_rows,
            # A downgrade starts from the current canonical schema.  Its
            # UUID primary keys are already the authority for every scoped
            # child FK, so aliasing (for example cost_model_versions.id <-
            # legacy_id) would mint a different parent ID while preserving
            # app_settings.active_cost_model_id.  Aliases remain necessary
            # only when upgrading an actual pre-0016 source.
            prefer_aliases=target_is_current and not roundtrip_preexisting,
        )
        if bind.dialect.name == "postgresql" and target_is_current:
            _install_and_validate_domain_locator_check()
        if guards:
            _install_guards()
    except Exception:
        # PostgreSQL rolls the migration transaction back atomically.  SQLite
        # transactional DDL is driver-dependent, so reconstruct the exact
        # source schema from the untouched physical backup before re-raising.
        if bind.dialect.name == "sqlite":
            _drop_application_tables()
            _restore_sqlite_source_schema(bind, source_schema, source_rows)
            if guards:
                _install_guards()
            _drop_backup_set(bind, _SOURCE_BACKUP_PREFIX)
            if not target_is_current:
                _drop_backup_set(bind, _ROUNDTRIP_BACKUP_PREFIX)
            bind.commit()
        raise
    _drop_backup_set(bind, _SOURCE_BACKUP_PREFIX)
    if target_is_current:
        _drop_backup_set(bind, _ROUNDTRIP_BACKUP_PREFIX)


def upgrade() -> None:
    _replace(CURRENT, guards=True)


def downgrade() -> None:
    _replace(PREVIOUS, guards=True)
