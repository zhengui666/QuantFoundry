#!/usr/bin/env python3
"""Add deterministic, valid rows needed by the populated migration gate.

This is a CI-only fixture loader. It never runs as part of application startup
and refuses to mutate a database without explicit test-only opt-in.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import runpy
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import MetaData, Table, create_engine, func, null, select, text
from sqlalchemy.engine import make_url

BACKEND_ROOT = Path(__file__).resolve().parents[1]
GATE_MANIFEST_PATH = BACKEND_ROOT / "schema/populated_migration_gate.json"
TARGET_TABLES = (
    "app_settings",
    "data_sources",
    "idempotency_records",
    "model_provider_connections",
    "records",
    "research_policy_versions",
    "session_tokens",
    "setup_bindings",
)
_FIXTURE_NOW = datetime(2026, 1, 1, tzinfo=UTC)
_UUID_COUNTER = 0


def _table(metadata: MetaData, name: str, bind: Any) -> Table:
    return Table(name, metadata, autoload_with=bind)


def _now() -> datetime:
    return _FIXTURE_NOW


def _uuid(value: Any = None) -> uuid.UUID:
    global _UUID_COUNTER
    if isinstance(value, uuid.UUID):
        return value
    _UUID_COUNTER += 1
    return uuid.uuid5(
        uuid.UUID("7d4dd1d8-75c0-4a9a-8b53-c05ef8f2c5a4"), str(_UUID_COUNTER)
    )


def _source_row(
    connection: Any,
    table: Table,
    workspace_id: Any = None,
    source_where: Any = None,
) -> dict[str, Any]:
    statement = select(table)
    if workspace_id is not None and "workspace_id" in table.c:
        statement = statement.where(table.c.workspace_id == workspace_id)
    if source_where is not None:
        statement = statement.where(source_where)
    row = connection.execute(statement.limit(1)).mappings().first()
    if row is None:
        raise RuntimeError(f"migration gate fixture has no source row for {table.name}")
    return dict(row)


def _workspaces(connection: Any, metadata: MetaData) -> list[Any]:
    table = metadata.tables["workspaces"]
    return list(connection.execute(select(table.c.id)).scalars())


def _insert(connection: Any, table: Table, values: dict[str, Any]) -> None:
    connection.execute(table.insert().values(values))


def _rechain_audit_events(connection: Any, table: Table) -> None:
    """Recompute the disposable fixture's audit chain after row surgery."""
    migration_hash = runpy.run_path(
        str(
            BACKEND_ROOT
            / "alembic/versions/0017_paper_scheduler_state_initialization.py"
        )
    )["_hash"]
    disable_triggers = connection.dialect.name == "postgresql"
    if disable_triggers:
        connection.exec_driver_sql("ALTER TABLE audit_events DISABLE TRIGGER USER")
    try:
        workspaces = connection.execute(
            select(table.c.workspace_id).distinct()
        ).scalars()
        for workspace_id in workspaces:
            previous: str | None = None
            rows = connection.execute(
                select(table)
                .where(table.c.workspace_id == workspace_id)
                .order_by(table.c.sequence)
            ).mappings()
            for row in rows:
                canonical = dict(row)
                canonical["prev_event_hash"] = previous
                canonical.pop("event_hash", None)
                event_hash = migration_hash(canonical)
                connection.execute(
                    table.update()
                    .where(table.c.id == row["id"])
                    .values(prev_event_hash=previous, event_hash=event_hash)
                )
                previous = event_hash
    finally:
        if disable_triggers:
            connection.exec_driver_sql("ALTER TABLE audit_events ENABLE TRIGGER USER")


