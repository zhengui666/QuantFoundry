"""Execute every canonical operation against real handlers and persisted state."""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import ValidationError
from sqlalchemy import select

from app.artifacts import read_parquet
from app.contracts import canonical_openapi, validate_json_schema
from app.event_contract import EVENT_TYPES, validate_event_payload
from app.local_provider import LocalProviderServer, create_server
from app.main import (
    AgentConfigRow,
    AgentRunRow,
    ApprovalRow,
    Audit,
    CostModelVersionRow,
    Event,
    ExperimentRow,
    FactorRow,
    HoldoutExposureRow,
    JobRow,
    ModelProviderConnectionRow,
    Record,
    SessionLocal,
    SnapshotPartitionRow,
    StrategyRow,
    StrategyVersionRow,
    ToolCallRow,
    app,
    content_hash,
    job,
    validation_action_capabilities,
)
from workers.main import run_agent_once, run_once

SPEC = canonical_openapi()
AUTH = {"Authorization": "Bearer matrix"}


@pytest.mark.parametrize("status", ["QUEUED", "RUNNING"])
def test_validation_capability_is_fail_closed_while_work_is_active(
    status: str,
) -> None:
    capability = validation_action_capabilities(
        status, None, "LOCKED", prerequisites_ready=False
    )
    assert len(capability) == 1
    assert capability[0]["action"] == "request_holdout_approval"
    assert capability[0]["allowed"] is False
    assert capability[0]["reason_code"] == "VALIDATION_IN_PROGRESS"
    assert capability[0]["idempotency_required"] is True
    assert capability[0]["if_match_required"] is True


def test_validation_capability_requires_completed_passing_evidence() -> None:
    denied = validation_action_capabilities(
        "WAITING_HOLDOUT", "PASS", "LOCKED", prerequisites_ready=False
    )
    assert denied[0]["allowed"] is False
    assert denied[0]["reason_code"] == "HOLDOUT_PREREQUISITES_INCOMPLETE"
    allowed = validation_action_capabilities(
        "WAITING_HOLDOUT", "PASS", "LOCKED", prerequisites_ready=True
    )
    assert allowed[0]["allowed"] is True
    assert allowed[0]["reason_code"] is None
    for status in ("COMPLETED", "FAILED", "CANCELLED"):
        assert validation_action_capabilities(status, "FAIL", "LOCKED") == []
    assert (
        validation_action_capabilities(
            "WAITING_HOLDOUT", "PASS", "APPROVAL_PENDING", prerequisites_ready=True
        )
        == []
    )


def test_approval_summary_schema_rejects_missing_and_leaked_detail_fields() -> None:
    schema = SPEC["components"]["schemas"]["ApprovalSummary"]
    summary = {
        "approval_id": "APR-00000000-0000-4000-8000-000000000201",
        "status": "PENDING",
        "revision": 1,
    }
    validate_json_schema(schema, summary)
    missing_revision = {
        key: value for key, value in summary.items() if key != "revision"
    }
    with pytest.raises(ValidationError):
        validate_json_schema(schema, missing_revision)
    with pytest.raises(ValidationError):
        validate_json_schema(schema, {**summary, "type": "HOLDOUT_UNLOCK"})


def _operation(operation_id: str) -> dict:
    return next(
        operation
        for methods in SPEC["paths"].values()
        for operation in methods.values()
        if isinstance(operation, dict) and operation.get("operationId") == operation_id
    )


def _resolved_response(response: dict) -> dict:
    if "$ref" not in response:
        return response
    return SPEC["components"]["responses"][response["$ref"].rsplit("/", 1)[-1]]


def _check(operation_id: str, response, expected_status: int) -> None:
    assert response.status_code == expected_status, (operation_id, response.text)
    declared = _resolved_response(
        _operation(operation_id)["responses"][str(expected_status)]
    )
    if operation_id == "streamEvents":
        assert response.headers["content-type"].startswith("text/event-stream")
        records = [
            json.loads(line.removeprefix("data: "))
            for line in response.text.splitlines()
            if line.startswith("data: ")
        ]
        assert records
        for record in records:
            validate_json_schema(SPEC["components"]["schemas"]["SseEnvelope"], record)
        return
    media_type = next(iter(declared.get("content", {})), None)
    if media_type == "text/markdown":
        assert response.headers["content-type"].startswith("text/markdown")
        assert response.text.startswith("# Investment Memo")
    else:
        assert response.headers["content-type"].startswith("application/json")
        schema = declared.get("content", {}).get("application/json", {}).get("schema")
        if schema:
            validate_json_schema(schema, response.json())
    for header in declared.get("headers", {}):
        assert header.lower() in response.headers


def _key(name: str) -> dict[str, str]:
    return AUTH | {"Idempotency-Key": f"matrix-{name}-{uuid.uuid4()}"}


