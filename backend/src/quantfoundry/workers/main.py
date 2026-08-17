"""Durable core/agent workers with leases, fencing and atomic effects."""

from __future__ import annotations

import logging
import os
import socket
import threading
import time
from datetime import UTC, datetime

from sqlalchemy import func, select, text, update

from quantfoundry.agents.runtime.runtime import (
    ToolExecutionFailure,
    advance_agent_run,
    cancel_agent_run,
    fail_agent_run,
    persist_tool_failure,
)
from quantfoundry.api import app as domain_main
from quantfoundry.api.app import Event, EventStreamWatermark, JobRow, SessionLocal
from quantfoundry.application.jobs.effects import apply_job_effect, apply_job_failure
from quantfoundry.infrastructure.artifacts.store import probe_artifact_store
from quantfoundry.infrastructure.jobs.queue import (
    LEASE_SECONDS,
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
        workspaces = session.execute(
            select(Event.workspace_id).where(Event.expires_at < threshold).distinct()
        ).all()
        count = 0
        for (workspace_id,) in workspaces:
            key = workspace_id or "system"
            if session.get_bind().dialect.name == "postgresql":
                session.execute(
                    text("SELECT pg_advisory_xact_lock(hashtext(:workspace_id))"),
                    {"workspace_id": key},
                )
            else:
                session.execute(
                    update(EventStreamWatermark)
                    .where(EventStreamWatermark.workspace_id == key)
                    .values(last_sequence=EventStreamWatermark.last_sequence)
                )
            maximum_sequence = session.scalar(
                select(func.max(Event.sequence)).where(
                    Event.workspace_id == key,
                    Event.expires_at < threshold,
                )
            )
            if maximum_sequence is None:
                continue
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
            count += (
                session.query(Event)
                .filter(
                    Event.workspace_id == key,
                    Event.expires_at < threshold,
                )
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
    base = configured or f"{socket.gethostname()}:{os.getpid()}"
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
        job = lock_active_lease(session, lease)
        session.info.update(
            {
                "actor_id": job.created_by_id,
                "workspace_id": job.workspace_id,
                "request_id": job.request_id or job.correlation_id,
            }
        )
        if job.cancel_requested_at is None and lease.queue_name == "agent":
            if isinstance(error, ToolExecutionFailure):
                persist_tool_failure(session, job, error)
            fail_agent_run(session, job, error)
        if job.cancel_requested_at is None:
            apply_job_failure(session, job)
        fail_job(session, lease, "JOB_FAILED", str(error))
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _lease_heartbeat_loop(
    lease: JobLease, stop: threading.Event, failures: list[Exception]
) -> None:
    while not stop.wait(max(1.0, LEASE_SECONDS / 3)):
        heartbeat_session = SessionLocal()
        try:
            heartbeat_job(heartbeat_session, lease)
            heartbeat_session.commit()
        except Exception as error:  # noqa: BLE001 - propagate at the fencing boundary
            heartbeat_session.rollback()
            failures.append(error)
            return
        finally:
            heartbeat_session.close()


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
    heartbeat_stop = threading.Event()
    heartbeat_failures: list[Exception] = []
    heartbeat_thread: threading.Thread | None = None
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
            from quantfoundry.application.jobs.effects import apply_job_cancellation

            if agent_queue:
                cancel_agent_run(session, job)
            apply_job_cancellation(session, job)
            result_ref = None
        else:
            # Release the claim-row lock before model/tool or core effect work;
            # the independent heartbeat transaction then remains writable.
            session.commit()
            job = session.get(JobRow, lease.job_id)
            if job is None:
                raise RuntimeError("claimed job disappeared after lease handoff")
            if job.cancel_requested_at:
                from quantfoundry.application.jobs.effects import apply_job_cancellation

                if agent_queue:
                    cancel_agent_run(session, job)
                apply_job_cancellation(session, job)
                result_ref = None
            else:
                heartbeat_job(session, lease)
                session.commit()
                heartbeat_thread = threading.Thread(
                    target=_lease_heartbeat_loop,
                    args=(lease, heartbeat_stop, heartbeat_failures),
                    daemon=True,
                )
                heartbeat_thread.start()
                if agent_queue:
                    while True:
                        step = advance_agent_run(session, job)
                        if step.terminal:
                            result_ref = step.result_ref
                            break
                        # Fence the checkpoint transaction before the next
                        # external/model step.
                        heartbeat_job(session, lease)
                        session.commit()
                        if crash_after_checkpoint:
                            raise SimulatedWorkerCrash(
                                "crash after durable Agent checkpoint"
                            )
                        session.expire_all()
                        job = session.get(JobRow, lease.job_id)
                        if job is None:
                            raise RuntimeError("agent job disappeared after checkpoint")
                        if job.cancel_requested_at:
                            from quantfoundry.application.jobs.effects import (
                                apply_job_cancellation,
                            )

                            cancel_agent_run(session, job)
                            apply_job_cancellation(session, job)
                            result_ref = None
                            break
                else:
                    result_ref = apply_job_effect(session, job)
                if heartbeat_failures:
                    raise LostLease("lease heartbeat failed during long-running work")
        if crash_after_effects:
            raise SimulatedWorkerCrash("crash before atomic job/effect commit")
        fenced_job = lock_active_lease(session, lease)
        if fenced_job.cancel_requested_at:
            from quantfoundry.application.jobs.effects import apply_job_cancellation

            session.rollback()
            cancellation_session = SessionLocal()
            try:
                cancellation_job = lock_active_lease(cancellation_session, lease)
                cancellation_session.info.update(
                    {
                        "actor_id": cancellation_job.created_by_id,
                        "workspace_id": cancellation_job.workspace_id,
                        "request_id": cancellation_job.request_id
                        or cancellation_job.correlation_id,
                    }
                )
                if agent_queue:
                    cancel_agent_run(cancellation_session, cancellation_job)
                apply_job_cancellation(cancellation_session, cancellation_job)
                complete_job(cancellation_session, lease, None)
                cancellation_session.commit()
            finally:
                cancellation_session.close()
            return 1
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
        heartbeat_stop.set()
        if heartbeat_thread is not None:
            heartbeat_thread.join(timeout=max(1.0, LEASE_SECONDS / 2))
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
