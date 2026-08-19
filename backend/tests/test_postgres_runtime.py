"""Real PostgreSQL locking, migration and immutable-trigger gate."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path

import psycopg
import pytest
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from alembic import command
from quantfoundry.api.app import (
    Actor,
    ApprovalRow,
    Audit,
    AuditChainHead,
    CostModelVersionRow,
    JobRow,
    Record,
    ResearchPolicyVersionRow,
    ResearchRow,
    StrategyRow,
    StrategyVersionRow,
    User,
    ValidationRow,
    Workspace,
    approval_prerequisites,
    content_hash,
    decide,
    emit,
    strategy_storage_fields,
)
from quantfoundry.infrastructure.jobs.queue import (
    LostLease,
    claim_job,
    complete_job,
    heartbeat_job,
    lock_active_lease,
    reap_expired_jobs,
)


def _run_migration(database_url: str, revision: str) -> None:
    previous = os.environ.get("QF_ALEMBIC_URL")
    os.environ["QF_ALEMBIC_URL"] = database_url
    try:
        root = Path(__file__).resolve().parents[1]
        config = Config(str(root / "alembic.ini"))
        config.set_main_option("script_location", str(root / "alembic"))
        command.upgrade(config, revision)
    finally:
        if previous is None:
            os.environ.pop("QF_ALEMBIC_URL", None)
        else:
            os.environ["QF_ALEMBIC_URL"] = previous


def _job(job_id: str, priority: int, queued_at: datetime, workspace_id: str) -> JobRow:
    wire = {
        "job_id": job_id,
        "job_type": "DATASET_VALIDATE",
        "status": "QUEUED",
        "progress": {
            "mode": "NONE",
            "completed_units": None,
            "total_units": None,
            "unit": None,
            "percent": None,
            "current_step_key": None,
            "current_step_label": None,
        },
        "error_code": None,
        "result_ref": None,
        "revision": 1,
        "queued_at": queued_at.isoformat(),
        "started_at": None,
        "finished_at": None,
        "last_updated_at": queued_at.isoformat(),
    }
    return JobRow(
        id=job_id,
        workspace_id=workspace_id,
        job_type="DATASET_VALIDATE",
        status="QUEUED",
        revision=1,
        payload=json.dumps(wire),
        input_payload="{}",
        payload_sha256=content_hash({}),
        queue_name="pg-claim",
        priority=priority,
        attempt=0,
        max_attempts=3,
        fencing_token=0,
        retry_safe=True,
        progress_mode="NONE",
        queued_at=queued_at,
        created_by_type="SYSTEM",
        created_by_id="pg-test",
        correlation_id=job_id,
    )


def test_postgres_migration_skip_locked_and_immutable_trigger() -> None:
    with psycopg.connect("dbname=postgres") as check:
        server_version = int(check.execute("SHOW server_version_num").fetchone()[0])
    if os.getenv("QF_REQUIRE_PG18") == "1":
        assert server_version >= 180000, "PG18 CI gate requires PostgreSQL 18+"

    database = f"qf_runtime_{uuid.uuid4().hex}"
    with psycopg.connect("dbname=postgres", autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{database}"')
    url = f"postgresql+psycopg:///{database}"
    engine = create_engine(url)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        _run_migration(url, "head")
        session = sessions()
        suffix = uuid.uuid4().hex
        public_uuid = uuid.uuid4()
        research_id = f"RSCH-{public_uuid}"
        strategy_id = f"STRAT-{public_uuid}"
        version_id = f"SV-{suffix}"
        workspace_id = str(uuid.uuid4())
        owner_id = f"owner-{suffix}"
        now = datetime.now(UTC)
        session.add(
            User(
                id=owner_id,
                email=f"{owner_id}@test.invalid",
                role="OWNER",
                revision=1,
            )
        )
        session.flush()
        session.add(
            Workspace(
                id=workspace_id,
                owner_id=owner_id,
                name="PG runtime test",
                revision=1,
            )
        )
        session.flush()
        session.add_all(
            [
                ResearchPolicyVersionRow(
                    id=f"policy-runtime:{suffix}",
                    workspace_id=workspace_id,
                    policy_id=f"RP-{public_uuid}",
                    version=1,
                    status="ACTIVE",
                    rules={},
                    max_research_steps=25,
                    max_tool_calls=50,
                    content_sha256=content_hash({"policy": suffix}),
                    created_by=owner_id,
                    created_at=now,
                    activated_at=now,
                ),
                CostModelVersionRow(
                    id=f"cost-runtime:{suffix}",
                    workspace_id=workspace_id,
                    cost_model_id=f"COST-{public_uuid}",
                    version=1,
                    status="ACTIVE",
                    commission_model={"type": "BPS", "value": 1},
                    slippage_model={"type": "BPS", "value": 2},
                    rebalance_timing="NEXT_OPEN",
                    fill_assumption="NEXT_OPEN",
                    content_sha256=content_hash({"cost": suffix}),
                    created_at=now,
                    activated_at=now,
                ),
            ]
        )
        session.flush()
        session.add(
            ResearchRow(
                id=research_id,
                workspace_id=workspace_id,
                status="DRAFT",
                revision=1,
                title="PG immutable",
                original_user_prompt="PG immutable",
                created_at=now,
                updated_at=now,
                detail="{}",
            )
        )
        session.add(
            StrategyRow(
                id=strategy_id,
                workspace_id=workspace_id,
                research_id=research_id,
                name="PG immutable",
                revision=1,
                detail="{}",
            )
        )
        strategy_detail = {
            "strategy_id": strategy_id,
            "name": "PG immutable",
            "thesis": "A deterministic PostgreSQL strategy",
            "universe": {
                "asset_class": "EQUITY",
                "symbols": [],
                "universe_id": "TEST",
            },
            "signals": [],
            "rules": {
                "selection_count": 1,
                "weighting": "EQUAL",
                "rebalance_frequency": "DAILY",
                "long_short": False,
                "leverage_limit": "1",
                "position_limit": "1",
            },
            "cost_model_id": f"COST-{public_uuid}",
            "benchmark": "TEST",
            "research_period": {"start": "2020-01-01", "end": "2020-06-30"},
            "validation_period": {"start": "2020-07-01", "end": "2020-09-30"},
            "holdout_period": {"start": "2020-10-01", "end": "2020-12-31"},
            "known_failure_modes": [],
        }
        session.add(
            StrategyVersionRow(
                id=version_id,
                workspace_id=workspace_id,
                strategy_id=strategy_id,
                version=1,
                state="FROZEN",
                spec_sha256=content_hash({"strategy": suffix}),
                frozen_at=datetime.now(UTC),
                revision=2,
                detail=json.dumps(strategy_detail),
                **strategy_storage_fields(
                    strategy_detail, lifecycle_state="FROZEN", is_frozen=True
                ),
            )
        )
        validation_id = f"VAL-{public_uuid}"
        session.add(
            ValidationRow(
                id=validation_id,
                workspace_id=workspace_id,
                strategy_version_id=version_id,
                status="WAITING_HOLDOUT",
                holdout_state="LOCKED",
                exposure_count=0,
                revision=1,
                detail='{"result":"PASS"}',
            )
        )
        first_id = f"JOB-{uuid.uuid4()}"
        second_id = f"JOB-{uuid.uuid4()}"
        session.add_all(
            [
                _job(first_id, 10, now, workspace_id),
                _job(second_id, 20, now, workspace_id),
            ]
        )
        session.add(
            Record(
                record_key=f"ART-{public_uuid}",
                workspace_id=workspace_id,
                kind="artifact",
                body='{"content_sha256":"immutable"}',
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
        session.close()

        barrier = threading.Barrier(2)

        def claim(identity: str) -> str:
            worker_session = sessions()
            try:
                barrier.wait()
                lease = claim_job(worker_session, "pg-claim", identity)
                assert lease is not None
                time.sleep(0.1)
                worker_session.commit()
                return lease.job_id
            finally:
                worker_session.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            claimed = set(pool.map(claim, ["pg-worker-a", "pg-worker-b"]))
        assert claimed == {first_id, second_id}

        stale_id = f"JOB-{uuid.uuid4()}"
        session = sessions()
        session.add(_job(stale_id, 0, now, workspace_id))
        session.commit()
        session.close()
        lease_started = datetime.now(UTC)
        session = sessions()
        stale_lease = claim_job(
            session,
            "pg-claim",
            "pg-stale-worker",
            now=lease_started,
            lease_seconds=1,
        )
        assert stale_lease is not None and stale_lease.job_id == stale_id
        session.commit()
        session.close()

        stale_effect_id = f"ART-{uuid.uuid4()}"
        stale_session = sessions()
        lock_active_lease(
            stale_session,
            stale_lease,
            now=lease_started + timedelta(milliseconds=500),
        )
        stale_session.add(
            Record(
                record_key=stale_effect_id,
                workspace_id=workspace_id,
                kind="artifact",
                body="{}",
                created_at=lease_started,
                updated_at=lease_started,
            )
        )
        stale_session.flush()
        reaper_session = sessions()
        assert reap_expired_jobs(
            reaper_session,
            now=lease_started + timedelta(seconds=2),
            queue_name="pg-claim",
        ) == (0, 0)
        reaper_session.commit()
        reaper_session.close()
        with pytest.raises(LostLease):
            complete_job(
                stale_session,
                stale_lease,
                {"stale": True},
                now=lease_started + timedelta(seconds=2),
            )
        stale_session.rollback()
        stale_session.close()
        verification = sessions()
        assert (
            verification.execute(
                select(Record).where(
                    Record.workspace_id == workspace_id,
                    Record.record_key == stale_effect_id,
                )
            ).scalar_one_or_none()
            is None
        )
        assert reap_expired_jobs(
            verification,
            now=lease_started + timedelta(seconds=2),
            queue_name="pg-claim",
        ) == (1, 0)
        verification.commit()
        replacement = claim_job(
            verification,
            "pg-claim",
            "pg-replacement-worker",
            now=lease_started + timedelta(seconds=2),
        )
        assert replacement is not None and replacement.job_id == stale_id
        assert replacement.fencing_token == stale_lease.fencing_token + 1
        verification.commit()
        with pytest.raises(LostLease):
            heartbeat_job(
                verification,
                stale_lease,
                now=lease_started + timedelta(seconds=2),
            )
        verification.rollback()
        verification.close()

        concurrency_uuid = uuid.uuid4()
        concurrency_strategy_id = f"STRAT-{concurrency_uuid}"
        concurrency_version_id = f"SV-X{suffix}"
        concurrency_validation_id = f"VAL-{concurrency_uuid}"
        concurrency_approval_id = f"APR-{concurrency_uuid}"
        concurrency_spec_sha256 = content_hash({"concurrent": suffix})
        concurrency_detail = {
            "strategy_id": concurrency_strategy_id,
            "name": "PG concurrency",
            "thesis": "A deterministic PostgreSQL strategy",
            "universe": {
                "asset_class": "EQUITY",
                "symbols": [],
                "universe_id": "TEST",
            },
            "signals": [],
            "rules": {
                "selection_count": 1,
                "weighting": "EQUAL",
                "rebalance_frequency": "DAILY",
                "long_short": False,
                "leverage_limit": "1",
                "position_limit": "1",
            },
            "cost_model_id": f"COST-{public_uuid}",
            "benchmark": "TEST",
            "research_period": {"start": "2020-01-01", "end": "2020-06-30"},
            "validation_period": {"start": "2020-07-01", "end": "2020-09-30"},
            "holdout_period": {"start": "2020-10-01", "end": "2020-12-31"},
            "known_failure_modes": [],
        }
        session = sessions()
        session.add(
            StrategyRow(
                id=concurrency_strategy_id,
                workspace_id=workspace_id,
                research_id=research_id,
                name="PG concurrency",
                revision=1,
                detail="{}",
            )
        )
        session.add(
            StrategyVersionRow(
                id=concurrency_version_id,
                workspace_id=workspace_id,
                strategy_id=concurrency_strategy_id,
                version=1,
                state="VALIDATED",
                spec_sha256=concurrency_spec_sha256,
                frozen_at=now,
                revision=4,
                detail=json.dumps(concurrency_detail),
                **strategy_storage_fields(
                    concurrency_detail, lifecycle_state="VALIDATED", is_frozen=True
                ),
            )
        )
        session.flush()
        session.add(
            ValidationRow(
                id=concurrency_validation_id,
                workspace_id=workspace_id,
                strategy_version_id=concurrency_version_id,
                status="WAITING_HOLDOUT",
                holdout_state="LOCKED",
                exposure_count=0,
                revision=2,
                detail='{"result":"PASS"}',
            )
        )
        session.flush()
        concurrency_validation = session.get(ValidationRow, concurrency_validation_id)
        concurrency_strategy = session.get(StrategyVersionRow, concurrency_version_id)
        assert concurrency_validation is not None and concurrency_strategy is not None
        prerequisites = approval_prerequisites(
            session, concurrency_validation, concurrency_strategy
        )
        prerequisites_sha256 = content_hash(prerequisites)
        subject_sha256 = content_hash(
            {
                "subject_type": "validation",
                "subject_id": concurrency_validation_id,
                "subject_version": 1,
                "subject_revision": 2,
                "strategy_version_id": concurrency_version_id,
                "strategy_spec_sha256": concurrency_spec_sha256,
                "prerequisites_sha256": prerequisites_sha256,
            }
        )
        requested_at = now.isoformat().replace("+00:00", "Z")
        session.add(
            ApprovalRow(
                id=concurrency_approval_id,
                workspace_id=workspace_id,
                validation_id=concurrency_validation_id,
                status="PENDING",
                subject_sha256=subject_sha256,
                subject_type="VALIDATION",
                subject_id=concurrency_validation_id,
                subject_version=1,
                subject_revision=2,
                subject_spec_sha256=concurrency_spec_sha256,
                prerequisites_sha256=prerequisites_sha256,
                revision=1,
                detail=json.dumps(
                    {
                        "approval_id": concurrency_approval_id,
                        "type": "HOLDOUT_UNLOCK",
                        "subject": {
                            "type": "VALIDATION",
                            "id": concurrency_validation_id,
                            "version": 1,
                            "revision": 2,
                            "sha256": subject_sha256,
                        },
                        "requester": {"type": "OWNER", "id": "pg-owner"},
                        "status": "PENDING",
                        "reason": "Concurrent approval proof",
                        "prerequisites": prerequisites,
                        "risk_summary": {
                            "risk_level": "HIGH",
                            "warning_codes": [],
                        },
                        "effects": [
                            {
                                "code": "HOLDOUT_UNLOCK",
                                "detail": "Allows one controlled holdout run",
                            }
                        ],
                        "revision": 1,
                        "requested_at": requested_at,
                        "decided_at": None,
                        "action_capabilities": [],
                    }
                ),
            )
        )
        session.flush()
        session.execute(
            text(
                "UPDATE validations SET holdout_state='APPROVAL_PENDING' WHERE id=:id"
            ),
            {"id": concurrency_validation_id},
        )
        session.commit()
        session.close()
        approval_barrier = threading.Barrier(2)

        def approve_concurrently(request_id: str) -> int:
            decision_session = sessions()
            decision_session.info.update(
                {
                    "actor_id": "pg-owner",
                    "workspace_id": workspace_id,
                    "request_id": request_id,
                }
            )
            try:
                approval_barrier.wait()
                status, _payload = decide(
                    concurrency_approval_id,
                    {"acknowledged_subject_sha256": subject_sha256},
                    f'W/"{concurrency_approval_id}:1"',
                    decision_session,
                    "APPROVED",
                    f"/approvals/{concurrency_approval_id}/approve",
                    Actor("pg-owner", workspace_id, "OWNER", request_id),
                )
                decision_session.commit()
                return status
            except HTTPException as error:
                decision_session.rollback()
                return error.status_code
            finally:
                decision_session.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            decision_statuses = sorted(
                pool.map(approve_concurrently, ["REQ-approve-a", "REQ-approve-b"])
            )
        assert decision_statuses == [200, 409]
        session = sessions()
        resolved = session.get(ApprovalRow, concurrency_approval_id)
        assert resolved is not None and resolved.status == "APPROVED"
        assert (
            session.query(Audit)
            .filter_by(object_type="approval", object_id=concurrency_approval_id)
            .count()
            == 1
        )
        session.close()

        chain_workspace = workspace_id
        session = sessions()
        starting_head = session.get(AuditChainHead, chain_workspace)
        starting_hash = starting_head.event_sha256 if starting_head else None
        session.close()

        def append_chain(index: int) -> None:
            chain_session = sessions()
            chain_session.info.update(
                {
                    "actor_id": f"actor-{index}",
                    "workspace_id": chain_workspace,
                    "request_id": f"REQ-chain-{index}",
                }
            )
            try:
                emit(
                    chain_session,
                    "event_stream",
                    f"EVT-{uuid.uuid4()}",
                    1,
                    "system.health.updated",
                )
                chain_session.commit()
            finally:
                chain_session.close()

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(append_chain, range(8)))
        session = sessions()
        chain_rows = (
            session.query(Audit)
            .filter(
                Audit.workspace_id == chain_workspace,
                Audit.object_type == "event_stream",
            )
            .all()
        )
        assert len(chain_rows) == 8
        current_hash = starting_hash
        remaining = list(chain_rows)
        while remaining:
            matches = [row for row in remaining if row.previous_sha256 == current_hash]
            assert len(matches) == 1
            current_hash = matches[0].event_sha256
            remaining.remove(matches[0])
        final_head = session.get(AuditChainHead, chain_workspace)
        assert final_head is not None and final_head.event_sha256 == current_hash
        session.close()

        session = sessions()
        with pytest.raises(DBAPIError):
            session.execute(
                text("UPDATE strategy_versions SET spec_sha256=:sha WHERE id=:id"),
                {"sha": "f" * 64, "id": version_id},
            )
        session.rollback()
        with pytest.raises(DBAPIError):
            session.execute(
                text("UPDATE records SET body='changed' WHERE record_key=:id"),
                {"id": f"ART-{public_uuid}"},
            )
        session.rollback()
        with pytest.raises(DBAPIError):
            session.execute(
                text(
                    "UPDATE validations SET holdout_state='EXPOSED', exposure_count=1 "
                    "WHERE id=:id"
                ),
                {"id": validation_id},
            )
        session.rollback()
        session.close()
    finally:
        engine.dispose()
        with psycopg.connect("dbname=postgres", autocommit=True) as admin:
            admin.execute(
                f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{database}'"
            )
            admin.execute(f'DROP DATABASE IF EXISTS "{database}"')