def _clone(
    connection: Any, table: Table, source: dict[str, Any], index: int
) -> dict[str, Any]:
    values = {name: value for name, value in source.items() if name in table.c}
    if "id" in values:
        values["id"] = _uuid()
    if "workspace_id" in values:
        values["workspace_id"] = source.get("workspace_id")
    if "internal_id" in values:
        values["internal_id"] = _uuid()
    if "token_sha256" in values:
        values["token_sha256"] = hashlib.sha256(
            f"qf-migration-gate-session-{index}".encode()
        ).hexdigest()
    if "request_sha256" in values:
        values["request_sha256"] = hashlib.sha256(
            f"qf-migration-gate-request-{index}".encode()
        ).hexdigest()
    if "content_sha256" in values:
        values["content_sha256"] = hashlib.sha256(
            f"qf-migration-gate-content-{table.name}-{index}".encode()
        ).hexdigest()
    if table.name == "agent_runs":
        if values.get("agent_run_id") is not None:
            values["agent_run_id"] = f"ARUN-{_uuid()}"
        if values.get("checkpoint_thread_id") is not None:
            values["checkpoint_thread_id"] = f"THREAD-MIGRATION-GATE-{index}"
        values["next_action"] = null()
    elif table.name == "audit_events":
        values["event_id"] = f"AUD-{_uuid()}"
        values["event_hash"] = hashlib.sha256(
            f"qf-migration-gate-audit-{index}".encode()
        ).hexdigest()
    elif table.name == "domain_events":
        values["event_id"] = f"EVT-{_uuid()}"
    elif table.name == "experiments":
        values["experiment_id"] = f"EXP-{_uuid()}"
    elif table.name == "approval_requests":
        values["approval_id"] = f"APR-{_uuid()}"
    elif table.name == "factors":
        values["factor_id"] = f"FAC-{_uuid()}"
    elif table.name == "jobs":
        values["job_id"] = f"JOB-{_uuid()}"
        if values.get("resume_token_hash") is not None:
            values["resume_token_hash"] = hashlib.sha256(
                f"qf-migration-gate-resume-{index}".encode()
            ).hexdigest()
    elif table.name == "provenance_records":
        values["provenance_id"] = f"PROV-{_uuid()}"
    elif table.name == "research_cases":
        values["research_id"] = f"RSCH-{_uuid()}"
    elif table.name == "tool_calls":
        values["tool_call_id"] = f"TCALL-{_uuid()}"
        values["input_sha256"] = hashlib.sha256(
            f"qf-migration-gate-tool-input-{index}".encode()
        ).hexdigest()
    elif table.name == "validation_runs":
        values["validation_id"] = f"VAL-{_uuid()}"
    elif table.name == "strategy_versions":
        values["version"] = int(values.get("version") or 1) + index
    if "record_key" in values:
        values["kind"] = "artifact"
        values["record_key"] = f"ART-{_uuid()}"
    if "legacy_id" in values:
        values["legacy_id"] = f"QF-GATE-{table.name}-{index}"
    if table.name == "agent_configs" and "role_key" in values:
        values["role_key"] = f"QF-GATE-ROLE-{index}"
    if table.name == "runtime_heartbeats":
        if "component" in values:
            values["component"] = f"qf-migration-gate-{index}"
        if "instance_id" in values:
            values["instance_id"] = f"instance-{_uuid()}"
    if table.name == "cost_model_versions" and "cost_model_id" in values:
        values["cost_model_id"] = f"COST-{_uuid()}"
    if table.name == "users" and "email" in values:
        values["email"] = f"qf-migration-gate-{index}@example.invalid"
    if "policy_id" in values:
        if not isinstance(values["policy_id"], uuid.UUID):
            values["policy_id"] = f"RP-{_uuid()}"
    if "normalized_route" in values:
        values["normalized_route"] = f"/__qf_migration_gate__/{table.name}/{index}"
    if "key" in values:
        values["key"] = f"qf-migration-gate-{table.name}-{index}"
    if "public_id" in values:
        values["public_id"] = f"SETTINGS-GATE-{index}"
    if "version" in values and "policy_family" in values:
        values["version"] = int(values["version"] or 1) + index
        values["status"] = "DRAFT"
    return values


def _next_sequence(connection: Any, table: Table, workspace_id: Any) -> int:
    value = connection.execute(
        select(func.max(table.c.sequence)).where(table.c.workspace_id == workspace_id)
    ).scalar_one()
    return int(value or 0) + 1


