"""QF-PAPER-SCH-001..007 durable Paper scheduler acceptance coverage.

These tests intentionally require the same real PostgreSQL 18/Alembic harness
as the release gate.  They do not fall back to SQLite or metadata bootstrap.
"""

from __future__ import annotations

import json
import os
import time as time_module
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, time, timedelta
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.artifacts import publish_staged, stage_json
from app.event_contract import validate_event_payload, validate_sse_envelope
from app.main import (
    ArtifactRow,
    Audit,
    Base,
    Event,
    JobRow,
    SessionLocal,
    content_hash,
    new_id,
)
from app.queue import (
    LostLease,
    claim_job,
    complete_job,
    lock_active_lease,
    reap_expired_jobs,
)
from scheduler.paper import (
    InvalidExecutionAssumption,
    PaperScheduler,
    Schedule,
    TradingCalendar,
)

pytestmark = [pytest.mark.paper_scheduler, pytest.mark.pg18]

EXPECTED_STATE_KEYS = {
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
}
EXPECTED_EVIDENCE_SECTIONS = {
    "identity",
    "decision",
    "job_lease",
    "time_calendar",
    "review",
}


@pytest.fixture(scope="module")
def pg18_session_factory() -> sessionmaker[Session]:
    """Require real PG18 and an Alembic-created head; never use SQLite."""

    database_url = os.getenv("QF_DATABASE_URL", "")
    if not database_url.startswith(("postgresql://", "postgresql+")):
        pytest.skip(
            "QF-PAPER-SCH acceptance requires QF_DATABASE_URL=PostgreSQL 18+; "
            "SQLite is not evidence"
        )
    bind = SessionLocal.kw["bind"]
    assert bind is not None
    with bind.connect() as connection:
        server_version = int(
            connection.execute(text("SHOW server_version_num")).scalar_one()
        )
        if server_version < 180000:
            pytest.skip(
                f"QF-PAPER-SCH acceptance requires PostgreSQL 18+; found {server_version}"
            )
        revision = connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one_or_none()
        if revision != "0017_paper_scheduler_state_init":
            pytest.fail(
                "QF-PAPER-SCH requires Alembic head "
                "0017_paper_scheduler_state_init; "
                f"found {revision!r}"
            )
    return sessionmaker(bind=bind, expire_on_commit=False)


