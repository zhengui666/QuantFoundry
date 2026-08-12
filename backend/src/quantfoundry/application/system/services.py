"""Read-only dependency health probes."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session


def _alembic_head() -> str:
    backend_root = Path(__file__).resolve().parents[4]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    return ScriptDirectory.from_config(config).get_current_head() or ""


def _database_state(session: Session, required_tables: set[str]) -> str:
    try:
        session.execute(select(1))
        inspector = inspect(session.get_bind())
        tables = set(inspector.get_table_names())
        if not required_tables.issubset(tables):
            return "UNAVAILABLE"
        if "alembic_version" not in tables:
            return (
                "HEALTHY"
                if os.getenv("QF_ALLOW_TEST_SCHEMA_BOOTSTRAP") == "1"
                else "DEGRADED"
            )
        current = session.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
        return "HEALTHY" if current == _alembic_head() else "DEGRADED"
    except SQLAlchemyError, OSError, ValueError:
        return "UNAVAILABLE"


def _runtime_state(session: Session, heartbeat_model: Any) -> str:
    try:
        threshold = datetime.now(UTC) - timedelta(seconds=120)
        rows = (
            session.execute(
                select(heartbeat_model).where(heartbeat_model.occurred_at >= threshold)
            )
            .scalars()
            .all()
        )
        components = {row.component for row in rows}
        queues = {row.queue_name for row in rows if row.component == "worker"}
        if {"core", "agent"}.issubset(queues) and "scheduler" in components:
            return "HEALTHY"
        return "DEGRADED"
    except SQLAlchemyError:
        return "UNAVAILABLE"


def _artifact_state() -> str:
    root_value = os.getenv("QF_ARTIFACT_DIR")
    if not root_value:
        return "UNAVAILABLE"
    root = Path(root_value)
    try:
        if not root.is_dir():
            return "UNAVAILABLE"
        if not os.access(root, os.R_OK | os.W_OK | os.X_OK):
            return "UNAVAILABLE"
        probe = root / ".qf-health-probe.json"
        if not probe.is_file():
            return "DEGRADED"
        payload = json.loads(probe.read_text(encoding="utf-8"))
        signed = {key: payload[key] for key in ("sentinel", "occurred_at")}
        expected_sha256 = hashlib.sha256(
            json.dumps(
                signed, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest()
        occurred_at = datetime.fromisoformat(
            str(payload["occurred_at"]).replace("Z", "+00:00")
        )
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=UTC)
        if (
            payload.get("sentinel") != "quantfoundry-artifact-store"
            or payload.get("content_sha256") != expected_sha256
        ):
            return "UNAVAILABLE"
        return (
            "HEALTHY"
            if occurred_at >= datetime.now(UTC) - timedelta(seconds=120)
            else "DEGRADED"
        )
    except OSError, ValueError, KeyError, TypeError, json.JSONDecodeError:
        return "UNAVAILABLE"


def probe_health(
    session: Session,
    job_model: Any,
    event_model: Any,
    heartbeat_model: Any,
) -> dict[str, str]:
    required_tables = {
        "jobs",
        "domain_events",
        "audit_events",
        "runtime_heartbeats",
        "holdout_exposures",
        "snapshot_partitions",
    }
    database = _database_state(session, required_tables)
    states = {
        "database": database,
        "job_queue": "UNAVAILABLE",
        "event_stream": "UNAVAILABLE",
        "artifact_store": _artifact_state(),
    }
    if database != "UNAVAILABLE":
        try:
            session.execute(select(job_model.id).limit(1))
            states["job_queue"] = _runtime_state(session, heartbeat_model)
            session.execute(select(event_model.sequence).limit(1))
            states["event_stream"] = "HEALTHY"
        except SQLAlchemyError:
            pass
    return states