def _clone_gate_row(
    connection: Any,
    metadata: MetaData,
    table: Table,
    source: dict[str, Any],
    index: int,
) -> dict[str, Any]:
    values = _clone(connection, table, source, index)
    if table.name in {"audit_events", "domain_events"}:
        values["sequence"] = _next_sequence(connection, table, values["workspace_id"])
    if table.name == "audit_events":
        previous = connection.execute(
            select(table.c.event_hash)
            .where(table.c.workspace_id == values["workspace_id"])
            .order_by(table.c.sequence.desc())
            .limit(1)
        ).scalar_one_or_none()
        values["prev_event_hash"] = previous
    if table.name == "snapshot_partitions":
        values["id"] = f"SPART-{_uuid()}"
        values["artifact_id"] = f"ART-{_uuid()}"
        if values.get("partition") not in {"RESEARCH", "VALIDATION", "HOLDOUT"}:
            values["partition"] = "RESEARCH"
    if table.name == "holdout_exposures":
        workspace_id = values["workspace_id"]

        def candidates(name: str) -> list[dict[str, Any]]:
            source_table = metadata.tables[name]
            return [
                dict(row)
                for row in connection.execute(
                    select(source_table).where(
                        source_table.c.workspace_id == workspace_id
                    )
                ).mappings()
            ]

        def unused(rows: list[dict[str, Any]], key: str, column: str) -> dict[str, Any]:
            used = set(connection.execute(select(table.c[column])).scalars())
            for row in rows:
                if row[key] not in used:
                    return row
            raise RuntimeError(f"migration gate fixture lacks unused {column}")

        approval_rows = candidates("approval_requests")
        try:
            approval = unused(approval_rows, "id", "approval_id")
        except RuntimeError:
            if not approval_rows:
                raise
            approval = _clone(
                connection,
                metadata.tables["approval_requests"],
                approval_rows[0],
                index,
            )
            approval["workspace_id"] = workspace_id
            _insert(connection, metadata.tables["approval_requests"], approval)
        job = unused(candidates("jobs"), "job_id", "job_id")
        validation_runs = candidates("validation_runs")
        if not validation_runs:
            raise RuntimeError("migration gate fixture requires a validation run")
        used_validation_ids = set(
            connection.execute(select(table.c.validation_id)).scalars()
        )
        available_validation_runs = [
            row
            for row in validation_runs
            if row["validation_id"] not in used_validation_ids
        ]
        if not available_validation_runs:
            raise RuntimeError("migration gate fixture lacks unused validation run")
        validation_run = available_validation_runs[index % len(available_validation_runs)]
        validation = metadata.tables["validations"]
        validation_row = (
            connection.execute(
                select(validation).where(
                    validation.c.workspace_id == workspace_id,
                    validation.c.id == validation_run["validation_id"],
                )
            )
            .mappings()
            .first()
        )
        if validation_row is None:
            raise RuntimeError(
                "migration gate fixture validation run has no validation dependency"
            )
        values.update(
            {
                "exposure_id": f"HOLD-{_uuid()}",
                "approval_id": approval["id"],
                "approval_public_id": approval["approval_id"],
                "job_id": job["job_id"],
                "exposed_by_job_id": job["id"],
                "validation_id": validation_row["id"],
                "validation_run_id": validation_run["id"],
            }
        )
    if table.name == "job_dependencies":
        jobs = connection.execute(
            select(
                metadata.tables["jobs"].c.id,
                metadata.tables["jobs"].c.job_id,
            ).where(metadata.tables["jobs"].c.workspace_id == values["workspace_id"])
        ).all()
        if len(jobs) < 2:
            raise RuntimeError("migration gate fixture requires two jobs per workspace")
        existing = {
            (row.job_public_id, row.depends_on_job_public_id)
            for row in connection.execute(
                select(table.c.job_public_id, table.c.depends_on_job_public_id).where(
                    table.c.workspace_id == values["workspace_id"]
                )
            )
        }
        source_job = dependency_job = None
        for offset in range(len(jobs) * len(jobs)):
            candidate = jobs[(index + offset) % len(jobs)]
            dependency = jobs[(index + offset + 1) % len(jobs)]
            if (
                candidate.job_id != dependency.job_id
                and (
                    candidate.job_id,
                    dependency.job_id,
                )
                not in existing
            ):
                source_job, dependency_job = candidate, dependency
                break
        if source_job is None or dependency_job is None:
            raise RuntimeError("migration gate fixture lacks unused job dependency")
        values.update(
            {
                "job_id": source_job.id,
                "depends_on_job_id": dependency_job.id,
                "job_public_id": source_job.job_id,
                "depends_on_job_public_id": dependency_job.job_id,
            }
        )
    return values