def _owner_graph(
    session: Session,
    token: str,
    *,
    strategy_frozen: bool = True,
    expected_turnover: int = 0,
    risk_max_turnover: int = 1,
) -> dict[str, Any]:
    """Insert the smallest valid frozen-paper parent graph for real PG tests."""

    workspace_id = str(uuid.uuid4())
    owner_id = f"paper-acceptance-{token}"
    now = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    session.execute(
        text(
            "INSERT INTO users (id, email, role, revision) "
            "VALUES (:id, :email, 'OWNER', 1)"
        ),
        {"id": owner_id, "email": f"{owner_id}@invalid.test"},
    )
    session.execute(
        text(
            "INSERT INTO workspaces (id, owner_id, name, revision) "
            "VALUES (:id, :owner, :name, 1)"
        ),
        {"id": workspace_id, "owner": owner_id, "name": f"Paper acceptance {token}"},
    )

    cost_internal = str(uuid.uuid4())
    cost_public = new_id("COST")
    session.execute(
        text(
            "INSERT INTO cost_model_versions "
            "(id, legacy_id, workspace_id, cost_model_id, version, status, "
            "content_sha256, created_at, activated_at, commission_model, "
            "slippage_model, spread_model, rebalance_timing, fill_assumption, currency) "
            "VALUES (:id, :legacy, :workspace, :public, 1, 'ACTIVE', :sha, :now, :now, "
            "CAST(:commission AS jsonb), CAST(:slippage AS jsonb), NULL, "
            "'DAILY', 'MID', 'USD')"
        ),
        {
            "id": cost_internal,
            "legacy": f"COST-LEGACY-{token}",
            "workspace": workspace_id,
            "public": cost_public,
            "sha": content_hash({"cost": token}),
            "now": now,
            "commission": json.dumps({"bps": 0}),
            "slippage": json.dumps({"bps": 0}),
        },
    )

    strategy_internal = str(uuid.uuid4())
    strategy_public = new_id("STRAT")
    research_public = new_id("RSCH")
    session.execute(
        text(
            "INSERT INTO strategies "
            "(id, strategy_id, workspace_id, research_id, revision, detail, name, "
            "current_version, status, origin_research_id, created_at, updated_at) "
            "VALUES (:id, :public, :workspace, :research, 1, '{}', :name, 1, "
            "'PAPER', NULL, :now, :now)"
        ),
        {
            "id": strategy_internal,
            "public": strategy_public,
            "workspace": workspace_id,
            "research": research_public,
            "name": f"paper-{token}",
            "now": now,
        },
    )

    strategy_version_internal = str(uuid.uuid4())
    strategy_version_legacy = f"SV-{uuid.uuid4()}"
    strategy_spec = content_hash({"strategy": token})
    session.execute(
        text(
            "INSERT INTO strategy_versions "
            "(id, legacy_id, workspace_id, strategy_id, strategy_public_id, cost_model_id, "
            "version, state, spec_sha256, frozen_at, revision, detail, research_period, "
            "validation_period, holdout_period, lifecycle_state, is_frozen, thesis, "
            "universe_spec, signals, selection_rules, position_sizing, portfolio_rules, "
            "rebalance_rules, "
            "exit_rules, benchmark_ref, risk_constraints, required_dataset_refs, "
            "known_failure_modes, expected_turnover, frozen_by, created_at) "
            "VALUES (:id, :legacy, :workspace, :strategy, :strategy_public, :cost, 1, "
            ":state, :sha, :frozen_at, 1, '{}', "
            "CAST(:period AS daterange), CAST(:period AS daterange), NULL, :state, :is_frozen, "
            "'', CAST('{}' AS jsonb), CAST('{}' AS jsonb), CAST('{}' AS jsonb), "
            "CAST('{}' AS jsonb), CAST('{}' AS jsonb), CAST('{}' AS jsonb), "
            "CAST('{}' AS jsonb), "
            "CAST('{}' AS jsonb), CAST('{}' AS jsonb), CAST('[]' AS jsonb), "
            "CAST('[]' AS jsonb), :expected_turnover, :owner, :now)"
        ),
        {
            "id": strategy_version_internal,
            "legacy": strategy_version_legacy,
            "workspace": workspace_id,
            "strategy": strategy_internal,
            "strategy_public": strategy_public,
            "cost": cost_internal,
            "sha": strategy_spec,
            "now": now,
            "period": "[2020-01-01,2030-01-01)",
            "owner": owner_id,
            "expected_turnover": expected_turnover,
            "state": "FROZEN" if strategy_frozen else "CANDIDATE",
            "is_frozen": strategy_frozen,
            "frozen_at": now if strategy_frozen else None,
        },
    )

    risk_internal = str(uuid.uuid4())
    risk_public = new_id("RISK")
    session.execute(
        text(
            "INSERT INTO risk_policy_versions "
            "(id, legacy_id, workspace_id, policy_id, policy_family, version, status, "
            "content_sha256, created_at, activated_at, max_single_position, "
            "max_strategy_weight, target_portfolio_vol, max_paper_drawdown, max_turnover, rules) "
            "VALUES (:id, :legacy, :workspace, :public, 'risk', 1, 'ACTIVE', :sha, "
            ":now, :now, 1, 1, 1, 1, :max_turnover, CAST('{}' AS jsonb))"
        ),
        {
            "id": risk_internal,
            "legacy": f"RISK-LEGACY-{token}",
            "workspace": workspace_id,
            "public": risk_public,
            "sha": content_hash({"risk": token}),
            "now": now,
            "max_turnover": risk_max_turnover,
        },
    )

    paper_public = new_id("PAPER")
    approval_internal = str(uuid.uuid4())
    approval_public = new_id("APR")
    session.execute(
        text(
            "INSERT INTO approval_requests "
            "(id, approval_id, workspace_id, validation_id, status, subject_sha256, "
            "subject_type, subject_id, subject_version, subject_revision, subject_spec_sha256, "
            "prerequisites_sha256, type, subject_hash, requested_by_type, requested_by_id, "
            "reason, prerequisites, risk_summary, effects, decision_reason, requested_at, "
            "decided_at, decided_by, revision, detail) "
            "VALUES (:id, :public, :workspace, NULL, 'APPROVED', :subject_sha, 'PAPER', :paper, "
            "1, 1, :subject_sha, :prereq_sha, 'PAPER_DEPLOYMENT', :subject_hash, "
            "'SYSTEM', :owner, 'test', "
            "CAST('{}' AS jsonb), CAST('{}' AS jsonb), CAST('[]' AS jsonb), 'accepted', "
            ":now, :now, :owner, 1, '{}')"
        ),
        {
            "id": approval_internal,
            "public": approval_public,
            "workspace": workspace_id,
            "paper": paper_public,
            "subject_sha": content_hash({"approval": token}),
            "prereq_sha": content_hash({"approval-prerequisites": token}),
            "subject_hash": content_hash({"approval-subject": token}),
            "owner": owner_id,
            "now": now,
        },
    )

    deployment_id = str(uuid.uuid4())
    return {
        "workspace_id": workspace_id,
        "owner_id": owner_id,
        "deployment_id": deployment_id,
        "paper_id": paper_public,
        "strategy_version_id": strategy_version_internal,
        "approval_id": approval_internal,
        "risk_policy_id": risk_internal,
        "now": now,
    }


