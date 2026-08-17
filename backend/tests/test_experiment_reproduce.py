"""Real API/worker coverage for immutable experiment reproduction."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from quantfoundry.api.app import (
    ArtifactRow,
    Audit,
    Event,
    ExperimentRow,
    JobRow,
    Record,
    SessionLocal,
    app,
)
from quantfoundry.application.jobs.effects import _memo_experiment_evidence
from quantfoundry.workers.main import run_once

OWNER = {"Authorization": "Bearer test"}
VIEWER = {"Authorization": "Bearer viewer"}


def _key(label: str) -> dict[str, str]:
    return OWNER | {"Idempotency-Key": f"reproduce-{label}-{uuid.uuid4()}"}


def _drain(job_id: str) -> JobRow:
    for _ in range(16):
        session = SessionLocal()
        row = session.get(JobRow, job_id)
        terminal = row is not None and row.status in {
            "COMPLETED",
            "FAILED",
            "CANCELLED",
        }
        session.close()
        if terminal:
            assert row is not None
            return row
        assert run_once(identity="reproduce-test-worker") == 1
    raise AssertionError(f"job did not terminate: {job_id}")


@pytest.fixture(scope="module")
def reproducible_source() -> dict[str, str]:
    client = TestClient(app)
    dataset_id = f"DSSET-{uuid.uuid4()}"
    root = Path(os.environ["QF_DATASET_DIR"])
    rows = [
        ("2020-01-02", "AAA", 100, 100),
        ("2020-01-02", "BBB", 101, 100),
        ("2020-02-03", "AAA", 102, 101),
        ("2020-02-03", "BBB", 104, 101),
        ("2020-03-02", "AAA", 103, 102),
        ("2020-03-02", "BBB", 108, 102),
        ("2020-04-01", "AAA", 105, 103),
        ("2020-04-01", "BBB", 112, 103),
    ]
    (root / f"{dataset_id}.csv").write_text(
        "event_time,available_at,symbol,close,benchmark_close,partition\n"
        + "\n".join(
            f"{day}T21:01:00Z,{day}T21:01:00Z,{symbol},{close},{benchmark},RESEARCH"
            for day, symbol, close, benchmark in rows
        ),
        encoding="utf-8",
    )
    (root / f"{dataset_id}.metadata.json").write_text(
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
    dataset_validation = client.post(
        f"/api/v1/data/datasets/{dataset_id}/validate",
        headers=_key("dataset-validation"),
        json={"check_profile": "RESEARCH_BASELINE"},
    )
    assert dataset_validation.status_code == 202, dataset_validation.text
    assert _drain(dataset_validation.json()["job_id"]).status == "COMPLETED"
    snapshot = client.post(
        f"/api/v1/data/datasets/{dataset_id}/snapshots",
        headers=_key("snapshot"),
        json={
            "snapshot_kind": "RESEARCH",
            "as_of_time": "2020-12-31T00:00:00Z",
            "coverage_start": "2020-01-01",
            "coverage_end": "2020-12-31",
        },
    )
    assert snapshot.status_code == 202, snapshot.text
    assert _drain(snapshot.json()["job_id"]).status == "COMPLETED"
    snapshot_id = snapshot.json()["resource_ref"]["id"]
    research = client.post(
        "/api/v1/research",
        headers=_key("research"),
        json={"title": "Reproduce source", "original_user_prompt": "Exact rerun"},
    )
    assert research.status_code == 201, research.text
    research_id = research.json()["research_id"]
    factor = client.post(
        "/api/v1/factors",
        headers=_key("factor"),
        json={
            "research_id": research_id,
            "name": "Reproduction factor",
            "category": "VALUE",
            "description": "Deterministic source",
            "economic_rationale": "Reproduction test",
            "formula": {"expression": "close", "required_fields": ["close"]},
            "universe": {
                "asset_class": "EQUITY",
                "symbols": [],
                "universe_id": "TEST",
            },
            "frequency": "DAILY",
        },
    )
    assert factor.status_code == 201, factor.text
    experiment_payload = {
        "research_id": research_id,
        "research_revision_no": 1,
        "objective": "Recompute identical evidence",
        "hypothesis": "Deterministic inputs produce deterministic output",
        "experiment_type": "FACTOR_ANALYSIS",
        "data_snapshot_id": snapshot_id,
        "factor_id": factor.json()["factor_id"],
        "factor_version": 1,
        "cost_model_id": "COST-00000000-0000-4000-8000-000000000003",
        "parameters": [],
        "engine_key": "qf-factor-v1",
        "engine_version": "1.0.0",
    }
    source = client.post(
        "/api/v1/experiments",
        headers=_key("source"),
        json=experiment_payload,
    )
    assert source.status_code == 202, source.text
    assert _drain(source.json()["job_id"]).status == "COMPLETED"
    return {
        "experiment_id": source.json()["resource_ref"]["id"],
        "experiment_payload": json.dumps(experiment_payload),
        "research_id": research_id,
    }


def test_memo_evidence_resolves_source_and_reproduce_lineage_fail_closed(
    reproducible_source: dict[str, str],
) -> None:
    client = TestClient(app)
    source_id = reproducible_source["experiment_id"]
    research_id = reproducible_source["research_id"]
    accepted = client.post(
        f"/api/v1/experiments/{source_id}/reproduce",
        headers=_key("memo-evidence-child"),
        json={},
    )
    assert accepted.status_code == 202
    child_id = accepted.json()["resource_ref"]["id"]
    child_job = _drain(accepted.json()["job_id"])
    assert child_job.status == "COMPLETED", child_job.error_detail

    pending = client.post(
        "/api/v1/experiments",
        headers=_key("memo-evidence-pending"),
        json=json.loads(reproducible_source["experiment_payload"]),
    )
    assert pending.status_code == 202
    pending_id = pending.json()["resource_ref"]["id"]

    session = SessionLocal()
    evidence = _memo_experiment_evidence(
        session,
        workspace_id="test-workspace",
        research_id=research_id,
    )
    evidence_ids = {item["experiment_id"] for item in evidence}
    assert {source_id, child_id}.issubset(evidence_ids)
    assert pending_id not in evidence_ids
    assert (
        _memo_experiment_evidence(
            session,
            workspace_id="matrix-workspace",
            research_id=research_id,
        )
        == []
    )
    for item in evidence:
        experiment = session.get(ExperimentRow, item["experiment_id"])
        assert experiment is not None
        detail = json.loads(experiment.detail)
        job_row = session.get(JobRow, detail["job_id"])
        assert job_row is not None and job_row.status == "COMPLETED"
        result_ref = json.loads(job_row.result_ref or "{}")
        artifact = (
            session.query(ArtifactRow)
            .filter_by(
                workspace_id="test-workspace",
                artifact_id=result_ref["artifact_id"],
                publication_state="PUBLISHED",
            )
            .one()
        )
        assert artifact.immutable is True and artifact.job_id == job_row.id
        provenance_id = item["provenance"]["provenance_id"]
        provenance = (
            session.query(Record)
            .filter_by(
                workspace_id="test-workspace",
                record_key=provenance_id,
                kind="provenance",
            )
            .one()
        )
        assert json.loads(provenance.body) == detail["provenance"]
    session.close()


def test_exact_reproduction_is_idempotent_immutable_and_deterministic(
    reproducible_source: dict[str, str],
) -> None:
    client = TestClient(app)
    source_id = reproducible_source["experiment_id"]
    session = SessionLocal()
    source = session.get(ExperimentRow, source_id)
    assert source is not None and source.immutable
    source_before = (source.revision, source.detail)
    source_detail = json.loads(source.detail)
    source_output = source_detail["provenance"]["output_sha256"]
    session.close()

    headers = _key("exact")
    accepted = client.post(
        f"/api/v1/experiments/{source_id}/reproduce", headers=headers, json={}
    )
    replay = client.post(
        f"/api/v1/experiments/{source_id}/reproduce", headers=headers, json={}
    )
    assert accepted.status_code == replay.status_code == 202
    assert accepted.json() == replay.json()
    child_id = accepted.json()["resource_ref"]["id"]
    assert accepted.headers["location"] == replay.headers["location"]
    assert accepted.headers["location"] == f"/api/v1/experiments/{child_id}"
    job = _drain(accepted.json()["job_id"])
    assert job.status == "COMPLETED", job.error_detail

    session = SessionLocal()
    source_after = session.get(ExperimentRow, source_id)
    child = session.get(ExperimentRow, child_id)
    assert source_after is not None
    assert (source_after.revision, source_after.detail) == source_before
    assert (
        child is not None
        and child.immutable
        and child.source_experiment_id == source_id
    )
    child_detail = json.loads(child.detail)
    assert child_detail["source_experiment_id"] == source_id
    assert child_detail["provenance"]["source_experiment_id"] == source_id
    assert child_detail["provenance"]["output_sha256"] == source_output
    reproduce_capability = child_detail["action_capabilities"][0]
    assert reproduce_capability["action"] == "reproduce"
    assert reproduce_capability["idempotency_required"] is True
    assert reproduce_capability["result_mode"] == "JOB"
    assert session.query(Audit).filter_by(object_id=child_id).count() >= 2
    assert session.query(Event).filter_by(object_id=child_id).count() >= 2
    session.close()


def test_controlled_override_and_idempotency_conflict(
    reproducible_source: dict[str, str],
) -> None:
    client = TestClient(app)
    source_id = reproducible_source["experiment_id"]
    headers = _key("controlled")
    payload = {
        "mode": "CONTROLLED_OVERRIDE",
        "execution_overrides": {
            "engine_version": "1.0.0",
            "adapter_version": "1.0.0",
            "code_version": "test-build",
        },
        "reason": "Repeat with explicitly pinned available execution versions",
    }
    accepted = client.post(
        f"/api/v1/experiments/{source_id}/reproduce",
        headers=headers,
        json=payload,
    )
    assert accepted.status_code == 202, accepted.text
    conflicting = client.post(
        f"/api/v1/experiments/{source_id}/reproduce",
        headers=headers,
        json={"mode": "EXACT"},
    )
    assert conflicting.status_code == 409
    assert conflicting.json()["code"] == "IDEMPOTENCY_CONFLICT"
    assert "location" not in conflicting.headers
    job = _drain(accepted.json()["job_id"])
    assert job.status == "COMPLETED", job.error_detail
    child = TestClient(app).get(accepted.headers["location"], headers=OWNER)
    assert child.status_code == 200
    assert child.json()["source_experiment_id"] == source_id
    assert child.json()["provenance"]["source_experiment_id"] == source_id


@pytest.mark.parametrize(
    "payload",
    [
        {"unexpected": True},
        {"mode": "UNKNOWN"},
        {"mode": "CONTROLLED_OVERRIDE", "execution_overrides": {}, "reason": "x"},
        {
            "mode": "CONTROLLED_OVERRIDE",
            "execution_overrides": {"engine_version": None},
            "reason": "x",
        },
        {
            "mode": "CONTROLLED_OVERRIDE",
            "execution_overrides": {"engine_version": "1.0.0"},
        },
    ],
)
def test_reproduce_request_constraints_fail_closed(
    reproducible_source: dict[str, str], payload: dict[str, object]
) -> None:
    response = TestClient(app).post(
        f"/api/v1/experiments/{reproducible_source['experiment_id']}/reproduce",
        headers=_key("invalid"),
        json=payload,
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_REQUEST"
    assert "location" not in response.headers


def test_reproduce_auth_permission_missing_source_and_preconditions(
    reproducible_source: dict[str, str],
) -> None:
    client = TestClient(app)
    path = f"/api/v1/experiments/{reproducible_source['experiment_id']}/reproduce"
    unauthenticated = client.post(path, json={})
    forbidden = client.post(
        path, headers=VIEWER | {"Idempotency-Key": "viewer-key-1234567890"}, json={}
    )
    missing_key = client.post(path, headers=OWNER, json={})
    missing_source = client.post(
        f"/api/v1/experiments/EXP-{uuid.uuid4()}/reproduce",
        headers=_key("missing"),
        json={},
    )
    assert unauthenticated.status_code == 401
    assert forbidden.status_code == 403
    assert missing_key.status_code == 428
    assert missing_key.json()["code"] == "PRECONDITION_REQUIRED"
    assert missing_source.status_code == 404
    for response in (unauthenticated, forbidden, missing_key, missing_source):
        assert "location" not in response.headers
        assert response.headers["content-type"].startswith("application/problem+json")


def test_non_immutable_source_is_rejected_without_child_location(
    reproducible_source: dict[str, str],
) -> None:
    client = TestClient(app)
    pending = client.post(
        "/api/v1/experiments",
        headers=_key("pending-source"),
        json=json.loads(reproducible_source["experiment_payload"]),
    )
    assert pending.status_code == 202
    rejected = client.post(
        f"/api/v1/experiments/{pending.json()['resource_ref']['id']}/reproduce",
        headers=_key("pending-reproduce"),
        json={},
    )
    assert rejected.status_code == 409
    assert rejected.json()["code"] == "EXPERIMENT_IMMUTABLE"
    assert "location" not in rejected.headers