def test_45_canonical_operation_ids_execute_real_handlers(
    monkeypatch, request: pytest.FixtureRequest
) -> None:
    client = TestClient(app)
    calls: list[str] = []
    response_bodies: list[str] = []
    holdout_sentinel = "QF_HOLDOUT_SENTINEL_MATRIX"
    provider_key = "matrix-provider-credential"
    provider_server: LocalProviderServer = create_server(
        "127.0.0.1",
        0,
        api_key=provider_key,
        model_name="test-model",
    )
    provider_thread = threading.Thread(
        target=provider_server.serve_forever,
        daemon=True,
    )
    provider_thread.start()

    def stop_provider() -> None:
        provider_server.shutdown()
        provider_server.server_close()
        provider_thread.join(timeout=2)

    request.addfinalizer(stop_provider)
    provider_host, provider_port = provider_server.server_address
    monkeypatch.setenv(
        "QF_OPENAI_BASE_URL", f"http://{provider_host}:{provider_port}/v1"
    )
    monkeypatch.setenv("QF_OPENAI_MODELS", "test-model")

    def request(operation: str, method: str, path: str, status: int, **kwargs):
        response = client.request(method, path, **kwargs)
        _check(operation, response, status)
        calls.append(operation)
        response_bodies.append(response.text)
        return response

    def drain_core_job(job_id: str) -> JobRow:
        for _ in range(32):
            session = SessionLocal()
            queued_job = session.get(JobRow, job_id)
            terminal = queued_job is not None and queued_job.status in {
                "COMPLETED",
                "FAILED",
                "CANCELLED",
            }
            session.close()
            if terminal:
                assert queued_job is not None
                return queued_job
            assert run_once(identity="matrix-core-worker") == 1
        raise AssertionError(f"job did not reach terminal state: {job_id}")

    def drain_agent_run(agent_run_id: str) -> AgentRunRow:
        for _ in range(128):
            session = SessionLocal()
            persisted = session.get(AgentRunRow, agent_run_id)
            assert persisted is not None
            terminal = persisted.status in {
                "COMPLETED",
                "FAILED",
                "CANCELLED",
                "WAITING_USER",
            }
            session.expunge(persisted)
            session.close()
            if terminal:
                return persisted
            if run_agent_once(identity="matrix-agent-worker") == 0:
                assert run_once(identity="matrix-core-worker") == 1
        raise AssertionError(f"agent run did not reach terminal state: {agent_run_id}")

    request("getSystemHealth", "GET", "/api/v1/system/health", 200)
    request("getSetupStatus", "GET", "/api/v1/setup/status", 200, headers=AUTH)
    request(
        "getSetupCapabilities",
        "GET",
        "/api/v1/setup/capabilities",
        200,
        headers=AUTH,
    )
    provider = request(
        "validateSetupProviderConnection",
        "POST",
        "/api/v1/setup/provider-connections/validate",
        200,
        headers=_key("provider"),
        json={
            "provider_id": "OPENAI_COMPATIBLE",
            "kind": "AI",
            "model_name": "test-model",
            "credential": "matrix-provider-credential",
        },
    )
    assert "credential" not in provider.text
    invalid_setup = client.post(
        "/api/v1/setup/complete",
        headers=_key("setup-invalid-policy"),
        json={
            "language": "zh-CN",
            "timezone": "Asia/Shanghai",
            "base_currency": "CNY",
            "number_format_locale": "zh-CN",
            "ai_connection_id": provider.json()["connection_id"],
            "default_benchmark": "CSI300",
            "default_frequency": "DAILY",
            "initial_paper_capital": "100000",
            "research_policy_id": "policy:missing",
            "risk_policy_id": "RISK-00000000-0000-4000-8000-000000000102",
            "cost_model_id": "COST-00000000-0000-4000-8000-000000000103",
        },
    )
    assert invalid_setup.status_code == 422
    validate_json_schema(
        SPEC["components"]["schemas"]["ApiProblem"], invalid_setup.json()
    )
    setup_payload = {
        "language": "zh-CN",
        "timezone": "Asia/Shanghai",
        "base_currency": "CNY",
        "number_format_locale": "zh-CN",
        "ai_connection_id": provider.json()["connection_id"],
        "default_benchmark": "CSI300",
        "default_frequency": "DAILY",
        "initial_paper_capital": "100000",
        "research_policy_id": "RP-00000000-0000-4000-8000-000000000101",
        "risk_policy_id": "RISK-00000000-0000-4000-8000-000000000102",
        "cost_model_id": "COST-00000000-0000-4000-8000-000000000103",
    }
    setup_headers = _key("setup")
    persisted_setup = request(
        "completeSetup",
        "POST",
        "/api/v1/setup/complete",
        200,
        headers=setup_headers,
        json=setup_payload,
    )
    settings_id = persisted_setup.json()["settings_id"]
    settings_etag = f'W/"{settings_id}:{persisted_setup.json()["revision"]}"'
    assert persisted_setup.headers["etag"] == settings_etag
    session = SessionLocal()
    settings_row = (
        session.query(Record)
        .filter_by(kind="settings", workspace_id="matrix-workspace")
        .one()
    )
    setup_audits = session.query(Audit).filter_by(object_id=settings_id).count()
    setup_events = session.query(Event).filter_by(object_id=settings_id).count()
    assert settings_row is not None
    assert settings_row.revision == persisted_setup.json()["revision"]
    assert json.loads(settings_row.body) == persisted_setup.json()
    stored_connection = session.get(
        ModelProviderConnectionRow, provider.json()["connection_id"]
    )
    assert stored_connection is not None
    assert stored_connection.status == "ACTIVE"
    assert stored_connection.expires_at is None
    assert b"matrix-provider-credential" not in stored_connection.ciphertext
    session.close()
    setup_replay = client.post(
        "/api/v1/setup/complete", headers=setup_headers, json=setup_payload
    )
    assert setup_replay.status_code == 200
    assert setup_replay.content == persisted_setup.content
    assert setup_replay.headers["etag"] == settings_etag
    session = SessionLocal()
    replayed_settings = (
        session.query(Record)
        .filter_by(kind="settings", workspace_id="matrix-workspace")
        .one()
    )
    assert replayed_settings is not None
    assert replayed_settings.revision == persisted_setup.json()["revision"]
    assert session.query(Audit).filter_by(object_id=settings_id).count() == setup_audits
    assert session.query(Event).filter_by(object_id=settings_id).count() == setup_events
    session.close()
    configured_setup = client.get("/api/v1/setup/status", headers=AUTH)
    assert configured_setup.status_code == 200
    assert configured_setup.json() == {
        "completed": True,
        "owner_session_ready": True,
        "ai_provider_configured": True,
        "ai_connection_id": provider.json()["connection_id"],
        "data_provider_configured": False,
        "research_policy_active": True,
        "research_policy_id": "RP-00000000-0000-4000-8000-000000000101",
        "risk_policy_active": True,
        "risk_policy_id": "RISK-00000000-0000-4000-8000-000000000102",
        "cost_model_active": True,
        "cost_model_id": "COST-00000000-0000-4000-8000-000000000103",
        "fallback_step": None,
    }
    session = SessionLocal()
    configured_cost = (
        session.query(CostModelVersionRow)
        .filter_by(
            workspace_id="matrix-workspace",
            cost_model_id="COST-00000000-0000-4000-8000-000000000103",
        )
        .one()
    )
    configured_cost.status = "RETIRED"
    session.commit()
    degraded_setup = client.get("/api/v1/setup/status", headers=AUTH)
    assert degraded_setup.status_code == 200
    assert degraded_setup.json()["completed"] is False
    assert degraded_setup.json()["cost_model_active"] is False
    assert degraded_setup.json()["cost_model_id"] is None
    assert degraded_setup.json()["fallback_step"] == "RESEARCH_DEFAULTS"
    configured_cost.status = "ACTIVE"
    session.commit()
    session.close()
    replacement_provider = client.post(
        "/api/v1/setup/provider-connections/validate",
        headers=_key("provider-reconfigure"),
        json={
            "provider_id": "OPENAI_COMPATIBLE",
            "kind": "AI",
            "model_name": "test-model",
            "credential": "matrix-provider-credential",
        },
    )
    assert replacement_provider.status_code == 200
    reconfigured_setup = client.post(
        "/api/v1/setup/complete",
        headers=_key("setup-reconfigure"),
        json={
            "language": "zh-CN",
            "timezone": "Asia/Shanghai",
            "base_currency": "CNY",
            "number_format_locale": "zh-CN",
            "ai_connection_id": replacement_provider.json()["connection_id"],
            "default_benchmark": "CSI300",
            "default_frequency": "DAILY",
            "initial_paper_capital": "100000",
            "research_policy_id": "RP-00000000-0000-4000-8000-000000000101",
            "risk_policy_id": "RISK-00000000-0000-4000-8000-000000000102",
            "cost_model_id": "COST-00000000-0000-4000-8000-000000000103",
        },
    )
    assert reconfigured_setup.status_code == 200
    assert reconfigured_setup.json()["revision"] == (
        persisted_setup.json()["revision"] + 1
    )
    assert reconfigured_setup.headers["etag"] == (
        f'W/"{reconfigured_setup.json()["settings_id"]}:'
        f'{reconfigured_setup.json()["revision"]}"'
    )
    reconfigured_status = client.get("/api/v1/setup/status", headers=AUTH)
    assert reconfigured_status.status_code == 200
    assert reconfigured_status.json()["completed"] is True
    assert (
        reconfigured_status.json()["ai_connection_id"]
        == replacement_provider.json()["connection_id"]
    )
    request("getOverview", "GET", "/api/v1/overview", 200, headers=AUTH)
    request(
        "listDataCapabilities", "GET", "/api/v1/data/capabilities", 200, headers=AUTH
    )
    request(
        "evaluateDataCapabilities",
        "POST",
        "/api/v1/data/capabilities/evaluate",
        200,
        headers=AUTH,
        json={
            "requirements": [
                {
                    "capability_key": "prices",
                    "asset_class": "EQUITY",
                    "frequency": "DAILY",
                    "start": "2020-01-01",
                    "end": "2020-12-31",
                    "fields": ["close"],
                    "pit_required": True,
                }
            ]
        },
    )
    dataset_id = f"DSSET-{uuid.uuid4()}"
    dates = [
        ("2020-01-02", "RESEARCH"),
        ("2020-02-03", "RESEARCH"),
        ("2020-03-02", "RESEARCH"),
        ("2020-04-01", "RESEARCH"),
        ("2020-05-01", "RESEARCH"),
        ("2020-06-01", "RESEARCH"),
        ("2020-06-02", "VALIDATION"),
        ("2020-07-01", "VALIDATION"),
        ("2020-09-01", "VALIDATION"),
        ("2020-09-02", "HOLDOUT"),
        ("2020-10-01", "HOLDOUT"),
        ("2020-12-31", "HOLDOUT"),
    ]
    market_rows = [
        {
            "event_time": f"{day}T21:00:00Z",
            "available_at": f"{day}T21:01:00Z",
            "symbol": symbol,
            "close": 100 + day_index * multiplier,
            "benchmark_close": 100 + day_index,
            "partition": partition,
        }
        for day_index, (day, partition) in enumerate(dates)
        for symbol, multiplier in (
            (
                (f"{holdout_sentinel}_A", 1),
                (f"{holdout_sentinel}_B", 2),
                (f"{holdout_sentinel}_C", 3),
            )
            if partition == "HOLDOUT"
            else (("AAA", 1), ("BBB", 2), ("CCC", 3))
        )
    ]
    dataset_root = Path(os.environ["QF_DATASET_DIR"])
    columns = [
        "event_time",
        "available_at",
        "symbol",
        "close",
        "benchmark_close",
        "partition",
    ]
    (dataset_root / f"{dataset_id}.csv").write_text(
        ",".join(columns)
        + "\n"
        + "\n".join(
            ",".join(str(row[column]) for column in columns) for row in market_rows
        ),
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
    dataset_validation = request(
        "validateDataset",
        "POST",
        f"/api/v1/data/datasets/{dataset_id}/validate",
        202,
        headers=_key("dataset-validation"),
        json={"check_profile": "RESEARCH_BASELINE"},
    )
    assert drain_core_job(dataset_validation.json()["job_id"]).status == "COMPLETED"
    snapshot = request(
        "createDatasetSnapshot",
        "POST",
        f"/api/v1/data/datasets/{dataset_id}/snapshots",
        202,
        headers=_key("snapshot"),
        json={
            "snapshot_kind": "RESEARCH",
            "as_of_time": "2020-12-31T00:00:00Z",
            "coverage_start": "2020-01-01",
            "coverage_end": "2020-12-31",
        },
    )
    snapshot_id = snapshot.json()["resource_ref"]["id"]
    assert drain_core_job(snapshot.json()["job_id"]).status == "COMPLETED"
    request(
        "getDatasetSnapshot",
        "GET",
        f"/api/v1/data/snapshots/{snapshot_id}",
        200,
        headers=AUTH,
    )
    duplicate_snapshot = client.post(
        f"/api/v1/data/datasets/{dataset_id}/snapshots",
        headers=_key("snapshot-dedup"),
        json={
            "snapshot_kind": "RESEARCH",
            "as_of_time": "2020-12-31T00:00:00Z",
            "coverage_start": "2020-01-01",
            "coverage_end": "2020-12-31",
        },
    )
    assert duplicate_snapshot.status_code == 202
    assert duplicate_snapshot.json()["resource_ref"]["id"] == snapshot_id
    assert drain_core_job(duplicate_snapshot.json()["job_id"]).status == "COMPLETED"
    request("listResearch", "GET", "/api/v1/research", 200, headers=AUTH)
    research = request(
        "createResearch",
        "POST",
        "/api/v1/research",
        201,
        headers=_key("research"),
        json={"title": "Matrix research", "original_user_prompt": "Test research"},
    )
    research_id = research.json()["research_id"]
    research_read = request(
        "getResearch",
        "GET",
        f"/api/v1/research/{research_id}",
        200,
        headers=AUTH,
    )
    factor = request(
        "createFactor",
        "POST",
        "/api/v1/factors",
        201,
        headers=_key("factor"),
        json={
            "research_id": research_id,
            "name": "Value factor",
            "category": "VALUE",
            "description": "Close-price factor",
            "economic_rationale": "Tests a stable observable input",
            "formula": {"expression": "close", "required_fields": ["close"]},
            "universe": {
                "asset_class": "EQUITY",
                "symbols": [],
                "universe_id": "CSI300",
            },
            "frequency": "DAILY",
        },
    )
    factor_id = factor.json()["factor_id"]
    started = request(
        "startResearch",
        "POST",
        f"/api/v1/research/{research_id}/start",
        202,
        headers=_key("start") | {"If-Match": research_read.headers["etag"]},
        json={"research_revision_no": 1, "capability_evaluation_confirmed": True},
    )
    experiment = request(
        "createExperiment",
        "POST",
        "/api/v1/experiments",
        202,
        headers=_key("experiment"),
        json={
            "research_id": research_id,
            "research_revision_no": 2,
            "objective": "Measure a deterministic factor",
            "hypothesis": "The factor has positive rank correlation",
            "experiment_type": "FACTOR_ANALYSIS",
            "data_snapshot_id": snapshot_id,
            "factor_id": factor_id,
            "factor_version": 1,
            "cost_model_id": "COST-00000000-0000-4000-8000-000000000103",
            "parameters": [],
            "engine_key": "qf-factor-v1",
            "engine_version": "1.0.0",
        },
    )
    experiment_id = experiment.json()["resource_ref"]["id"]
    request(
        "getExperiment",
        "GET",
        f"/api/v1/experiments/{experiment_id}",
        200,
        headers=AUTH,
    )
    experiment_job = drain_core_job(experiment.json()["job_id"])
    assert experiment_job.status == "COMPLETED", experiment_job.error_detail
    request(
        "analyzeFactor",
        "POST",
        f"/api/v1/factors/{factor_id}/analyses",
        202,
        headers=_key("factor-analysis"),
        json={
            "factor_version": 1,
            "snapshot_id": snapshot_id,
            "forward_return_horizons": [1, 5],
        },
    )
    strategy_factor = client.post(
        "/api/v1/factors",
        headers=_key("strategy-factor"),
        json={
            "research_id": research_id,
            "name": "Strategy-only factor",
            "category": "VALUE",
            "description": "Separates research evidence from strategy signals",
            "economic_rationale": "Memo evidence remains bound through research",
            "formula": {"expression": "close", "required_fields": ["close"]},
            "universe": {
                "asset_class": "EQUITY",
                "symbols": [],
                "universe_id": "CSI300",
            },
            "frequency": "DAILY",
        },
    )
    assert strategy_factor.status_code == 201
    strategy_factor_id = strategy_factor.json()["factor_id"]
    strategy_factor_analysis = client.post(
        f"/api/v1/factors/{strategy_factor_id}/analyses",
        headers=_key("strategy-factor-analysis"),
        json={
            "factor_version": 1,
            "snapshot_id": snapshot_id,
            "forward_return_horizons": [1, 5],
        },
    )
    assert strategy_factor_analysis.status_code == 202
    strategy_factor_job = drain_core_job(strategy_factor_analysis.json()["job_id"])
    assert strategy_factor_job.status == "COMPLETED", strategy_factor_job.error_detail
    strategy = request(
        "createStrategy",
        "POST",
        "/api/v1/strategies",
        201,
        headers=_key("strategy"),
        json={
            "research_id": research_id,
            "name": "Matrix strategy",
            "thesis": "A deterministic factor strategy",
            "universe": {
                "asset_class": "EQUITY",
                "symbols": [],
                "universe_id": "CSI300",
            },
            "signals": [
                {
                    "factor_id": strategy_factor_id,
                    "factor_version": 1,
                    "direction": "LONG",
                    "weight": "1",
                }
            ],
            "rules": {
                "selection_count": 1,
                "weighting": "EQUAL",
                "rebalance_frequency": "DAILY",
                "long_short": False,
                "leverage_limit": "1",
                "position_limit": "1",
            },
            "cost_model_id": "COST-00000000-0000-4000-8000-000000000103",
            "benchmark": "CSI300",
            "research_period": {"start": "2020-01-01", "end": "2020-06-01"},
            "validation_period": {"start": "2020-06-02", "end": "2020-09-01"},
            "holdout_period": {"start": "2020-09-02", "end": "2020-12-31"},
            "known_failure_modes": ["Regime shift"],
        },
    )
    strategy_id = strategy.json()["strategy_id"]
    strategy_read = request(
        "getStrategyVersion",
        "GET",
        f"/api/v1/strategies/{strategy_id}/versions/1",
        200,
        headers=AUTH,
    )
    initial_capabilities = {
        item["action"]: item for item in strategy_read.json()["action_capabilities"]
    }
    assert set(initial_capabilities) == {"run_fast_backtest", "freeze"}
    assert initial_capabilities["run_fast_backtest"] == {
        "action": "run_fast_backtest",
        "visibility": "SHOW",
        "allowed": True,
        "reason_code": None,
        "reason_detail": None,
        "requires_confirmation": False,
        "idempotency_required": True,
        "if_match_required": False,
        "result_mode": "JOB",
        "danger_level": "STATE_CHANGE",
    }
    assert initial_capabilities["freeze"] == {
        "action": "freeze",
        "visibility": "SHOW",
        "allowed": False,
        "reason_code": "VALIDATION_PREREQUISITES_INCOMPLETE",
        "reason_detail": None,
        "requires_confirmation": True,
        "idempotency_required": True,
        "if_match_required": True,
        "result_mode": "IMMEDIATE",
        "danger_level": "IRREVERSIBLE",
    }
    current_strategy = request(
        "getCurrentStrategyVersion",
        "GET",
        f"/api/v1/strategies/{strategy_id}/current-version",
        200,
        headers=AUTH,
    )
    assert current_strategy.json() == strategy_read.json()
    premature_freeze = client.post(
        f"/api/v1/strategies/{strategy_id}/versions/1/freeze",
        headers=_key("premature-freeze") | {"If-Match": strategy_read.headers["etag"]},
        json={"expected_spec_sha256": strategy.json()["spec_sha256"]},
    )
    assert premature_freeze.status_code == 409
    assert premature_freeze.json()["code"] == "VALIDATION_PREREQUISITES_INCOMPLETE"
    backtest = request(
        "runFastBacktest",
        "POST",
        f"/api/v1/strategies/{strategy_id}/versions/1/backtests",
        202,
        headers=_key("backtest"),
        json={
            "snapshot_id": snapshot_id,
            "cost_model_id": "COST-00000000-0000-4000-8000-000000000103",
            "engine_key": "qf-simulation-v1",  # gitleaks:allow
            "engine_version": "1.0.0",
            "parameters": [],
        },
    )
    completed_backtest = drain_core_job(backtest.json()["job_id"])
    assert completed_backtest.status == "COMPLETED", completed_backtest.error_detail
    strategy_after_backtest = client.get(
        f"/api/v1/strategies/{strategy_id}/versions/1", headers=AUTH
    )
    assert strategy_after_backtest.status_code == 200
    assert strategy_after_backtest.json()["latest_backtest"]["state"] == "AVAILABLE"
    assert strategy_after_backtest.json()["revision"] == 2
    completed_capabilities = {
        item["action"]: item
        for item in strategy_after_backtest.json()["action_capabilities"]
    }
    assert completed_capabilities["run_fast_backtest"]["allowed"] is True
    assert completed_capabilities["freeze"]["allowed"] is True
    assert completed_capabilities["freeze"]["reason_code"] is None
    session = SessionLocal()
    source_row = session.get(ExperimentRow, experiment_id)
    assert source_row is not None and source_row.immutable
    source_before = (source_row.revision, source_row.detail)
    source_output_sha256 = json.loads(source_row.detail)["provenance"]["output_sha256"]
    session.close()
    reproduced = request(
        "reproduceExperiment",
        "POST",
        f"/api/v1/experiments/{experiment_id}/reproduce",
        202,
        headers=_key("experiment-reproduce"),
        json={},
    )
    child_id = reproduced.json()["resource_ref"]["id"]
    assert reproduced.headers["location"] == f"/api/v1/experiments/{child_id}"
    assert child_id != experiment_id
    assert drain_core_job(reproduced.json()["job_id"]).status == "COMPLETED"
    session = SessionLocal()
    source_after = session.get(ExperimentRow, experiment_id)
    child = session.get(ExperimentRow, child_id)
    assert (
        source_after is not None
        and (source_after.revision, source_after.detail) == source_before
    )
    assert child is not None and child.immutable
    child_detail = json.loads(child.detail)
    assert child_detail["source_experiment_id"] == experiment_id
    assert child_detail["provenance"]["source_experiment_id"] == experiment_id
    assert child_detail["provenance"]["output_sha256"] == source_output_sha256
    session.close()
    frozen_strategy = request(
        "freezeStrategy",
        "POST",
        f"/api/v1/strategies/{strategy_id}/versions/1/freeze",
        200,
        headers=_key("freeze") | {"If-Match": strategy_after_backtest.headers["etag"]},
        json={"expected_spec_sha256": strategy.json()["spec_sha256"]},
    )
    assert frozen_strategy.json()["lifecycle_state"] == "FROZEN"
    assert frozen_strategy.json()["action_capabilities"] == [
        {
            "action": "start_validation",
            "visibility": "SHOW",
            "allowed": True,
            "reason_code": None,
            "reason_detail": None,
            "requires_confirmation": False,
            "idempotency_required": True,
            "if_match_required": False,
            "result_mode": "JOB",
            "danger_level": "STATE_CHANGE",
        }
    ]
    validation = request(
        "createValidation",
        "POST",
        "/api/v1/validations",
        202,
        headers=_key("validation"),
        json={
            "strategy_id": strategy_id,
            "strategy_version": 1,
            "policy_id": "RP-00000000-0000-4000-8000-000000000104",
            "strict_engine_key": "qf-validation-v1",
            "strict_engine_version": "1.0.0",
            "test_suite_version": "1.0.0",
        },
    )
    validation_id = validation.json()["resource_ref"]["id"]
    validating_strategy = client.get(
        f"/api/v1/strategies/{strategy_id}/versions/1", headers=AUTH
    )
    assert validating_strategy.status_code == 200
    assert validating_strategy.json()["lifecycle_state"] == "VALIDATING"
    assert validating_strategy.json()["action_capabilities"] == []
    pending_validation = client.get(
        f"/api/v1/validations/{validation_id}", headers=AUTH
    )
    assert pending_validation.status_code == 200
    assert pending_validation.json()["status"] == "QUEUED"
    assert pending_validation.json()["action_capabilities"] == [
        {
            "action": "request_holdout_approval",
            "visibility": "SHOW",
            "allowed": False,
            "reason_code": "VALIDATION_IN_PROGRESS",
            "reason_detail": None,
            "requires_confirmation": False,
            "idempotency_required": True,
            "if_match_required": True,
            "result_mode": "IMMEDIATE",
            "danger_level": "STATE_CHANGE",
        }
    ]
    premature_approval = client.post(
        f"/api/v1/validations/{validation_id}/holdout-approval-requests",
        headers=_key("premature-approval")
        | {"If-Match": pending_validation.headers["etag"]},
        json={"reason": "Must wait for deterministic validation"},
    )
    assert premature_approval.status_code == 409
    assert premature_approval.json()["code"] == "HOLDOUT_PREREQUISITES_INCOMPLETE"
    session = SessionLocal()
    assert (
        session.query(ApprovalRow).filter_by(validation_id=validation_id).count() == 0
    )
    session.close()
    assert drain_core_job(validation.json()["job_id"]).status == "COMPLETED"
    terminal_strategy = client.get(
        f"/api/v1/strategies/{strategy_id}/versions/1", headers=AUTH
    )
    assert terminal_strategy.status_code == 200
    assert terminal_strategy.json()["lifecycle_state"] in {"VALIDATED", "REJECTED"}
    assert terminal_strategy.json()["action_capabilities"] == []
    validation_read = request(
        "getValidation",
        "GET",
        f"/api/v1/validations/{validation_id}",
        200,
        headers=AUTH,
    )
    assert validation_read.json()["status"] == "WAITING_HOLDOUT"
    assert validation_read.json()["result"] == "PASS"
    assert validation_read.json()["action_capabilities"] == [
        {
            "action": "request_holdout_approval",
            "visibility": "SHOW",
            "allowed": True,
            "reason_code": None,
            "reason_detail": None,
            "requires_confirmation": False,
            "idempotency_required": True,
            "if_match_required": True,
            "result_mode": "IMMEDIATE",
            "danger_level": "STATE_CHANGE",
        }
    ]
    stale_approval = client.post(
        f"/api/v1/validations/{validation_id}/holdout-approval-requests",
        headers=_key("stale-pending-approval")
        | {"If-Match": pending_validation.headers["etag"]},
        json={"reason": "Stale pre-completion request"},
    )
    assert stale_approval.status_code == 412
    assert stale_approval.json()["code"] == "REVISION_MISMATCH"
    request(
        "getHoldoutGate",
        "GET",
        f"/api/v1/validations/{validation_id}/holdout",
        200,
        headers=AUTH,
    )
    denied_holdout = client.post(
        f"/api/v1/validations/{validation_id}/holdout-runs",
        headers=_key("holdout-denied") | {"If-Match": validation_read.headers["etag"]},
        json={"approval_id": "APR-00000000-0000-4000-8000-000000000199"},
    )
    assert denied_holdout.status_code == 403
    assert denied_holdout.json()["code"] == "HOLDOUT_APPROVAL_REQUIRED"
    approval = request(
        "requestHoldoutApproval",
        "POST",
        f"/api/v1/validations/{validation_id}/holdout-approval-requests",
        201,
        headers=_key("approval-request")
        | {"If-Match": validation_read.headers["etag"]},
        json={"reason": "Controlled matrix holdout"},
    )
    approval_id = approval.json()["approval_id"]
    pending_gate = client.get(
        f"/api/v1/validations/{validation_id}/holdout", headers=AUTH
    )
    assert pending_gate.status_code == 200
    assert pending_gate.json()["state"] == "APPROVAL_PENDING"
    assert pending_gate.json()["approval"] == {
        "approval_id": approval_id,
        "status": "PENDING",
        "revision": 1,
    }
    validation_after_request = client.get(
        f"/api/v1/validations/{validation_id}", headers=AUTH
    )
    assert validation_after_request.status_code == 200
    assert pending_gate.headers["etag"] == validation_after_request.headers["etag"]
    assert set(pending_gate.json()["approval"]) == {
        "approval_id",
        "status",
        "revision",
    }
    losing_concurrent_approval = client.post(
        f"/api/v1/validations/{validation_id}/holdout-approval-requests",
        headers=_key("losing-concurrent-approval")
        | {"If-Match": validation_read.headers["etag"]},
        json={"reason": "Concurrent duplicate owner intent"},
    )
    assert losing_concurrent_approval.status_code == 412
    assert losing_concurrent_approval.json()["code"] == "REVISION_MISMATCH"
    request("listApprovals", "GET", "/api/v1/approvals", 200, headers=AUTH)
    approval_read = request(
        "getApproval",
        "GET",
        f"/api/v1/approvals/{approval_id}",
        200,
        headers=AUTH,
    )
    request(
        "rejectApproval",
        "POST",
        f"/api/v1/approvals/{approval_id}/reject",
        200,
        headers=_key("reject") | {"If-Match": approval_read.headers["etag"]},
        json={
            "reason": "Exercise the canonical rejection transition",
            "acknowledged_subject_sha256": approval.json()["subject"]["sha256"],
        },
    )
    rejected_validation = client.get(
        f"/api/v1/validations/{validation_id}", headers=AUTH
    )
    approval = client.post(
        f"/api/v1/validations/{validation_id}/holdout-approval-requests",
        headers=_key("approval-request-after-reject")
        | {"If-Match": rejected_validation.headers["etag"]},
        json={"reason": "Controlled matrix holdout after rejected request"},
    )
    assert approval.status_code == 201
    approval_id = approval.json()["approval_id"]
    approved = request(
        "approveApproval",
        "POST",
        f"/api/v1/approvals/{approval_id}/approve",
        200,
        headers=_key("approve") | {"If-Match": f'W/"{approval_id}:1"'},
        json={"acknowledged_subject_sha256": approval.json()["subject"]["sha256"]},
    )
    approved_gate = client.get(
        f"/api/v1/validations/{validation_id}/holdout", headers=AUTH
    )
    assert approved_gate.status_code == 200
    assert approved_gate.json()["state"] == "UNLOCKED"
    assert approved_gate.json()["approval"] == {
        "approval_id": approval_id,
        "status": "APPROVED",
        "revision": 2,
    }
    assert approved_gate.headers["etag"] == (
        f'W/"{validation_id}:{approved.json()["subject_ref"]["revision"]}"'
    )
    run = request(
        "runHoldout",
        "POST",
        f"/api/v1/validations/{validation_id}/holdout-runs",
        202,
        headers=_key("holdout-run") | {"If-Match": approved_gate.headers["etag"]},
        json={"approval_id": approval_id},
    )

    # Drain real core jobs until the unsafe holdout job atomically writes its
    # immutable exposure, artifact, provenance, audit and event.
    drain_core_job(run.json()["job_id"])
    session = SessionLocal()
    holdout_job = session.get(JobRow, run.json()["job_id"])
    exposure = (
        session.query(HoldoutExposureRow)
        .filter_by(validation_id=validation_id)
        .one_or_none()
    )
    assert holdout_job is not None and holdout_job.status == "COMPLETED", (
        None if holdout_job is None else holdout_job.error_detail
    )
    assert exposure is not None and exposure.job_id == holdout_job.id
    session.close()
    request(
        "getHoldoutResult",
        "GET",
        f"/api/v1/validations/{validation_id}/holdout/result",
        200,
        headers=AUTH,
    )

    memo = request(
        "generateMemo",
        "POST",
        "/api/v1/memos",
        202,
        headers=_key("memo"),
        json={"strategy_id": strategy_id, "strategy_version": 1},
    )
    memo_id = memo.json()["resource_ref"]["id"]
    assert drain_core_job(memo.json()["job_id"]).status == "COMPLETED"
    request("getMemo", "GET", f"/api/v1/memos/{memo_id}", 200, headers=AUTH)
    request(
        "exportMemo",
        "GET",
        f"/api/v1/memos/{memo_id}/export?format=MARKDOWN",
        200,
        headers=AUTH,
    )

    # Seed two additional candidate versions from an already validated canonical
    # specification. Their backtest/freeze evidence is still produced through
    # real handlers and workers below.
    candidate_strategy_id = f"STRAT-{uuid.uuid4()}"
    frozen_strategy_id = f"STRAT-{uuid.uuid4()}"
    second_factor_id = f"FAC-{uuid.uuid4()}"
    session = SessionLocal()
    source_factor = session.get(FactorRow, factor_id)
    source_strategy = session.get(StrategyVersionRow, f"{strategy_id}:1")
    if source_strategy is None:
        source_strategy = (
            session.query(StrategyVersionRow)
            .filter_by(strategy_id=strategy_id, version=1)
            .one()
        )
    assert source_factor is not None
    factor_detail = json.loads(source_factor.detail)
    factor_detail.update(
        {
            "factor_id": second_factor_id,
            "name": "Agent comparison factor",
            "revision": 1,
        }
    )
    session.add(
        FactorRow(
            id=second_factor_id,
            workspace_id="matrix-workspace",
            research_id=research_id,
            revision=1,
            detail=json.dumps(factor_detail),
        )
    )
    for seeded_strategy_id in (candidate_strategy_id, frozen_strategy_id):
        seeded_detail = json.loads(source_strategy.detail)
        seeded_detail.update(
            {
                "strategy_id": seeded_strategy_id,
                "name": f"Agent fixture {seeded_strategy_id}",
                "lifecycle_state": "CANDIDATE",
                "is_frozen": False,
                "frozen_at": None,
                "frozen_by": None,
                "revision": 1,
            }
        )
        session.add(
            StrategyRow(
                id=seeded_strategy_id,
                workspace_id="matrix-workspace",
                research_id=research_id,
                revision=1,
                detail=json.dumps(seeded_detail),
            )
        )
        session.flush()
        session.add(
            StrategyVersionRow(
                id=f"{seeded_strategy_id}:1",
                workspace_id="matrix-workspace",
                strategy_id=seeded_strategy_id,
                version=1,
                state="CANDIDATE",
                spec_sha256=source_strategy.spec_sha256,
                revision=1,
                detail=json.dumps(seeded_detail),
            )
        )
    session.commit()
    session.close()
    seeded_backtest = client.post(
        f"/api/v1/strategies/{frozen_strategy_id}/versions/1/backtests",
        headers=_key("agent-frozen-backtest"),
        json={
            "snapshot_id": snapshot_id,
            "cost_model_id": "COST-00000000-0000-4000-8000-000000000103",
            "engine_key": "qf-simulation-v1",  # gitleaks:allow
            "engine_version": "1.0.0",
            "parameters": [],
        },
    )
    assert seeded_backtest.status_code == 202
    assert drain_core_job(seeded_backtest.json()["job_id"]).status == "COMPLETED"
    seeded_strategy_read = client.get(
        f"/api/v1/strategies/{frozen_strategy_id}/versions/1", headers=AUTH
    )
    assert seeded_strategy_read.status_code == 200
    frozen = client.post(
        f"/api/v1/strategies/{frozen_strategy_id}/versions/1/freeze",
        headers=_key("agent-frozen-freeze")
        | {"If-Match": seeded_strategy_read.headers["etag"]},
        json={"expected_spec_sha256": source_strategy.spec_sha256},
    )
    assert frozen.status_code == 200

    request("listAgents", "GET", "/api/v1/agents", 200, headers=AUTH)
    config = request(
        "getAgentConfig",
        "GET",
        "/api/v1/agents/RESEARCH_DIRECTOR/config",
        200,
        headers=AUTH,
    )
    request(
        "updateAgentConfig",
        "PUT",
        "/api/v1/agents/RESEARCH_DIRECTOR/config",
        200,
        headers=AUTH | {"If-Match": config.headers["etag"]},
        json={"model_provider": "openai-compatible", "model_name": "test-model"},
    )
    actions = [
        {
            "type": "tool",
            "name": "get_market_data",
            "arguments": {
                "snapshot_id": snapshot_id,
                "symbols": ["TEST"],
                "start": "2020-09-02",
                "end": "2020-12-31",
                "frequency": "DAILY",
            },
        },
        {
            "type": "tool",
            "name": "validate_dataset",
            "arguments": {"dataset_id": dataset_id},
        },
        {
            "type": "tool",
            "name": "create_data_snapshot",
            "arguments": {"dataset_id": dataset_id},
        },
        {
            "type": "tool",
            "name": "define_factor",
            "arguments": {
                "research_id": research_id,
                "definition": {
                    "name": "Agent-defined factor",
                    "category": "VALUE",
                    "description": "Defined by the real semantic-tool executor",
                    "economic_rationale": "Deterministic close-price evidence",
                    "formula": {"expression": "close", "required_fields": ["close"]},
                    "universe": {
                        "asset_class": "EQUITY",
                        "symbols": [],
                        "universe_id": "CSI300",
                    },
                    "frequency": "DAILY",
                },
            },
        },
        {
            "type": "tool",
            "name": "analyze_factor",
            "arguments": {
                "factor_id": second_factor_id,
                "factor_version": 1,
                "snapshot_id": snapshot_id,
            },
        },
        {
            "type": "tool",
            "name": "calculate_factor",
            "arguments": {
                "factor_id": factor_id,
                "factor_version": 1,
                "snapshot_id": snapshot_id,
            },
        },
        {
            "type": "tool",
            "name": "compare_factors",
            "arguments": {
                "factor_refs": [
                    {"id": factor_id, "version": 1},
                    {"id": second_factor_id, "version": 1},
                ],
                "snapshot_id": snapshot_id,
            },
        },
        {
            "type": "tool",
            "name": "define_strategy",
            "arguments": {
                "research_id": research_id,
                "definition": {
                    "name": "Agent-defined strategy",
                    "thesis": "Semantic tool creates a typed deterministic strategy",
                    "universe": {
                        "asset_class": "EQUITY",
                        "symbols": [],
                        "universe_id": "CSI300",
                    },
                    "signals": [
                        {
                            "factor_id": factor_id,
                            "factor_version": 1,
                            "direction": "LONG",
                            "weight": "1",
                        }
                    ],
                    "rules": {
                        "selection_count": 1,
                        "weighting": "EQUAL",
                        "rebalance_frequency": "DAILY",
                        "long_short": False,
                        "leverage_limit": "1",
                        "position_limit": "1",
                    },
                    "cost_model_id": "COST-00000000-0000-4000-8000-000000000103",
                    "benchmark": "CSI300",
                    "research_period": {"start": "2020-01-01", "end": "2020-06-01"},
                    "validation_period": {
                        "start": "2020-06-02",
                        "end": "2020-09-01",
                    },
                    "holdout_period": {"start": "2020-09-02", "end": "2020-12-31"},
                    "known_failure_modes": ["Regime shift"],
                },
            },
        },
        {
            "type": "tool",
            "name": "run_fast_backtest",
            "arguments": {
                "strategy_id": candidate_strategy_id,
                "strategy_version": 1,
                "snapshot_id": snapshot_id,
            },
        },
        {
            "type": "tool",
            "name": "compare_backtests",
            "arguments": {"experiment_ids": [experiment_id, child_id]},
        },
        {
            "type": "tool",
            "name": "run_parameter_sensitivity",
            "arguments": {
                "strategy_id": candidate_strategy_id,
                "strategy_version": 1,
                "snapshot_id": snapshot_id,
                "parameter_grid": {"selection_count": [1, 2]},
            },
        },
        {"type": "conclude", "summary": "Matrix evidence recorded"},
        {
            "type": "tool",
            "name": "run_validation_suite",
            "arguments": {"strategy_id": frozen_strategy_id, "strategy_version": 1},
        },
        {"type": "conclude", "summary": "Red-team validation queued"},
    ]
    provider_server.actions = actions
    provider_server.action_index = 0
    session = SessionLocal()
    director_run_id = (
        session.query(AgentRunRow)
        .filter_by(research_id=research_id, role="RESEARCH_DIRECTOR")
        .one()
        .id
    )
    session.close()
    persisted_director_run = drain_agent_run(director_run_id)
    session = SessionLocal()
    persisted_director_job = (
        session.query(JobRow)
        .filter_by(queue_name="agent", workspace_id="matrix-workspace")
        .order_by(JobRow.queued_at)
        .first()
    )
    assert persisted_director_run.status == "COMPLETED", (
        persisted_director_run.decision_summary,
        persisted_director_job.error_detail if persisted_director_job else None,
    )
    session.close()
    red_config = client.get("/api/v1/agents/RED_TEAM_RESEARCHER/config", headers=AUTH)
    assert red_config.status_code == 200
    red_config_update = client.put(
        "/api/v1/agents/RED_TEAM_RESEARCHER/config",
        headers=AUTH | {"If-Match": red_config.headers["etag"]},
        json={"model_provider": "openai-compatible", "model_name": "test-model"},
    )
    assert red_config_update.status_code == 200
    session = SessionLocal()
    timestamp = datetime.now(UTC)
    session.info.update(
        {
            "actor_id": "matrix-owner",
            "workspace_id": "matrix-workspace",
            "request_id": f"REQ-red-team-{uuid.uuid4()}",
        }
    )
    red_run_id = f"ARUN-{uuid.uuid4()}"
    session.add(
        AgentRunRow(
            id=red_run_id,
            workspace_id="matrix-workspace",
            research_id=research_id,
            role="RED_TEAM_RESEARCHER",
            status="QUEUED",
            checkpoint="{}",
            revision=1,
            agent_version="1.0",
            model_provider="openai-compatible",
            model_name="test-model",
            objective="Execute strict validation through the real tool registry",
            context_sha256=content_hash({"agent_run_id": red_run_id}),
            created_at=timestamp,
        )
    )
    red_accepted = job(
        session,
        "AGENT_RUN",
        input_payload={"agent_run_id": red_run_id},
        queue_name="agent",
        priority=0,
    )
    session.commit()
    session.close()
    persisted_red_run = drain_agent_run(red_run_id)
    session = SessionLocal()
    persisted_red_job = session.get(JobRow, red_accepted["job_id"])
    persisted_red_config = session.get(
        AgentConfigRow, ("matrix-workspace", "RED_TEAM_RESEARCHER")
    )
    red_calls = session.query(ToolCallRow).filter_by(agent_run_id=red_run_id).all()
    red_child_jobs = [
        session.query(JobRow).filter_by(id=call.job_id).one_or_none()
        for call in red_calls
        if call.job_id
    ]
    for red_child_job in red_child_jobs:
        assert red_child_job is not None
        assert red_child_job.status == "COMPLETED", red_child_job.error_detail
    assert persisted_red_run is not None and persisted_red_run.status == "COMPLETED", (
        persisted_red_run.decision_summary if persisted_red_run else None,
        persisted_red_job.error_detail if persisted_red_job else None,
        [
            (call.tool_name, call.status, call.result_summary, call.warnings)
            for call in red_calls
        ],
        [
            (
                child.id,
                child.status,
                child.error_code,
                child.error_detail[-1200:] if child.error_detail else None,
            )
            for child in red_child_jobs
            if child is not None
        ],
    )
    assert (
        persisted_red_config is not None
        and persisted_red_config.model_provider == "openai-compatible"
    )
    assert persisted_red_run.decision_summary == "Red-team validation queued"
    session.close()
    assert provider_server.action_index == len(actions)

    session = SessionLocal()
    agent_run = (
        session.query(AgentRunRow)
        .filter_by(research_id=research_id, role="RESEARCH_DIRECTOR")
        .one()
    )
    tool_calls = (
        session.query(ToolCallRow)
        .filter_by(agent_run_id=agent_run.id)
        .order_by(ToolCallRow.started_at)
        .all()
    )
    assert {call.tool_name for call in tool_calls} == {
        "get_market_data",
        "validate_dataset",
        "create_data_snapshot",
        "define_factor",
        "analyze_factor",
        "calculate_factor",
        "compare_factors",
        "define_strategy",
        "run_fast_backtest",
        "compare_backtests",
        "run_parameter_sensitivity",
    }
    assert all(call.policy_version_ref == "RPV-matrix-workspace" for call in tool_calls)
    tool_call = next(call for call in tool_calls if call.tool_name == "get_market_data")
    child_job_ids = [call.job_id for call in tool_calls if call.job_id is not None]
    red_tool_call = session.query(ToolCallRow).filter_by(agent_run_id=red_run_id).one()
    assert red_tool_call.tool_name == "run_validation_suite"
    assert red_tool_call.policy_version_ref == "RPV-matrix-workspace"
    assert red_tool_call.job_id is not None
    child_job_ids.append(red_tool_call.job_id)
    session.close()
    for child_job_id in child_job_ids:
        assert drain_core_job(child_job_id).status == "COMPLETED"
    request(
        "getAgentRun",
        "GET",
        f"/api/v1/agent-runs/{agent_run.id}",
        200,
        headers=AUTH,
    )
    request(
        "getToolCall",
        "GET",
        f"/api/v1/tool-calls/{tool_call.id}",
        200,
        headers=AUTH,
    )
    request(
        "getJob",
        "GET",
        f"/api/v1/jobs/{started.json()['job_id']}",
        200,
        headers=AUTH,
    )
    request(
        "streamEvents",
        "GET",
        "/api/v1/events/stream",
        200,
        headers=AUTH | {"Last-Event-ID": "0"},
    )

    expected = {
        operation["operationId"]
        for methods in SPEC["paths"].values()
        for operation in methods.values()
        if isinstance(operation, dict) and "operationId" in operation
    }
    assert len(expected) == len(calls) == SPEC["info"]["x-quantfoundry-operation-count"]
    assert set(calls) == expected
    assert holdout_sentinel not in "\n".join(response_bodies)

    session = SessionLocal()
    bindings = {
        binding.partition: binding
        for binding in session.query(SnapshotPartitionRow)
        .filter_by(snapshot_id=snapshot_id)
        .all()
    }
    public_record = session.execute(
        select(Record).where(
            Record.workspace_id == "matrix-workspace",
            Record.record_key == bindings["PUBLIC"].artifact_id,
        )
    ).scalar_one_or_none()
    holdout_record = session.execute(
        select(Record).where(
            Record.workspace_id == "matrix-workspace",
            Record.record_key == bindings["HOLDOUT"].artifact_id,
        )
    ).scalar_one_or_none()
    assert public_record is not None and holdout_record is not None
    public_metadata = json.loads(public_record.body)
    holdout_metadata = json.loads(holdout_record.body)
    public_artifact = json.dumps(
        read_parquet(public_metadata["storage_key"], public_metadata["content_sha256"])
    )
    protected_artifact = json.dumps(
        read_parquet(
            holdout_metadata["storage_key"], holdout_metadata["content_sha256"]
        )
    )
    persisted_public_state = "\n".join(
        [
            *(row.payload for row in session.query(Audit).all()),
            *(row.payload for row in session.query(Event).all()),
            *(row.checkpoint for row in session.query(AgentRunRow).all()),
            public_artifact,
        ]
    )
    matrix_events = (
        session.query(Event).filter_by(workspace_id="matrix-workspace").all()
    )
    assert matrix_events
    assert all(event.event_type in EVENT_TYPES for event in matrix_events)
    assert all(event.request_id for event in matrix_events)
    assert all(
        validate_event_payload(json.loads(event.payload)) == json.loads(event.payload)
        for event in matrix_events
    )
    session.close()
    assert holdout_sentinel not in persisted_public_state
    assert holdout_sentinel in protected_artifact