def _seed_deployment(
    session: Session,
    token: str,
    *,
    timezone: str = "UTC",
    due_time: str = "09:00",
    calendar: str | None = None,
    state: str | None = "ACTIVE",
    watermark: datetime | None = None,
    deployment_status: str = "ACTIVE",
    strategy_frozen: bool = True,
    expected_turnover: int = 0,
    risk_max_turnover: int = 1,
) -> dict[str, Any]:
    value = _owner_graph(
        session,
        token,
        strategy_frozen=strategy_frozen,
        expected_turnover=expected_turnover,
        risk_max_turnover=risk_max_turnover,
    )
    now = value["now"]
    watermark = watermark or now
    assumption = json.dumps(
        {
            "schedule_timezone": timezone,
            "daily_due_time": due_time,
            "trading_calendar": calendar,
        }
    )
    session.execute(
        text(
            "INSERT INTO paper_deployments "
            "(id, workspace_id, paper_id, strategy_version_id, approval_id, risk_policy_id, "
            "initial_capital, currency, start_date, execution_assumption, status, current_nav, "
            "last_run_date, last_success_at, revision, created_at, updated_at) "
            "VALUES (:id, :workspace, :paper, :strategy, :approval, :risk, 100000, 'USD', "
            ":start_date, CAST(:assumption AS jsonb), :status, 100000, NULL, NULL, 1, :now, :now)"
        ),
        {
            "id": value["deployment_id"],
            "workspace": value["workspace_id"],
            "paper": value["paper_id"],
            "strategy": value["strategy_version_id"],
            "approval": value["approval_id"],
            "risk": value["risk_policy_id"],
            "start_date": date(2020, 1, 1),
            "assumption": assumption,
            "status": deployment_status,
            "now": now,
        },
    )
    if state is not None:
        PaperScheduler().transition_state(
            session,
            workspace_id=value["workspace_id"],
            paper_id=value["deployment_id"],
            to_state=state,
            now=watermark,
            actor_id="system",
            reason_code="SCHEDULER_STATE_INITIALIZED_NO_HISTORY",
            initialization=True,
        )
    session.commit()
    value.update(
        {
            "timezone": timezone,
            "due_time": due_time,
            "calendar": calendar,
            "watermark": watermark,
        }
    )
    return value


def _seed_gate_inputs(
    factory: sessionmaker[Session],
    deployment: dict[str, Any],
    trading_date: date,
    *,
    quality_status: str = "COMPLETED",
    result_state: str | None = "HEALTHY",
    stale_data_detected: bool | None = False,
) -> None:
    """Persist real snapshot/DataQuality inputs consumed by the worker gates."""

    session = factory()
    try:
        now = datetime.combine(trading_date, time(8), tzinfo=UTC)
        providers = Base.metadata.tables["data_providers"]
        datasets = Base.metadata.tables["datasets"]
        snapshots = Base.metadata.tables["dataset_snapshots"]
        quality_runs = Base.metadata.tables["data_quality_runs"]
        provider_id = uuid.uuid4()
        dataset_id = uuid.uuid4()
        quality_id = uuid.uuid4()
        snapshot_id = uuid.uuid4()
        session.execute(
            providers.insert().values(
                id=provider_id,
                workspace_id=deployment["workspace_id"],
                provider_id=f"fixture-{uuid.uuid4().hex[:12]}",
                adapter_key="fixture",
                display_name="scheduler fixture",
                status="CONNECTED",
                is_default=False,
                config={"version": "1"},
                credential_ref=None,
                last_tested_at=now,
                last_success_at=now,
                last_error_code=None,
                revision=1,
                created_at=now,
                updated_at=now,
            )
        )
        session.execute(
            datasets.insert().values(
                id=dataset_id,
                workspace_id=deployment["workspace_id"],
                dataset_id=new_id("DSSET"),
                provider_id=provider_id,
                name="scheduler fixture",
                kind="PRICE",
                asset_class="US_EQUITY",
                frequency="DAILY",
                schema_version=1,
                coverage_start=date(2020, 1, 1),
                coverage_end=trading_date,
                pit_semantics="VERIFIED",
                latest_partition_at=now,
                quality_state=result_state or "UNKNOWN",
                metadata={"fixture": True},
                revision=1,
                created_at=now,
                updated_at=now,
            )
        )
        manifest_job = JobRow(
            id=new_id("JOB"),
            workspace_id=deployment["workspace_id"],
            job_type="SNAPSHOT_CREATE",
            status="COMPLETED",
            revision=1,
            payload="{}",
            input_payload="{}",
            payload_sha256=content_hash({}),
            queue_name="core",
            priority=100,
            attempt=1,
            max_attempts=1,
            fencing_token=1,
            retry_safe=True,
            progress_mode="NONE",
            queued_at=now,
            started_at=now,
            finished_at=now,
            created_by_type="SYSTEM",
            created_by_id="scheduler-fixture",
        )
        session.add(manifest_job)
        session.flush()
        storage_key, digest = stage_json(
            session, {"snapshot": str(snapshot_id)}, object_key=new_id("ART")
        )
        publish_staged(session, storage_key, digest)
        manifest = ArtifactRow(
            artifact_id=new_id("ART"),
            workspace_id=deployment["workspace_id"],
            job_id=manifest_job.id,
            kind="JSON",
            media_type="application/json",
            storage_key=storage_key,
            size_bytes=64,
            sha256=digest,
            schema_name="snapshot_manifest",
            schema_version=1,
            metadata_json={"snapshot_id": str(snapshot_id)},
            publication_state="PUBLISHED",
            published_at=now,
            created_at=now,
            immutable=True,
        )
        session.add(manifest)
        session.flush()
        session.execute(
            quality_runs.insert().values(
                id=quality_id,
                workspace_id=deployment["workspace_id"],
                quality_run_id=new_id("DQ"),
                dataset_id=dataset_id,
                snapshot_id=None,
                status=quality_status,
                result_state=result_state,
                coverage_ratio=1,
                duplicate_rows=0,
                missing_sessions=0,
                lookahead_detected=False,
                survivorship_safe=True,
                stale_data_detected=stale_data_detected,
                checks=[],
                provenance_id=None,
                started_at=now,
                finished_at=now if quality_status == "COMPLETED" else None,
            )
        )
        session.execute(
            snapshots.insert().values(
                id=snapshot_id,
                workspace_id=deployment["workspace_id"],
                snapshot_id=new_id("DS"),
                dataset_id=dataset_id,
                snapshot_kind="PAPER",
                as_of_time=now,
                coverage_start=date(2020, 1, 1),
                coverage_end=trading_date,
                manifest_artifact_id=manifest.id,
                row_count=1,
                schema_sha256=content_hash({"schema": 1}),
                content_sha256=content_hash(
                    {"workspace": deployment["workspace_id"], "date": str(trading_date)}
                ),
                provider_metadata={"version": "1"},
                quality_run_id=quality_id,
                created_at=now,
                created_by_job_id=manifest_job.internal_id,
            )
        )
        session.execute(
            quality_runs.update()
            .where(quality_runs.c.id == quality_id)
            .values(snapshot_id=snapshot_id)
        )
        session.commit()
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