def _ensure_rows(connection: Any, metadata: MetaData, name: str, floor: int) -> None:
    table = metadata.tables[name]
    count = int(
        connection.execute(select(func.count()).select_from(table)).scalar_one()
    )
    if count >= floor:
        return
    if name in {"audit_chain_heads", "event_stream_watermarks"}:
        workspaces = _workspaces(connection, metadata)
        existing = set(connection.execute(select(table.c.workspace_id)).scalars())
        for workspace_id in workspaces:
            if count >= floor:
                break
            if workspace_id in existing:
                continue
            if name == "audit_chain_heads":
                latest = connection.execute(
                    select(
                        metadata.tables["audit_events"].c.event_hash,
                        metadata.tables["audit_events"].c.sequence,
                    )
                    .where(
                        metadata.tables["audit_events"].c.workspace_id == workspace_id
                    )
                    .order_by(metadata.tables["audit_events"].c.sequence.desc())
                    .limit(1)
                ).first()
                values = {
                    "workspace_id": workspace_id,
                    "event_sha256": None if latest is None else latest.event_hash,
                    "revision": 0 if latest is None else latest.sequence,
                }
            else:
                latest = connection.execute(
                    select(func.max(metadata.tables["domain_events"].c.sequence)).where(
                        metadata.tables["domain_events"].c.workspace_id == workspace_id
                    )
                ).scalar_one()
                values = {
                    "workspace_id": workspace_id,
                    "last_sequence": int(latest or 0),
                    "expired_through_sequence": 0,
                }
            _insert(connection, table, values)
            existing.add(workspace_id)
            count += 1
        if count < floor:
            raise RuntimeError(f"migration gate fixture lacks workspace for {name}")
        return
    source = _source_row(connection, table)
    for index in range(floor - count):
        values = _clone_gate_row(connection, metadata, table, source, count + index)
        _insert(connection, table, values)


def _count(connection: Any, table: Table) -> int:
    return int(connection.execute(select(func.count()).select_from(table)).scalar_one())


def _ensure_workspace_dependency(
    connection: Any,
    metadata: MetaData,
    name: str,
    workspace_id: Any,
    source_where: Any = None,
) -> dict[str, Any]:
    table = metadata.tables[name]
    statement = select(table).where(table.c.workspace_id == workspace_id)
    if source_where is not None:
        statement = statement.where(source_where)
    row = (
        connection.execute(statement.limit(1))
        .mappings()
        .first()
    )
    if row is not None:
        return dict(row)
    source = _source_row(connection, table, source_where=source_where)
    stable_index = int.from_bytes(
        hashlib.sha256(f"{name}:{workspace_id}".encode()).digest()[:8], "big"
    )
    values = _clone(connection, table, source, stable_index)
    values["workspace_id"] = workspace_id
    if name == "model_provider_connections" and "owner_actor_id" in table.c:
        values["owner_actor_id"] = connection.execute(
            select(metadata.tables["workspaces"].c.owner_id).where(
                metadata.tables["workspaces"].c.id == workspace_id
            )
        ).scalar_one()
    if name in {
        "research_policy_versions",
        "risk_policy_versions",
        "cost_model_versions",
    }:
        values["status"] = "ACTIVE"
        if "activated_at" in table.c:
            values["activated_at"] = _now()
    _insert(connection, table, values)
    return values


def _ensure_settings_record(
    connection: Any, metadata: MetaData, workspace_id: str
) -> None:
    table = metadata.tables["records"]
    found = connection.execute(
        select(table.c.id).where(
            table.c.workspace_id == workspace_id,
            table.c.record_key == "SETTINGS-DEFAULT",
        )
    ).first()
    if found is not None:
        return
    now = _now()
    _insert(
        connection,
        table,
        {
            "id": _uuid(),
            "workspace_id": workspace_id,
            "record_key": "SETTINGS-DEFAULT",
            "kind": "settings",
            "revision": 1,
            "body": "{}",
            "created_at": now,
            "updated_at": now,
        },
    )


def _ensure_app_settings(
    connection: Any, metadata: MetaData, workspace_id: Any
) -> None:
    table = metadata.tables["app_settings"]
    if connection.execute(
        select(table.c.id).where(table.c.workspace_id == workspace_id)
    ).first():
        return
    ai = _ensure_workspace_dependency(
        connection,
        metadata,
        "model_provider_connections",
        workspace_id,
        source_where=metadata.tables["model_provider_connections"].c.kind == "AI",
    )
    research = _ensure_workspace_dependency(
        connection, metadata, "research_policy_versions", workspace_id
    )
    risk = _ensure_workspace_dependency(
        connection, metadata, "risk_policy_versions", workspace_id
    )
    cost = _ensure_workspace_dependency(
        connection, metadata, "cost_model_versions", workspace_id
    )
    now = _now()
    _insert(
        connection,
        table,
        {
            "id": _uuid(),
            "workspace_id": workspace_id,
            "public_id": "SETTINGS-DEFAULT",
            "revision": 1,
            "language": "zh-CN",
            "timezone": "UTC",
            "base_currency": "USD",
            "number_format_locale": "en-US",
            "ai_connection_id": ai["id"],
            "default_data_provider_id": None,
            "default_benchmark": "SPX",
            "default_frequency": "DAILY",
            "default_research_start": None,
            "initial_paper_capital": 100000,
            "active_research_policy_id": research["id"],
            "active_risk_policy_id": risk["id"],
            "active_cost_model_id": cost["id"],
            "created_at": now,
            "updated_at": now,
        },
    )


