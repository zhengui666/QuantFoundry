"""Fail-closed, Core-only Paper scheduler baseline readiness gate.

Revision ID: 0017_paper_scheduler_state_initialization
Revises: 0016_section14_schema
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import MetaData, Table, Text, Uuid, create_engine, select, text
from sqlalchemy.engine import Connection

from alembic import op
from quantfoundry.domain.value_objects.public_ids import is_public_id

revision = "0017_paper_scheduler_state_init"
down_revision = "0016_section14_schema"
branch_labels = None
depends_on = None

_STATUS_MAP = {
    "ACTIVE": "ACTIVE",
    "PAUSED": "PAUSED",
    "STOPPED": "DISABLED",
    "PENDING": "DISABLED",
    "FAILED": "DISABLED",
    "DISABLED": "DISABLED",
}
_REQUIRED = {
    "paper_deployments": {"id", "workspace_id", "paper_id", "status", "revision"},
    "paper_scheduler_states": {
        "id",
        "workspace_id",
        "paper_id",
        "scheduler_status",
        "suppressed_since_utc",
        "resume_watermark_utc",
        "revision",
    },
    "audit_events": {
        "id",
        "event_id",
        "actor_type",
        "actor_id",
        "workspace_id",
        "sequence",
        "action_type",
        "object_type",
        "object_id",
        "object_version",
        "object_revision",
        "result",
        "summary",
        "detail_artifact_id",
        "prev_event_hash",
        "event_hash",
        "occurred_at",
        "input_hash",
        "before_hash",
        "after_hash",
    },
    "domain_events": {
        "sequence",
        "event_id",
        "workspace_id",
        "event_type",
        "object_type",
        "object_id",
        "payload",
        "occurred_at",
        "expires_at",
    },
    "audit_chain_heads": {"workspace_id", "event_sha256", "revision"},
    "event_stream_watermarks": {
        "workspace_id",
        "last_sequence",
        "expired_through_sequence",
    },
}
_EVIDENCE_KEY = "paper_scheduler_state_evidence.v1"
_EVIDENCE_FIELDS = {
    "state_transition_id",
    "workspace_id",
    "paper_id",
    "from_state",
    "to_state",
    "effective_at_utc",
    "suppressed_since_utc",
    "resume_watermark_utc",
    "initialization_utc",
    "domain_event_sequence",
    "revision",
    "reason_code",
    "actor",
    "system",
    "commit_build_locator",
}


class SchedulerInitializationError(RuntimeError):
    """A legacy baseline cannot be proven, so readiness remains blocked."""

    def __init__(
        self,
        reason: str,
        reports: list[dict[str, str]] | None = None,
        quarantine_rows: list[Mapping[str, Any]] | None = None,
    ):
        self.reports = reports or []
        self.quarantine_rows = [dict(row) for row in quarantine_rows or []]
        suffix = (
            f": {json.dumps(self.reports, sort_keys=True, separators=(',', ':'))}"
            if self.reports
            else ""
        )
        super().__init__(f"{reason}{suffix}")


def _quarantine_report(row: Mapping[str, Any] | None, reason: str) -> dict[str, str]:
    payload = dict(row or {})
    locator = next(
        (
            str(payload[name])
            for name in ("paper_id", "id", "workspace_id")
            if payload.get(name) not in (None, "")
        ),
        "unknown",
    )
    encoded = json.dumps(payload, default=str, sort_keys=True, separators=(",", ":"))
    return {
        "locator": locator,
        "payload_sha256": hashlib.sha256(encoded.encode()).hexdigest(),
        "reason": reason,
    }


def _block(reason: str, row: Mapping[str, Any] | None = None) -> None:
    payload = dict(row or {})
    raise SchedulerInitializationError(
        reason,
        [_quarantine_report(payload, reason)],
        [payload],
    )


def _quarantine_table_name(bind: Connection) -> str:
    return (
        "migration_quarantine.scheduler_state_initialization_0017"
        if bind.dialect.name == "postgresql"
        else "_qf_migration_quarantine_0017"
    )


def _persist_quarantine(bind: Connection, error: SchedulerInitializationError) -> None:
    """Persist a restricted migration-only record after rolling back 0017 data."""
    reports = error.reports or [_quarantine_report(None, str(error))]
    rows = error.quarantine_rows or [{} for _ in reports]
    own_connection = bind.dialect.name == "postgresql" or (
        bind.dialect.name == "sqlite" and ":memory:" not in str(bind.engine.url)
    )
    engine = create_engine(bind.engine.url) if own_connection else None
    connection = engine.connect() if engine is not None else bind
    table_name = _quarantine_table_name(bind)
    try:
        if bind.dialect.name == "postgresql":
            connection.execute(text("CREATE SCHEMA IF NOT EXISTS migration_quarantine"))
            connection.execute(
                text("REVOKE ALL ON SCHEMA migration_quarantine FROM PUBLIC")
            )
            connection.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS "
                    "migration_quarantine.scheduler_state_initialization_0017 ("
                    "id bigserial PRIMARY KEY, recorded_at timestamptz NOT NULL, "
                    "workspace_locator text, source_locator text NOT NULL, "
                    "reason text NOT NULL, payload_sha256 char(64) NOT NULL, "
                    "payload_json text NOT NULL)"
                )
            )
            connection.execute(
                text(
                    "REVOKE ALL ON TABLE "
                    "migration_quarantine.scheduler_state_initialization_0017 FROM PUBLIC"
                )
            )
        else:
            connection.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS _qf_migration_quarantine_0017 ("
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, recorded_at TEXT NOT NULL, "
                    "workspace_locator TEXT, source_locator TEXT NOT NULL, "
                    "reason TEXT NOT NULL, payload_sha256 TEXT NOT NULL, "
                    "payload_json TEXT NOT NULL)"
                )
            )
        for report, row in zip(reports, rows, strict=True):
            connection.execute(
                text(
                    f"INSERT INTO {table_name} (recorded_at, workspace_locator, "
                    "source_locator, reason, payload_sha256, payload_json) VALUES "
                    "(:recorded_at, :workspace_locator, :source_locator, :reason, "
                    ":payload_sha256, :payload_json)"
                ),
                {
                    "recorded_at": datetime.now(UTC),
                    "workspace_locator": str(row.get("workspace_id"))
                    if row.get("workspace_id") is not None
                    else None,
                    "source_locator": report["locator"],
                    "reason": report["reason"],
                    "payload_sha256": report["payload_sha256"],
                    "payload_json": json.dumps(
                        row, default=str, sort_keys=True, separators=(",", ":")
                    ),
                },
            )
        connection.commit()
    finally:
        if connection is not bind:
            connection.close()
        if engine is not None:
            engine.dispose()


def _legacy_target(deployment: Mapping[str, Any]) -> str:
    status = deployment.get("status")
    revision = deployment.get("revision")
    if (
        not isinstance(status, str)
        or status not in _STATUS_MAP
        or deployment.get("id") in (None, "")
        or deployment.get("workspace_id") in (None, "")
        or deployment.get("paper_id") in (None, "")
        or not isinstance(revision, int)
        or isinstance(revision, bool)
        or revision < 1
    ):
        _block(
            "ambiguous scheduler initialization: unclassifiable legacy data", deployment
        )
    return _STATUS_MAP[cast(str, status)]


def _validate_deployment_authority(rows: Sequence[Mapping[str, Any]]) -> None:
    seen_identity: set[tuple[Any, Any]] = set()
    seen_locator: set[tuple[Any, Any]] = set()
    for deployment in rows:
        _legacy_target(deployment)
        identity = (deployment["workspace_id"], deployment["id"])
        locator = (deployment["workspace_id"], deployment["paper_id"])
        if identity in seen_identity or locator in seen_locator:
            _block(
                "ambiguous scheduler initialization: duplicate legacy deployment",
                deployment,
            )
        seen_identity.add(identity)
        seen_locator.add(locator)


def _tables(bind: Connection) -> tuple[Table, Table, Table, Table, Table, Table]:
    metadata = MetaData()
    metadata.reflect(bind=bind, only=list(_REQUIRED))
    missing = sorted(set(_REQUIRED) - set(metadata.tables))
    if missing:
        raise SchedulerInitializationError(f"missing initialization tables: {missing}")
    for name, required in _REQUIRED.items():
        actual = set(metadata.tables[name].c.keys())
        if required - actual:
            raise SchedulerInitializationError(
                f"unclassifiable {name} schema: missing={sorted(required - actual)}"
            )
    return (
        metadata.tables["paper_deployments"],
        metadata.tables["paper_scheduler_states"],
        metadata.tables["audit_events"],
        metadata.tables["domain_events"],
        metadata.tables["audit_chain_heads"],
        metadata.tables["event_stream_watermarks"],
    )


def _utc_timestamp(bind: Connection, value: Any, field: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise SchedulerInitializationError(
                f"ambiguous scheduler initialization: invalid {field}"
            ) from exc
    else:
        raise SchedulerInitializationError(
            f"ambiguous scheduler initialization: invalid {field}"
        )
    if parsed.tzinfo is None:
        if bind.dialect.name != "sqlite":
            raise SchedulerInitializationError(
                f"ambiguous scheduler initialization: non-UTC {field}"
            )
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _closed_object(value: Any, fields: set[str], field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != fields:
        raise SchedulerInitializationError(
            f"ambiguous scheduler initialization: invalid {field}"
        )
    if any(item in (None, "") for item in value.values()):
        raise SchedulerInitializationError(
            f"ambiguous scheduler initialization: invalid {field}"
        )
    return value


def _json_column_value(table: Table, column: str, value: Mapping[str, Any]) -> Any:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"))
        if isinstance(table.c[column].type, Text)
        else value
    )


def _uuid_column_value(table: Table, column: str, value: uuid.UUID) -> Any:
    return value if isinstance(table.c[column].type, Uuid) else str(value)


def _mapping_value(value: Any) -> Mapping[str, Any] | None:
    if isinstance(value, Mapping):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return None
        return decoded if isinstance(decoded, Mapping) else None
    return None


def _canonical_audit_hash_payload(
    audit_events: Table, audit: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        column.name: audit.get(column.name)
        for column in audit_events.columns
        if column.name != "event_hash"
    }


def _validate_evidence(
    bind: Connection,
    audit_events: Table,
    domain_events: Table,
    event_stream_watermarks: Table,
    deployment: Mapping[str, Any],
    baseline: Mapping[str, Any],
) -> None:
    audits = (
        bind.execute(
            select(audit_events).where(
                audit_events.c.workspace_id == deployment["workspace_id"],
                audit_events.c.object_type == "paper",
                audit_events.c.object_id == deployment["paper_id"],
                audit_events.c.action_type == "SCHEDULER_STATE_INITIALIZED_NO_HISTORY",
                audit_events.c.detail_artifact_id.is_(None),
            )
        )
        .mappings()
        .all()
    )
    if len(audits) != 1:
        _block("missing or ambiguous scheduler initialization evidence", deployment)
    summary = _mapping_value(audits[0]["summary"])
    if summary is None or set(summary) != {_EVIDENCE_KEY}:
        _block("ambiguous scheduler initialization evidence", deployment)
    evidence = summary[_EVIDENCE_KEY]
    if not isinstance(evidence, Mapping) or set(evidence) != _EVIDENCE_FIELDS:
        _block("ambiguous scheduler initialization evidence", deployment)
    audit = audits[0]

    effective = _utc_timestamp(bind, evidence["effective_at_utc"], "effective_at_utc")
    initialization = _utc_timestamp(
        bind, evidence["initialization_utc"], "initialization_utc"
    )
    evidence_watermark = _utc_timestamp(
        bind, evidence["resume_watermark_utc"], "resume_watermark_utc"
    )
    baseline_watermark = _utc_timestamp(
        bind, baseline["resume_watermark_utc"], "baseline resume_watermark_utc"
    )
    evidence_suppressed = evidence["suppressed_since_utc"]
    baseline_suppressed = baseline["suppressed_since_utc"]
    baseline_suppressed_at = (
        _utc_timestamp(bind, baseline_suppressed, "baseline suppressed_since_utc")
        if baseline_suppressed is not None
        else None
    )
    audit_occurred = _utc_timestamp(bind, audit["occurred_at"], "audit occurred_at")
    audit_valid = (
        audit.get("actor_type") == "SYSTEM"
        and audit.get("actor_id") == "alembic:0017"
        and audit.get("result") == "SUCCESS"
        and audit.get("object_type") == "paper"
        and audit.get("object_id") == deployment["paper_id"]
        and audit.get("object_version") is None
        and audit.get("object_revision") == baseline["revision"]
        and audit_occurred == initialization
        and audit.get("detail_artifact_id") is None
        and audit.get("before_hash") is None
        and audit.get("input_hash")
        == _hash(
            {"paper_id": deployment["paper_id"], "status": str(deployment["status"])}
        )
        and audit.get("after_hash") == _hash(evidence)
    )
    if not audit_valid:
        _block("ambiguous scheduler initialization audit envelope", deployment)
    valid = (
        isinstance(evidence["state_transition_id"], str)
        and is_public_id("domain_event", evidence["state_transition_id"])
        and str(evidence["workspace_id"]) == str(deployment["workspace_id"])
        and evidence["paper_id"] == deployment["paper_id"]
        and evidence["from_state"] is None
        and evidence["to_state"] == baseline["scheduler_status"]
        and effective == initialization == evidence_watermark == baseline_watermark
        and (
            (evidence["to_state"] == "ACTIVE" and evidence_suppressed is None)
            or (
                evidence["to_state"] != "ACTIVE"
                and evidence_suppressed is not None
                and _utc_timestamp(bind, evidence_suppressed, "suppressed_since_utc")
                == effective
                == baseline_suppressed_at
            )
        )
        and isinstance(evidence["revision"], int)
        and not isinstance(evidence["revision"], bool)
        and evidence["revision"] == baseline["revision"]
        and isinstance(evidence["domain_event_sequence"], int)
        and not isinstance(evidence["domain_event_sequence"], bool)
        and evidence["domain_event_sequence"] >= 1
        and evidence["reason_code"] == "SCHEDULER_STATE_INITIALIZED_NO_HISTORY"
    )
    if not valid:
        _block("ambiguous scheduler initialization evidence", deployment)
    _closed_object(evidence["actor"], {"type", "id"}, "actor")
    _closed_object(evidence["system"], {"service", "instance_id"}, "system")
    _closed_object(
        evidence["commit_build_locator"],
        {"commit_sha", "build_id"},
        "commit_build_locator",
    )
    if evidence["actor"] != {"type": "SYSTEM", "id": "alembic:0017"}:
        _block("ambiguous scheduler initialization actor", deployment)
    if evidence["system"] != {"service": "alembic", "instance_id": "0017"}:
        _block("ambiguous scheduler initialization system", deployment)
    if evidence["commit_build_locator"] != {
        "commit_sha": "migration-0017",
        "build_id": "alembic-0017",
    }:
        _block("ambiguous scheduler initialization build locator", deployment)
    canonical_audit = _canonical_audit_hash_payload(audit_events, audit)
    canonical_audit["occurred_at"] = initialization
    if audit.get("event_hash") != _hash(canonical_audit):
        _block("ambiguous scheduler initialization audit hash", deployment)
    events = (
        bind.execute(
            select(domain_events).where(
                domain_events.c.workspace_id == deployment["workspace_id"],
                domain_events.c.event_id == evidence["state_transition_id"],
            )
        )
        .mappings()
        .all()
    )
    retention = (
        bind.execute(
            select(event_stream_watermarks).where(
                event_stream_watermarks.c.workspace_id == deployment["workspace_id"]
            )
        )
        .mappings()
        .one_or_none()
    )
    expired_canonical_event = (
        not events
        and isinstance(evidence["domain_event_sequence"], int)
        and not isinstance(evidence["domain_event_sequence"], bool)
        and retention is not None
        and isinstance(retention["expired_through_sequence"], int)
        and not isinstance(retention["expired_through_sequence"], bool)
        and retention["expired_through_sequence"] >= evidence["domain_event_sequence"]
    )
    if expired_canonical_event:
        return
    if len(events) != 1:
        _block("ambiguous scheduler initialization paper.updated event", deployment)
    event = events[0]
    if (
        event["event_type"] != "paper.updated"
        or event["object_type"] != "paper"
        or event["object_id"] != deployment["paper_id"]
    ):
        _block("ambiguous scheduler initialization paper.updated event", deployment)
    payload = _mapping_value(event["payload"])
    event_instant = _utc_timestamp(bind, event["occurred_at"], "event occurred_at")
    closed = (
        isinstance(payload, Mapping)
        and set(payload) == {"status"}
        and payload["status"] == evidence["to_state"]
        and event.get("actor_id") == evidence["actor"]["id"]
        and event.get("object_version") is None
        and isinstance(event.get("object_revision"), int)
        and not isinstance(event.get("object_revision"), bool)
        and event.get("object_revision") >= 1
        and event.get("revision") == event.get("object_revision")
        and event.get("schema_version") == 1
        and event.get("sequence") == evidence["domain_event_sequence"]
        and event_instant == initialization
        and _utc_timestamp(bind, event["expires_at"], "event expires_at")
        == initialization + timedelta(days=7)
    )
    if not closed:
        _block("ambiguous scheduler initialization paper.updated event", deployment)


def _validate_support_rows(
    bind: Connection,
    audit_events: Table,
    domain_events: Table,
    audit_chain_heads: Table,
    event_stream_watermarks: Table,
    workspace_id: Any,
) -> None:
    audit = (
        bind.execute(
            select(audit_events.c.event_hash, audit_events.c.sequence)
            .where(audit_events.c.workspace_id == workspace_id)
            .order_by(audit_events.c.sequence.desc())
            .limit(1)
        )
        .mappings()
        .one_or_none()
    )
    event = (
        bind.execute(
            select(domain_events.c.sequence)
            .where(domain_events.c.workspace_id == workspace_id)
            .order_by(domain_events.c.sequence.desc())
            .limit(1)
        )
        .mappings()
        .one_or_none()
    )
    head = (
        bind.execute(
            select(audit_chain_heads)
            .where(audit_chain_heads.c.workspace_id == workspace_id)
            .with_for_update()
        )
        .mappings()
        .one_or_none()
    )
    watermark = (
        bind.execute(
            select(event_stream_watermarks)
            .where(event_stream_watermarks.c.workspace_id == workspace_id)
            .with_for_update()
        )
        .mappings()
        .one_or_none()
    )
    if audit is None:
        head_valid = head is None
    else:
        head_valid = (
            head is not None
            and head["event_sha256"] == audit["event_hash"]
            and isinstance(head["revision"], int)
            and not isinstance(head["revision"], bool)
            and head["revision"] >= 1
        )
    if event is None:
        watermark_valid = watermark is None or (
            isinstance(watermark["last_sequence"], int)
            and not isinstance(watermark["last_sequence"], bool)
            and isinstance(watermark["expired_through_sequence"], int)
            and not isinstance(watermark["expired_through_sequence"], bool)
            and watermark["last_sequence"] == watermark["expired_through_sequence"]
        )
    else:
        watermark_valid = (
            watermark is not None
            and watermark["last_sequence"] == event["sequence"]
            and isinstance(watermark["expired_through_sequence"], int)
            and watermark["expired_through_sequence"] <= watermark["last_sequence"]
        )
    if not head_valid or not watermark_valid:
        _block(
            "ambiguous scheduler initialization support state",
            {"workspace_id": workspace_id},
        )


def _validate_baselines(bind: Connection) -> None:
    deployments, states, audit_events, domain_events, heads, watermarks = _tables(bind)
    rows = [
        dict(row)
        for row in bind.execute(select(deployments).with_for_update()).mappings().all()
    ]
    _validate_deployment_authority(rows)
    deployment_pairs = {(row["workspace_id"], row["id"]) for row in rows}
    state_rows = bind.execute(select(states).with_for_update()).mappings().all()
    grouped: dict[tuple[Any, Any], list[Mapping[str, Any]]] = {}
    for row in state_rows:
        grouped.setdefault((row["workspace_id"], row["paper_id"]), []).append(dict(row))
    if set(grouped) - deployment_pairs:
        orphan = next(
            row
            for pair, rows_for_pair in grouped.items()
            if pair not in deployment_pairs
            for row in rows_for_pair
        )
        _block("ambiguous scheduler initialization: orphan state", orphan)

    missing = [pair for pair in deployment_pairs if not grouped.get(pair)]
    ambiguous = [pair for pair in deployment_pairs if len(grouped.get(pair, [])) > 1]
    if missing or ambiguous:
        affected = next(
            row
            for row in rows
            if (row["workspace_id"], row["id"]) in (missing or ambiguous)
        )
        _block(
            "missing or ambiguous scheduler state initialization; readiness blocked",
            affected,
        )

    for deployment in rows:
        target = _legacy_target(deployment)
        existing = grouped.get((deployment["workspace_id"], deployment["id"]), [])
        baseline = existing[0]
        revision = baseline["revision"]
        valid = (
            baseline["scheduler_status"] == target
            and isinstance(revision, int)
            and not isinstance(revision, bool)
            and revision >= 1
            and baseline["resume_watermark_utc"] is not None
            and ((target == "ACTIVE") == (baseline["suppressed_since_utc"] is None))
        )
        if not valid:
            _block(
                "ambiguous scheduler state initialization; readiness blocked", baseline
            )
        _validate_evidence(
            bind,
            audit_events,
            domain_events,
            watermarks,
            dict(deployment),
            baseline,
        )
    for workspace_id in {row["workspace_id"] for row in rows}:
        _validate_support_rows(
            bind, audit_events, domain_events, heads, watermarks, workspace_id
        )


def _next_sequence(
    table: Table,
    bind: Connection,
    workspace_id: Any,
    watermarks: Table | None = None,
) -> int:
    values = bind.execute(
        select(table.c.sequence).where(table.c.workspace_id == workspace_id)
    ).scalars()
    current = max((int(value) for value in values), default=0)
    if watermarks is not None:
        watermark = bind.execute(
            select(watermarks.c.last_sequence).where(
                watermarks.c.workspace_id == workspace_id
            )
        ).scalar_one_or_none()
        current = max(current, int(watermark or 0))
    return current + 1


def _previous_audit_hash(
    audit_events: Table, bind: Connection, workspace_id: Any
) -> str | None:
    row = (
        bind.execute(
            select(audit_events.c.event_hash)
            .where(audit_events.c.workspace_id == workspace_id)
            .order_by(audit_events.c.sequence.desc())
            .limit(1)
        )
        .mappings()
        .one_or_none()
    )
    return None if row is None else str(row["event_hash"])


def _hash(value: Mapping[str, Any]) -> str:
    encoded = json.dumps(value, default=str, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def _insert_baseline(
    bind: Connection,
    states: Table,
    audit_events: Table,
    domain_events: Table,
    audit_chain_heads: Table,
    event_stream_watermarks: Table,
    deployment: Mapping[str, Any],
    target: str,
    instant: datetime,
) -> None:
    workspace_id = deployment["workspace_id"]
    paper_id = deployment["paper_id"]
    deployment_id = deployment["id"]
    revision = int(deployment["revision"])
    suppressed = instant if target != "ACTIVE" else None
    if bind.dialect.name == "postgresql":
        bind.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:workspace_id))"),
            {"workspace_id": str(workspace_id)},
        )
    watermark = (
        bind.execute(
            select(event_stream_watermarks)
            .where(event_stream_watermarks.c.workspace_id == workspace_id)
            .with_for_update()
        )
        .mappings()
        .one_or_none()
    )
    if watermark is None:
        bind.execute(
            event_stream_watermarks.insert().values(
                workspace_id=workspace_id,
                last_sequence=0,
                expired_through_sequence=0,
            )
        )
    state = {
        "id": _uuid_column_value(states, "id", uuid.uuid4()),
        "workspace_id": workspace_id,
        "paper_id": deployment_id,
        "scheduler_status": target,
        "suppressed_since_utc": suppressed,
        "resume_watermark_utc": instant,
        "revision": revision,
        "created_at": instant,
        "updated_at": instant,
    }
    state_values = {key: value for key, value in state.items() if key in states.c}
    bind.execute(states.insert().values(**state_values))

    domain_event_sequence = _next_sequence(
        domain_events, bind, workspace_id, event_stream_watermarks
    )
    state_transition_id = f"EVT-{uuid.uuid4()}"
    evidence = {
        "state_transition_id": state_transition_id,
        "workspace_id": str(workspace_id),
        "paper_id": paper_id,
        "from_state": None,
        "to_state": target,
        "effective_at_utc": instant.isoformat(),
        "suppressed_since_utc": suppressed.isoformat() if suppressed else None,
        "resume_watermark_utc": instant.isoformat(),
        "initialization_utc": instant.isoformat(),
        "domain_event_sequence": domain_event_sequence,
        "revision": revision,
        "reason_code": "SCHEDULER_STATE_INITIALIZED_NO_HISTORY",
        "actor": {"type": "SYSTEM", "id": "alembic:0017"},
        "system": {"service": "alembic", "instance_id": "0017"},
        "commit_build_locator": {
            "commit_sha": "migration-0017",
            "build_id": "alembic-0017",
        },
    }
    summary = {_EVIDENCE_KEY: evidence}
    audit_id = uuid.uuid4()
    audit = {
        "id": _uuid_column_value(audit_events, "id", audit_id),
        "event_id": f"AUD-{uuid.uuid4()}",
        "actor_type": "SYSTEM",
        "actor_id": "alembic:0017",
        "workspace_id": workspace_id,
        "sequence": _next_sequence(audit_events, bind, workspace_id),
        "action_type": "SCHEDULER_STATE_INITIALIZED_NO_HISTORY",
        "object_type": "paper",
        "object_id": paper_id,
        "object_version": None,
        "object_revision": revision,
        "result": "SUCCESS",
        "summary": _json_column_value(audit_events, "summary", summary),
        "detail_artifact_id": None,
        "prev_event_hash": _previous_audit_hash(audit_events, bind, workspace_id),
        "occurred_at": instant,
        "input_hash": _hash(
            {"paper_id": paper_id, "status": str(deployment["status"])}
        ),
        "before_hash": None,
        "after_hash": _hash(evidence),
    }
    audit["event_hash"] = _hash(_canonical_audit_hash_payload(audit_events, audit))
    bind.execute(audit_events.insert().values(**audit))

    event = {
        "sequence": domain_event_sequence,
        "event_id": state_transition_id,
        "workspace_id": workspace_id,
        "actor_id": "alembic:0017",
        "event_type": "paper.updated",
        "object_type": "paper",
        "object_id": paper_id,
        "object_version": None,
        "object_revision": revision,
        "revision": revision,
        "payload": _json_column_value(
            domain_events, "payload", {"status": target}
        ),
        "request_id": None,
        "correlation_id": None,
        "causation_id": None,
        "job_id": None,
        "agent_run_id": None,
        "tool_call_id": None,
        "occurred_at": instant,
        "expires_at": instant + timedelta(days=7),
        "schema_version": 1,
    }
    bind.execute(
        domain_events.insert().values(
            **{key: value for key, value in event.items() if key in domain_events.c}
        )
    )
    head = (
        bind.execute(
            select(audit_chain_heads)
            .where(audit_chain_heads.c.workspace_id == workspace_id)
            .with_for_update()
        )
        .mappings()
        .one_or_none()
    )
    if head is None:
        bind.execute(
            audit_chain_heads.insert().values(
                workspace_id=workspace_id, event_sha256=audit["event_hash"], revision=1
            )
        )
    else:
        bind.execute(
            audit_chain_heads.update()
            .where(audit_chain_heads.c.workspace_id == workspace_id)
            .values(event_sha256=audit["event_hash"], revision=head["revision"] + 1)
        )
    watermark = (
        bind.execute(
            select(event_stream_watermarks)
            .where(event_stream_watermarks.c.workspace_id == workspace_id)
            .with_for_update()
        )
        .mappings()
        .one_or_none()
    )
    event_sequence = event["sequence"]
    bind.execute(
        event_stream_watermarks.update()
        .where(event_stream_watermarks.c.workspace_id == workspace_id)
        .values(last_sequence=event_sequence)
    )


def _initialize_missing_baselines(bind: Connection) -> None:
    deployments, states, audit_events, domain_events, heads, watermarks = _tables(bind)
    rows = [
        dict(row)
        for row in bind.execute(select(deployments).with_for_update()).mappings().all()
    ]
    _validate_deployment_authority(rows)
    existing = bind.execute(select(states).with_for_update()).mappings().all()
    grouped: dict[tuple[Any, Any], list[Mapping[str, Any]]] = {}
    for row in existing:
        grouped.setdefault((row["workspace_id"], row["paper_id"]), []).append(dict(row))
    deployment_pairs = {(row["workspace_id"], row["id"]) for row in rows}
    if set(grouped) - deployment_pairs or any(
        len(grouped.get(pair, [])) > 1 for pair in deployment_pairs
    ):
        ambiguous_state = next(
            row
            for pair, rows_for_pair in grouped.items()
            if pair not in deployment_pairs or len(rows_for_pair) > 1
            for row in rows_for_pair
        )
        _block(
            "missing or ambiguous scheduler state initialization; readiness blocked",
            ambiguous_state,
        )
    targets: list[tuple[dict[str, Any], str]] = []
    for deployment in rows:
        target = _legacy_target(deployment)
        if not grouped.get((deployment["workspace_id"], deployment["id"])):
            targets.append((dict(deployment), target))
    instant = datetime.now(UTC)
    for deployment_mapping, target in targets:
        _validate_support_rows(
            bind,
            audit_events,
            domain_events,
            heads,
            watermarks,
            deployment_mapping["workspace_id"],
        )
        if deployment_mapping["status"] == "STOPPED":
            bind.execute(
                deployments.update()
                .where(deployments.c.id == deployment_mapping["id"])
                .where(deployments.c.workspace_id == deployment_mapping["workspace_id"])
                .values(status="DISABLED")
            )
            deployment_mapping["status"] = "DISABLED"
        _insert_baseline(
            bind,
            states,
            audit_events,
            domain_events,
            heads,
            watermarks,
            deployment_mapping,
            target,
            instant,
        )


def _run_upgrade(bind: Connection) -> None:
    transaction = bind.begin_nested() if bind.in_transaction() else bind.begin()
    try:
        _initialize_missing_baselines(bind)
        _validate_baselines(bind)
        transaction.commit()
    except SchedulerInitializationError as error:
        if transaction.is_active:
            transaction.rollback()
        if bind.dialect.name == "sqlite" and bind.in_transaction():
            bind.rollback()
        _persist_quarantine(bind, error)
        raise
    except Exception:
        if transaction.is_active:
            transaction.rollback()
        raise


def upgrade() -> None:
    """Block readiness unless every deployment has one proven baseline."""
    bind = op.get_bind()
    _run_upgrade(bind)


def downgrade() -> None:
    """0017 changes data only; 0016 owns the table schema."""