def _discover(
    factory: sessionmaker[Session],
    deployment: dict[str, Any],
    now: datetime,
    *,
    scheduler: PaperScheduler | None = None,
) -> int:
    session = factory()
    try:
        count = (scheduler or PaperScheduler()).discover(
            session,
            now=now,
            owner=deployment["owner_id"],
            workspace_id=deployment["workspace_id"],
        )
        session.commit()
        return count
    except BaseException:
        session.rollback()
        raise
    finally:
        session.close()


def _count(session: Session, table_name: str, workspace_id: str, **filters: Any) -> int:
    table = Base.metadata.tables[table_name]
    conditions = [table.c.workspace_id == workspace_id]
    conditions.extend(getattr(table.c, key) == value for key, value in filters.items())
    return int(
        session.scalar(select(func.count()).select_from(table).where(*conditions)) or 0
    )


def _prioritize_paper_job(
    factory: sessionmaker[Session], deployment: dict[str, Any]
) -> None:
    session = factory()
    try:
        session.execute(
            text(
                "UPDATE jobs j SET priority=0 FROM paper_daily_runs r "
                "WHERE r.job_id=j.id AND r.workspace_id=:workspace"
            ),
            {"workspace": deployment["workspace_id"]},
        )
        session.commit()
    finally:
        session.close()


class _FixtureCalendar(TradingCalendar):
    def __init__(self, closed: set[date]) -> None:
        self.closed = closed

    def is_trading_day(self, calendar_id: str, day: date) -> tuple[bool, str]:
        if calendar_id != "FIXTURE_CALENDAR":
            raise InvalidExecutionAssumption("calendar is unavailable")
        return day.weekday() < 5 and day not in self.closed, "fixture-v1"


