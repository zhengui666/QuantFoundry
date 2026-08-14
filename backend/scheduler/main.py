"""Scheduler heartbeat, safe lease reaping and event retention."""

from __future__ import annotations

import os
import socket
import time
from datetime import UTC, datetime

from app import main as domain_main
from app.artifacts import probe_artifact_store, reap_orphan_artifacts
from app.control_plane import restore_active_domain_database
from app.main import ArtifactRow, SessionLocal
from app.queue import reap_expired_jobs, record_heartbeat
from scheduler.paper import PaperScheduler
from workers.main import cleanup_expired_events


def scheduler_id() -> str:
    return (
        os.getenv("QF_SCHEDULER_ID")
        or f"{socket.gethostname()}:{os.getpid()}:scheduler"
    )


def run_once() -> int:
    if not domain_main.app.state.domain_database_available:
        try:
            restore_active_domain_database()
        except Exception:  # noqa: BLE001 - recovery loop must remain alive
            return 0
        if not domain_main.app.state.domain_database_available:
            return 0
    probe_artifact_store()
    session = SessionLocal()
    try:
        record_heartbeat(session, "scheduler", scheduler_id(), None)
        PaperScheduler().discover(session, now=datetime.now(UTC), owner=scheduler_id())
        retried, failed = reap_expired_jobs(session, queue_name="core")
        reap_orphan_artifacts(session, ArtifactRow)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    cleanup_expired_events()
    return retried + failed


def run_forever(poll_seconds: float = 15.0) -> None:
    while True:
        try:
            run_once()
        except Exception:  # noqa: BLE001 - one failed cycle must not kill scheduler
            pass
        time.sleep(poll_seconds)


if __name__ == "__main__":
    run_forever()
