"""P0 paper daily scheduler; internal-only and deliberately HTTP-free."""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any, cast
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import and_, func, select, update
from sqlalchemy.orm import Session

from quantfoundry.api.app import (
    ArtifactRow,
    Base,
    JobRow,
    content_hash,
    emit,
    new_id,
)
from quantfoundry.infrastructure.artifacts.store import publish_staged, stage_json

TERMINAL = frozenset({"COMPLETED", "BLOCKED", "FAILED"})
ACTIVE_EXECUTION = frozenset({"QUEUED", "RUNNING"})
ACTIVE = "ACTIVE"
MAX_ATTEMPTS = 3
LEASE_SECONDS = 60
EVIDENCE_KEYS = frozenset(
    {
        "identity",
        "decision",
        "job_lease",
        "time_calendar",
        "review",
    }
)


class PaperSchedulerError(RuntimeError):
    pass


class InvalidExecutionAssumption(PaperSchedulerError):
    pass


@dataclass(frozen=True)
class Schedule:
    timezone: str
    due_time: time
    calendar: str | None


@dataclass(frozen=True)
class GateDecision:
    gate: str
    outcome: str
    reason_code: str
    detail: str
    values: Mapping[str, Any]


@dataclass(frozen=True)
class LeaseSnapshot:
    owner: str | None
    expires_at: datetime | None
    heartbeat_at: datetime | None
    next_retry_at: datetime | None = None


class TradingCalendar:
    """Deployment-bound calendar resolver. Implementations must be versioned."""

    def is_trading_day(self, calendar_id: str, day: date) -> tuple[bool, str]:
        raise NotImplementedError


class WeekdayCalendar(TradingCalendar):
    def is_trading_day(self, calendar_id: str, day: date) -> tuple[bool, str]:
        if calendar_id != "WEEKDAY_ONLY":
            raise InvalidExecutionAssumption("calendar is unavailable")
        return day.weekday() < 5, "WEEKDAY_ONLY"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("scheduler clock must be timezone-aware UTC")
    return value.astimezone(UTC)


def _parse_schedule(value: object) -> Schedule:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (TypeError, ValueError) as error:
            raise InvalidExecutionAssumption(
                "execution_assumption is not valid JSON"
            ) from error
    required = {
        "schedule_timezone",
        "daily_due_time",
        "trading_calendar",
    }
    if not isinstance(value, dict) or not required.issubset(value):
        raise InvalidExecutionAssumption("execution_assumption is incomplete")
    timezone = value["schedule_timezone"]
    due = value["daily_due_time"]
    calendar = value["trading_calendar"]
    if not isinstance(timezone, str) or not isinstance(due, str):
        raise InvalidExecutionAssumption("schedule timezone/due-time is invalid")
    if calendar is not None and not isinstance(calendar, str):
        raise InvalidExecutionAssumption("trading calendar is invalid")
    try:
        ZoneInfo(timezone)
        parsed_due = time.fromisoformat(due)
    except (ValueError, ZoneInfoNotFoundError) as error:
        raise InvalidExecutionAssumption(
            "schedule timezone/due-time is invalid"
        ) from error
    if parsed_due.tzinfo is not None:
        raise InvalidExecutionAssumption(
            "daily_due_time must not contain a timezone offset"
        )
    if parsed_due.second or parsed_due.microsecond:
        raise InvalidExecutionAssumption("daily_due_time must be minute-precise")
    return Schedule(timezone, parsed_due, calendar)


def _invalid_schedule() -> Schedule:
    return Schedule("UTC", time(0), "INVALID")


def _wall_time_to_utc(day: date, due_time: time, timezone: str) -> datetime:
    """Resolve exactly one valid local wall time; reject DST gaps/folds."""
    zone = ZoneInfo(timezone)
    local_naive = datetime.combine(day, due_time)
    candidates = []
    for fold in (0, 1):
        local = local_naive.replace(tzinfo=zone, fold=fold)
        instant = local.astimezone(UTC)
        if instant.astimezone(zone).replace(tzinfo=None) == local_naive:
            candidates.append(instant)
    unique = sorted(set(candidates))
    if len(unique) != 1:
        raise InvalidExecutionAssumption(
            "daily_due_time is nonexistent or ambiguous in schedule timezone"
        )
    return unique[0]


def _calendar_label(schedule: Schedule, version: str) -> dict[str, str] | str:
    return (
        "WEEKDAY_ONLY"
        if schedule.calendar is None
        else {"id": schedule.calendar, "version": version}
    )