def test_QF_PAPER_SCH_001_timezone_due_time_and_state_fail_closed(
    pg18_session_factory: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    """QF-PAPER-SCH-001: UTC/local due-time and prerequisite rejection."""

    deployment = _seed_deployment(
        pg18_session_factory(),
        uuid.uuid4().hex[:10],
        timezone="Asia/Tokyo",
        due_time="09:00",
        watermark=datetime(2026, 1, 8, 12, 0, tzinfo=UTC),
    )
    # The host TZ must not participate in trading-date derivation.
    monkeypatch.setenv("TZ", "Pacific/Honolulu")
    if hasattr(time_module, "tzset"):
        time_module.tzset()
    before = datetime(2026, 1, 8, 23, 59, tzinfo=UTC)
    after = datetime(2026, 1, 9, 0, 0, tzinfo=UTC)
    assert _discover(pg18_session_factory, deployment, before) == 0
    assert _discover(pg18_session_factory, deployment, after) == 1

    session = pg18_session_factory()
    try:
        run = session.execute(
            text(
                "SELECT trading_date FROM paper_daily_runs "
                "WHERE workspace_id=:workspace AND paper_id=:paper"
            ),
            {
                "workspace": deployment["workspace_id"],
                "paper": deployment["deployment_id"],
            },
        ).scalar_one()
        assert run == date(2026, 1, 9)
        missing_state = _seed_deployment(
            session,
            uuid.uuid4().hex[:10],
            watermark=datetime(2026, 1, 8, tzinfo=UTC),
            state=None,
        )
        session.commit()
        assert _discover(pg18_session_factory, missing_state, after) == 0
        mismatch = _seed_deployment(
            session, uuid.uuid4().hex[:10], watermark=datetime(2026, 1, 8, tzinfo=UTC)
        )
        session.execute(
            text("UPDATE paper_deployments SET status='PAUSED' WHERE id=:id"),
            {"id": mismatch["deployment_id"]},
        )
        session.commit()
        assert _discover(pg18_session_factory, mismatch, after) == 0
        with pytest.raises(InvalidExecutionAssumption):
            PaperScheduler()._candidate(  # noqa: SLF001 - acceptance of fail-closed boundary
                session,
                {
                    "workspace_id": deployment["workspace_id"],
                    "id": deployment["deployment_id"],
                },
                {"resume_watermark_utc": None},
                Schedule("Asia/Tokyo", time(9, 0), None),
                after,
            )
    finally:
        session.close()


def test_QF_PAPER_SCH_002_calendar_and_weekday_only(
    pg18_session_factory: sessionmaker[Session],
) -> None:
    """QF-PAPER-SCH-002: closed calendar dates and WEEKDAY_ONLY semantics."""

    baseline = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    closed_calendar = _seed_deployment(
        pg18_session_factory(),
        uuid.uuid4().hex[:10],
        calendar="FIXTURE_CALENDAR",
        watermark=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
    )
    weekday = _seed_deployment(
        pg18_session_factory(), uuid.uuid4().hex[:10], watermark=baseline
    )
    holiday = _seed_deployment(
        pg18_session_factory(),
        uuid.uuid4().hex[:10],
        calendar="FIXTURE_CALENDAR",
        watermark=datetime(2026, 1, 5, 8, 0, tzinfo=UTC),
    )
    unknown = _seed_deployment(
        pg18_session_factory(),
        uuid.uuid4().hex[:10],
        calendar="UNKNOWN_CALENDAR",
        watermark=baseline,
    )
    now = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
    calendar = _FixtureCalendar({date(2026, 1, 5)})
    # The Friday due instant is at/before the calendar deployment watermark;
    # Monday holiday therefore cannot turn into a Friday debt run.
    assert (
        _discover(
            pg18_session_factory,
            closed_calendar,
            now,
            scheduler=PaperScheduler(calendar),
        )
        == 0
    )
    assert (
        _discover(
            pg18_session_factory, holiday, now, scheduler=PaperScheduler(calendar)
        )
        == 0
    )
    assert (
        _discover(
            pg18_session_factory, unknown, now, scheduler=PaperScheduler(calendar)
        )
        == 0
    )
    assert _discover(pg18_session_factory, weekday, now) == 1

    session = pg18_session_factory()
    try:
        assert _count(session, "paper_daily_runs", closed_calendar["workspace_id"]) == 0
        assert _count(session, "paper_daily_runs", holiday["workspace_id"]) == 0
        assert _count(session, "paper_daily_runs", unknown["workspace_id"]) == 0
        assert session.execute(
            text(
                "SELECT trading_date FROM paper_daily_runs "
                "WHERE workspace_id=:workspace"
            ),
            {"workspace": weekday["workspace_id"]},
        ).scalar_one() == date(2026, 1, 5)
    finally:
        session.close()


def test_QF_PAPER_SCH_003_bounded_catchup_suppression_and_resume(
    pg18_session_factory: sessionmaker[Session],
) -> None:
    """QF-PAPER-SCH-003: one-day catch-up, no suppression debt, watermark resume."""

    old = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    catchup = _seed_deployment(
        pg18_session_factory(), uuid.uuid4().hex[:10], watermark=old
    )
    paused = _seed_deployment(
        pg18_session_factory(), uuid.uuid4().hex[:10], state="PAUSED", watermark=old
    )
    disabled = _seed_deployment(
        pg18_session_factory(), uuid.uuid4().hex[:10], state="DISABLED", watermark=old
    )
    monday_before_due = datetime(2026, 1, 5, 8, 0, tzinfo=UTC)
    assert _discover(pg18_session_factory, catchup, monday_before_due) == 1
    assert (
        _discover(pg18_session_factory, paused, datetime(2026, 1, 5, 10, 0, tzinfo=UTC))
        == 0
    )
    assert (
        _discover(
            pg18_session_factory, disabled, datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
        )
        == 0
    )

    session = pg18_session_factory()
    try:
        session.execute(
            text("SELECT COUNT(*) FROM paper_daily_runs WHERE workspace_id=:workspace"),
            {"workspace": catchup["workspace_id"]},
        ).scalar_one()
        dates = (
            session.execute(
                text(
                    "SELECT trading_date FROM paper_daily_runs WHERE workspace_id=:workspace"
                ),
                {"workspace": catchup["workspace_id"]},
            )
            .scalars()
            .all()
        )
        assert dates == [date(2026, 1, 2)]

        resume_at = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
        PaperScheduler().transition_state(
            session,
            workspace_id=paused["workspace_id"],
            paper_id=paused["deployment_id"],
            to_state="ACTIVE",
            now=resume_at,
            actor_id="system",
            reason_code="RESUME",
        )
        session.commit()
        resumed = session.execute(
            text(
                "SELECT resume_watermark_utc FROM paper_scheduler_states "
                "WHERE workspace_id=:workspace AND paper_id=:paper"
            ),
            {"workspace": paused["workspace_id"], "paper": paused["deployment_id"]},
        ).scalar_one()
        assert resumed == resume_at
    finally:
        session.close()
    assert (
        _discover(pg18_session_factory, paused, datetime(2026, 1, 5, 11, 0, tzinfo=UTC))
        == 0
    )
    assert (
        _discover(pg18_session_factory, paused, datetime(2026, 1, 6, 10, 0, tzinfo=UTC))
        == 1
    )


def test_QF_PAPER_SCH_004_natural_key_concurrency_and_workspace_isolation(
    pg18_session_factory: sessionmaker[Session],
) -> None:
    """QF-PAPER-SCH-004: concurrent wakeups converge per workspace natural key."""

    now = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
    first = _seed_deployment(
        pg18_session_factory(),
        uuid.uuid4().hex[:10],
        watermark=datetime(2026, 1, 1, tzinfo=UTC),
    )
    second = _seed_deployment(
        pg18_session_factory(),
        uuid.uuid4().hex[:10],
        watermark=datetime(2026, 1, 1, tzinfo=UTC),
    )

    def wake(value: dict[str, Any]) -> int:
        return _discover(pg18_session_factory, value, now)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(wake, [first] * 8))
    assert sorted(results) == [0] * 7 + [1]

    with ThreadPoolExecutor(max_workers=2) as pool:
        isolated_results = list(pool.map(wake, [second, second]))
    assert sorted(isolated_results) == [0, 1]
    session = pg18_session_factory()
    try:
        for deployment in (first, second):
            assert _count(session, "paper_daily_runs", deployment["workspace_id"]) == 1
            assert (
                _count(
                    session,
                    "jobs",
                    deployment["workspace_id"],
                    job_type="PAPER_DAILY_RUN",
                )
                == 1
            )
        assert (
            session.execute(
                text(
                    "SELECT COUNT(*) FROM paper_daily_runs r "
                    "JOIN jobs j ON j.id=r.job_id AND j.workspace_id=r.workspace_id "
                    "WHERE r.workspace_id=:workspace AND j.job_type='PAPER_DAILY_RUN'"
                ),
                {"workspace": first["workspace_id"]},
            ).scalar_one()
            == 1
        )
    finally:
        session.close()