def _ensure_setup_binding(
    connection: Any, metadata: MetaData, workspace_id: Any
) -> None:
    table = metadata.tables["setup_bindings"]
    if connection.execute(
        select(table.c.workspace_id).where(table.c.workspace_id == workspace_id)
    ).first():
        return
    _ensure_settings_record(connection, metadata, workspace_id)
    ai = _ensure_workspace_dependency(
        connection,
        metadata,
        "model_provider_connections",
        workspace_id,
        source_where=metadata.tables["model_provider_connections"].c.kind == "AI",
    )
    research = _ensure_workspace_dependency(
        connection, metadata, "research_policy_versions", workspace_id
    )
    risk = _ensure_workspace_dependency(
        connection, metadata, "risk_policy_versions", workspace_id
    )
    cost = _ensure_workspace_dependency(
        connection, metadata, "cost_model_versions", workspace_id
    )
    now = _now()
    _insert(
        connection,
        table,
        {
            "workspace_id": workspace_id,
            "settings_record_id": "SETTINGS-DEFAULT",
            "ai_connection_id": ai["id"],
            "data_connection_id": None,
            "research_policy_version_id": research["legacy_id"],
            "risk_policy_version_id": risk["legacy_id"],
            "cost_model_version_id": cost["legacy_id"],
            "revision": 1,
            "created_at": now,
            "updated_at": now,
        },
    )


