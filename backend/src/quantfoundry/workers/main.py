"""Durable core/agent workers with leases, fencing and atomic effects."""

from __future__ import annotations

import logging
import os
import socket
import time
from datetime import UTC, datetime

from sqlalchemy import func, select

from quantfoundry.agents.runtime.runtime import (
    ToolExecutionFailure,
    advance_agent_run,
    fail_agent_run,
    persist_tool_failure,
)
from quantfoundry.api import app as domain_main
from quantfoundry.api.app import Event, EventStreamWatermark, JobRow, SessionLocal
from quantfoundry.application.jobs.effects import apply_job_effect, apply_job_failure
from quantfoundry.infrastructure.artifacts.store import probe_artifact_store
from quantfoundry.infrastructure.jobs.queue import (
    JobLease,
    LostLease,
    claim_job,
    complete_job,
    fail_job,
    heartbeat_job,
    lock_active_lease,
)


class SimulatedWorkerCrash(RuntimeError):
    """Test hook proving uncommitted effects roll back and leases recover."""


logger = logging.getLogger(__name__)


def _domain_ready() -> bool:
    if getattr(domain_main.app.state, "domain_database_available", True):
        return True
    try:
        from app.control_plane import restore_active_domain_database

        restore_active_domain_database()
    except Exception:  # noqa: BLE001 - recovery loop must stay alive
        return False
    return bool(getattr(domain_main.app.state, "domain_database_available", False))


def cleanup_expired_events(now: datetime | None = None) -> int:
    if not _domain_ready():
        return 0
    session = SessionLocal()
    try:
        threshold = now or datetime.now(UTC)
        expired = session.execute(
            select(Event.workspace_id, func.max(Event.sequence))
            .where(Event.expires_at < threshold)
            .group_by(Event.workspace_id)
        ).all()
        for workspace_id, maximum_sequence in expired:
            key = workspace_id or "system"
            state = session.execute(
                select(EventStreamWatermark)
                .where(EventStreamWatermark.workspace_id == key)
                .with_for_update()
            ).scalar_one_or_none()
            if state is None:
                session.add(
                    EventStreamWatermark(
                        workspace_id=key,
                        last_sequence=maximum_sequence,
                        expired_through_sequence=maximum_sequence,
                    )
                )
            else:
                state.last_sequence = max(state.last_sequence, maximum_sequence)
                state.expired_through_sequence = max(
                    state.expired_through_sequence, maximum_sequence
                )
        count = (
            session.query(Event)
            .filter(Event.expires_at < threshold)
            .delete(synchronize_session=False)
        )
        session.commit()
        return count
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def worker_id(queue_name: str) -> str:
    configured = os.getenv("QF_WORKER_ID")
    base = configured or socket.gethostname()
    return f"{base}:{queue_name}"


def _claim(queue_name: str, identity: str) -> JobLease | None:
    session = SessionLocal()
    try:
        lease = claim_job(session, queue_name, identity)
        session.commit()
        return lease
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _mark_failed(lease: JobLease, error: Exception) -> None:
    session = SessionLocal()
    try:
        job = session.get(JobRow, lease.job_id)
        if job is not None:
            session.info.update(
                {
                    "actor_id": job.created_by_id,
                    "workspace_id": job.workspace_id,
                    "request_id": job.request_id or job.correlation_id,
                }
            )
        if job is not None and lease.queue_name == "agent":
            if isinstance(error, ToolExecutionFailure):
                persist_tool_failure(session, job, error)
            fail_agent_run(session, job, error)
        if job is not None:
            apply_job_failure(session, job)
        fail_job(session, lease, "JOB_FAILED", str(error))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _run_once(
    agent_queue: bool,
    *,
    identity: str | None = None,
    crash_after_effects: bool = False,
    crash_after_checkpoint: bool = False,
) -> int:
    if not _domain_ready():
        return 0
    queue_name = "agent" if agent_queue else "core"
    probe_artifact_store()
    lease = _claim(queue_name, identity or worker_id(queue_name))
    if lease is None:
        return 0
    session = SessionLocal()
    try:
        job = session.get(JobRow, lease.job_id)
        if job is None:
            raise RuntimeError("claimed job disappeared")
        job = lock_active_lease(session, lease)
        session.info.update(
            {
                "actor_id": job.created_by_id,
                "workspace_id": job.workspace_id,
                "request_id": job.request_id or job.correlation_id,
            }
        )
        if job.cancel_requested_at:
            result_ref = None
        elif agent_queue:
            while True:
                step = advance_agent_run(
                    session,
                    job,
                )
                if step.terminal:
                    result_ref = step.result_ref
                    break
                # Fence the whole checkpoint/effect transaction.  If the lease
                # expired during the model/tool call, this CAS fails and every
                # domain effect in the session is rolled back.
                heartbeat_job(session, lease)
                session.commit()
                if crash_after_checkpoint:
                    raise SimulatedWorkerCrash("crash after durable Agent checkpoint")
                session.expire_all()
                job = session.get(JobRow, lease.job_id)
                if job is None:
                    raise RuntimeError("agent job disappeared after checkpoint")
                job = lock_active_lease(session, lease)
        else:
            result_ref = apply_job_effect(session, job)
        if crash_after_effects:
            raise SimulatedWorkerCrash("crash before atomic job/effect commit")
        complete_job(session, lease, result_ref)
        session.commit()
        return 1
    except SimulatedWorkerCrash:
        session.rollback()
        raise
    except LostLease:
        session.rollback()
        return 1
    except Exception as error:  # noqa: BLE001 - worker boundary records arbitrary failures
        session.rollback()
        _mark_failed(lease, error)
        return 1
    finally:
        session.close()


def run_once(*, identity: str | None = None, crash_after_effects: bool = False) -> int:
    return _run_once(
        agent_queue=False,
        identity=identity,
        crash_after_effects=crash_after_effects,
    )


def run_agent_once(
    *,
    identity: str | None = None,
    crash_after_effects: bool = False,
    crash_after_checkpoint: bool = False,
) -> int:
    return _run_once(
        agent_queue=True,
        identity=identity,
        crash_after_effects=crash_after_effects,
        crash_after_checkpoint=crash_after_checkpoint,
    )


def run_forever(agent_queue: bool = False, poll_seconds: float = 1.0) -> None:
    """Core and agent workers only claim their configured queue."""
    while True:
        try:
            _run_once(agent_queue)
        except Exception:  # noqa: BLE001 - worker boundary retries after recovery
            logger.exception(
                "worker loop recovered after an iteration failure",
                extra={"queue": "agent" if agent_queue else "core"},
            )
        time.sleep(poll_seconds)


if __name__ == "__main__":
    run_forever(agent_queue=os.getenv("QF_WORKER_KIND") == "agent")
