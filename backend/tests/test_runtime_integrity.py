"""Negative and crash tests for durable runtime invariants."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import threading
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import ValidationError
from sqlalchemy import create_engine, func, select, text
from sqlalchemy import event as sqlalchemy_event
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from quantfoundry.adapters.provider.local import LocalProviderServer, create_server
from quantfoundry.agents.runtime.runtime import (
    REGISTRY,
    AgentRuntimeError,
    AgentStep,
    OpenAICompatibleModel,
    RemoteCodexModel,
    ToolPolicyDenied,
    advance_agent_run,
)
from quantfoundry.api.app import (
    AgentConfigRow,
    AgentRunRow,
    ApprovalRow,
    ArtifactRow,
    Audit,
    Base,
    DataSource,
    Event,
    EventStreamWatermark,
    ExperimentRow,
    HoldoutExposureRow,
    JobDependencyRow,
    JobRow,
    Record,
    ResearchPolicyVersionRow,
    ResearchRow,
    SessionLocal,
    SnapshotPartitionRow,
    SnapshotRow,
    StrategyRow,
    StrategyVersionRow,
    ToolCallRow,
    User,
    ValidationRow,
    Workspace,
    app,
    content_hash,
    create_provenance,
    job,
)
from quantfoundry.api.sse.stream import durable_event_stream
from quantfoundry.contracts.events.locator import register_sqlite_functions
from quantfoundry.infrastructure.artifacts.store import (
    read_json,
    reap_orphan_artifacts,
    stage_json,
)
from quantfoundry.infrastructure.jobs.queue import (
    JobNotCancellable,
    LostLease,
    claim_job,
    complete_job,
    heartbeat_job,
    reap_expired_jobs,
    request_cancellation,
)
from quantfoundry.scheduler.main import probe_artifact_store
from quantfoundry.scheduler.main import run_once as run_scheduler_once
from quantfoundry.workers.main import (
    SimulatedWorkerCrash,
    cleanup_expired_events,
    run_agent_once,
    run_once,
)

AUTH = {"Authorization": "Bearer test"}


def _key(label: str) -> dict[str, str]:
    return AUTH | {"Idempotency-Key": f"integrity-{label}-{uuid.uuid4()}"}


class LocalProviderHarness:
    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.monkeypatch = monkeypatch
        self.servers: list[tuple[LocalProviderServer, threading.Thread]] = []

    def start(
        self,
        actions: list[dict[str, object]],
        *,
        failure_statuses: list[int] | None = None,
    ) -> LocalProviderServer:
        api_key = "agent-provider-credential"
        server = create_server(
            "127.0.0.1",
            0,
            actions=actions,
            api_key=api_key,
            model_name="test-model",
            failure_statuses=failure_statuses,
        )
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.servers.append((server, thread))
        host, port = server.server_address
        self.monkeypatch.setenv("QF_OPENAI_BASE_URL", f"http://{host}:{port}/v1")
        self.monkeypatch.setenv("QF_OPENAI_API_KEY", api_key)
        return server

    def close(self) -> None:
        for server, thread in self.servers:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


@pytest.fixture
def local_provider(monkeypatch: pytest.MonkeyPatch) -> LocalProviderHarness:
    harness = LocalProviderHarness(monkeypatch)
    try:
        yield harness
    finally:
        harness.close()


def _assert_integrity(statement: str, parameters: dict[str, str]) -> None:
    session = SessionLocal()
    try:
        with pytest.raises(DBAPIError):
            session.execute(text(statement), parameters)
        session.rollback()
    finally:
        session.close()


def _seed_strategy_version(
    session: Session,
    suffix: str,
    *,
    state: str = "FROZEN",
    spec_sha256: str | None = None,
    detail: str | None = None,
) -> tuple[str, str, str]:
    research_id = f"RSCH-{suffix}"
    strategy_id = f"STRAT-{suffix}"
    strategy_version_id = f"SV-{suffix}"
    session.add(
        ResearchRow(
            id=research_id,
            workspace_id="test-workspace",
            status="DRAFT",
            revision=1,
            title="Runtime integrity fixture",
            detail="{}",
        )
    )
    session.flush()
    session.add(
        StrategyRow(
            id=strategy_id,
            workspace_id="test-workspace",
            research_id=research_id,
            revision=1,
            detail="{}",
        )
    )
    session.flush()
    session.add(
        StrategyVersionRow(
            id=strategy_version_id,
            workspace_id="test-workspace",
            strategy_id=strategy_id,
            version=1,
            state=state,
            spec_sha256=spec_sha256 or content_hash({"strategy": suffix}),
            frozen_at=datetime.now(UTC),
            revision=2,
            detail=detail
            or json.dumps(
                {
                    "cost_model_id": "COST-00000000-0000-4000-8000-000000000003",
                    "research_period": {
                        "start": "2020-01-01",
                        "end": "2020-06-30",
                    },
                    "validation_period": {
                        "start": "2020-07-01",
                        "end": "2020-09-30",
                    },
                    "holdout_period": {
                        "start": "2020-10-01",
                        "end": "2020-12-31",
                    },
                }
            ),
        )
    )
    session.flush()
    return research_id, strategy_id, strategy_version_id


def test_database_rejects_changes_to_all_immutable_evidence() -> None:
    suffix = str(uuid.uuid4())
    now = datetime.now(UTC)
    session = SessionLocal()
    session.info.update(
        actor_id="test-owner",
        workspace_id="test-workspace",
        request_id=f"REQ-{suffix}",
    )
    session.add(
        ResearchRow(
            id=f"RSCH-{suffix}",
            workspace_id="test-workspace",
            status="DRAFT",
            revision=1,
            title="Immutable evidence parent",
            detail="{}",
        )
    )
    session.add(
        StrategyRow(
            id=f"STRAT-{suffix}",
            workspace_id="test-workspace",
            research_id=f"RSCH-{suffix}",
            revision=1,
            detail="{}",
        )
    )
    accepted = job(session, "HOLDOUT_RUN", input_payload={"fixture": suffix})
    session.flush()
    manifest_artifact_id = f"ART-{uuid.uuid4()}"
    session.add(
        ArtifactRow(
            artifact_id=manifest_artifact_id,
            workspace_id="test-workspace",
            job_id=accepted["job_id"],
            kind="dataset_snapshot_manifest",
            media_type="application/json",
            storage_backend="LOCAL",
            storage_key=f"test/{manifest_artifact_id}.json",
            size_bytes=2,
            sha256=content_hash({}),
            metadata_json={"fixture": suffix},
            publication_state="PUBLISHED",
            created_at=now,
            published_at=now,
            immutable=True,
        )
    )
    session.flush()
    provider_id = uuid.uuid4()
    dataset_internal_id = uuid.uuid4()
    snapshot_internal_id = uuid.uuid4()
    session.execute(
        Base.metadata.tables["data_providers"]
        .insert()
        .values(
            id=provider_id,
            workspace_id="test-workspace",
            provider_id=f"provider-{provider_id.hex[:20]}",
            adapter_key="test-immutable",
            display_name="Immutable test provider",
            status="CONNECTED",
            is_default=False,
            config={"fixture": suffix},
            revision=1,
            created_at=now,
            updated_at=now,
        )
    )
    session.execute(
        Base.metadata.tables["datasets"]
        .insert()
        .values(
            id=dataset_internal_id,
            workspace_id="test-workspace",
            dataset_id=f"DSSET-{suffix}",
            provider_id=provider_id,
            name="Immutable test dataset",
            kind="PRICE",
            asset_class="EQUITY",
            schema_version=1,
            pit_semantics="VERIFIED",
            quality_state="HEALTHY",
            metadata={"fixture": suffix},
            revision=1,
            created_at=now,
            updated_at=now,
        )
    )
    session.execute(
        Base.metadata.tables["dataset_snapshots"]
        .insert()
        .values(
            id=snapshot_internal_id,
            workspace_id="test-workspace",
            snapshot_id=f"DS-{suffix}",
            dataset_id=dataset_internal_id,
            snapshot_kind="RESEARCH",
            as_of_time=now,
            coverage_start=now.date(),
            coverage_end=now.date(),
            manifest_artifact_id=session.query(ArtifactRow)
            .filter_by(artifact_id=manifest_artifact_id)
            .one()
            .id,
            schema_sha256=content_hash({"schema": suffix}),
            content_sha256=content_hash({"snapshot": suffix}),
            provider_metadata={"fixture": suffix},
            created_at=now,
        )
    )
    session.add(
        SnapshotRow(
            id=f"DS-{suffix}",
            workspace_id="test-workspace",
            dataset_id=f"DSSET-{suffix}",
            content_sha256=content_hash({"snapshot": suffix}),
            immutable=True,
            revision=1,
            detail="{}",
        )
    )
    session.add(
        ExperimentRow(
            id=f"EXP-{suffix}",
            workspace_id="test-workspace",
            research_id=f"RSCH-{suffix}",
            immutable=True,
            revision=2,
            detail=json.dumps(
                {
                    "data_snapshot_id": f"DS-{suffix}",
                    "cost_model_id": "COST-00000000-0000-4000-8000-000000000003",
                }
            ),
        )
    )
    session.add(
        StrategyVersionRow(
            id=f"SV-{suffix}",
            workspace_id="test-workspace",
            strategy_id=f"STRAT-{suffix}",
            version=1,
            state="FROZEN",
            spec_sha256=content_hash({"strategy": suffix}),
            frozen_at=now,
            revision=2,
            detail=json.dumps(
                {
                    "cost_model_id": "COST-00000000-0000-4000-8000-000000000003",
                    "research_period": {
                        "start": "2020-01-01",
                        "end": "2020-06-30",
                    },
                    "validation_period": {
                        "start": "2020-07-01",
                        "end": "2020-09-30",
                    },
                    "holdout_period": {
                        "start": "2020-10-01",
                        "end": "2020-12-31",
                    },
                }
            ),
        )
    )
    session.flush()
    session.add(
        SnapshotPartitionRow(
            id=f"SPART-{suffix}",
            snapshot_id=f"DS-{suffix}",
            partition="PUBLIC",
            artifact_id=f"ART-{uuid.uuid4()}",
            content_sha256=content_hash({"partition": suffix}),
            row_count=1,
            created_at=now,
        )
    )
    session.add(
        ValidationRow(
            id=f"VAL-{suffix}",
            workspace_id="test-workspace",
            strategy_version_id=f"SV-{suffix}",
            status="WAITING_HOLDOUT",
            holdout_state="LOCKED",
            exposure_count=0,
            revision=1,
            detail='{"result":"PASS"}',
        )
    )
    session.flush()
    validation_row = session.get(ValidationRow, f"VAL-{suffix}")
    strategy_version = session.get(StrategyVersionRow, f"SV-{suffix}")
    validation_policy = (
        session.query(ResearchPolicyVersionRow)
        .filter_by(workspace_id="test-workspace", status="ACTIVE")
        .first()
    )
    holdout_job = session.get(JobRow, accepted["job_id"])
    assert (
        validation_row is not None
        and strategy_version is not None
        and validation_policy is not None
        and holdout_job is not None
    )
    session.execute(
        Base.metadata.tables["validation_runs"]
        .insert()
        .values(
            id=uuid.uuid4(),
            workspace_id="test-workspace",
            validation_id=validation_row.id,
            strategy_version_id=strategy_version.internal_id,
            policy_id=validation_policy.internal_id,
            strict_engine_key="test-immutable",
            strict_engine_version="1.0.0",
            status="WAITING_HOLDOUT",
            result="PASS",
            test_suite_version="1.0.0",
            test_plan=[{"fixture": suffix}],
            warnings=[],
            failures=[],
            holdout_state="LOCKED",
            job_id=holdout_job.internal_id,
            revision=1,
            created_at=now,
        )
    )
    approval_detail = {
        "approval_id": f"APR-{suffix}",
        "type": "HOLDOUT_UNLOCK",
        "subject": {
            "type": "validation",
            "id": validation_row.id,
            "version": 1,
            "revision": 1,
            "sha256": content_hash({"approval": suffix}),
        },
        "requester": {"type": "OWNER", "id": "test-owner"},
        "status": "APPROVED",
        "reason": "Immutable evidence fixture",
        "prerequisites": [],
        "risk_summary": {"risk_level": "HIGH", "warning_codes": []},
        "effects": [{"code": "HOLDOUT_UNLOCK", "detail": "fixture"}],
        "requested_at": now.isoformat().replace("+00:00", "Z"),
        "decided_at": now.isoformat().replace("+00:00", "Z"),
    }
    audit_sequence = (
        session.scalar(
            select(func.coalesce(func.max(Audit.sequence), 0)).where(
                Audit.workspace_id == "test-workspace"
            )
        )
        + 1
    )
    event_sequence = (
        session.scalar(
            select(func.coalesce(func.max(Event.sequence), 0)).where(
                Event.workspace_id == "test-workspace"
            )
        )
        + 1
    )
    session.add_all(
        [
            ApprovalRow(
                id=f"APR-{suffix}",
                workspace_id="test-workspace",
                validation_id=f"VAL-{suffix}",
                status="APPROVED",
                subject_sha256=content_hash({"approval": suffix}),
                subject_type="VALIDATION",
                subject_id=f"VAL-{suffix}",
                subject_version=1,
                subject_revision=1,
                subject_spec_sha256=content_hash({"strategy": suffix}),
                prerequisites_sha256=content_hash({"prerequisites": suffix}),
                revision=2,
                detail=json.dumps(approval_detail),
            ),
            Audit(
                id=f"AUD-{suffix}",
                actor_type="OWNER",
                actor_id="test-owner",
                workspace_id="test-workspace",
                sequence=audit_sequence,
                request_id=f"REQ-{suffix}",
                action="CREATED",
                object_type="event_stream",
                object_id=f"EVT-{suffix}",
                object_revision=1,
                payload="{}",
                event_sha256=content_hash({"audit": suffix}),
                occurred_at=now,
            ),
            Event(
                sequence=event_sequence,
                event_id=f"EVT-{suffix}",
                workspace_id="test-workspace",
                request_id=f"REQ-{suffix}",
                event_type="notification.created",
                object_type="notification",
                object_id=f"NOTIF-{suffix}",
                object_revision=1,
                revision=1,
                payload='{"state":"CREATED","status":null}',
                occurred_at=now,
                expires_at=now + timedelta(days=7),
            ),
        ]
    )
    watermark = session.get(EventStreamWatermark, "test-workspace")
    assert watermark is not None
    watermark.last_sequence = max(watermark.last_sequence, event_sequence)
    session.flush()
    result_artifact_id = f"ART-{suffix}"
    session.add(
        ArtifactRow(
            artifact_id=result_artifact_id,
            workspace_id="test-workspace",
            job_id=accepted["job_id"],
            kind="holdout_result",
            media_type="application/json",
            storage_backend="LOCAL",
            storage_key=f"test/{result_artifact_id}.json",
            size_bytes=2,
            sha256=content_hash({"result": suffix}),
            metadata_json={"fixture": suffix},
            publication_state="PUBLISHED",
            created_at=now,
            published_at=now,
            immutable=True,
        )
    )
    session.flush()
    provenance_id = create_provenance(
        session,
        input_value={"fixture": suffix},
        output_sha256=content_hash({"result": suffix}),
        engine_name="test-immutable",
        engine_version="1.0.0",
    )["provenance_id"]
    immutable_artifact_record_id = f"ART-{uuid.uuid4()}"
    immutable_provenance_record_id = f"PROV-{uuid.uuid4()}"
    session.add_all(
        [
            HoldoutExposureRow(
                id=f"HOLD-{suffix}",
                workspace_id="test-workspace",
                validation_id=f"VAL-{suffix}",
                strategy_version_id=f"SV-{suffix}",
                approval_id=f"APR-{suffix}",
                job_id=accepted["job_id"],
                result_artifact_id=result_artifact_id,
                provenance_id=provenance_id,
                result_sha256=content_hash({"result": suffix}),
                period=json.dumps({"start": "2020-10-01", "end": "2020-12-31"}),
                result="{}",
                exposed_at=now,
                contamination=False,
            ),
            Record(
                record_key=immutable_artifact_record_id,
                workspace_id="test-workspace",
                kind="artifact",
                body='{"content_sha256":"immutable"}',
                created_at=now,
                updated_at=now,
            ),
            Record(
                record_key=immutable_provenance_record_id,
                workspace_id="test-workspace",
                kind="provenance",
                body='{"provenance_id":"immutable"}',
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    session.commit()
    session.close()

    _assert_integrity(
        "UPDATE data_snapshots SET detail='changed' WHERE id=:id",
        {"id": f"DS-{suffix}"},
    )
    _assert_integrity(
        "UPDATE snapshot_partitions SET row_count=2 WHERE id=:id",
        {"id": f"SPART-{suffix}"},
    )
    _assert_integrity(
        "UPDATE validations SET holdout_state='APPROVAL_PENDING' WHERE id=:id",
        {"id": f"VAL-{suffix}"},
    )
    _assert_integrity(
        "UPDATE validations SET holdout_state='EXPOSED', exposure_count=1 WHERE id=:id",
        {"id": f"VAL-{suffix}"},
    )
    _assert_integrity(
        "UPDATE experiments SET detail='changed' WHERE experiment_id=:id",
        {"id": f"EXP-{suffix}"},
    )
    _assert_integrity(
        "UPDATE strategy_versions SET spec_sha256=:sha WHERE legacy_id=:id",
        {"id": f"SV-{suffix}", "sha": "f" * 64},
    )
    _assert_integrity(
        "DELETE FROM audit_events WHERE event_id=:id", {"id": f"AUD-{suffix}"}
    )
    _assert_integrity(
        "DELETE FROM domain_events WHERE event_id=:id", {"id": f"EVT-{suffix}"}
    )
    _assert_integrity(
        "UPDATE holdout_exposures SET result='changed' WHERE exposure_id=:id",
        {"id": f"HOLD-{suffix}"},
    )
    _assert_integrity(
        "UPDATE records SET body='changed' WHERE record_key=:id",
        {"id": immutable_artifact_record_id},
    )
    _assert_integrity(
        "DELETE FROM records WHERE record_key=:id",
        {"id": immutable_provenance_record_id},
    )


def test_queue_priority_fencing_and_safe_vs_unsafe_reaping() -> None:
    queue_name = f"test-{uuid.uuid4().hex[:12]}"
    session = SessionLocal()
    session.info.update(
        actor_id="test-owner",
        workspace_id="test-workspace",
        request_id=f"REQ-{uuid.uuid4()}",
    )
    lower = job(session, "DATASET_VALIDATE", queue_name=queue_name, priority=20)
    higher = job(session, "DATASET_VALIDATE", queue_name=queue_name, priority=10)
    unsafe = job(
        session,
        "HOLDOUT_RUN",
        queue_name=f"{queue_name}-unsafe",
        priority=0,
        retry_safe=False,
        max_attempts=1,
    )
    session.commit()

    first = claim_job(session, queue_name, "worker-a")
    assert first is not None and first.job_id == higher["job_id"]
    session.commit()
    row = session.get(JobRow, first.job_id)
    assert row is not None
    row.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()
    assert reap_expired_jobs(session, queue_name=queue_name) == (1, 0)
    session.commit()
    second = claim_job(session, queue_name, "worker-b")
    assert second is not None and second.job_id == higher["job_id"]
    assert second.fencing_token == first.fencing_token + 1
    session.commit()
    with pytest.raises(LostLease):
        heartbeat_job(session, first)
    session.rollback()
    with pytest.raises(LostLease):
        complete_job(session, first, {"stale": True})
    session.rollback()

    unsafe_lease = claim_job(session, f"{queue_name}-unsafe", "worker-a")
    assert unsafe_lease is not None and unsafe_lease.job_id == unsafe["job_id"]
    session.commit()
    unsafe_row = session.get(JobRow, unsafe_lease.job_id)
    assert unsafe_row is not None
    unsafe_row.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()
    assert reap_expired_jobs(session, queue_name=f"{queue_name}-unsafe") == (0, 1)
    session.commit()
    session.refresh(unsafe_row)
    assert unsafe_row.status == "FAILED" and unsafe_row.error_code == "JOB_LEASE_LOST"
    assert session.get(JobRow, lower["job_id"]).status == "QUEUED"
    cancelled = request_cancellation(session, lower["job_id"])
    assert cancelled.status == "CANCELLED" and cancelled.cancel_requested_at is not None
    session.commit()
    with pytest.raises(JobNotCancellable):
        request_cancellation(session, lower["job_id"])
    session.rollback()
    session.close()


def test_sqlite_foreign_keys_are_enforced_for_every_connection() -> None:
    session = SessionLocal()
    if session.get_bind().dialect.name != "sqlite":
        session.close()
        pytest.skip("SQLite-specific foreign-key connection hook")
    assert session.scalar(text("PRAGMA foreign_keys")) == 1
    session.add(
        SnapshotPartitionRow(
            id=f"SPART-orphan-{uuid.uuid4().hex}",
            snapshot_id="DS-550e8400-e29b-41d4-a716-446655440020",
            partition="PUBLIC",
            artifact_id="ART-550e8400-e29b-41d4-a716-446655440020",
            content_sha256="0" * 64,
            row_count=0,
            created_at=datetime.now(UTC),
        )
    )
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    session.close()


def test_artifact_staging_finalizes_after_commit_and_cleans_after_rollback() -> None:
    artifact_root = Path(os.environ["QF_ARTIFACT_DIR"])
    committed = {"artifact": uuid.uuid4().hex, "value": 1}
    session = SessionLocal()
    storage_key, digest = stage_json(session, committed)
    assert not (artifact_root / storage_key).exists()
    session.commit()
    assert read_json(storage_key, digest) == committed
    session.close()

    rolled_back = {"artifact": uuid.uuid4().hex, "value": 2}
    session = SessionLocal()
    rolled_back_key, rolled_back_digest = stage_json(session, rolled_back)
    staged_paths = set(
        (artifact_root / ".staging").glob(f"{rolled_back_digest}.*.stage")
    )
    assert staged_paths and not (artifact_root / rolled_back_key).exists()
    session.rollback()
    assert all(not path.exists() for path in staged_paths)
    assert not (artifact_root / rolled_back_key).exists()
    session.close()


def test_formal_staged_artifact_recovers_to_published() -> None:
    suffix = str(uuid.uuid4())
    artifact_id = f"ART-{suffix}"
    body = {"artifact": artifact_id, "value": 3}
    session = SessionLocal()
    session.info.update(
        {
            "actor_id": "test-owner",
            "workspace_id": "test-workspace",
            "request_id": f"REQ-{suffix}",
        }
    )
    accepted = job(
        session,
        "MEMO_GENERATE",
        input_payload={"memo_id": f"MEMO-{suffix}"},
        queue_name="core",
    )
    job_row = session.get(JobRow, accepted["job_id"])
    assert job_row is not None
    job_row.status = "COMPLETED"
    storage_key, digest = stage_json(session, body, object_key=artifact_id)
    session.add(
        ArtifactRow(
            artifact_id=artifact_id,
            workspace_id="test-workspace",
            job_id=job_row.id,
            kind="recovery_test",
            media_type="application/json",
            storage_backend="LOCAL",
            storage_key=storage_key,
            size_bytes=len(json.dumps(body, sort_keys=True, separators=(",", ":"))),
            sha256=digest,
            schema_name="recovery_test",
            schema_version=1,
            metadata_json={"job_id": job_row.id},
            publication_state="STAGED",
            created_at=datetime.now(UTC) - timedelta(seconds=301),
            immutable=True,
        )
    )
    session.commit()
    assert read_json(storage_key, digest) == body
    assert reap_orphan_artifacts(
        session,
        ArtifactRow,
        minimum_age_seconds=300,
    ) == (1, 0)
    session.commit()
    artifact = session.query(ArtifactRow).filter_by(artifact_id=artifact_id).one()
    assert artifact.publication_state == "PUBLISHED"
    assert artifact.publication_error is None and artifact.published_at is not None
    session.close()


@pytest.mark.parametrize(
    ("fault", "published_before_rollback"),
    [("before_publish", False), ("after_publish", False)],
)
def test_artifact_publication_fault_never_commits_reference_or_leaves_orphan(
    monkeypatch: pytest.MonkeyPatch,
    fault: str,
    published_before_rollback: bool,
) -> None:
    suffix = uuid.uuid4().hex
    dataset_id = f"DSSET-{uuid.uuid4()}"
    dataset_root = Path(os.environ["QF_DATASET_DIR"])
    (dataset_root / f"{dataset_id}.csv").write_text(
        "event_time,available_at,symbol,close,benchmark_close,partition\n"
        "2025-01-02T21:00:00Z,2025-01-02T21:01:00Z,AAA,100,100,RESEARCH\n",
        encoding="utf-8",
    )
    (dataset_root / f"{dataset_id}.metadata.json").write_text(
        json.dumps(
            {
                "provider_id": "LOCAL_DETERMINISTIC",
                "adapter_key": "local-arrow",
                "adapter_version": "1.0.0",
                "timezone": "America/New_York",
                "calendar": "WEEKDAY",
            }
        ),
        encoding="utf-8",
    )
    root = Path(os.environ["QF_ARTIFACT_DIR"])
    before_files = {path for path in root.rglob("*") if path.is_file()}
    session = SessionLocal()
    session.info.update(
        {
            "actor_id": "test-owner",
            "workspace_id": "test-workspace",
            "request_id": f"REQ-{suffix}",
        }
    )
    session.add(
        DataSource(
            id=dataset_id,
            workspace_id="test-workspace",
            provider_id="LOCAL_DETERMINISTIC_DATA",
            status="ACTIVE",
            revision=1,
        )
    )
    accepted = job(
        session,
        "DATASET_VALIDATE",
        input_payload={"dataset_id": dataset_id, "check_profile": "RESEARCH_BASELINE"},
        queue_name="core",
        priority=0,
        retry_safe=False,
        max_attempts=1,
    )
    fault_job = session.get(JobRow, accepted["job_id"])
    assert fault_job is not None
    fault_job.queued_at = datetime.now(UTC) - timedelta(days=1)
    before_rows = session.scalar(select(func.count()).select_from(ArtifactRow))
    session.commit()
    session.close()

    monkeypatch.setenv("QF_ARTIFACT_FAULT", fault)
    assert run_once(identity=f"artifact-fault-{suffix}") == 1
    monkeypatch.delenv("QF_ARTIFACT_FAULT")
    session = SessionLocal()
    failed_job = session.get(JobRow, accepted["job_id"])
    assert failed_job is not None and failed_job.status == "FAILED"
    assert session.scalar(select(func.count()).select_from(ArtifactRow)) == before_rows
    new_files = {
        path
        for path in root.rglob("*")
        if path.is_file()
        and path not in before_files
        and path.name != ".qf-health-probe.json"
    }
    assert bool(new_files) is published_before_rollback
    _, removed = reap_orphan_artifacts(
        session,
        ArtifactRow,
        minimum_age_seconds=0,
    )
    session.commit()
    assert removed >= int(published_before_rollback)
    assert all(not path.exists() for path in new_files)
    session.close()


def test_worker_crash_rolls_back_effect_then_reaper_recovers() -> None:
    dataset_id = f"DSSET-{uuid.uuid4()}"
    dataset_root = Path(os.environ["QF_DATASET_DIR"])
    (dataset_root / f"{dataset_id}.csv").write_text(
        "event_time,available_at,symbol,close,benchmark_close,partition\n"
        "2020-01-02T21:00:00Z,2020-01-02T21:01:00Z,AAA,100,100,RESEARCH\n"
        "2020-01-03T21:00:00Z,2020-01-03T21:01:00Z,AAA,101,101,RESEARCH\n",
        encoding="utf-8",
    )
    (dataset_root / f"{dataset_id}.metadata.json").write_text(
        json.dumps(
            {
                "provider_id": "LOCAL_DETERMINISTIC",
                "adapter_key": "local-arrow",
                "adapter_version": "1.0.0",
                "timezone": "America/New_York",
                "calendar": "WEEKDAY",
            }
        ),
        encoding="utf-8",
    )
    session = SessionLocal()
    session.info.update(
        {
            "actor_id": "test-owner",
            "workspace_id": "test-workspace",
            "request_id": f"REQ-{uuid.uuid4()}",
        }
    )
    session.add(
        DataSource(
            id=dataset_id,
            workspace_id="test-workspace",
            provider_id="LOCAL_DETERMINISTIC_DATA",
            status="ACTIVE",
            revision=1,
        )
    )
    accepted = job(
        session,
        "DATASET_VALIDATE",
        {"type": "dataset", "id": dataset_id, "version": None, "revision": 1},
        input_payload={"dataset_id": dataset_id, "check_profile": "RESEARCH_BASELINE"},
        queue_name="core",
        priority=0,
    )
    before = session.scalar(select(func.count()).select_from(Record))
    session.commit()
    session.close()

    with pytest.raises(SimulatedWorkerCrash):
        run_once(identity="crash-worker", crash_after_effects=True)
    session = SessionLocal()
    row = session.get(JobRow, accepted["job_id"])
    assert row is not None and row.status == "RUNNING" and row.attempt == 1
    assert session.scalar(select(func.count()).select_from(Record)) == before
    row.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()
    assert reap_expired_jobs(session, queue_name="core") == (1, 0)
    session.commit()
    session.close()
    assert run_once(identity="recovery-worker") == 1
    session = SessionLocal()
    row = session.get(JobRow, accepted["job_id"])
    assert row is not None and row.status == "COMPLETED" and row.attempt == 2
    assert session.scalar(select(func.count()).select_from(Record)) == before + 2
    session.close()


def test_agent_checkpoint_effect_rolls_back_when_lease_expires_during_step(
    monkeypatch,
) -> None:
    suffix = uuid.uuid4().hex
    effect_id = f"ART-{uuid.uuid4()}"
    session = SessionLocal()
    session.info.update(
        {
            "actor_id": "test-owner",
            "workspace_id": "test-workspace",
            "request_id": f"REQ-{suffix}",
        }
    )
    accepted = job(
        session,
        "AGENT_RUN",
        input_payload={"agent_run_id": f"ARUN-{uuid.uuid4()}"},
        queue_name="agent",
        priority=0,
        retry_safe=False,
        max_attempts=1,
    )
    session.commit()
    session.close()

    def uncommitted_effect(session: Session, _job: JobRow) -> AgentStep:
        now = datetime.now(UTC)
        session.add(
            Record(
                record_key=effect_id,
                workspace_id="test-workspace",
                kind="artifact",
                revision=1,
                body="{}",
                created_at=now,
                updated_at=now,
            )
        )
        return AgentStep(False, None)

    def expired_fence(session: Session, lease) -> None:
        heartbeat_job(session, lease, now=datetime.now(UTC) + timedelta(seconds=61))

    monkeypatch.setattr("workers.main.advance_agent_run", uncommitted_effect)
    monkeypatch.setattr("workers.main.heartbeat_job", expired_fence)
    assert run_agent_once(identity=f"stale-agent-{suffix}") == 1
    session = SessionLocal()
    assert (
        session.execute(
            select(Record).where(
                Record.workspace_id == "test-workspace",
                Record.record_key == effect_id,
            )
        ).scalar_one_or_none()
        is None
    )
    leased_job = session.get(JobRow, accepted["job_id"])
    assert leased_job is not None and leased_job.status == "RUNNING"
    leased_job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()
    _, failed = reap_expired_jobs(session, queue_name="agent")
    session.commit()
    session.refresh(leased_job)
    assert failed >= 1
    assert leased_job.status == "FAILED"
    assert leased_job.error_code == "JOB_LEASE_LOST"
    session.close()


def test_holdout_worker_failure_atomically_closes_domain_state() -> None:
    suffix = str(uuid.uuid4())
    validation_id = f"VAL-{suffix}"
    session = SessionLocal()
    session.info.update(
        {
            "actor_id": "test-owner",
            "workspace_id": "test-workspace",
            "request_id": f"REQ-{suffix}",
        }
    )
    _, _, strategy_version_id = _seed_strategy_version(session, suffix)
    accepted = job(
        session,
        "HOLDOUT_RUN",
        input_payload={
            "validation_id": validation_id,
            "approval_id": f"APR-{suffix}",
        },
        queue_name="core",
        priority=0,
        retry_safe=False,
        max_attempts=1,
    )
    now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    detail = {
        "validation_id": validation_id,
        "strategy": {"id": f"STRAT-{suffix}", "version": 1},
        "policy_id": "RP-00000000-0000-4000-8000-000000000004",
        "strict_engine": {"name": "qf-validation-v1", "version": "1.0.0"},
        "status": "WAITING_HOLDOUT",
        "result": "PASS",
        "test_suite_version": "1.0.0",
        "tests": [],
        "warnings": [],
        "failures": [],
        "holdout_state": "RUNNING",
        "red_team_run_id": None,
        "job_id": accepted["job_id"],
        "revision": 1,
        "action_capabilities": [],
        "started_at": now,
        "finished_at": now,
        "created_at": now,
    }
    session.add(
        ValidationRow(
            id=validation_id,
            workspace_id="test-workspace",
            strategy_version_id=strategy_version_id,
            status="WAITING_HOLDOUT",
            holdout_state="RUNNING",
            exposure_count=0,
            revision=1,
            detail=json.dumps(detail),
        )
    )
    session.commit()
    session.close()

    assert run_once(identity="holdout-failure-worker") == 1
    session = SessionLocal()
    failed_job = session.get(JobRow, accepted["job_id"])
    validation = session.get(ValidationRow, validation_id)
    failure_event = (
        session.query(Event)
        .filter_by(object_type="validation", object_id=validation_id)
        .order_by(Event.sequence.desc())
        .first()
    )
    assert failed_job is not None and failed_job.status == "FAILED"
    assert validation is not None and validation.status == "FAILED"
    assert validation.holdout_state == "FAILED"
    assert json.loads(validation.detail)["failures"] == [
        "Deterministic worker execution failed"
    ]
    assert (
        failure_event is not None and failure_event.event_type == "validation.updated"
    )
    session.close()


def test_approval_stale_transition_is_committed_with_problem() -> None:
    suffix = str(uuid.uuid4())
    validation_id = f"VAL-{suffix}"
    strategy_id = f"STRAT-{suffix}"
    strategy_version_id = f"SV-{suffix}"
    spec_sha256 = content_hash({"strategy": suffix})
    session = SessionLocal()
    seeded_research_id, seeded_strategy_id, seeded_version_id = _seed_strategy_version(
        session,
        suffix,
        state="VALIDATED",
        spec_sha256=spec_sha256,
        detail=json.dumps(
            {
                "cost_model_id": "COST-00000000-0000-4000-8000-000000000003",
                "research_period": {
                    "start": "2024-01-01",
                    "end": "2024-06-30",
                },
                "validation_period": {
                    "start": "2024-07-01",
                    "end": "2024-12-31",
                },
                "holdout_period": {
                    "start": "2025-01-01",
                    "end": "2025-02-01",
                },
            }
        ),
    )
    assert seeded_research_id == f"RSCH-{suffix}"
    assert seeded_strategy_id == strategy_id
    assert seeded_version_id == strategy_version_id
    session.add(
        ValidationRow(
            id=validation_id,
            workspace_id="test-workspace",
            strategy_version_id=strategy_version_id,
            status="WAITING_HOLDOUT",
            holdout_state="LOCKED",
            exposure_count=0,
            revision=1,
            detail=json.dumps({"result": "PASS"}),
        )
    )
    session.commit()
    session.close()
    client = TestClient(app)
    requested = client.post(
        f"/api/v1/validations/{validation_id}/holdout-approval-requests",
        headers=_key("stale-request") | {"If-Match": f'W/"{validation_id}:1"'},
        json={"reason": "Bind exact subject"},
    )
    assert requested.status_code == 201
    approval_id = requested.json()["approval_id"]
    session = SessionLocal()
    validation = session.get(ValidationRow, validation_id)
    assert validation is not None
    validation.revision += 1
    session.commit()
    session.close()
    decided = client.post(
        f"/api/v1/approvals/{approval_id}/approve",
        headers=_key("stale-decision") | {"If-Match": f'W/"{approval_id}:1"'},
        json={"acknowledged_subject_sha256": requested.json()["subject"]["sha256"]},
    )
    assert decided.status_code == 409
    assert decided.headers["content-type"].startswith("application/problem+json")
    assert decided.json()["code"] == "APPROVAL_STALE"
    session = SessionLocal()
    approval = session.get(ApprovalRow, approval_id)
    assert approval is not None and approval.status == "STALE"
    assert (
        session.query(Audit)
        .filter_by(
            object_type="approval",
            object_id=approval_id,
            action="approval.updated",
        )
        .count()
        == 1
    )
    session.close()
    _assert_integrity(
        "UPDATE approval_requests SET status='PENDING' WHERE approval_id=:id",
        {"id": approval_id},
    )


def test_agent_registry_policy_duplicate_guard_and_disable_checkpoint(
    local_provider: LocalProviderHarness,
) -> None:
    assert len(REGISTRY.tools) == 13
    dataset_id = f"DSSET-{uuid.uuid4()}"
    strategy_id = f"STRAT-{uuid.uuid4()}"
    session = SessionLocal()
    with pytest.raises(ValidationError):
        REGISTRY.validate_request(
            session,
            "validate_dataset",
            "RESEARCH_DIRECTOR",
            {"dataset_id": dataset_id, "unexpected": True},
            {"data_capability"},
        )
    with pytest.raises(ToolPolicyDenied):
        REGISTRY.validate_request(
            session,
            "validate_dataset",
            "PERFORMANCE_ANALYST",
            {"dataset_id": dataset_id},
            {"data_capability"},
        )
    with pytest.raises(ToolPolicyDenied, match="owner_intent"):
        REGISTRY.validate_request(
            session,
            "freeze_strategy",
            "RESEARCH_DIRECTOR",
            {
                "strategy_id": strategy_id,
                "strategy_version": 1,
                "if_match": f'W/"{strategy_id}:1"',
            },
            {"strategy_freeze_eligible"},
        )
    suffix = str(uuid.uuid4())
    snapshot_id = f"DS-{suffix}"
    now = datetime.now(UTC)
    session.info.update({"actor_id": "test-owner", "workspace_id": "test-workspace"})
    session.add(
        SnapshotRow(
            id=snapshot_id,
            workspace_id="test-workspace",
            dataset_id=f"DSSET-{suffix}",
            content_sha256=content_hash({"snapshot": suffix}),
            immutable=True,
            revision=1,
            detail="{}",
        )
    )
    session.flush()
    session.add(
        SnapshotPartitionRow(
            id=f"SPART-{suffix}",
            snapshot_id=snapshot_id,
            partition="PUBLIC",
            artifact_id=f"ART-{suffix}",
            content_sha256=content_hash({"artifact": suffix}),
            row_count=1,
            created_at=now,
        )
    )
    session.add(
        Record(
            record_key=f"ART-{suffix}",
            workspace_id="test-workspace",
            kind="artifact",
            revision=1,
            body="{}",
            created_at=now,
            updated_at=now,
        )
    )
    session.merge(
        AgentConfigRow(
            workspace_id="test-workspace",
            role="PERFORMANCE_ANALYST",
            enabled=True,
            revision=1,
            model_provider="openai-compatible",
            model_name="test-model",
            runtime_profile="DEFAULT",
            tool_timeout_seconds=30,
            created_at=now,
            updated_at=now,
        )
    )
    run_id = f"ARUN-{suffix}"
    session.add(
        AgentRunRow(
            id=run_id,
            workspace_id="test-workspace",
            role="PERFORMANCE_ANALYST",
            status="QUEUED",
            checkpoint="{}",
            revision=1,
            agent_version="1.0",
            model_provider="openai-compatible",
            model_name="test-model",
            objective="Test duplicate guard",
            context_sha256=content_hash({"run": suffix}),
            created_at=now,
        )
    )
    accepted = job(
        session,
        "AGENT_RUN",
        {"type": "agent_run", "id": run_id, "version": None, "revision": 1},
        input_payload={"agent_run_id": run_id},
        queue_name="agent",
        priority=0,
    )
    session.commit()
    session.close()
    action = {
        "type": "tool",
        "name": "get_market_data",
        "arguments": {
            "snapshot_id": snapshot_id,
            "symbols": ["TEST"],
            "start": "2025-01-01",
            "end": "2025-01-31",
            "frequency": "DAILY",
        },
    }
    provider = local_provider.start(
        [action, action, {"type": "conclude", "summary": "done"}],
    )
    assert run_agent_once(identity="agent-integrity") == 1
    session = SessionLocal()
    session.info.update(
        actor_id="test-owner",
        workspace_id="test-workspace",
        request_id=f"REQ-{uuid.uuid4()}",
    )
    run = session.get(AgentRunRow, run_id)
    queued_job = session.get(JobRow, accepted["job_id"])
    assert run is not None and run.status == "COMPLETED" and run.tool_call_count == 1
    assert run.step_count == 3 and provider.action_index == 3
    assert queued_job is not None and queued_job.status == "COMPLETED"
    assert session.query(ToolCallRow).filter_by(agent_run_id=run_id).count() == 1

    disabled_id = f"ARUN-{uuid.uuid4()}"
    config = session.get(AgentConfigRow, ("test-workspace", "PERFORMANCE_ANALYST"))
    assert config is not None
    config.enabled = False
    config.revision += 1
    session.add(
        AgentRunRow(
            id=disabled_id,
            workspace_id="test-workspace",
            role="PERFORMANCE_ANALYST",
            status="QUEUED",
            checkpoint="{}",
            revision=1,
            agent_version="1.0",
            model_provider="openai-compatible",
            model_name="test-model",
            objective="Disable checkpoint",
            context_sha256=content_hash({"run": disabled_id}),
            created_at=now,
        )
    )
    disabled_job = job(
        session,
        "AGENT_RUN",
        input_payload={"agent_run_id": disabled_id},
        queue_name="agent",
        priority=0,
    )
    session.commit()
    session.close()
    assert run_agent_once(identity="agent-disabled") == 1
    session = SessionLocal()
    disabled = session.get(AgentRunRow, disabled_id)
    disabled_job_row = session.get(JobRow, disabled_job["job_id"])
    assert disabled is not None and disabled.status == "CANCELLED"
    assert "AGENT_DISABLED" in disabled.decision_summary
    assert json.loads(disabled.checkpoint)["safe_checkpoint"] == "CANCELLED"
    assert disabled_job_row is not None and disabled_job_row.status == "COMPLETED"
    config = session.get(AgentConfigRow, ("test-workspace", "PERFORMANCE_ANALYST"))
    assert config is not None
    config.enabled = True
    config.revision += 1
    session.commit()
    session.close()


def test_research_director_cannot_complete_without_experiment_evidence(
    local_provider: LocalProviderHarness,
) -> None:
    provider = local_provider.start(
        [{"type": "conclude", "summary": "premature completion"}]
    )
    client = TestClient(app)
    created = client.post(
        "/api/v1/research",
        headers=_key("zero-tool-research"),
        json={
            "title": "Fail-closed Research completion",
            "original_user_prompt": "Do not accept a conclusion without evidence",
        },
    )
    assert created.status_code == 201, created.text
    research_id = created.json()["research_id"]
    current = client.get(f"/api/v1/research/{research_id}", headers=AUTH)
    assert current.status_code == 200, current.text

    session = SessionLocal()
    config = session.get(AgentConfigRow, ("test-workspace", "RESEARCH_DIRECTOR"))
    assert config is not None
    original_provider = config.model_provider
    original_model = config.model_name
    config.model_provider = "openai-compatible"
    config.model_name = "test-model"
    session.commit()
    session.close()
    try:
        started = client.post(
            f"/api/v1/research/{research_id}/start",
            headers=_key("zero-tool-start") | {"If-Match": current.headers["etag"]},
            json={
                "research_revision_no": 1,
                "capability_evaluation_confirmed": True,
            },
        )
        assert started.status_code == 202, started.text
        assert run_agent_once(identity=f"zero-tool-{uuid.uuid4()}") == 1

        session = SessionLocal()
        run = (
            session.query(AgentRunRow)
            .filter_by(
                workspace_id="test-workspace",
                research_id=research_id,
                role="RESEARCH_DIRECTOR",
            )
            .one()
        )
        queued_job = session.get(JobRow, started.json()["job_id"])
        research = session.get(ResearchRow, research_id)
        assert run.status == "FAILED"
        assert run.step_count == 0 and run.tool_call_count == 0
        assert json.loads(run.checkpoint)["failure_type"] == "AgentRuntimeError"
        assert queued_job is not None and queued_job.status == "FAILED"
        assert research is not None and research.status == "WAITING_USER"
        assert json.loads(research.detail)["status"] == "WAITING_USER"
        assert (
            session.query(ExperimentRow)
            .filter_by(workspace_id="test-workspace", research_id=research_id)
            .count()
            == 0
        )
        assert provider.action_index == 1
        session.close()
    finally:
        session = SessionLocal()
        config = session.get(AgentConfigRow, ("test-workspace", "RESEARCH_DIRECTOR"))
        assert config is not None
        config.model_provider = original_provider
        config.model_name = original_model
        session.commit()
        session.close()


def test_agent_async_tool_waits_on_formal_dependency_and_resumes_once(
    local_provider: LocalProviderHarness,
) -> None:
    suffix = str(uuid.uuid4())
    dataset_id = f"DSSET-{suffix}"
    dataset_root = Path(os.environ["QF_DATASET_DIR"])
    (dataset_root / f"{dataset_id}.csv").write_text(
        "event_time,available_at,symbol,close,benchmark_close,partition\n"
        "2025-01-02T21:00:00Z,2025-01-02T21:01:00Z,AAA,100,100,RESEARCH\n",
        encoding="utf-8",
    )
    (dataset_root / f"{dataset_id}.metadata.json").write_text(
        json.dumps(
            {
                "provider_id": "LOCAL_DETERMINISTIC",
                "adapter_key": "local-arrow",
                "adapter_version": "1.0.0",
                "timezone": "America/New_York",
                "calendar": "WEEKDAY",
            }
        ),
        encoding="utf-8",
    )
    now = datetime.now(UTC)
    run_id = f"ARUN-{suffix}"
    session = SessionLocal()
    session.info.update(
        {
            "actor_id": "test-owner",
            "workspace_id": "test-workspace",
            "request_id": f"REQ-{suffix}",
        }
    )
    session.add(
        DataSource(
            id=dataset_id,
            workspace_id="test-workspace",
            provider_id="LOCAL_DETERMINISTIC_DATA",
            status="ACTIVE",
            revision=1,
        )
    )
    session.merge(
        AgentConfigRow(
            workspace_id="test-workspace",
            role="RESEARCH_DIRECTOR",
            enabled=True,
            revision=1,
            model_provider="openai-compatible",
            model_name="test-model",
            runtime_profile="DEFAULT",
            tool_timeout_seconds=30,
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        AgentRunRow(
            id=run_id,
            workspace_id="test-workspace",
            role="RESEARCH_DIRECTOR",
            status="QUEUED",
            checkpoint="{}",
            revision=1,
            agent_version="1.0",
            model_provider="openai-compatible",
            model_name="test-model",
            objective="Validate then consume a durable child result",
            context_sha256=content_hash({"run": run_id}),
            created_at=now,
        )
    )
    parent = job(
        session,
        "AGENT_RUN",
        input_payload={"agent_run_id": run_id},
        queue_name="agent",
        priority=0,
    )
    session.commit()
    session.close()
    provider = local_provider.start(
        [
            {
                "type": "tool",
                "name": "validate_dataset",
                "arguments": {"dataset_id": dataset_id},
            },
            {"type": "conclude", "summary": "child result consumed"},
        ]
    )

    assert run_agent_once(identity=f"agent-parent-{suffix}") == 1
    session = SessionLocal()
    run = session.get(AgentRunRow, run_id)
    parent_job = session.get(JobRow, parent["job_id"])
    tool_call = session.query(ToolCallRow).filter_by(agent_run_id=run_id).one()
    assert run is not None and run.status == "RUNNING"
    assert json.loads(run.checkpoint)["graph_status"] == "WAITING_JOB"
    assert parent_job is not None and parent_job.status == "COMPLETED"
    assert tool_call.status == "RUNNING" and tool_call.job_id is not None
    child_job = session.get(JobRow, tool_call.job_id)
    resume_job = (
        session.query(JobRow)
        .filter_by(job_type="AGENT_RESUME", workspace_id="test-workspace")
        .order_by(JobRow.queued_at.desc())
        .first()
    )
    assert child_job is not None and child_job.status == "QUEUED"
    assert resume_job is not None and resume_job.status == "QUEUED"
    dependency = session.get(
        JobDependencyRow,
        (resume_job.id, child_job.id),
    )
    assert dependency is not None and dependency.dependency_type == "TERMINAL"
    assert resume_job.resume_token_hash == run.pending_resume_token_hash
    assert resume_job.resume_fencing_token == run.resume_fencing_token == 1
    child_job.priority = 0
    child_job.queued_at = datetime.now(UTC) - timedelta(days=1)
    session.commit()
    session.close()

    assert run_agent_once(identity=f"agent-before-child-{suffix}") == 0
    for _ in range(32):
        session = SessionLocal()
        child_job = session.get(JobRow, child_job.id)
        assert child_job is not None
        child_terminal = child_job.status in {"COMPLETED", "FAILED", "CANCELLED"}
        session.close()
        if child_terminal:
            break
        assert run_once(identity=f"core-child-{suffix}") == 1
    assert child_job.status == "COMPLETED"
    assert run_agent_once(identity=f"agent-resume-{suffix}") == 1
    session = SessionLocal()
    run = session.get(AgentRunRow, run_id)
    tool_call = session.query(ToolCallRow).filter_by(agent_run_id=run_id).one()
    resume_job = session.get(JobRow, resume_job.id)
    assert run is not None and run.status == "COMPLETED"
    assert run.decision_summary == "child result consumed"
    assert run.pending_resume_token_hash is None
    assert tool_call.status == "SUCCESS"
    child_result = json.loads(tool_call.result_summary)
    assert child_result["status"] == "COMPLETED"
    assert child_result["job_id"] == child_job.id
    assert resume_job is not None and resume_job.status == "COMPLETED"
    assert resume_job.current_step_key == "RESUME_CONSUMED"
    assert provider.action_index == 2
    session.close()


def test_agent_crash_resumes_from_durable_safe_checkpoint(
    local_provider: LocalProviderHarness,
) -> None:
    suffix = str(uuid.uuid4())
    snapshot_id = f"DS-{suffix}"
    run_id = f"ARUN-{suffix}"
    now = datetime.now(UTC)
    session = SessionLocal()
    session.info.update({"actor_id": "test-owner", "workspace_id": "test-workspace"})
    session.add(
        SnapshotRow(
            id=snapshot_id,
            workspace_id="test-workspace",
            dataset_id=f"DSSET-{suffix}",
            content_sha256=content_hash({"snapshot": suffix}),
            immutable=True,
            revision=1,
            detail="{}",
        )
    )
    session.flush()
    session.add(
        SnapshotPartitionRow(
            id=f"SPART-{suffix}",
            snapshot_id=snapshot_id,
            partition="PUBLIC",
            artifact_id=f"ART-{suffix}",
            content_sha256=content_hash({"artifact": suffix}),
            row_count=1,
            created_at=now,
        )
    )
    session.add(
        Record(
            record_key=f"ART-{suffix}",
            workspace_id="test-workspace",
            kind="artifact",
            revision=1,
            body="{}",
            created_at=now,
            updated_at=now,
        )
    )
    session.merge(
        AgentConfigRow(
            workspace_id="test-workspace",
            role="FACTOR_SCIENTIST",
            enabled=True,
            revision=1,
            model_provider="openai-compatible",
            model_name="test-model",
            runtime_profile="DEFAULT",
            tool_timeout_seconds=30,
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        AgentRunRow(
            id=run_id,
            workspace_id="test-workspace",
            role="FACTOR_SCIENTIST",
            status="QUEUED",
            checkpoint="{}",
            revision=1,
            agent_version="1.0",
            model_provider="openai-compatible",
            model_name="test-model",
            objective="Crash resume",
            context_sha256=content_hash({"run": suffix}),
            created_at=now,
        )
    )
    accepted = job(
        session,
        "AGENT_RUN",
        input_payload={"agent_run_id": run_id},
        queue_name="agent",
        priority=0,
    )
    session.commit()
    session.close()
    action = {
        "type": "tool",
        "name": "get_market_data",
        "arguments": {
            "snapshot_id": snapshot_id,
            "symbols": ["TEST"],
            "start": "2025-01-01",
            "end": "2025-01-31",
            "frequency": "DAILY",
        },
    }
    provider = local_provider.start(
        [action, {"type": "conclude", "summary": "resumed"}]
    )
    with pytest.raises(SimulatedWorkerCrash):
        run_agent_once(
            identity="agent-crash",
            crash_after_checkpoint=True,
        )
    session = SessionLocal()
    run = session.get(AgentRunRow, run_id)
    queued_job = session.get(JobRow, accepted["job_id"])
    assert run is not None and run.status == "RUNNING"
    assert json.loads(run.checkpoint)["safe_checkpoint"] == "AFTER_TOOL"
    assert queued_job is not None and queued_job.status == "RUNNING"
    queued_job.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()
    retried, _ = reap_expired_jobs(session, queue_name="agent")
    session.commit()
    session.refresh(queued_job)
    assert retried >= 1
    assert queued_job.status == "QUEUED"
    session.close()
    assert run_agent_once(identity="agent-resume") == 1
    assert provider.action_index == 2
    session = SessionLocal()
    run = session.get(AgentRunRow, run_id)
    queued_job = session.get(JobRow, accepted["job_id"])
    assert run is not None and run.status == "COMPLETED" and run.tool_call_count == 1
    assert queued_job is not None and queued_job.status == "COMPLETED"
    session.close()


def test_agent_hard_budget_stops_before_another_model_or_tool_call(
    local_provider: LocalProviderHarness,
) -> None:
    suffix = str(uuid.uuid4())
    snapshot_id = f"DS-{suffix}"
    run_id = f"ARUN-{suffix}"
    now = datetime.now(UTC)
    session = SessionLocal()
    session.info.update({"actor_id": "test-owner", "workspace_id": "test-workspace"})
    session.add(
        SnapshotRow(
            id=snapshot_id,
            workspace_id="test-workspace",
            dataset_id=f"DSSET-{suffix}",
            content_sha256=content_hash({"snapshot": suffix}),
            immutable=True,
            revision=1,
            detail="{}",
        )
    )
    session.flush()
    session.add(
        SnapshotPartitionRow(
            id=f"SPART-{suffix}",
            snapshot_id=snapshot_id,
            partition="PUBLIC",
            artifact_id=f"ART-{suffix}",
            content_sha256=content_hash({"artifact": suffix}),
            row_count=1,
            created_at=now,
        )
    )
    session.add(
        Record(
            record_key=f"ART-{suffix}",
            workspace_id="test-workspace",
            kind="artifact",
            revision=1,
            body="{}",
            created_at=now,
            updated_at=now,
        )
    )
    session.merge(
        AgentConfigRow(
            workspace_id="test-workspace",
            role="RED_TEAM_RESEARCHER",
            enabled=True,
            revision=1,
            model_provider="openai-compatible",
            model_name="test-model",
            runtime_profile="DEFAULT",
            tool_timeout_seconds=30,
            max_steps_override=1,
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        AgentRunRow(
            id=run_id,
            workspace_id="test-workspace",
            role="RED_TEAM_RESEARCHER",
            status="QUEUED",
            checkpoint="{}",
            revision=1,
            agent_version="1.0",
            model_provider="openai-compatible",
            model_name="test-model",
            objective="Budget gate",
            context_sha256=content_hash({"run": suffix}),
            created_at=now,
        )
    )
    accepted = job(
        session,
        "AGENT_RUN",
        input_payload={"agent_run_id": run_id},
        queue_name=f"budget-{uuid.UUID(suffix).hex[:20]}",
    )
    session.commit()
    queued_job = session.get(JobRow, accepted["job_id"])
    assert queued_job is not None
    action = {
        "type": "tool",
        "name": "get_market_data",
        "arguments": {
            "snapshot_id": snapshot_id,
            "symbols": ["TEST"],
            "start": "2025-01-01",
            "end": "2025-01-31",
            "frequency": "DAILY",
        },
    }
    provider = local_provider.start(
        [action, {"type": "conclude", "summary": "must not run"}],
    )
    first = advance_agent_run(session, queued_job)
    assert not first.terminal
    session.commit()
    second = advance_agent_run(session, queued_job)
    assert second.terminal
    session.commit()
    run = session.get(AgentRunRow, run_id)
    assert run is not None and run.status == "WAITING_USER"
    assert run.decision_summary == "AGENT_BUDGET_EXCEEDED"
    assert run.model_call_count == 1 and run.tool_call_count == 1
    assert provider.action_index == 1
    session.close()


def test_openai_compatible_adapter_retries_real_http_and_sends_bearer(
    monkeypatch: pytest.MonkeyPatch,
    local_provider: LocalProviderHarness,
) -> None:
    monkeypatch.setenv("QF_AGENT_PROVIDER_MAX_ATTEMPTS", "3")
    provider = local_provider.start(
        [{"type": "conclude", "summary": "provider ok"}],
        failure_statuses=[503],
    )
    model = OpenAICompatibleModel(model_name="provider-model", timeout_seconds=7)
    assert model.next_action({"safe": "context"}) == {
        "type": "conclude",
        "summary": "provider ok",
        "input_tokens": 1,
        "output_tokens": 1,
    }
    posts = [entry for entry in provider.request_log if entry["method"] == "POST"]
    assert len(posts) == 2
    assert all(entry["authorized"] is True for entry in posts)
    assert all(entry["path"] == "/v1/chat/completions" for entry in posts)
    assert posts[-1]["model"] == "provider-model"

    monkeypatch.delenv("QF_OPENAI_API_KEY")
    with pytest.raises(AgentRuntimeError, match="credentials are absent"):
        OpenAICompatibleModel(model_name="provider-model", timeout_seconds=7)


def test_remote_codex_binds_singleton_identity_and_stable_invocation(
    monkeypatch: pytest.MonkeyPatch,
    local_provider: LocalProviderHarness,
) -> None:
    monkeypatch.setenv("QF_CODEX_RUNTIME_ID", "CODEX-DEFAULT")
    monkeypatch.setenv("QF_CODEX_REMOTE_INSTANCE_ID", "remote-codex-test")
    monkeypatch.delenv("QF_CODEX_MODEL", raising=False)
    provider = local_provider.start([{"type": "conclude", "summary": "codex ok"}])
    model = RemoteCodexModel(model_name="codex-model", timeout_seconds=7)
    checkpoint = {
        "model_action_index": 2,
        "context": {
            "agent_run_id": "ARUN-550e8400-e29b-41d4-a716-446655440000",
            "role": "RESEARCH_DIRECTOR",
        },
    }

    assert model.next_action(checkpoint) == {
        "type": "conclude",
        "summary": "codex ok",
        "input_tokens": 1,
        "output_tokens": 1,
    }
    model.next_action(checkpoint)
    posts = [entry for entry in provider.request_log if entry["method"] == "POST"]
    assert len(posts) == 2
    assert {entry["runtime"] for entry in posts} == {"CODEX-DEFAULT"}
    assert {entry["instance"] for entry in posts} == {"remote-codex-test"}
    assert len({entry["invocation"] for entry in posts}) == 1

    monkeypatch.setenv("QF_CODEX_RUNTIME_ID", "CODEX-SECOND")
    with pytest.raises(AgentRuntimeError, match="only CODEX-DEFAULT"):
        RemoteCodexModel(model_name="codex-model", timeout_seconds=7)


@pytest.mark.parametrize(
    "base_url",
    [
        "ftp://codex.example/v1",
        "https://user:password@codex.example/v1",
        "https://codex.example/v1?token=secret",
    ],
)
def test_remote_codex_rejects_unsafe_endpoint_configuration(
    monkeypatch: pytest.MonkeyPatch,
    base_url: str,
) -> None:
    monkeypatch.setenv("QF_CODEX_BASE_URL", base_url)
    monkeypatch.setenv("QF_CODEX_API_KEY", "codex-runtime-credential")
    with pytest.raises(AgentRuntimeError, match="endpoint is invalid"):
        RemoteCodexModel(model_name="codex-model", timeout_seconds=7)


def test_failed_real_tool_rolls_back_then_persists_independent_evidence(
    local_provider: LocalProviderHarness,
) -> None:
    suffix = str(uuid.uuid4())
    snapshot_id = f"DS-{suffix}"
    run_id = f"ARUN-{suffix}"
    now = datetime.now(UTC)
    session = SessionLocal()
    session.info.update(
        {
            "actor_id": "test-owner",
            "workspace_id": "test-workspace",
            "request_id": f"REQ-{suffix}",
        }
    )
    session.add(
        SnapshotRow(
            id=snapshot_id,
            workspace_id="test-workspace",
            dataset_id=f"DSSET-{suffix}",
            content_sha256=content_hash({"snapshot": suffix}),
            immutable=True,
            revision=1,
            detail="{}",
        )
    )
    session.merge(
        AgentConfigRow(
            workspace_id="test-workspace",
            role="PERFORMANCE_ANALYST",
            enabled=True,
            revision=1,
            model_provider="openai-compatible",
            model_name="test-model",
            runtime_profile="DEFAULT",
            tool_timeout_seconds=30,
            created_at=now,
            updated_at=now,
        )
    )
    session.add(
        AgentRunRow(
            id=run_id,
            workspace_id="test-workspace",
            role="PERFORMANCE_ANALYST",
            status="QUEUED",
            checkpoint="{}",
            revision=1,
            agent_version="1.0",
            model_provider="openai-compatible",
            model_name="test-model",
            objective="Fail a missing public partition",
            context_sha256=content_hash({"run": suffix}),
            created_at=now,
        )
    )
    accepted = job(
        session,
        "AGENT_RUN",
        input_payload={"agent_run_id": run_id},
        queue_name="agent",
        priority=0,
        retry_safe=False,
        max_attempts=1,
    )
    session.commit()
    session.close()
    action = {
        "type": "tool",
        "name": "get_market_data",
        "arguments": {
            "snapshot_id": snapshot_id,
            "symbols": ["TEST"],
            "start": "2025-01-01",
            "end": "2025-01-31",
            "frequency": "DAILY",
        },
    }
    provider = local_provider.start([action])
    assert run_agent_once(identity="agent-tool-failure") == 1
    assert provider.action_index == 1
    session = SessionLocal()
    failed_job = session.get(JobRow, accepted["job_id"])
    failed_run = session.get(AgentRunRow, run_id)
    failed_call = session.query(ToolCallRow).filter_by(agent_run_id=run_id).one()
    assert failed_job is not None and failed_job.status == "FAILED"
    assert failed_run is not None and failed_run.status == "FAILED"
    assert failed_call.status == "ERROR"
    assert json.loads(failed_call.warnings)[0]["code"] == "TOOL_EXECUTION_FAILED"
    assert (
        session.query(SnapshotPartitionRow).filter_by(snapshot_id=snapshot_id).count()
        == 0
    )
    session.close()


def test_sse_live_polling_observes_post_connect_event_and_cursor_expiry() -> None:
    local_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sqlalchemy_event.listen(
        local_engine,
        "connect",
        lambda connection, _record: register_sqlite_functions(connection),
    )
    Base.metadata.create_all(local_engine)
    sessions = sessionmaker(bind=local_engine, expire_on_commit=False)
    now = datetime.now(UTC)
    initial_event_id = f"EVT-{uuid.uuid4()}"
    live_event_id = f"EVT-{uuid.uuid4()}"
    burst_event_ids = [f"EVT-{uuid.uuid4()}" for _ in range(3)]
    session = sessions()
    session.add(
        Event(
            sequence=10,
            event_id=initial_event_id,
            workspace_id="test-workspace",
            request_id="REQ-initial",
            event_type="notification.created",
            object_type="notification",
            object_id=f"NOTIF-{uuid.uuid4()}",
            object_revision=1,
            revision=1,
            payload='{"state":"INITIAL","status":null}',
            occurred_at=now,
            expires_at=now + timedelta(days=7),
        )
    )
    session.add(
        EventStreamWatermark(
            workspace_id="test-workspace",
            last_sequence=10,
            expired_through_sequence=9,
        )
    )
    session.commit()
    session.close()

    async def scenario() -> None:
        previous = os.environ.pop("QF_SSE_TEST_CLOSE", None)

        def validate(value: str) -> str:
            return value

        def fixed_now() -> str:
            return now.isoformat()

        try:
            expired_stream = durable_event_stream(
                sessions,
                Event,
                1,
                validate,
                fixed_now,
                workspace_id="test-workspace",
                watermark_model=EventStreamWatermark,
            )
            expired = await anext(expired_stream)
            assert "resync_required" in expired and "resync_from_sequence" in expired

            live_stream = durable_event_stream(
                sessions,
                Event,
                10,
                validate,
                fixed_now,
                workspace_id="test-workspace",
                watermark_model=EventStreamWatermark,
                poll_seconds=0.01,
                heartbeat_seconds=5,
                batch_size=1,
            )
            pending = asyncio.create_task(anext(live_stream))
            await asyncio.sleep(0.03)
            writer = sessions()
            watermark = writer.get(EventStreamWatermark, "test-workspace")
            assert watermark is not None
            watermark.last_sequence += 1
            writer.add(
                Event(
                    sequence=watermark.last_sequence,
                    event_id=live_event_id,
                    workspace_id="test-workspace",
                    request_id="REQ-live",
                    event_type="notification.updated",
                    object_type="agent_config",
                    object_id="RESEARCH_DIRECTOR",
                    object_revision=1,
                    revision=1,
                    payload='{"state":"LIVE","status":null}',
                    occurred_at=datetime.now(UTC),
                    expires_at=datetime.now(UTC) + timedelta(days=7),
                )
            )
            writer.commit()
            writer.close()
            observed = await asyncio.wait_for(pending, timeout=1)
            assert live_event_id in observed and "notification.updated" in observed
            writer = sessions()
            watermark = writer.get(EventStreamWatermark, "test-workspace")
            assert watermark is not None
            for index in range(3):
                watermark.last_sequence += 1
                writer.add(
                    Event(
                        sequence=watermark.last_sequence,
                        event_id=burst_event_ids[index],
                        workspace_id="test-workspace",
                        request_id=f"REQ-burst-{index}",
                        event_type="notification.updated",
                        object_type="agent_config",
                        object_id="RESEARCH_DIRECTOR",
                        object_revision=1,
                        revision=1,
                        payload='{"state":"BURST","status":null}',
                        occurred_at=datetime.now(UTC),
                        expires_at=datetime.now(UTC) + timedelta(days=7),
                    )
                )
            writer.commit()
            writer.close()
            burst = [
                await asyncio.wait_for(anext(live_stream), timeout=1) for _ in range(3)
            ]
            assert all(
                burst_event_ids[index] in value for index, value in enumerate(burst)
            )
            await live_stream.aclose()
        finally:
            if previous is not None:
                os.environ["QF_SSE_TEST_CLOSE"] = previous

    asyncio.run(scenario())
    local_engine.dispose()


def test_sse_heartbeat_uses_exact_15_second_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    local_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    sqlalchemy_event.listen(
        local_engine,
        "connect",
        lambda connection, _record: register_sqlite_functions(connection),
    )
    Base.metadata.create_all(local_engine)
    sessions = sessionmaker(bind=local_engine, expire_on_commit=False)
    clock = {"now": 0.0}
    sleeps: list[float] = []

    async def advance(seconds: float) -> None:
        sleeps.append(seconds)
        clock["now"] += seconds

    monkeypatch.delenv("QF_SSE_TEST_CLOSE", raising=False)
    monkeypatch.setattr("app.sse.time.monotonic", lambda: clock["now"])
    monkeypatch.setattr("app.sse.asyncio.sleep", advance)

    async def scenario() -> None:
        stream = durable_event_stream(
            sessions,
            Event,
            None,
            lambda value: value,
            lambda: datetime.now(UTC).isoformat(),
            workspace_id="heartbeat-workspace",
            poll_seconds=3,
        )
        assert await anext(stream) == ": heartbeat\n\n"
        assert clock["now"] == 15
        assert sleeps == [3, 3, 3, 3, 3]
        await stream.aclose()

    asyncio.run(scenario())
    local_engine.dispose()


def test_sse_last_event_id_header_is_forwarded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, int | None] = {}

    async def stream_once(
        _session_factory,
        _event_model,
        last_event_id,
        _envelope,
        _now,
        **_kwargs,
    ):
        captured["last_event_id"] = last_event_id
        yield ": heartbeat\n\n"

    monkeypatch.setattr("app.main.durable_event_stream", stream_once)
    response = TestClient(app).get(
        "/api/v1/events/stream",
        headers=AUTH | {"Last-Event-ID": "17"},
    )
    assert response.status_code == 200
    assert captured == {"last_event_id": 17}


def test_event_retention_preserves_workspace_cursor_expiry() -> None:
    workspace_id = str(uuid.uuid4())
    owner_id = f"retention-owner-{uuid.uuid4()}"
    expired_at = datetime.now(UTC) - timedelta(seconds=1)
    session = SessionLocal()
    session.add(
        User(
            id=owner_id,
            email=f"{owner_id}@invalid.local",
            role="OWNER",
            revision=1,
        )
    )
    session.add(
        Workspace(
            id=workspace_id,
            owner_id=owner_id,
            name="Retention fixture",
            revision=1,
        )
    )
    session.flush()
    event_id = f"EVT-{uuid.uuid4()}"
    event = Event(
        sequence=1,
        event_id=event_id,
        workspace_id=workspace_id,
        request_id=f"REQ-{uuid.uuid4()}",
        event_type="notification.updated",
        object_type="agent_config",
        object_id="RESEARCH_DIRECTOR",
        object_revision=1,
        revision=1,
        payload='{"state":"EXPIRED","status":null}',
        occurred_at=expired_at,
        expires_at=expired_at,
    )
    session.add(event)
    session.flush()
    sequence = event.sequence
    session.add(
        EventStreamWatermark(
            workspace_id=workspace_id,
            last_sequence=sequence,
            expired_through_sequence=0,
        )
    )
    session.commit()
    session.close()
    assert cleanup_expired_events() >= 1

    async def scenario() -> None:
        def validate(value: str) -> str:
            return value

        def current_time() -> str:
            return datetime.now(UTC).isoformat()

        stream = durable_event_stream(
            SessionLocal,
            Event,
            sequence,
            validate,
            current_time,
            workspace_id=workspace_id,
            watermark_model=EventStreamWatermark,
        )
        response = await anext(stream)
        assert "system.resync_required" in response
        await stream.aclose()

    asyncio.run(scenario())


def test_health_probe_does_not_create_missing_artifact_directory(
    tmp_path, monkeypatch
) -> None:
    missing = tmp_path / "must-not-be-created-by-get"
    monkeypatch.setenv("QF_ARTIFACT_DIR", str(missing))
    response = TestClient(app).get("/api/v1/system/health")
    assert response.status_code == 503
    assert response.json()["code"] == "SERVICE_DEGRADED"
    assert not missing.exists()


def test_artifact_health_requires_scheduler_and_worker_write_read_probe(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("QF_ARTIFACT_DIR", str(tmp_path))
    client = TestClient(app)
    before = set(tmp_path.iterdir())
    degraded = client.get("/api/v1/system/health")
    assert degraded.status_code == 200
    assert degraded.json()["artifact_store"] == "DEGRADED"
    assert set(tmp_path.iterdir()) == before

    probe_artifact_store()
    healthy = client.get("/api/v1/system/health")
    assert healthy.status_code == 200
    assert healthy.json()["artifact_store"] == "HEALTHY"
    marker = tmp_path / ".qf-health-probe.json"
    content = marker.read_text(encoding="utf-8")
    client.get("/api/v1/system/health")
    assert marker.read_text(encoding="utf-8") == content

    marker.unlink()

    def no_claim(_queue: str, _identity: str) -> None:
        return None

    monkeypatch.setattr("workers.main._claim", no_claim)
    assert run_once(identity="artifact-probe-worker") == 0
    assert marker.is_file()
    assert client.get("/api/v1/system/health").json()["artifact_store"] == "HEALTHY"

    marker.write_text("{}", encoding="utf-8")
    unavailable = client.get("/api/v1/system/health")
    assert unavailable.status_code == 503
    assert unavailable.json()["code"] == "SERVICE_DEGRADED"


def test_scheduler_finalizes_referenced_stage_and_reaps_orphan(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("QF_ARTIFACT_DIR", str(tmp_path))
    encoded = json.dumps(
        {"scheduler": "referenced", "run": uuid.uuid4().hex},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    storage_key = f"{digest[:2]}/{digest}.json"
    staging = tmp_path / ".staging"
    staging.mkdir()
    staged = staging / f"{digest}.json.fixture.stage"
    staged.write_bytes(encoded)
    old = datetime.now(UTC).timestamp() - 600
    os.utime(staged, (old, old))
    orphan = tmp_path / "zz" / "orphan.json"
    orphan.parent.mkdir()
    orphan.write_text("orphan", encoding="utf-8")
    os.utime(orphan, (old, old))
    session = SessionLocal()
    session.info.update(
        {
            "actor_id": "test-owner",
            "workspace_id": "test-workspace",
            "request_id": f"REQ-scheduler-{uuid.uuid4()}",
        }
    )
    accepted = job(
        session,
        "MEMO_GENERATE",
        input_payload={"memo_id": f"MEMO-{uuid.uuid4()}"},
        queue_name="core",
    )
    job_row = session.get(JobRow, accepted["job_id"])
    assert job_row is not None
    job_row.status = "COMPLETED"
    session.add(
        ArtifactRow(
            artifact_id=f"ART-{uuid.uuid4()}",
            workspace_id="test-workspace",
            job_id=job_row.id,
            kind="scheduler_test",
            media_type="application/json",
            storage_backend="LOCAL",
            storage_key=storage_key,
            size_bytes=len(encoded),
            sha256=digest,
            schema_name="scheduler_test",
            schema_version=1,
            metadata_json={"job_id": job_row.id},
            publication_state="STAGED",
            created_at=datetime.now(UTC) - timedelta(seconds=600),
            immutable=True,
        )
    )
    session.commit()
    session.close()
    run_scheduler_once()
    assert (tmp_path / storage_key).read_bytes() == encoded
    assert not staged.exists()
    assert not orphan.exists()