def _repair_scheduler_fixture(connection: Any, metadata: MetaData) -> None:
    """Make negative scheduler-test rows valid before the migration gate.

    The application suite intentionally leaves fail-closed rows behind. The
    populated migration gate must exercise a valid legacy corpus, so normalize
    only this disposable CI database before taking its fingerprint.
    """
    migration = runpy.run_path(
        str(
            BACKEND_ROOT
            / "alembic/versions/0017_paper_scheduler_state_initialization.py"
        )
    )
    affected_workspace_ids: set[Any] = set()
    # The repeated application suite intentionally emits multiple scheduler
    # evidence events. Rebuild this disposable evidence stream deterministically
    # so the migration's exactly-one baseline contract is testable.
    if connection.dialect.name == "postgresql":
        connection.exec_driver_sql("ALTER TABLE audit_events DISABLE TRIGGER USER")
        connection.exec_driver_sql("ALTER TABLE domain_events DISABLE TRIGGER USER")
        try:
            evidence_key = migration["_EVIDENCE_KEY"]
            audit_table = _table(metadata, "audit_events", connection)
            event_table = _table(metadata, "domain_events", connection)
            audit_ids = []
            event_ids = []
            evidence_rows = connection.execute(
                select(
                    audit_table.c.id,
                    audit_table.c.workspace_id,
                    audit_table.c.summary,
                ).where(
                    audit_table.c.action_type
                    == "SCHEDULER_STATE_INITIALIZED_NO_HISTORY",
                    audit_table.c.object_type == "paper",
                )
            ).mappings()
            for row in evidence_rows:
                if row["workspace_id"] is not None:
                    affected_workspace_ids.add(row["workspace_id"])
                summary = row["summary"]
                if isinstance(summary, str):
                    try:
                        summary = json.loads(summary)
                    except json.JSONDecodeError:
                        continue
                evidence = (
                    summary.get(evidence_key) if isinstance(summary, dict) else None
                )
                state_transition_id = (
                    evidence.get("state_transition_id")
                    if isinstance(evidence, dict)
                    else None
                )
                if state_transition_id:
                    audit_ids.append(row["id"])
                    event_ids.append(state_transition_id)
            if audit_ids:
                connection.execute(
                    audit_table.delete().where(audit_table.c.id.in_(audit_ids))
                )
            if event_ids:
                connection.execute(
                    event_table.delete().where(event_table.c.event_id.in_(event_ids))
                )
            _rechain_audit_events(connection, audit_table)
        finally:
            connection.exec_driver_sql("ALTER TABLE audit_events ENABLE TRIGGER USER")
            connection.exec_driver_sql("ALTER TABLE domain_events ENABLE TRIGGER USER")
    for name in (
        "paper_deployments",
        "paper_scheduler_states",
        "audit_events",
        "domain_events",
        "audit_chain_heads",
        "event_stream_watermarks",
    ):
        _table(metadata, name, connection)
    deployments = metadata.tables["paper_deployments"]
    states = metadata.tables["paper_scheduler_states"]
    audits = metadata.tables["audit_events"]
    events = metadata.tables["domain_events"]
    heads = metadata.tables["audit_chain_heads"]
    watermarks = metadata.tables["event_stream_watermarks"]
    workspace_ids = {
        row[0] for row in connection.execute(select(deployments.c.workspace_id)).all()
    } | affected_workspace_ids
    for workspace_id in workspace_ids:
        _rechain_audit_events(connection, audits)
        latest_audit = connection.execute(
            select(audits.c.event_hash, audits.c.sequence)
            .where(audits.c.workspace_id == workspace_id)
            .order_by(audits.c.sequence.desc())
            .limit(1)
        ).first()
        if latest_audit is None:
            connection.execute(
                heads.delete().where(heads.c.workspace_id == workspace_id)
            )
        else:
            result = connection.execute(
                heads.update()
                .where(heads.c.workspace_id == workspace_id)
                .values(
                    event_sha256=latest_audit.event_hash, revision=latest_audit.sequence
                )
            )
            if result.rowcount == 0:
                connection.execute(
                    heads.insert().values(
                        workspace_id=workspace_id,
                        event_sha256=latest_audit.event_hash,
                        revision=latest_audit.sequence,
                    )
                )
        latest_event = connection.execute(
            select(events.c.sequence)
            .where(events.c.workspace_id == workspace_id)
            .order_by(events.c.sequence.desc())
            .limit(1)
        ).scalar_one_or_none()
        if latest_event is None:
            connection.execute(
                watermarks.delete().where(watermarks.c.workspace_id == workspace_id)
            )
        else:
            result = connection.execute(
                watermarks.update()
                .where(watermarks.c.workspace_id == workspace_id)
                .values(last_sequence=latest_event)
            )
            if result.rowcount == 0:
                connection.execute(
                    watermarks.insert().values(
                        workspace_id=workspace_id,
                        last_sequence=latest_event,
                        expired_through_sequence=0,
                    )
                )
    status_for_target = {"ACTIVE": "ACTIVE", "PAUSED": "PAUSED", "DISABLED": "DISABLED"}
    for deployment in connection.execute(select(deployments)).mappings().all():
        pair = (deployment["workspace_id"], deployment["id"])
        state_rows = (
            connection.execute(
                select(states).where(
                    states.c.workspace_id == pair[0], states.c.paper_id == pair[1]
                )
            )
            .mappings()
            .all()
        )
        if len(state_rows) > 1:
            raise RuntimeError(f"ambiguous scheduler fixture state: {pair!r}")
        if not state_rows:
            migration["_validate_support_rows"](
                connection,
                audits,
                events,
                heads,
                watermarks,
                deployment["workspace_id"],
            )
            migration["_insert_baseline"](
                connection,
                deployments,
                states,
                audits,
                events,
                heads,
                watermarks,
                dict(deployment),
                migration["_legacy_target"](dict(deployment)),
                _now(),
            )
            continue
        target = str(state_rows[0]["scheduler_status"])
        if target not in status_for_target:
            raise RuntimeError(f"invalid scheduler fixture state: {pair!r}")
        audit_rows = (
            connection.execute(
                select(audits).where(
                    audits.c.workspace_id == pair[0],
                    audits.c.object_type == "paper",
                    audits.c.object_id == deployment["paper_id"],
                    audits.c.action_type == "SCHEDULER_STATE_INITIALIZED_NO_HISTORY",
                    audits.c.detail_artifact_id.is_(None),
                )
            )
            .mappings()
            .all()
        )
        if not audit_rows:
            connection.execute(
                states.delete()
                .where(states.c.workspace_id == pair[0])
                .where(states.c.paper_id == pair[1])
            )
            migration["_validate_support_rows"](
                connection,
                audits,
                events,
                heads,
                watermarks,
                deployment["workspace_id"],
            )
            migration["_insert_baseline"](
                connection,
                deployments,
                states,
                audits,
                events,
                heads,
                watermarks,
                dict(deployment),
                target,
                _now(),
            )
            if deployment["status"] != status_for_target[target]:
                connection.execute(
                    deployments.update()
                    .where(deployments.c.workspace_id == pair[0])
                    .where(deployments.c.id == pair[1])
                    .values(status=status_for_target[target])
                )
            continue
        if len(audit_rows) > 1:
            raise RuntimeError(f"ambiguous scheduler fixture evidence: {pair!r}")
        summary = audit_rows[0]["summary"]
        if isinstance(summary, str):
            summary = json.loads(summary)
        evidence = summary[migration["_EVIDENCE_KEY"]]
        transition_id = evidence["state_transition_id"]
        event_rows = (
            connection.execute(
                select(events).where(
                    events.c.workspace_id == pair[0],
                    events.c.event_id == transition_id,
                    events.c.event_type == "paper.updated",
                    events.c.object_type == "paper",
                    events.c.object_id == deployment["paper_id"],
                )
            )
            .mappings()
            .all()
        )
        if not event_rows:
            instant = datetime.fromisoformat(
                str(evidence["initialization_utc"]).replace("Z", "+00:00")
            ).astimezone(UTC)
            sequence = int(evidence["domain_event_sequence"])
            if sequence < 1 or isinstance(evidence["domain_event_sequence"], bool):
                raise RuntimeError(
                    f"invalid scheduler fixture event sequence: {pair!r}"
                )
            occupied = connection.execute(
                select(events.c.event_id).where(
                    events.c.workspace_id == pair[0],
                    events.c.sequence == sequence,
                )
            ).scalar_one_or_none()
            if occupied is not None:
                raise RuntimeError(
                    f"scheduler fixture event sequence is already occupied: {pair!r}"
                )
            connection.execute(
                events.insert().values(
                    sequence=sequence,
                    event_id=transition_id,
                    workspace_id=pair[0],
                    actor_id="alembic:0017",
                    event_type="paper.updated",
                    object_type="paper",
                    object_id=deployment["paper_id"],
                    object_version=None,
                    object_revision=state_rows[0]["revision"],
                    revision=state_rows[0]["revision"],
                    payload={"status": target},
                    request_id=None,
                    correlation_id=None,
                    causation_id=None,
                    job_id=None,
                    agent_run_id=None,
                    tool_call_id=None,
                    occurred_at=instant,
                    expires_at=instant + timedelta(days=7),
                    schema_version=1,
                )
            )
            watermark = connection.execute(
                select(watermarks.c.last_sequence).where(
                    watermarks.c.workspace_id == pair[0]
                )
            ).scalar_one_or_none()
            if watermark is None:
                connection.execute(
                    watermarks.insert().values(
                        workspace_id=pair[0],
                        last_sequence=sequence,
                        expired_through_sequence=0,
                    )
                )
            elif sequence > watermark:
                connection.execute(
                    watermarks.update()
                    .where(watermarks.c.workspace_id == pair[0])
                    .values(last_sequence=sequence)
                )
        # Negative tests may deliberately desynchronize the deployment status;
        # preserve the proven state/evidence and restore the authoritative
        # legacy status for the migration corpus.
        if deployment["status"] != status_for_target[target]:
            connection.execute(
                deployments.update()
                .where(deployments.c.workspace_id == pair[0])
                .where(deployments.c.id == pair[1])
                .values(status=status_for_target[target])
            )

    for workspace_id in workspace_ids:
        latest_audit = connection.execute(
            select(audits.c.event_hash, audits.c.sequence)
            .where(audits.c.workspace_id == workspace_id)
            .order_by(audits.c.sequence.desc())
            .limit(1)
        ).first()
        if latest_audit is not None:
            connection.execute(
                heads.update()
                .where(heads.c.workspace_id == workspace_id)
                .values(
                    event_sha256=latest_audit.event_hash, revision=latest_audit.sequence
                )
            )
        latest_event = connection.execute(
            select(events.c.sequence)
            .where(events.c.workspace_id == workspace_id)
            .order_by(events.c.sequence.desc())
            .limit(1)
        ).scalar_one_or_none()
        if latest_event is not None:
            connection.execute(
                watermarks.update()
                .where(watermarks.c.workspace_id == workspace_id)
                .values(last_sequence=latest_event)
            )