def test_QF_PAPER_SCH_005_lease_fence_retry_crash_and_unknown_result(
    pg18_session_factory: sessionmaker[Session],
) -> None:
    """QF-PAPER-SCH-005: fenced lease takeover and review-required crash recovery."""

    from app.job_effects import apply_job_effect
    from workers.main import SimulatedWorkerCrash, run_once

    deployment = _seed_deployment(
        pg18_session_factory(),
        uuid.uuid4().hex[:10],
        watermark=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert (
        _discover(
            pg18_session_factory, deployment, datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
        )
        == 1
    )
    _seed_gate_inputs(pg18_session_factory, deployment, date(2026, 1, 5))
    _prioritize_paper_job(pg18_session_factory, deployment)
    claim_at = datetime(2026, 1, 5, 10, 1, tzinfo=UTC)
    first_session = pg18_session_factory()
    try:
        lease_a = claim_job(
            first_session, "core", "paper-worker-a", now=claim_at, lease_seconds=1
        )
        assert lease_a is not None
        first_session.commit()
    finally:
        first_session.close()

    reaper = pg18_session_factory()
    try:
        assert reap_expired_jobs(
            reaper, now=claim_at + timedelta(seconds=2), queue_name="core"
        ) == (1, 0)
        reaper.commit()
        retried_job = reaper.get(JobRow, lease_a.job_id)
        assert retried_job is not None
        assert retried_job.status == "QUEUED"
        assert retried_job.error_code == "JOB_LEASE_LOST"
        assert retried_job.queued_at == claim_at + timedelta(seconds=3)
        retry_artifacts = (
            reaper.execute(
                select(ArtifactRow).where(
                    ArtifactRow.workspace_id == deployment["workspace_id"],
                    ArtifactRow.schema_name == "paper_scheduler_evidence",
                )
            )
            .scalars()
            .all()
        )
        retry_evidence = [
            json.loads(
                (Path(os.environ["QF_ARTIFACT_DIR"]) / artifact.storage_key).read_text()
            )
            for artifact in retry_artifacts
        ]
        retry_transitions = {
            value["decision"]["transition"]: value for value in retry_evidence
        }
        assert {"LEASE_LOST", "RETRY_SCHEDULED"} <= set(retry_transitions)
        assert (
            retry_transitions["RETRY_SCHEDULED"]["job_lease"]["next_retry_at"]
            == "2026-01-05T10:01:03Z"
        )
        assert retry_transitions["RETRY_SCHEDULED"]["job_lease"]["lease_owner"] == (
            "paper-worker-a"
        )
    finally:
        reaper.close()

    second_session = pg18_session_factory()
    try:
        lease_b = claim_job(
            second_session,
            "core",
            "paper-worker-b",
            now=claim_at + timedelta(seconds=3),
            lease_seconds=60,
        )
        assert lease_b is not None
        second_session.commit()
    finally:
        second_session.close()

    stale = pg18_session_factory()
    try:
        stale_job = stale.get(JobRow, lease_a.job_id)
        assert stale_job is not None
        with pytest.raises(LostLease):
            complete_job(stale, lease_a, None, now=claim_at + timedelta(seconds=4))
        stale.rollback()
    finally:
        stale.close()

    execute_session = pg18_session_factory()
    try:
        job = execute_session.get(JobRow, lease_b.job_id)
        assert job is not None
        job = lock_active_lease(
            execute_session, lease_b, now=claim_at + timedelta(seconds=3)
        )
        apply_job_effect(execute_session, job)
        complete_job(
            execute_session, lease_b, None, now=claim_at + timedelta(seconds=3)
        )
        execute_session.commit()
    finally:
        execute_session.close()

    unknown = _seed_deployment(
        pg18_session_factory(),
        uuid.uuid4().hex[:10],
        watermark=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert (
        _discover(
            pg18_session_factory, unknown, datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
        )
        == 1
    )
    _seed_gate_inputs(pg18_session_factory, unknown, date(2026, 1, 5))
    mark = pg18_session_factory()
    try:
        mark.execute(
            text(
                "UPDATE jobs SET retry_safe=FALSE, priority=0 "
                "WHERE workspace_id=:workspace"
            ),
            {"workspace": unknown["workspace_id"]},
        )
        mark.commit()
    finally:
        mark.close()
    with pytest.raises(SimulatedWorkerCrash):
        run_once(identity="paper-worker-crash", crash_after_effects=True)
    recovery = pg18_session_factory()
    try:
        assert reap_expired_jobs(
            recovery, now=datetime.now(UTC) + timedelta(seconds=120), queue_name="core"
        ) == (0, 1)
        recovery.commit()
        row = recovery.execute(
            text("SELECT status FROM paper_daily_runs WHERE workspace_id=:workspace"),
            {"workspace": unknown["workspace_id"]},
        ).scalar_one()
        assert row == "FAILED"
        evidence = recovery.execute(
            text(
                "SELECT a.detail_artifact_id FROM audit_events a "
                "WHERE a.workspace_id=:workspace AND a.object_type='paper_run' "
                "ORDER BY a.sequence DESC LIMIT 1"
            ),
            {"workspace": unknown["workspace_id"]},
        ).scalar_one()
        assert evidence is not None
        transitions = {
            artifact.metadata_json["transition"]
            for artifact in recovery.execute(
                select(ArtifactRow).where(
                    ArtifactRow.workspace_id == unknown["workspace_id"],
                    ArtifactRow.schema_name == "paper_scheduler_evidence",
                )
            ).scalars()
        }
        assert {"LEASE_LOST", "RETRY_EXHAUSTED", "FAILED"} <= transitions
    finally:
        recovery.close()


def test_QF_PAPER_SCH_006_gates_and_terminal_runs_do_not_rerun(
    pg18_session_factory: sessionmaker[Session],
) -> None:
    """QF-PAPER-SCH-006: blocked/complete terminal rows suppress future work."""

    from workers.main import run_once

    now = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
    cases: list[tuple[str, dict[str, Any], dict[str, Any]]] = [
        ("DATA_QUALITY_BLOCKED", {}, {"result_state": "BLOCKED"}),
        ("STALE_DATA", {}, {"stale_data_detected": True}),
        ("PAPER_VERSION_MISMATCH", {"strategy_frozen": False}, {}),
        (
            "PAPER_RISK_BLOCKED",
            {"expected_turnover": 2, "risk_max_turnover": 1},
            {},
        ),
    ]
    for expected_reason, deployment_options, gate_options in cases:
        deployment = _seed_deployment(
            pg18_session_factory(),
            uuid.uuid4().hex[:10],
            watermark=datetime(2026, 1, 1, tzinfo=UTC),
            **deployment_options,
        )
        assert _discover(pg18_session_factory, deployment, now) == 1
        _seed_gate_inputs(
            pg18_session_factory,
            deployment,
            date(2026, 1, 5),
            **gate_options,
        )
        _prioritize_paper_job(pg18_session_factory, deployment)
        assert run_once(identity=f"paper-gate-{expected_reason}") == 1
        session = pg18_session_factory()
        try:
            status, reason = session.execute(
                text(
                    "SELECT status, block_reason_code FROM paper_daily_runs "
                    "WHERE workspace_id=:workspace"
                ),
                {"workspace": deployment["workspace_id"]},
            ).one()
            assert (status, reason) == ("BLOCKED", expected_reason)
            assert _count(session, "paper_orders", deployment["workspace_id"]) == 0
            assert (
                _count(
                    session,
                    "artifacts",
                    deployment["workspace_id"],
                    schema_name="paper_scheduler_evidence",
                )
                >= 2
            )
        finally:
            session.close()
        assert _discover(pg18_session_factory, deployment, now) == 0

    failed = _seed_deployment(
        pg18_session_factory(),
        uuid.uuid4().hex[:10],
        watermark=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert _discover(pg18_session_factory, failed, now) == 1
    _seed_gate_inputs(
        pg18_session_factory,
        failed,
        date(2026, 1, 5),
        quality_status="RUNNING",
        result_state=None,
        stale_data_detected=None,
    )
    _prioritize_paper_job(pg18_session_factory, failed)
    assert run_once(identity="paper-gate-unknown") == 1
    session = pg18_session_factory()
    try:
        assert session.execute(
            text(
                "SELECT r.status, j.status FROM paper_daily_runs r "
                "JOIN jobs j ON j.id=r.job_id WHERE r.workspace_id=:workspace"
            ),
            {"workspace": failed["workspace_id"]},
        ).one() == ("FAILED", "FAILED")
        assert _count(session, "paper_orders", failed["workspace_id"]) == 0
        latest_artifact = (
            session.execute(
                select(ArtifactRow)
                .where(
                    ArtifactRow.workspace_id == failed["workspace_id"],
                    ArtifactRow.schema_name == "paper_scheduler_evidence",
                )
                .order_by(ArtifactRow.created_at.desc())
            )
            .scalars()
            .first()
        )
        assert latest_artifact is not None
        evidence = json.loads(
            (
                Path(os.environ["QF_ARTIFACT_DIR"]) / latest_artifact.storage_key
            ).read_text()
        )
        assert evidence["review"] == {
            "review_required": True,
            "review_reason_code": "PAPER_DAILY_RUN_UNKNOWN_RESULT",
            "replay_disposition": "NO_AUTOMATIC_REPLAY",
        }
    finally:
        session.close()
    assert _discover(pg18_session_factory, failed, now) == 0
    assert _discover(pg18_session_factory, failed, now + timedelta(days=1)) == 1

    invalid = _seed_deployment(
        pg18_session_factory(),
        uuid.uuid4().hex[:10],
        timezone="Not/AZone",
        watermark=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert _discover(pg18_session_factory, invalid, now) == 0


def test_QF_PAPER_SCH_007_evidence_boundary_migration_and_closed_sse_negative(
    pg18_session_factory: sessionmaker[Session],
) -> None:
    """QF-PAPER-SCH-007: mutually exclusive state/execution evidence and closed SSE."""

    deployment = _seed_deployment(
        pg18_session_factory(),
        uuid.uuid4().hex[:10],
        watermark=datetime(2026, 1, 1, tzinfo=UTC),
    )
    session = pg18_session_factory()
    try:
        state_audits = (
            session.execute(
                select(Audit).where(
                    Audit.workspace_id == deployment["workspace_id"],
                    Audit.object_type == "paper",
                )
            )
            .scalars()
            .all()
        )
        assert state_audits
        for audit in state_audits:
            summary = json.loads(str(audit.payload))
            assert set(summary) == EXPECTED_STATE_KEYS
            assert audit.detail_artifact_id is None
        assert _count(session, "jobs", deployment["workspace_id"]) == 0
        assert _count(session, "artifacts", deployment["workspace_id"]) == 0
    finally:
        session.close()

    assert (
        _discover(
            pg18_session_factory, deployment, datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
        )
        == 1
    )
    _seed_gate_inputs(pg18_session_factory, deployment, date(2026, 1, 5))
    _prioritize_paper_job(pg18_session_factory, deployment)
    from workers.main import run_once

    assert run_once(identity="paper-evidence-worker") == 1
    session = pg18_session_factory()
    try:
        audit = session.execute(
            select(Audit)
            .where(
                Audit.workspace_id == deployment["workspace_id"],
                Audit.object_type == "paper_run",
            )
            .order_by(Audit.sequence.desc())
            .limit(1)
        ).scalar_one()
        assert audit.detail_artifact_id is not None
        artifact = session.get(ArtifactRow, audit.detail_artifact_id)
        assert artifact is not None
        job = session.execute(
            select(JobRow).where(JobRow.id == artifact.job_id)
        ).scalar_one()
        assert job.workspace_id == deployment["workspace_id"]
        assert job.job_type == "PAPER_DAILY_RUN"
        evidence = json.loads(
            (Path(os.environ["QF_ARTIFACT_DIR"]) / artifact.storage_key).read_text()
        )
        assert set(evidence) == EXPECTED_EVIDENCE_SECTIONS
        assert evidence["identity"]["workspace_id"] == deployment["workspace_id"]
        assert (
            evidence["identity"]["idempotency_locator"]["trading_date"] == "2026-01-05"
        )
        assert evidence["job_lease"]["job_id"] == job.id

        events = (
            session.execute(
                select(Event).where(
                    Event.workspace_id == deployment["workspace_id"],
                    Event.object_type == "paper",
                )
            )
            .scalars()
            .all()
        )
        assert events
        for event in events:
            payload = json.loads(str(event.payload))
            assert set(payload) <= {"state", "status"}
            assert "resume_watermark_utc" not in payload
    finally:
        session.close()

    with pytest.raises(ValidationError):
        validate_event_payload(
            {"state": "ACTIVE", "status": "ACTIVE", "resume_watermark_utc": "secret"}
        )
    with pytest.raises(ValidationError):
        validate_sse_envelope(
            {
                "schema_version": 1,
                "event_id": new_id("EVT"),
                "sequence": 1,
                "event_type": "paper.updated",
                "occurred_at": "2026-01-05T10:00:00Z",
                "object_type": "paper",
                "object_id": deployment["paper_id"],
                "object_version": None,
                "object_revision": 2,
                "request_id": new_id("REQ"),
                "job_id": None,
                "agent_run_id": None,
                "tool_call_id": None,
                "payload": {
                    "state": "ACTIVE",
                    "status": "ACTIVE",
                    "paper_scheduler_evidence": "forbidden",
                },
            }
        )