class PaperScheduler:
    def __init__(self, calendar: TradingCalendar | None = None) -> None:
        self.calendar = calendar or WeekdayCalendar()

    def discover(
        self,
        session: Session,
        *,
        now: datetime,
        owner: str,
        workspace_id: Any | None = None,
    ) -> int:
        """Create-or-get at most one due run for each ACTIVE deployment."""
        timestamp = _utc(now)
        deployments = Base.metadata.tables["paper_deployments"]
        states = Base.metadata.tables["paper_scheduler_states"]
        statement = (
            select(
                deployments,
                *(column.label(f"scheduler_{column.name}") for column in states.c),
            )
            .join(
                states,
                and_(
                    states.c.workspace_id == deployments.c.workspace_id,
                    states.c.paper_id == deployments.c.id,
                ),
            )
            .where(
                deployments.c.status == ACTIVE,
                states.c.scheduler_status == ACTIVE,
                states.c.resume_watermark_utc.is_not(None),
                states.c.suppressed_since_utc.is_(None),
            )
            .with_for_update(skip_locked=True)
        )
        if workspace_id is not None:
            statement = statement.where(deployments.c.workspace_id == workspace_id)
        rows = session.execute(statement).mappings()
        created = 0
        for raw_deployment in rows:
            deployment: dict[str, Any] = dict(raw_deployment)
            state: Mapping[str, Any] = {
                key: deployment.pop(f"scheduler_{key}") for key in states.c.keys()
            }
            try:
                schedule = _parse_schedule(deployment["execution_assumption"])
                candidate, calendar_version = self._candidate(
                    session, deployment, state, schedule, timestamp
                )
            except (InvalidExecutionAssumption, PaperSchedulerError, ValueError):
                # Invalid configuration is fail-closed. No run/job/order is created.
                continue
            if candidate is not None:
                created += int(
                    self._create_or_get(
                        session,
                        deployment,
                        schedule,
                        calendar_version,
                        candidate,
                        timestamp,
                        owner,
                    )
                )
        return created

    def transition_state(
        self,
        session: Session,
        *,
        workspace_id: Any,
        paper_id: Any,
        to_state: str,
        now: datetime,
        actor_id: str,
        reason_code: str,
        initialization: bool = False,
    ) -> None:
        """Atomically mutate suppression truth and emit only the legal paper event."""
        if to_state not in {"ACTIVE", "PAUSED", "DISABLED"}:
            raise PaperSchedulerError("unknown scheduler state")
        timestamp = _utc(now)
        deployments = Base.metadata.tables["paper_deployments"]
        states = Base.metadata.tables["paper_scheduler_states"]
        deployment = (
            session.execute(
                select(deployments)
                .where(
                    deployments.c.workspace_id == workspace_id,
                    deployments.c.id == paper_id,
                )
                .with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        if deployment is None:
            raise PaperSchedulerError("paper deployment is not workspace-scoped")
        state = (
            session.execute(
                select(states)
                .where(
                    states.c.workspace_id == workspace_id, states.c.paper_id == paper_id
                )
                .with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        if initialization and state is not None:
            raise PaperSchedulerError("scheduler state is already initialized")
        if not initialization and state is None:
            raise PaperSchedulerError("scheduler state is missing")
        from_state = None if state is None else state["scheduler_status"]
        if state is not None and not initialization and from_state == to_state:
            return
        suppressed = None if to_state == ACTIVE else timestamp
        values = {
            "scheduler_status": to_state,
            "suppressed_since_utc": suppressed,
            "resume_watermark_utc": timestamp
            if to_state == ACTIVE or state is None
            else state["resume_watermark_utc"],
            "updated_at": timestamp,
        }
        if state is None:
            session.execute(
                states.insert().values(
                    id=uuid.uuid4(),
                    workspace_id=workspace_id,
                    paper_id=paper_id,
                    revision=1,
                    created_at=timestamp,
                    **values,
                )
            )
            revision = 1
        else:
            result = session.execute(
                update(states)
                .where(
                    states.c.id == state["id"], states.c.revision == state["revision"]
                )
                .values(**values, revision=state["revision"] + 1)
            )
            if getattr(result, "rowcount", 0) != 1:
                raise PaperSchedulerError("scheduler state revision conflict")
            revision = int(state["revision"]) + 1
        deployment_status = "ACTIVE" if to_state == ACTIVE else to_state
        session.execute(
            update(deployments)
            .where(deployments.c.id == paper_id)
            .values(
                status=deployment_status,
                updated_at=timestamp,
                revision=deployment["revision"] + 1,
            )
        )
        state_transition_id = new_id("EVT")
        summary = self._state_summary(
            state_transition_id=state_transition_id,
            workspace_id=workspace_id,
            paper_id=deployment["paper_id"],
            from_state=from_state,
            to_state=to_state,
            effective_at=timestamp,
            suppressed_since=suppressed,
            watermark=values["resume_watermark_utc"],
            revision=revision,
            reason_code=reason_code,
            actor_id=actor_id,
            initialization=initialization,
        )
        emit(
            session,
            "paper",
            deployment["paper_id"],
            deployment["revision"] + 1,
            "paper.updated",
            payload={"status": deployment_status},
            workspace_id=str(workspace_id),
            actor_id=actor_id,
            audit_summary={"paper_scheduler_state_evidence.v1": summary},
            audit_action_type=(reason_code if initialization else None),
            occurred_at=timestamp,
            event_id=state_transition_id,
        )

    @staticmethod
    def _state_summary(**value: Any) -> dict[str, Any]:
        def stamp(item: datetime | None) -> str | None:
            return (
                None if item is None else _utc(item).isoformat().replace("+00:00", "Z")
            )

        summary = {
            "state_transition_id": value["state_transition_id"],
            "workspace_id": str(value["workspace_id"]),
            "paper_id": value["paper_id"],
            "from_state": value["from_state"],
            "to_state": value["to_state"],
            "effective_at_utc": stamp(value["effective_at"]),
            "suppressed_since_utc": stamp(value["suppressed_since"]),
            "resume_watermark_utc": stamp(value["watermark"]),
            "initialization_utc": stamp(value["effective_at"])
            if value["initialization"]
            else None,
            "revision": value["revision"],
            "reason_code": value["reason_code"],
            "actor": {
                "type": "SYSTEM" if value["actor_id"] == "system" else "OWNER",
                "id": value["actor_id"],
            },
            "system": {"service": "paper-scheduler", "instance_id": "scheduler"},
            "commit_build_locator": {"commit_sha": "unknown", "build_id": "unknown"},
        }
        if set(summary) != {
            "state_transition_id",
            "workspace_id",
            "paper_id",
            "from_state",
            "to_state",
            "effective_at_utc",
            "suppressed_since_utc",
            "resume_watermark_utc",
            "initialization_utc",
            "revision",
            "reason_code",
            "actor",
            "system",
            "commit_build_locator",
        }:
            raise PaperSchedulerError("state evidence is not closed")
        return summary

    def _candidate(
        self,
        session: Session,
        deployment: Mapping[str, Any],
        state: Mapping[str, Any],
        schedule: Schedule,
        now: datetime,
    ) -> tuple[date | None, str]:
        local = now.astimezone(ZoneInfo(schedule.timezone))
        current = local.date()
        watermark = state.get("resume_watermark_utc")
        if not isinstance(watermark, datetime) or watermark.tzinfo is None:
            raise InvalidExecutionAssumption("scheduler watermark is invalid")
        runs = Base.metadata.tables["paper_daily_runs"]
        active_run = session.execute(
            select(runs.c.id).where(
                runs.c.workspace_id == deployment["workspace_id"],
                runs.c.paper_id == deployment["id"],
                runs.c.status.in_(ACTIVE_EXECUTION),
            )
        ).scalar_one_or_none()
        if active_run is not None:
            return None, "WEEKDAY_ONLY"
        probe = (
            current
            if local.timetz().replace(tzinfo=None) >= schedule.due_time
            else current - timedelta(days=1)
        )
        for _ in range(16):
            is_open, version = self._is_trading_day(schedule, probe)
            if is_open:
                due_utc = _wall_time_to_utc(probe, schedule.due_time, schedule.timezone)
                if due_utc <= _utc(watermark):
                    return None, version
                existing = session.execute(
                    select(runs.c.status).where(
                        runs.c.workspace_id == deployment["workspace_id"],
                        runs.c.paper_id == deployment["id"],
                        runs.c.trading_date == probe,
                    )
                ).scalar_one_or_none()
                if existing is None:
                    states = Base.metadata.tables["paper_scheduler_states"]
                    session.execute(
                        update(states)
                        .where(
                            states.c.id == state["id"],
                            states.c.revision == state["revision"],
                        )
                        .values(last_eligible_trading_date=probe, updated_at=now)
                    )
                    return probe, version
                # A run already exists for the newest eligible trading date.
                # Its natural key owns this date whether it is queued, running,
                # or terminal; scanning backward would create stale debt runs
                # and would re-run after a terminal gate result.
                return None, version
            probe -= timedelta(days=1)
        raise InvalidExecutionAssumption(
            "calendar cannot determine a recent trading day"
        )

    def _is_trading_day(self, schedule: Schedule, day: date) -> tuple[bool, str]:
        if schedule.calendar is None:
            return day.weekday() < 5, "WEEKDAY_ONLY"
        return self.calendar.is_trading_day(schedule.calendar, day)

    def _create_or_get(
        self,
        session: Session,
        deployment: Mapping[str, Any],
        schedule: Schedule,
        calendar_version: str,
        day: date,
        now: datetime,
        owner: str,
    ) -> bool:
        runs = Base.metadata.tables["paper_daily_runs"]
        workspace_id = deployment["workspace_id"]
        existing = (
            session.execute(
                select(runs)
                .where(
                    and_(
                        runs.c.workspace_id == workspace_id,
                        runs.c.paper_id == deployment["id"],
                        runs.c.trading_date == day,
                    )
                )
                .with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        if existing is not None:
            return False
        job_id = new_id("JOB")
        run_id = new_id("PRUN")
        command = {
            "paper_id": deployment["paper_id"],
            "paper_run_id": run_id,
            "trading_date": day.isoformat(),
            "trading_calendar": _calendar_label(schedule, calendar_version),
            "execution_assumption_revision": int(deployment["revision"]),
            "execution_assumption_sha256": content_hash(
                deployment["execution_assumption"]
            ),
        }
        job = JobRow(
            id=job_id,
            workspace_id=workspace_id,
            job_type="PAPER_DAILY_RUN",
            status="QUEUED",
            revision=1,
            payload=json.dumps(
                {"job_id": job_id, "job_type": "PAPER_DAILY_RUN", "status": "QUEUED"}
            ),
            input_payload=json.dumps(command, sort_keys=True),
            payload_sha256=content_hash(command),
            # PAPER_DAILY_RUN is a core-worker job.  There is no separate,
            # unconsumed "paper" queue: doing so strands due runs forever.
            queue_name="core",
            priority=100,
            attempt=0,
            max_attempts=MAX_ATTEMPTS,
            fencing_token=0,
            retry_safe=True,
            progress_mode="NONE",
            queued_at=now,
            created_by_type="SYSTEM",
            created_by_id=owner,
            correlation_id=run_id,
        )
        session.add(job)
        session.flush()
        session.execute(
            runs.insert().values(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                paper_run_id=run_id,
                paper_id=deployment["id"],
                trading_date=day,
                status="QUEUED",
                job_id=job.internal_id,
                started_at=None,
                finished_at=None,
            )
        )
        self._transition_evidence(
            session,
            deployment,
            {
                "paper_run_id": run_id,
                "status": "QUEUED",
                "job_id": job_id,
                "attempt": 0,
                "fencing_token": 0,
            },
            schedule,
            calendar_version,
            day,
            now,
            "CREATE",
            None,
            "QUEUED",
            "SCHEDULE_DUE",
            "NONE",
            False,
            "NOT_APPLICABLE",
        )
        return True

    def execute_claimed(self, session: Session, job: JobRow) -> None:
        """Execute the deterministic PaperDailyRun boundary under core-job fencing.

        The caller has already locked the Job lease.  This method deliberately
        uses that same transaction for the run state, evidence Artifact/Audit,
        and event, so a stale worker cannot commit a Paper transition.
        """
        if job.job_type != "PAPER_DAILY_RUN":
            raise PaperSchedulerError("not a PaperDailyRun job")
        inputs = json.loads(cast(str, job.input_payload))
        run_id = inputs.get("paper_run_id")
        if not isinstance(run_id, str):
            raise PaperSchedulerError("PaperDailyRun input is invalid")
        runs = Base.metadata.tables["paper_daily_runs"]
        deployments = Base.metadata.tables["paper_deployments"]
        found = (
            session.execute(
                select(runs)
                .where(
                    runs.c.workspace_id == job.workspace_id,
                    runs.c.paper_run_id == run_id,
                )
                .with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        row = None if found is None else cast(Mapping[str, Any], dict(found))
        if row is None or row["workspace_id"] != job.workspace_id:
            raise PaperSchedulerError("PaperDailyRun is not workspace-scoped")
        if row["status"] in TERMINAL:
            return
        found_deployment = (
            session.execute(
                select(deployments)
                .where(
                    deployments.c.workspace_id == job.workspace_id,
                    deployments.c.id == row["paper_id"],
                )
                .with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        deployment = (
            None
            if found_deployment is None
            else cast(Mapping[str, Any], dict(found_deployment))
        )
        if deployment is None:
            raise PaperSchedulerError("PaperDailyRun deployment is missing")
        try:
            schedule = _parse_schedule(deployment["execution_assumption"])
            is_trading_day, calendar_version = self._is_trading_day(
                schedule, row["trading_date"]
            )
        except (InvalidExecutionAssumption, PaperSchedulerError, ValueError) as error:
            self._finish_run(
                session,
                deployment,
                row,
                job,
                "FAILED",
                "CONFIGURATION_INVALID",
                "UNKNOWN_POST_SIDE_EFFECT",
                True,
                "NO_AUTOMATIC_REPLAY",
                schedule=_invalid_schedule(),
                calendar_version="UNAVAILABLE",
            )
            raise PaperSchedulerError(
                "PaperDailyRun configuration failed closed"
            ) from error
        expected_calendar = inputs.get("trading_calendar")
        if not is_trading_day:
            self._finish_run(
                session,
                deployment,
                row,
                job,
                "BLOCKED",
                "NON_TRADING_DAY",
                "NONE",
                False,
                "NOT_APPLICABLE",
                block_reason_code="NON_TRADING_DAY",
            )
            return None
        if expected_calendar != _calendar_label(schedule, calendar_version):
            self._finish_run(
                session,
                deployment,
                row,
                job,
                "BLOCKED",
                "CALENDAR_VERSION_MISMATCH",
                "NONE",
                True,
                "NO_AUTOMATIC_REPLAY",
                block_reason_code="CALENDAR_VERSION_MISMATCH",
            )
            return None
        now = datetime.now(UTC)
        if row["status"] == "QUEUED":
            session.execute(
                update(runs)
                .where(runs.c.id == row["id"])
                .values(
                    status="RUNNING",
                    started_at=now,
                )
            )
            running = dict(row)
            running["status"] = "RUNNING"
            self._transition_evidence(
                session,
                deployment,
                running,
                schedule,
                calendar_version,
                row["trading_date"],
                now,
                "LEASE_ACQUIRED",
                "QUEUED",
                "RUNNING",
                "LEASE_ACQUIRED",
                "SAFE_PRE_ORDER",
                False,
                "NOT_APPLICABLE",
            )
            row = running
        elif row["status"] == "RUNNING":
            # A reaped safe pre-order Job keeps the same run/natural key.  The
            # new core-worker lease is the recovery decision; it never creates
            # a second Job, run, order chain, or catch-up entitlement.
            self._transition_evidence(
                session,
                deployment,
                row,
                schedule,
                calendar_version,
                row["trading_date"],
                now,
                "RECOVERY_ACQUIRED",
                "RUNNING",
                "RUNNING",
                "SAFE_PRE_ORDER_RECOVERY",
                "SAFE_PRE_ORDER",
                False,
                "SAFE_RETRY_SAME_RUN",
            )
        decisions = self._evaluate_gates(
            session,
            deployment=deployment,
            run=row,
            job=job,
            inputs=inputs,
            now=now,
        )
        runs_values: dict[str, Any] = {
            "risk_result": {
                "schema_name": "paper_gate_results",
                "schema_version": 1,
                "gates": [
                    {
                        "gate": decision.gate,
                        "outcome": decision.outcome,
                        "reason_code": decision.reason_code,
                    }
                    for decision in decisions
                ],
            }
        }
        for decision in decisions:
            if decision.gate == "DATA_QUALITY":
                for key in ("data_snapshot_id", "data_quality_run_id"):
                    if key in decision.values:
                        runs_values[key] = decision.values[key]
        session.execute(
            update(runs).where(runs.c.id == row["id"]).values(**runs_values)
        )
        for decision in decisions:
            if decision.outcome == "UNKNOWN":
                raise PaperSchedulerError(
                    f"{decision.gate} returned unknown: {decision.reason_code}"
                )
            if decision.outcome == "REJECTED":
                self._finish_run(
                    session,
                    deployment,
                    row,
                    job,
                    "BLOCKED",
                    decision.reason_code,
                    "NONE",
                    False,
                    "NOT_APPLICABLE",
                    now=now,
                    block_reason_code=decision.reason_code,
                )
                return None
        self._finish_run(
            session,
            deployment,
            row,
            job,
            "COMPLETED",
            "PAPER_DAILY_RUN_COMPLETED",
            "NONE",
            False,
            "NOT_APPLICABLE",
            now=now,
        )
        return None

    def _evaluate_gates(
        self,
        session: Session,
        *,
        deployment: Mapping[str, Any],
        run: Mapping[str, Any],
        job: JobRow,
        inputs: Mapping[str, Any],
        now: datetime,
    ) -> list[GateDecision]:
        data_quality = self._data_quality_gate(
            session, deployment=deployment, run=run, now=now
        )
        freshness = self._freshness_gate(run=run, quality=data_quality)
        strategy = self._strategy_version_gate(
            session, deployment=deployment, inputs=inputs
        )
        risk = self._risk_gate(
            session, deployment=deployment, run=run, strategy=strategy
        )
        return [data_quality, freshness, strategy, risk]

    def _data_quality_gate(
        self,
        session: Session,
        *,
        deployment: Mapping[str, Any],
        run: Mapping[str, Any],
        now: datetime,
    ) -> GateDecision:
        snapshots = Base.metadata.tables["dataset_snapshots"]
        quality = Base.metadata.tables["data_quality_runs"]
        strategies = Base.metadata.tables["strategy_versions"]
        strategy = session.execute(
            select(strategies.c.required_dataset_refs).where(
                strategies.c.workspace_id == deployment["workspace_id"],
                strategies.c.id == deployment["strategy_version_id"],
            )
        ).scalar_one_or_none()
        if strategy is None:
            return GateDecision(
                "DATA_QUALITY",
                "UNKNOWN",
                "STRATEGY_DATASET_BINDING_UNKNOWN",
                "bound strategy version is unavailable",
                {},
            )
        if isinstance(strategy, str):
            try:
                strategy = json.loads(strategy)
            except json.JSONDecodeError:
                strategy = None
        if not isinstance(strategy, list):
            return GateDecision(
                "DATA_QUALITY",
                "UNKNOWN",
                "STRATEGY_DATASET_BINDING_UNKNOWN",
                "required dataset references are invalid",
                {},
            )
        required_refs = [
            value
            if isinstance(value, str)
            else next(
                (
                    value.get(key)
                    for key in ("dataset_id", "id", "public_id")
                    if isinstance(value, dict) and isinstance(value.get(key), str)
                ),
                None,
            )
            for value in strategy
        ]
        if any(value is None for value in required_refs):
            return GateDecision(
                "DATA_QUALITY",
                "UNKNOWN",
                "STRATEGY_DATASET_BINDING_UNKNOWN",
                "required dataset references are incomplete",
                {},
            )
        required_refs = list(dict.fromkeys(cast(list[str], required_refs)))
        datasets = Base.metadata.tables["datasets"]
        if required_refs:
            dataset_rows = session.execute(
                select(datasets.c.id, datasets.c.dataset_id).where(
                    datasets.c.workspace_id == deployment["workspace_id"]
                )
            ).mappings()
            dataset_ids = [
                row["id"]
                for row in dataset_rows
                if str(row["id"]) in required_refs
                or str(row["dataset_id"]) in required_refs
            ]
            if len(dataset_ids) != len(required_refs):
                return GateDecision(
                    "DATA_QUALITY",
                    "REJECTED",
                    "DATA_SNAPSHOT_MISSING",
                    "a required dataset is not bound in the workspace",
                    {"required_dataset_refs": required_refs},
                )
        else:
            dataset_ids = [None]

        rows = []
        for dataset_id in dataset_ids:
            statement = (
                select(
                    snapshots.c.id.label("snapshot_internal_id"),
                    snapshots.c.snapshot_id.label("snapshot_public_id"),
                    snapshots.c.coverage_end,
                    snapshots.c.as_of_time,
                    quality.c.id.label("quality_internal_id"),
                    quality.c.quality_run_id,
                    quality.c.status.label("quality_status"),
                    quality.c.result_state,
                    quality.c.lookahead_detected,
                    quality.c.survivorship_safe,
                    quality.c.stale_data_detected,
                )
                .join(
                    quality,
                    and_(
                        quality.c.workspace_id == snapshots.c.workspace_id,
                        quality.c.id == snapshots.c.quality_run_id,
                    ),
                )
                .where(
                    snapshots.c.workspace_id == deployment["workspace_id"],
                    snapshots.c.coverage_end >= run["trading_date"],
                    snapshots.c.as_of_time <= now,
                )
                .order_by(
                    snapshots.c.coverage_end.desc(), snapshots.c.as_of_time.desc()
                )
                .limit(1)
            )
            if dataset_id is not None:
                statement = statement.where(snapshots.c.dataset_id == dataset_id)
            row = session.execute(statement).mappings().one_or_none()
            if row is None:
                return GateDecision(
                    "DATA_QUALITY",
                    "REJECTED",
                    "DATA_SNAPSHOT_MISSING",
                    "no eligible snapshot for every required dataset",
                    {"required_dataset_refs": required_refs},
                )
            rows.append(row)

        values = {
            "data_snapshot_ids": [row["snapshot_internal_id"] for row in rows],
            "data_quality_run_ids": [row["quality_internal_id"] for row in rows],
            "data_snapshot_id": rows[0]["snapshot_internal_id"],
            "data_quality_run_id": rows[0]["quality_internal_id"],
            "coverage_end": min(row["coverage_end"] for row in rows),
            "as_of_time": max(row["as_of_time"] for row in rows),
            "stale_data_detected": any(row["stale_data_detected"] for row in rows),
            "required_dataset_refs": required_refs,
        }
        for row in rows:
            if row["quality_status"] != "COMPLETED" or row["result_state"] is None:
                return GateDecision(
                    "DATA_QUALITY",
                    "UNKNOWN",
                    "DATA_QUALITY_RESULT_UNKNOWN",
                    "quality result is not terminal",
                    values,
                )
            if (
                row["result_state"] == "BLOCKED"
                or row["lookahead_detected"] is True
                or row["survivorship_safe"] is False
            ):
                return GateDecision(
                    "DATA_QUALITY",
                    "REJECTED",
                    "DATA_QUALITY_BLOCKED",
                    "deterministic data-quality gate rejected",
                    values,
                )
            if row["result_state"] not in {"HEALTHY", "WARN"}:
                return GateDecision(
                    "DATA_QUALITY",
                    "UNKNOWN",
                    "DATA_QUALITY_RESULT_UNKNOWN",
                    "quality result is not recognized",
                    values,
                )
        return GateDecision(
            "DATA_QUALITY",
            "PASSED",
            "DATA_QUALITY_PASSED",
            "quality result accepted for every required dataset",
            values,
        )

    @staticmethod
    def _freshness_gate(
        *, run: Mapping[str, Any], quality: GateDecision
    ) -> GateDecision:
        if not quality.values:
            return GateDecision(
                "FRESHNESS",
                "REJECTED",
                "STALE_DATA",
                "freshness has no eligible snapshot",
                {},
            )
        stale = quality.values.get("stale_data_detected")
        coverage_end = quality.values.get("coverage_end")
        if stale is None:
            return GateDecision(
                "FRESHNESS",
                "UNKNOWN",
                "FRESHNESS_RESULT_UNKNOWN",
                "stale-data result is missing",
                {},
            )
        if (
            stale
            or not isinstance(coverage_end, date)
            or coverage_end < run["trading_date"]
        ):
            return GateDecision(
                "FRESHNESS",
                "REJECTED",
                "STALE_DATA",
                "snapshot is stale for trading date",
                {},
            )
        return GateDecision(
            "FRESHNESS", "PASSED", "FRESHNESS_PASSED", "snapshot is current", {}
        )

    @staticmethod
    def _strategy_version_gate(
        session: Session,
        *,
        deployment: Mapping[str, Any],
        inputs: Mapping[str, Any],
    ) -> GateDecision:
        versions = Base.metadata.tables["strategy_versions"]
        strategy = (
            session.execute(
                select(versions).where(
                    versions.c.workspace_id == deployment["workspace_id"],
                    versions.c.id == deployment["strategy_version_id"],
                )
            )
            .mappings()
            .one_or_none()
        )
        assumption_matches = (
            inputs.get("paper_id") == deployment["paper_id"]
            and inputs.get("execution_assumption_revision") == deployment["revision"]
            and inputs.get("execution_assumption_sha256")
            == content_hash(deployment["execution_assumption"])
        )
        if (
            strategy is None
            or strategy["is_frozen"] is not True
            or strategy["state"] not in {"FROZEN", "PAPER"}
            or not assumption_matches
        ):
            return GateDecision(
                "STRATEGY_VERSION",
                "REJECTED",
                "PAPER_VERSION_MISMATCH",
                "frozen deployment revision no longer matches",
                {},
            )
        return GateDecision(
            "STRATEGY_VERSION",
            "PASSED",
            "STRATEGY_VERSION_PASSED",
            "frozen strategy and deployment revision match",
            {"strategy": dict(strategy)},
        )

    @staticmethod
    def _risk_gate(
        session: Session,
        *,
        deployment: Mapping[str, Any],
        run: Mapping[str, Any],
        strategy: GateDecision,
    ) -> GateDecision:
        if strategy.outcome != "PASSED":
            return GateDecision(
                "RISK",
                "REJECTED",
                "PAPER_RISK_BLOCKED",
                "risk input strategy is unavailable",
                {},
            )
        policies = Base.metadata.tables["risk_policy_versions"]
        positions = Base.metadata.tables["paper_positions"]
        policy = (
            session.execute(
                select(policies).where(
                    policies.c.workspace_id == deployment["workspace_id"],
                    policies.c.id == deployment["risk_policy_id"],
                )
            )
            .mappings()
            .one_or_none()
        )
        if policy is None or policy["status"] != "ACTIVE":
            return GateDecision(
                "RISK",
                "UNKNOWN",
                "RISK_POLICY_UNAVAILABLE",
                "bound risk policy is not active",
                {},
            )
        latest = session.scalar(
            select(positions.c.as_of_date)
            .where(
                positions.c.workspace_id == deployment["workspace_id"],
                positions.c.paper_id == deployment["id"],
                positions.c.as_of_date <= run["trading_date"],
            )
            .order_by(positions.c.as_of_date.desc())
            .limit(1)
        )
        weights = (
            []
            if latest is None
            else list(
                session.scalars(
                    select(positions.c.weight).where(
                        positions.c.workspace_id == deployment["workspace_id"],
                        positions.c.paper_id == deployment["id"],
                        positions.c.as_of_date == latest,
                    )
                )
            )
        )
        try:
            max_weight = max(
                (abs(Decimal(value)) for value in weights), default=Decimal(0)
            )
            gross_weight = sum((abs(Decimal(value)) for value in weights), Decimal(0))
            expected_turnover = Decimal(
                strategy.values["strategy"]["expected_turnover"]
            )
            limits = {
                "max_single_position": Decimal(policy["max_single_position"]),
                "max_strategy_weight": Decimal(policy["max_strategy_weight"]),
                "max_turnover": Decimal(policy["max_turnover"]),
            }
        except (InvalidOperation, KeyError, TypeError, ValueError):
            return GateDecision(
                "RISK",
                "UNKNOWN",
                "RISK_RESULT_UNKNOWN",
                "risk inputs are incomplete",
                {},
            )
        if not all(
            value.is_finite()
            for value in (
                max_weight,
                gross_weight,
                expected_turnover,
                *limits.values(),
            )
        ):
            return GateDecision(
                "RISK",
                "UNKNOWN",
                "RISK_RESULT_UNKNOWN",
                "risk inputs are non-finite",
                {},
            )
        violations = [
            name
            for name, actual, limit in (
                ("MAX_SINGLE_POSITION", max_weight, limits["max_single_position"]),
                ("MAX_STRATEGY_WEIGHT", gross_weight, limits["max_strategy_weight"]),
                ("MAX_TURNOVER", expected_turnover, limits["max_turnover"]),
            )
            if actual > limit
        ]
        values = {
            "max_weight": str(max_weight),
            "gross_weight": str(gross_weight),
            "expected_turnover": str(expected_turnover),
            "violations": violations,
        }
        if violations:
            return GateDecision(
                "RISK",
                "REJECTED",
                "PAPER_RISK_BLOCKED",
                "deterministic risk gate rejected",
                values,
            )
        return GateDecision(
            "RISK", "PASSED", "RISK_GATE_PASSED", "risk limits accepted", values
        )

    def fail_claimed(
        self,
        session: Session,
        job: JobRow,
        *,
        reason_code: str,
        now: datetime | None = None,
        lease_snapshot: LeaseSnapshot | None = None,
        status: str = "FAILED",
    ) -> None:
        """Fail uncertain recovery closed; no automatic Paper replay is legal."""
        if job.job_type != "PAPER_DAILY_RUN":
            return
        runs = Base.metadata.tables["paper_daily_runs"]
        deployments = Base.metadata.tables["paper_deployments"]
        found = (
            session.execute(
                select(runs).where(runs.c.job_id == job.internal_id).with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        row = None if found is None else cast(Mapping[str, Any], dict(found))
        if row is None or row["status"] in TERMINAL:
            return
        found_deployment = (
            session.execute(
                select(deployments).where(
                    deployments.c.workspace_id == job.workspace_id,
                    deployments.c.id == row["paper_id"],
                )
            )
            .mappings()
            .one_or_none()
        )
        deployment = (
            None
            if found_deployment is None
            else cast(Mapping[str, Any], dict(found_deployment))
        )
        if deployment is None:
            return
        try:
            schedule = _parse_schedule(deployment["execution_assumption"])
            _, calendar_version = self._is_trading_day(schedule, row["trading_date"])
        except InvalidExecutionAssumption:
            self._finish_run(
                session,
                deployment,
                row,
                job,
                status,
                "CONFIGURATION_INVALID",
                "UNKNOWN_POST_SIDE_EFFECT",
                True,
                "NO_AUTOMATIC_REPLAY",
                now=now,
                lease_snapshot=lease_snapshot,
                schedule=_invalid_schedule(),
                calendar_version="UNAVAILABLE",
            )
            return
        self._finish_run(
            session,
            deployment,
            row,
            job,
            status,
            reason_code,
            "UNKNOWN_POST_SIDE_EFFECT",
            True,
            "NO_AUTOMATIC_REPLAY",
            now=now,
            lease_snapshot=lease_snapshot,
        )

    def _finish_run(
        self,
        session: Session,
        deployment: Mapping[str, Any],
        run: Mapping[str, Any],
        job: JobRow,
        status: str,
        reason_code: str,
        certainty: str,
        review_required: bool,
        replay: str,
        *,
        now: datetime | None = None,
        block_reason_code: str | None = None,
        lease_snapshot: LeaseSnapshot | None = None,
        schedule: Schedule | None = None,
        calendar_version: str | None = None,
    ) -> None:
        runs = Base.metadata.tables["paper_daily_runs"]
        now = now or datetime.now(UTC)
        session.execute(
            update(runs)
            .where(runs.c.id == run["id"])
            .values(
                status=status,
                block_reason_code=block_reason_code,
                finished_at=now,
            )
        )
        finished = dict(run)
        finished["status"] = status
        schedule = schedule or _invalid_schedule()
        if calendar_version is None:
            try:
                schedule = _parse_schedule(deployment["execution_assumption"])
                calendar_version = self._is_trading_day(schedule, run["trading_date"])[
                    1
                ]
            except InvalidExecutionAssumption:
                schedule = _invalid_schedule()
                calendar_version = "UNAVAILABLE"
        self._transition_evidence(
            session,
            deployment,
            finished,
            schedule,
            calendar_version,
            run["trading_date"],
            now,
            status,
            run["status"],
            status,
            reason_code,
            certainty,
            review_required,
            replay,
            lease_snapshot=lease_snapshot,
        )

    def record_expired_lease(
        self,
        session: Session,
        job: JobRow,
        *,
        now: datetime,
        safe_retry: bool,
        lease_snapshot: LeaseSnapshot,
    ) -> None:
        runs = Base.metadata.tables["paper_daily_runs"]
        deployments = Base.metadata.tables["paper_deployments"]
        row = (
            session.execute(
                select(runs)
                .where(
                    runs.c.workspace_id == job.workspace_id,
                    runs.c.job_id == job.internal_id,
                )
                .with_for_update()
            )
            .mappings()
            .one_or_none()
        )
        if row is None or row["status"] in TERMINAL:
            return
        run = cast(Mapping[str, Any], dict(row))
        found_deployment = (
            session.execute(
                select(deployments).where(
                    deployments.c.workspace_id == job.workspace_id,
                    deployments.c.id == row["paper_id"],
                )
            )
            .mappings()
            .one_or_none()
        )
        if found_deployment is None:
            deployment: Mapping[str, Any] = {
                "workspace_id": job.workspace_id,
                "paper_id": run["paper_id"],
                "execution_assumption": None,
            }
            self._finish_run(
                session,
                deployment,
                run,
                job,
                "FAILED",
                "SCHEDULER_RECOVERY_INVALID",
                "UNKNOWN_POST_SIDE_EFFECT",
                True,
                "NO_AUTOMATIC_REPLAY",
                now=now,
                lease_snapshot=lease_snapshot,
                schedule=_invalid_schedule(),
                calendar_version="UNAVAILABLE",
            )
            return
        deployment = cast(Mapping[str, Any], dict(found_deployment))
        try:
            schedule = _parse_schedule(deployment["execution_assumption"])
            _, calendar_version = self._is_trading_day(schedule, run["trading_date"])
        except (InvalidExecutionAssumption, PaperSchedulerError, ValueError):
            self._finish_run(
                session,
                deployment,
                run,
                job,
                "FAILED",
                "SCHEDULER_RECOVERY_INVALID",
                "UNKNOWN_POST_SIDE_EFFECT",
                True,
                "NO_AUTOMATIC_REPLAY",
                now=now,
                lease_snapshot=lease_snapshot,
                schedule=_invalid_schedule(),
                calendar_version="UNAVAILABLE",
            )
            return
        self._transition_evidence(
            session,
            deployment,
            run,
            schedule,
            calendar_version,
            run["trading_date"],
            now,
            "LEASE_LOST",
            run["status"],
            run["status"],
            "JOB_LEASE_LOST",
            "SAFE_PRE_ORDER" if safe_retry else "UNKNOWN_POST_SIDE_EFFECT",
            not safe_retry,
            "SAFE_RETRY_SAME_RUN" if safe_retry else "NO_AUTOMATIC_REPLAY",
            lease_snapshot=lease_snapshot,
        )
        if safe_retry:
            self._transition_evidence(
                session,
                deployment,
                run,
                schedule,
                calendar_version,
                run["trading_date"],
                now,
                "RETRY_SCHEDULED",
                run["status"],
                run["status"],
                "JOB_LEASE_LOST",
                "SAFE_PRE_ORDER",
                False,
                "SAFE_RETRY_SAME_RUN",
                lease_snapshot=lease_snapshot,
            )
        else:
            self._transition_evidence(
                session,
                deployment,
                run,
                schedule,
                calendar_version,
                run["trading_date"],
                now,
                "RETRY_EXHAUSTED",
                run["status"],
                run["status"],
                "JOB_LEASE_LOST",
                "UNKNOWN_POST_SIDE_EFFECT",
                True,
                "NO_AUTOMATIC_REPLAY",
                lease_snapshot=lease_snapshot,
            )
            self._finish_run(
                session,
                deployment,
                run,
                job,
                "FAILED",
                "JOB_LEASE_LOST",
                "UNKNOWN_POST_SIDE_EFFECT",
                True,
                "NO_AUTOMATIC_REPLAY",
                now=now,
                lease_snapshot=lease_snapshot,
            )

    def _transition_evidence(
        self,
        session: Session,
        deployment: Mapping[str, Any],
        run: Mapping[str, Any],
        schedule: Schedule,
        calendar_version: str,
        day: date,
        now: datetime,
        transition: str,
        from_status: str | None,
        to_status: str,
        reason_code: str,
        certainty: str,
        review_required: bool,
        replay: str,
        *,
        lease_snapshot: LeaseSnapshot | None = None,
    ) -> None:
        job_reference = run["job_id"]
        job: Any = None
        if isinstance(job_reference, str):
            job = session.get(JobRow, job_reference)
        if job is None:
            job = session.execute(
                select(JobRow).where(JobRow.internal_id == job_reference)
            ).scalar_one()
        payload = {
            "identity": {
                "evidence_version": 1,
                "workspace_id": str(deployment["workspace_id"]),
                "paper_id": str(deployment["paper_id"]),
                "paper_run_id": run["paper_run_id"],
                "trading_date": day.isoformat(),
                "idempotency_locator": {
                    "workspace_id": str(deployment["workspace_id"]),
                    "paper_id": str(deployment["paper_id"]),
                    "trading_date": day.isoformat(),
                },
            },
            "decision": {
                "transition": transition,
                "from_status": from_status,
                "to_status": to_status,
                "reason_code": reason_code,
                "reason_detail": reason_code,
                "side_effect_certainty": certainty,
            },
            "job_lease": {
                "job_id": job.id,
                "attempt": job.attempt,
                "max_attempts": job.max_attempts,
                "lease_owner": lease_snapshot.owner
                if lease_snapshot
                else job.lease_owner,
                "lease_expires_at": self._iso(
                    lease_snapshot.expires_at
                    if lease_snapshot
                    else job.lease_expires_at
                ),
                "heartbeat_at": self._iso(
                    lease_snapshot.heartbeat_at if lease_snapshot else job.heartbeat_at
                ),
                "fencing_token": job.fencing_token,
                "retry_safe": job.retry_safe,
                "next_retry_at": self._iso(
                    lease_snapshot.next_retry_at if lease_snapshot else None
                ),
            },
            "time_calendar": {
                "occurred_at": self._iso(now),
                "created_at": self._iso(job.queued_at),
                "started_at": self._iso(job.started_at),
                "finished_at": self._iso(job.finished_at),
                "schedule_timezone": schedule.timezone,
                "daily_due_time": schedule.due_time.strftime("%H:%M"),
                "trading_calendar": _calendar_label(schedule, calendar_version),
            },
            "review": {
                "review_required": review_required,
                "review_reason_code": reason_code if review_required else None,
                "replay_disposition": replay,
            },
        }
        if set(payload) != EVIDENCE_KEYS:
            raise PaperSchedulerError("scheduler evidence envelope is not closed")
        session.flush()
        audit_events = Base.metadata.tables["audit_events"]
        previous_revision = session.scalar(
            select(func.max(audit_events.c.object_revision)).where(
                audit_events.c.workspace_id == deployment["workspace_id"],
                audit_events.c.object_type == "paper_run",
                audit_events.c.object_id == run["paper_run_id"],
            )
        )
        object_revision = int(previous_revision or 0) + 1
        storage_key, digest = stage_json(
            session, payload, object_key=run["paper_run_id"]
        )
        publish_staged(session, storage_key, digest)
        artifact = ArtifactRow(
            artifact_id=new_id("ART"),
            workspace_id=deployment["workspace_id"],
            job_id=job.id,
            kind="JSON",
            media_type="application/json",
            storage_key=storage_key,
            size_bytes=len(
                json.dumps(
                    payload,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                ).encode("utf-8")
            ),
            sha256=digest,
            schema_name="paper_scheduler_evidence",
            schema_version=1,
            metadata_json={
                "paper_id": deployment["paper_id"],
                "paper_run_id": run["paper_run_id"],
                "trading_date": day.isoformat(),
                "transition": transition,
                "reason_code": reason_code,
            },
            publication_state="STAGED",
            created_at=now,
            immutable=True,
        )
        session.add(artifact)
        session.flush()
        emit(
            session,
            "paper_run",
            run["paper_run_id"],
            object_revision,
            "paper.run.updated",
            payload={
                "state": to_status,
                "status": to_status,
            },
            job_id=job.id,
            workspace_id=str(deployment["workspace_id"]),
            actor_id="system",
            correlation_id=run["paper_run_id"],
            audit_summary={"transition": transition, "reason_code": reason_code},
            detail_artifact_id=cast(uuid.UUID, artifact.id),
        )

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        return None if value is None else _utc(value).isoformat().replace("+00:00", "Z")