def populate(database_url: str) -> dict[str, int]:
    if os.getenv("QF_ALLOW_MIGRATION_GATE_SEED") != "1":
        raise RuntimeError(
            "migration gate fixture requires QF_ALLOW_MIGRATION_GATE_SEED=1"
        )
    marker = os.getenv("QF_MIGRATION_GATE_MARKER")
    expected_database = os.getenv("QF_PG18_CI_DATABASE_NAME")
    parsed = make_url(database_url)
    if not marker:
        raise RuntimeError(
            "QF_MIGRATION_GATE_MARKER is required; refusing destructive fixture mutation"
        )
    if parsed.drivername != "postgresql+psycopg":
        raise RuntimeError("migration gate fixture requires PostgreSQL psycopg")
    if expected_database and parsed.database != expected_database:
        raise RuntimeError(
            "migration gate fixture database identity does not match CI target"
        )
    import json

    manifest = json.loads(GATE_MANIFEST_PATH.read_text(encoding="utf-8"))
    floors = manifest["critical_table_floors"]
    minimum_rows = int(manifest["minimum_rows"])
    engine = create_engine(database_url)
    metadata = MetaData()
    try:
        with engine.connect() as connection:
            markers = connection.execute(
                text(
                    "SELECT marker FROM migration_gate_control.marker ORDER BY marker"
                )
            ).scalars().all()
            if markers != [marker]:
                raise RuntimeError("migration gate target marker does not match")
        with engine.begin() as connection:
            metadata.reflect(bind=connection)
            reflected = {name: metadata.tables[name] for name in TARGET_TABLES}
            if "workspaces" in floors:
                _ensure_rows(
                    connection, metadata, "workspaces", int(floors["workspaces"])
                )
            # Tables with no rows need valid workspace-bound dependencies first.
            workspaces = _workspaces(connection, metadata)
            if len(workspaces) < 2:
                raise RuntimeError("migration gate fixture requires two workspaces")
            _repair_scheduler_fixture(connection, metadata)
            for workspace_id in workspaces[:2]:
                _ensure_app_settings(connection, metadata, workspace_id)
                _ensure_setup_binding(connection, metadata, workspace_id)
            for name in floors:
                if name in {"app_settings", "setup_bindings"}:
                    continue
                _ensure_rows(connection, metadata, name, int(floors[name]))
            total_rows = sum(
                _count(connection, table)
                for table in metadata.tables.values()
                if table.name != "alembic_version"
            )
            if total_rows < minimum_rows:
                _ensure_rows(
                    connection,
                    metadata,
                    "records",
                    _count(connection, metadata.tables["records"])
                    + minimum_rows
                    - total_rows,
                )
            audits = metadata.tables["audit_events"]
            events = metadata.tables["domain_events"]
            heads = metadata.tables["audit_chain_heads"]
            watermarks = metadata.tables["event_stream_watermarks"]
            _rechain_audit_events(connection, audits)
            for workspace_id in workspaces:
                latest_audit = connection.execute(
                    select(audits.c.event_hash, audits.c.sequence)
                    .where(audits.c.workspace_id == workspace_id)
                    .order_by(audits.c.sequence.desc())
                    .limit(1)
                ).first()
                if latest_audit is not None:
                    if (
                        connection.execute(
                            heads.update()
                            .where(heads.c.workspace_id == workspace_id)
                            .values(
                                event_sha256=latest_audit.event_hash,
                                revision=latest_audit.sequence,
                            )
                        ).rowcount
                        == 0
                    ):
                        connection.execute(
                            heads.insert().values(
                                workspace_id=workspace_id,
                                event_sha256=latest_audit.event_hash,
                                revision=latest_audit.sequence,
                            )
                        )
                latest_event = connection.execute(
                    select(events.c.sequence)
                    .where(events.c.workspace_id == workspace_id)
                    .order_by(events.c.sequence.desc())
                    .limit(1)
                ).scalar_one_or_none()
                if latest_event is not None:
                    if (
                        connection.execute(
                            watermarks.update()
                            .where(watermarks.c.workspace_id == workspace_id)
                            .values(last_sequence=latest_event)
                        ).rowcount
                        == 0
                    ):
                        connection.execute(
                            watermarks.insert().values(
                                workspace_id=workspace_id,
                                last_sequence=latest_event,
                                expired_through_sequence=0,
                            )
                        )
            return {name: _count(connection, reflected[name]) for name in TARGET_TABLES}
    finally:
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv("QF_DATABASE_URL"))
    args = parser.parse_args()
    if not args.database_url:
        parser.error("--database-url or QF_DATABASE_URL is required")
    print("migration gate fixture counts:", populate(args.database_url))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
