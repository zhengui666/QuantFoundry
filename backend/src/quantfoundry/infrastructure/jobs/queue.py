"""PostgreSQL-safe durable job leasing and fencing primitives."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

from sqlalchemy import and_, exists, or_, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session, aliased

from quantfoundry.api.app import JobDependencyRow, JobRow, RuntimeHeartbeat, emit
from quantfoundry.contracts.events.locator import job_result_ref_valid

LEASE_SECONDS = 60


class LostLease(RuntimeError):
    """The worker no longer owns the job fencing token."""


class JobNotCancellable(RuntimeError):
    pass


@dataclass(frozen=True)
class JobLease:
    job_id: str
    worker_id: str
    fencing_token: int
    queue_name: str


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _update_wire_payload(row: JobRow, now: datetime) -> None:
    detail = json.loads(row.payload)
    percent = None
    if row.total_units and row.completed_units is not None:
        percent = min(100, int(row.completed_units * 100 / row.total_units))
    detail.update(
        {
            "status": row.status,
            "error_code": row.error_code,
            "result_ref": json.loads(row.result_ref) if row.result_ref else None,
            "revision": row.revision,
            "queued_at": _iso(row.queued_at),
            "started_at": _iso(row.started_at),
            "finished_at": _iso(row.finished_at),
            "last_updated_at": _iso(now),
            "progress": {
                "mode": row.progress_mode,
                "completed_units": row.completed_units,
                "total_units": row.total_units,
                "unit": row.progress_unit,
                "percent": percent,
                "current_step_key": row.current_step_key,
                "current_step_label": row.current_step_label,
            },
        }
    )
    row.payload = json.dumps(detail)


def record_heartbeat(
    session: Session,
    component: str,
    instance_id: str,
    queue_name: str | None,
    now: datetime | None = None,
) -> None:
    timestamp = now or datetime.now(UTC)
    key = {"component": component, "instance_id": instance_id}
    row = session.get(RuntimeHeartbeat, key)
    if row is None:
        session.add(
            RuntimeHeartbeat(
                component=component,
                instance_id=instance_id,
                queue_name=queue_name,
                occurred_at=timestamp,
            )
        )
    else:
        row.queue_name = queue_name
        row.occurred_at = timestamp


def claim_job(
    session: Session,
    queue_name: str,
    worker_id: str,
    *,
    now: datetime | None = None,
    lease_seconds: int = LEASE_SECONDS,
) -> JobLease | None:
    timestamp = now or datetime.now(UTC)
    dependency = aliased(JobDependencyRow)
    prerequisite = aliased(JobRow)
    unsatisfied_dependency = (
        select(dependency.job_id)
        .join(
            prerequisite,
            and_(
                prerequisite.id == dependency.depends_on_job_id,
                prerequisite.workspace_id == dependency.workspace_id,
            ),
        )
        .where(
            dependency.job_id == JobRow.id,
            dependency.workspace_id == JobRow.workspace_id,
            or_(
                dependency.dependency_type == "SUCCESS",
                dependency.dependency_type == "TERMINAL",
            ),
            or_(
                (
                    (dependency.dependency_type == "SUCCESS")
                    & (prerequisite.status != "COMPLETED")
                ),
                (
                    (dependency.dependency_type == "TERMINAL")
                    & prerequisite.status.not_in({"COMPLETED", "FAILED", "CANCELLED"})
                ),
            ),
        )
    )
    statement = (
        select(JobRow)
        .where(
            JobRow.status == "QUEUED",
            JobRow.queue_name == queue_name,
            JobRow.queued_at <= timestamp,
            ~exists(unsatisfied_dependency),
        )
        .order_by(JobRow.priority.asc(), JobRow.queued_at.asc(), JobRow.id.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    row = session.execute(statement).scalar_one_or_none()
    record_heartbeat(session, "worker", worker_id, queue_name, timestamp)
    if row is None:
        return None
    row.status = "RUNNING"
    row.lease_owner = worker_id
    row.lease_expires_at = timestamp + timedelta(seconds=lease_seconds)
    row.heartbeat_at = timestamp
    row.attempt += 1
    row.fencing_token += 1
    row.started_at = row.started_at or timestamp
    row.revision += 1
    _update_wire_payload(row, timestamp)
    emit(
        session,
        "job",
        row.id,
        row.revision,
        "job.updated",
        payload={
            "state": "RUNNING",
            "status": "RUNNING",
            "progress_mode": row.progress_mode,
            "completed_units": row.completed_units,
            "total_units": row.total_units,
            "current_step_key": row.current_step_key,
        },
        job_id=row.id,
        correlation_id=row.correlation_id,
        request_id=row.request_id,
        actor_id=row.created_by_id,
        workspace_id=row.workspace_id,
    )
    session.flush()
    return JobLease(row.id, worker_id, row.fencing_token, queue_name)


def _owned_job(session: Session, lease: JobLease) -> JobRow:
    row = session.execute(
        select(JobRow).where(JobRow.id == lease.job_id).with_for_update()
    ).scalar_one_or_none()
    if (
        row is None
        or row.status != "RUNNING"
        or row.lease_owner != lease.worker_id
        or row.fencing_token != lease.fencing_token
    ):
        raise LostLease(f"lost lease for {lease.job_id}")
    return row


def lock_active_lease(
    session: Session, lease: JobLease, *, now: datetime | None = None
) -> JobRow:
    """Lock the fenced job before any domain effect is allowed to execute."""

    timestamp = now or datetime.now(UTC)
    row = session.execute(
        select(JobRow)
        .where(
            JobRow.id == lease.job_id,
            JobRow.status == "RUNNING",
            JobRow.lease_owner == lease.worker_id,
            JobRow.fencing_token == lease.fencing_token,
            JobRow.lease_expires_at > timestamp,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if row is None:
        raise LostLease(f"lost or expired lease for {lease.job_id}")
    return row


def heartbeat_job(
    session: Session,
    lease: JobLease,
    *,
    now: datetime | None = None,
    lease_seconds: int = LEASE_SECONDS,
) -> None:
    timestamp = now or datetime.now(UTC)
    result = cast(
        CursorResult[Any],
        session.execute(
            update(JobRow)
            .where(
                JobRow.id == lease.job_id,
                JobRow.status == "RUNNING",
                JobRow.lease_owner == lease.worker_id,
                JobRow.fencing_token == lease.fencing_token,
                JobRow.lease_expires_at > timestamp,
            )
            .values(
                heartbeat_at=timestamp,
                lease_expires_at=timestamp + timedelta(seconds=lease_seconds),
            )
            .execution_options(synchronize_session=False)
        ),
    )
    if result.rowcount != 1:
        raise LostLease(f"lost or expired lease for {lease.job_id}")
    record_heartbeat(session, "worker", lease.worker_id, lease.queue_name, timestamp)


def update_progress(
    session: Session,
    lease: JobLease,
    *,
    completed_units: int | None = None,
    total_units: int | None = None,
    unit: str | None = None,
    step_key: str | None = None,
    step_label: str | None = None,
    now: datetime | None = None,
) -> None:
    timestamp = now or datetime.now(UTC)
    row = lock_active_lease(session, lease, now=timestamp)
    if total_units is not None and total_units < 0:
        raise ValueError("total_units must be non-negative")
    if completed_units is not None and completed_units < 0:
        raise ValueError("completed_units must be non-negative")
    if (
        completed_units is not None
        and total_units is not None
        and completed_units > total_units
    ):
        raise ValueError("completed_units cannot exceed total_units")
    row.progress_mode = "UNITS" if total_units is not None else "NONE"
    row.completed_units = completed_units
    row.total_units = total_units
    row.progress_unit = unit
    row.current_step_key = step_key
    row.current_step_label = step_label
    row.revision += 1
    _update_wire_payload(row, timestamp)


def request_cancellation(
    session: Session, job_id: str, *, now: datetime | None = None
) -> JobRow:
    timestamp = now or datetime.now(UTC)
    row = session.execute(
        select(JobRow).where(JobRow.id == job_id).with_for_update()
    ).scalar_one_or_none()
    if row is None:
        raise KeyError(job_id)
    if row.status not in {"QUEUED", "RUNNING"}:
        raise JobNotCancellable(job_id)
    row.cancel_requested_at = timestamp
    if row.status == "QUEUED":
        from quantfoundry.application.jobs.effects import apply_job_cancellation

        apply_job_cancellation(session, row)
        row.status = "CANCELLED"
        row.finished_at = timestamp
    row.revision += 1
    _update_wire_payload(row, timestamp)
    emit(
        session,
        "job",
        row.id,
        row.revision,
        "job.updated",
        payload={"state": row.status, "status": row.status},
        job_id=row.id,
        correlation_id=row.correlation_id,
        request_id=row.request_id,
        actor_id=row.created_by_id,
        workspace_id=row.workspace_id,
    )
    return row


def complete_job(
    session: Session,
    lease: JobLease,
    result_ref: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> JobRow:
    timestamp = now or datetime.now(UTC)
    row = lock_active_lease(session, lease, now=timestamp)
    if result_ref is not None and not job_result_ref_valid(result_ref):
        raise ValueError("job result_ref violates the closed canonical schema")
    next_status = "CANCELLED" if row.cancel_requested_at else "COMPLETED"
    next_revision = row.revision + 1
    detail = json.loads(row.payload)
    detail.update(
        {
            "status": next_status,
            "error_code": None,
            "result_ref": result_ref,
            "revision": next_revision,
            "started_at": _iso(row.started_at),
            "finished_at": _iso(timestamp),
            "last_updated_at": _iso(timestamp),
        }
    )
    result = cast(
        CursorResult[Any],
        session.execute(
            update(JobRow)
            .where(
                JobRow.id == lease.job_id,
                JobRow.status == "RUNNING",
                JobRow.lease_owner == lease.worker_id,
                JobRow.fencing_token == lease.fencing_token,
                JobRow.revision == row.revision,
                JobRow.lease_expires_at > timestamp,
            )
            .values(
                status=next_status,
                result_ref=json.dumps(result_ref) if result_ref else None,
                error_code=None,
                error_detail=None,
                finished_at=timestamp,
                lease_owner=None,
                lease_expires_at=None,
                heartbeat_at=timestamp,
                revision=next_revision,
                payload=json.dumps(detail),
            )
            .execution_options(synchronize_session=False)
        ),
    )
    if result.rowcount != 1:
        raise LostLease(f"lost or expired lease for {lease.job_id}")
    session.expire(row)
    row = session.get(JobRow, lease.job_id)
    assert row is not None
    emit(
        session,
        "job",
        row.id,
        row.revision,
        "job.updated",
        payload={"state": row.status, "status": row.status},
        job_id=row.id,
        correlation_id=row.correlation_id,
        request_id=row.request_id,
        actor_id=row.created_by_id,
        workspace_id=row.workspace_id,
    )
    return row


def fail_job(
    session: Session,
    lease: JobLease,
    error_code: str,
    error_detail: str,
    *,
    now: datetime | None = None,
) -> JobRow:
    timestamp = now or datetime.now(UTC)
    row = lock_active_lease(session, lease, now=timestamp)
    next_revision = row.revision + 1
    next_status = "CANCELLED" if row.cancel_requested_at else "FAILED"
    detail = json.loads(row.payload)
    detail.update(
        {
            "status": next_status,
            "error_code": error_code,
            "revision": next_revision,
            "started_at": _iso(row.started_at),
            "finished_at": _iso(timestamp),
            "last_updated_at": _iso(timestamp),
        }
    )
    lease_snapshot = None
    if row.job_type == "PAPER_DAILY_RUN":
        from quantfoundry.scheduler.paper import LeaseSnapshot

        lease_snapshot = LeaseSnapshot(
            owner=row.lease_owner,
            expires_at=row.lease_expires_at,
            heartbeat_at=row.heartbeat_at,
        )
    result = cast(
        CursorResult[Any],
        session.execute(
            update(JobRow)
            .where(
                JobRow.id == lease.job_id,
                JobRow.status == "RUNNING",
                JobRow.lease_owner == lease.worker_id,
                JobRow.fencing_token == lease.fencing_token,
                JobRow.revision == row.revision,
                JobRow.lease_expires_at > timestamp,
            )
            .values(
                status=next_status,
                error_code=error_code,
                error_detail=error_detail,
                finished_at=timestamp,
                lease_owner=None,
                lease_expires_at=None,
                heartbeat_at=timestamp,
                revision=next_revision,
                payload=json.dumps(detail),
            )
            .execution_options(synchronize_session=False)
        ),
    )
    if result.rowcount != 1:
        raise LostLease(f"lost or expired lease for {lease.job_id}")
    session.expire(row)
    row = session.get(JobRow, lease.job_id)
    assert row is not None
    if row.job_type == "PAPER_DAILY_RUN":
        from quantfoundry.scheduler.paper import PaperScheduler

        PaperScheduler().fail_claimed(
            session,
            row,
            reason_code="PAPER_DAILY_RUN_UNKNOWN_RESULT",
            now=timestamp,
            lease_snapshot=lease_snapshot,
            status=next_status,
        )
    emit(
        session,
        "job",
        row.id,
        row.revision,
        "job.updated",
        payload={"state": next_status, "status": next_status},
        job_id=row.id,
        correlation_id=row.correlation_id,
        request_id=row.request_id,
        actor_id=row.created_by_id,
        workspace_id=row.workspace_id,
    )
    return row


def reap_expired_jobs(
    session: Session,
    *,
    now: datetime | None = None,
    queue_name: str | None = None,
) -> tuple[int, int]:
    timestamp = now or datetime.now(UTC)
    statement = select(JobRow).where(
        JobRow.status == "RUNNING", JobRow.lease_expires_at < timestamp
    )
    if queue_name is not None:
        statement = statement.where(JobRow.queue_name == queue_name)
    rows = session.execute(statement.with_for_update(skip_locked=True)).scalars().all()
    retried = failed = 0
    for row in rows:
        cancellation_requested = row.cancel_requested_at is not None
        safe_retry = bool(
            not cancellation_requested
            and row.retry_safe
            and row.attempt < row.max_attempts
        )
        expired_owner = row.lease_owner
        expired_at = row.lease_expires_at
        expired_heartbeat = row.heartbeat_at
        next_retry_at = (
            timestamp
            + timedelta(seconds=min(60, 2 ** max(cast(int, row.attempt) - 1, 0)))
            if safe_retry and row.job_type == "PAPER_DAILY_RUN"
            else None
        )
        if cancellation_requested and row.job_type != "PAPER_DAILY_RUN":
            from quantfoundry.application.jobs.effects import apply_job_cancellation

            if row.queue_name == "agent":
                from quantfoundry.agents.runtime.runtime import cancel_agent_run

                cancel_agent_run(session, row)
            apply_job_cancellation(session, row)
        elif not safe_retry and row.job_type != "PAPER_DAILY_RUN":
            from quantfoundry.agents.runtime.runtime import fail_agent_run
            from quantfoundry.application.jobs.effects import apply_job_failure

            if row.queue_name == "agent":
                fail_agent_run(session, row, LostLease("worker lease expired"))
            apply_job_failure(session, row)
        row.status = (
            "CANCELLED"
            if cancellation_requested
            else "QUEUED"
            if safe_retry
            else "FAILED"
        )
        row.error_code = (
            "JOB_CANCELLED"
            if cancellation_requested
            else "JOB_LEASE_LOST"
            if row.job_type == "PAPER_DAILY_RUN" or not safe_retry
            else None
        )
        row.error_detail = (
            "lease expired after cancellation request"
            if cancellation_requested
            else "lease expired; retry scheduled"
            if safe_retry and row.job_type == "PAPER_DAILY_RUN"
            else None
            if safe_retry
            else "lease expired; automatic retry unsafe"
        )
        row.lease_owner = None
        row.lease_expires_at = None
        row.heartbeat_at = timestamp
        row.finished_at = None if safe_retry else timestamp
        if next_retry_at is not None:
            row.queued_at = next_retry_at
        row.revision += 1
        _update_wire_payload(row, timestamp)
        if row.job_type == "PAPER_DAILY_RUN":
            from quantfoundry.scheduler.paper import LeaseSnapshot, PaperScheduler

            PaperScheduler().record_expired_lease(
                session,
                row,
                now=timestamp,
                safe_retry=safe_retry,
                lease_snapshot=LeaseSnapshot(
                    owner=expired_owner,
                    expires_at=expired_at,
                    heartbeat_at=expired_heartbeat,
                    next_retry_at=next_retry_at,
                ),
            )
        emit(
            session,
            "job",
            row.id,
            row.revision,
            "job.updated",
            payload={
                "state": row.status,
                "status": row.status,
                "reason_code": None if safe_retry else "JOB_LEASE_LOST",
            },
            job_id=row.id,
            correlation_id=row.correlation_id,
            request_id=row.request_id,
            actor_id=row.created_by_id,
            workspace_id=row.workspace_id,
        )
        if safe_retry:
            retried += 1
        else:
            failed += 1
    return retried, failed
