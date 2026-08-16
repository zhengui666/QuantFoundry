"""Read-only dependency health probes."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.util.exc import CommandError
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
    except (CommandError, SQLAlchemyError, OSError, ValueError):
        return "UNAVAILABLE"


def _runtime_state(session: Session, heartbeat_model: Any) -> str:
    try:
        now = datetime.now(UTC)
        threshold = now - timedelta(seconds=120)
        ceiling = now + timedelta(seconds=30)
        rows = (
            session.execute(
                select(heartbeat_model).where(
                    heartbeat_model.occurred_at >= threshold,
                    heartbeat_model.occurred_at <= ceiling,
                )
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
        if not os.access(root, os.R_OK | os.X_OK):
            return "UNAVAILABLE"
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=root, prefix=".qf-health-write-", delete=True
        ) as handle:
            handle.write(b"quantfoundry-artifact-health\n")
            handle.flush()
            os.fsync(handle.fileno())
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
        now = datetime.now(UTC)
        return (
            "HEALTHY"
            if now - timedelta(seconds=120) <= occurred_at <= now + timedelta(seconds=30)
            else "DEGRADED"
        )
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
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
    probe_session = Session(bind=session.get_bind())
    try:
        database = _database_state(probe_session, required_tables)
        states = {
            "database": database,
            "job_queue": "UNAVAILABLE",
            "event_stream": "UNAVAILABLE",
            "artifact_store": _artifact_state(),
        }
        if database == "UNAVAILABLE":
            return states
        try:
            probe_session.execute(select(job_model.id).limit(1))
            states["job_queue"] = _runtime_state(probe_session, heartbeat_model)
        except SQLAlchemyError:
            states["job_queue"] = "UNAVAILABLE"
        try:
            probe_session.execute(select(event_model.sequence).limit(1))
            states["event_stream"] = "HEALTHY"
        except SQLAlchemyError:
            states["event_stream"] = "UNAVAILABLE"
        return states
    finally:
        probe_session.close()
