"""Scheduler heartbeat, safe lease reaping and event retention."""

from __future__ import annotations

import logging
import os
import socket
import time
from datetime import UTC, datetime

from quantfoundry.api import app as domain_main
from quantfoundry.api.app import ArtifactRow, SessionLocal
from quantfoundry.infrastructure.artifacts.store import (
    probe_artifact_store,
    reap_orphan_artifacts,
)
from quantfoundry.infrastructure.jobs.queue import reap_expired_jobs, record_heartbeat
from quantfoundry.scheduler.paper import PaperScheduler
from quantfoundry.workers.main import cleanup_expired_events

logger = logging.getLogger(__name__)


def scheduler_id() -> str:
    return os.getenv("QF_SCHEDULER_ID") or f"{socket.gethostname()}:{os.getpid()}"


def _domain_ready() -> bool:
    if getattr(domain_main.app.state, "domain_database_available", True):
        return True
    try:
        from app.control_plane import restore_active_domain_database

        restore_active_domain_database()
    except Exception:  # noqa: BLE001 - recovery loop must stay alive
        return False
    return bool(getattr(domain_main.app.state, "domain_database_available", False))


def run_once() -> int:
    if not _domain_ready():
        return 0
    maintenance_error: Exception | None = None
    artifact_store_ready = True
    try:
        probe_artifact_store()
    except Exception as error:
        logger.exception("scheduler artifact maintenance failed")
        maintenance_error = error
        artifact_store_ready = False
    try:
        session = SessionLocal()
    except Exception as error:
        logger.exception("scheduler domain session creation failed")
        maintenance_error = maintenance_error or error
        session = None
    if session is not None:
        try:
            record_heartbeat(session, "scheduler", scheduler_id(), None)
            PaperScheduler().discover(
                session, now=datetime.now(UTC), owner=scheduler_id()
            )
            retried, failed = reap_expired_jobs(session)
            session.commit()
        except Exception as error:
            session.rollback()
            logger.exception("scheduler domain maintenance failed")
            maintenance_error = error
            retried = failed = 0
        finally:
            session.close()
    else:
        retried = failed = 0
    if artifact_store_ready:
        artifact_session = None
        try:
            artifact_session = SessionLocal()
            reap_orphan_artifacts(artifact_session, ArtifactRow)
            artifact_session.commit()
        except Exception as error:
            if artifact_session is not None:
                artifact_session.rollback()
            logger.exception("scheduler artifact reaping failed")
            maintenance_error = maintenance_error or error
        finally:
            if artifact_session is not None:
                artifact_session.close()
    try:
        cleanup_expired_events()
    except Exception as error:
        logger.exception("scheduler event retention failed")
        maintenance_error = maintenance_error or error
    if maintenance_error is not None:
        raise maintenance_error
    return retried + failed


def run_forever(poll_seconds: float = 15.0) -> None:
    while True:
        try:
            run_once()
        except Exception:  # noqa: BLE001 - scheduler retries after recovery
            logger.exception("scheduler iteration failed; retrying")
        time.sleep(poll_seconds)


if __name__ == "__main__":
    run_forever()
