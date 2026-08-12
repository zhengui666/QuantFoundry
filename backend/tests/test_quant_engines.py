"""Independent golden/property tests for local deterministic engine contracts."""

from __future__ import annotations

import json
import os
import random
import stat
import uuid
from dataclasses import replace
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as parquet
import pytest
from fastapi.testclient import TestClient

from quantfoundry.api.app import HoldoutExposureRow, JobRow, SessionLocal, app
from quantfoundry.engines.core import (
    CostModel,
    DatasetBundle,
    ValidationPolicy,
    compute_factor_rows,
    data_quality_profile,
    factor_metrics,
    holdout_policy_result,
    load_dataset,
    simulation_metrics,
    snapshot_content_sha256,
    snapshot_rows,
    validation_checks,
)
from quantfoundry.infrastructure.artifacts.store import (
    ArtifactStoreError,
    put_json,
    read_json,
)
from quantfoundry.workers.main import run_once


def _metadata(root: Path, dataset_id: str) -> None:
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


def _market_row(
    day: str,
    symbol: str,
    close: float,
    benchmark: float,
    partition: str = "VALIDATION",
) -> dict[str, object]:
    return {
        "event_time": f"{day}T21:00:00Z",
        "available_at": f"{day}T21:01:00Z",
        "date": day,
        "symbol": symbol,
        "close": close,
        "benchmark_close": benchmark,
        "partition": partition,
    }


def test_csv_and_parquet_adapter_enforce_pit_as_of_and_schema(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("QF_DATASET_DIR", str(tmp_path))
    columns = [
        "event_time",
        "available_at",
        "symbol",
        "close",
        "benchmark_close",
        "partition",
    ]
    source_rows = [
        {
            "event_time": "2020-06-01T21:00:00Z",
            "available_at": "2020-06-01T21:01:00Z",
            "symbol": "AAA",
            "close": 100.0,
            "benchmark_close": 100.0,
            "partition": "RESEARCH",
        },
        {
            "event_time": "2020-06-02T21:00:00Z",
            "available_at": "2020-07-01T21:01:00Z",
            "symbol": "AAA",
            "close": 101.0,
            "benchmark_close": 101.0,
            "partition": "VALIDATION",
        },
        {
            "event_time": "2020-09-02T21:00:00Z",
            "available_at": "2020-09-02T21:01:00Z",
            "symbol": "QF_HOLDOUT_SENTINEL",
            "close": 102.0,
            "benchmark_close": 102.0,
            "partition": "HOLDOUT",
        },
    ]
    csv_id = "DSSET-550e8400-e29b-41d4-a716-446655440010"
    (tmp_path / f"{csv_id}.csv").write_text(
        ",".join(columns)
        + "\n"
        + "\n".join(
            ",".join(str(row[column]) for column in columns) for row in source_rows
        ),
        encoding="utf-8",
    )
    _metadata(tmp_path, csv_id)
    csv_bundle = load_dataset(csv_id)
    public, protected = snapshot_rows(
        csv_bundle, "2020-01-01", "2020-12-31", "2020-06-30T23:59:59Z"
    )
    assert [row["date"] for row in public] == ["2020-06-01"]
    assert protected == []
    assert all(row["available_at"] <= "2020-06-30T23:59:59Z" for row in public)

    parquet_id = "DSSET-550e8400-e29b-41d4-a716-446655440011"
    parquet.write_table(
        pa.Table.from_pylist(source_rows), tmp_path / f"{parquet_id}.parquet"
    )
    _metadata(tmp_path, parquet_id)
    parquet_bundle = load_dataset(parquet_id)
    assert parquet_bundle.rows == csv_bundle.rows
    assert parquet_bundle.schema_sha256 == csv_bundle.schema_sha256
    original_hash = snapshot_content_sha256(csv_id, csv_bundle, public, protected)
    assert original_hash != snapshot_content_sha256(
        "DSSET-550e8400-e29b-41d4-a716-446655440012",
        csv_bundle,
        public,
        protected,
    )
    assert original_hash != snapshot_content_sha256(
        csv_id,
        replace(csv_bundle, adapter_version="2.0.0"),
        public,
        protected,
    )


def test_factor_ic_rank_ic_turnover_and_coverage_golden() -> None:
    rows = [
        _market_row("2020-01-02", "AAA", 10, 100),
        _market_row("2020-01-02", "BBB", 20, 100),
        _market_row("2020-01-02", "CCC", 30, 100),
        _market_row("2020-01-03", "AAA", 10.5, 101),
        _market_row("2020-01-03", "BBB", 22, 101),
        _market_row("2020-01-03", "CCC", 36, 101),
        _market_row("2020-01-06", "AAA", 11.025, 102),
        _market_row("2020-01-06", "BBB", 24.2, 102),
        _market_row("2020-01-06", "CCC", 43.2, 102),
    ]
    result = factor_metrics(rows, [1])
    assert factor_metrics(rows, [1]) == result
    horizon = result["horizons"]["1"]
    assert horizon["rank_ic"] == pytest.approx(1.0, abs=1e-12)
    assert horizon["ic"] > 0.95
    assert result["coverage"] == pytest.approx(1.0, abs=0)
    assert result["turnover"] == pytest.approx(0.0, abs=0)
    assert result["observations"] == 6


def test_versioned_golden_reference_and_tolerance_manifest() -> None:
    golden_root = Path(__file__).parent / "fixtures" / "golden" / "v1"
    expected = json.loads((golden_root / "expected.json").read_text())
    tolerances = json.loads((golden_root / "tolerances.json").read_text())
    assert expected["formula_semantics_version"] == "qf-canonical-math-v1"
    assert tolerances["manifest_version"] == 1
    rows = [
        _market_row("2020-01-02", "AAA", 10, 100),
        _market_row("2020-01-02", "BBB", 20, 100),
        _market_row("2020-01-02", "CCC", 30, 100),
        _market_row("2020-01-03", "AAA", 10.5, 101),
        _market_row("2020-01-03", "BBB", 22, 101),
        _market_row("2020-01-03", "CCC", 36, 101),
        _market_row("2020-01-06", "AAA", 11.025, 102),
        _market_row("2020-01-06", "BBB", 24.2, 102),
        _market_row("2020-01-06", "CCC", 43.2, 102),
    ]
    actual_factor = factor_metrics(rows, [1])
    expected_factor = expected["factor"]
    assert actual_factor["observations"] == expected_factor["observations"]
    correlation_tolerance = tolerances["float64_correlation"]
    for field in (
        "ic",
        "ic_ir",
        "rank_ic",
        "rank_ic_ir",
        "neutralized_ic",
        "quantile_return_spread",
    ):
        assert actual_factor["horizons"]["1"][field] == pytest.approx(
            expected_factor["horizon_1"][field],
            abs=correlation_tolerance["absolute"],
            rel=correlation_tolerance["relative"],
        )
    backtest_rows = [
        _market_row("2020-01-02", "AAA", 10, 100),
        _market_row("2020-01-02", "BBB", 20, 100),
        _market_row("2020-01-03", "AAA", 11, 101),
        _market_row("2020-01-03", "BBB", 18, 101),
        _market_row("2020-01-06", "AAA", 12, 102),
        _market_row("2020-01-06", "BBB", 21, 102),
    ]
    actual_backtest = simulation_metrics(
        backtest_rows, 1, CostModel("cost:zero", 1, 0, 0)
    )
    expected_backtest = expected["backtest"]
    return_tolerance = tolerances["float64_return"]
    for field in (
        "returns",
        "total_return",
        "benchmark_total_return",
        "cagr",
        "annualized_volatility",
        "sharpe",
        "sortino",
        "calmar",
        "maximum_drawdown",
        "turnover",
        "average_holding_period",
        "commission",
        "slippage",
        "cash_weight",
        "exposure",
    ):
        assert actual_backtest[field] == pytest.approx(
            expected_backtest[field],
            abs=return_tolerance["absolute"],
            rel=return_tolerance["relative"],
        )
    weight_tolerance = tolerances["float64_weight"]
    for field in ("final_weights", "risk_contribution"):
        assert actual_backtest[field] == pytest.approx(
            expected_backtest[field],
            abs=weight_tolerance["absolute"],
            rel=weight_tolerance["relative"],
        )
    assert actual_backtest["observations"] == expected_backtest["observations"]
    assert actual_backtest["trade_count"] == expected_backtest["trade_count"]


def test_factor_oracle_changes_portfolio_returns() -> None:
    rows = [
        _market_row("2020-01-02", "AAA", 10, 100),
        _market_row("2020-01-02", "BBB", 100, 100),
        _market_row("2020-01-03", "AAA", 20, 101),
        _market_row("2020-01-03", "BBB", 110, 101),
        _market_row("2020-01-06", "AAA", 10, 102),
        _market_row("2020-01-06", "BBB", 121, 102),
    ]
    momentum = [
        {**row, "strategy_score": row["factor_score"]}
        for row in compute_factor_rows(rows, "momentum_1")
    ]
    mean_reversion = [
        {**row, "strategy_score": row["factor_score"]}
        for row in compute_factor_rows(rows, "mean_reversion_1")
    ]
    cost = CostModel("cost:zero", 1, 0, 0)
    momentum_result = simulation_metrics(momentum, 1, cost)
    mean_reversion_result = simulation_metrics(mean_reversion, 1, cost)
    assert momentum_result["returns"] == pytest.approx([-0.5], abs=1e-12)
    assert mean_reversion_result["returns"] == pytest.approx([0.1], abs=1e-12)
    assert momentum_result["final_weights"] == {"AAA": 1.0}
    assert mean_reversion_result["final_weights"] == {"BBB": 1.0}
    assert momentum_result["returns"] != mean_reversion_result["returns"]


def test_factor_formula_strategy_spec_corporate_actions_and_policy() -> None:
    raw_rows = [
        {
            **_market_row("2020-01-02", "AAA", 100, 100),
            "in_universe": True,
            "split_factor": 1.0,
            "dividend": 0.0,
        },
        {
            **_market_row("2020-01-02", "BBB", 100, 100),
            "in_universe": False,
            "split_factor": 1.0,
            "dividend": 0.0,
        },
        {
            **_market_row("2020-01-03", "AAA", 50, 101),
            "in_universe": True,
            "split_factor": 2.0,
            "dividend": 0.0,
        },
        {
            **_market_row("2020-01-03", "BBB", 150, 101),
            "in_universe": False,
            "split_factor": 1.0,
            "dividend": 0.0,
        },
        {
            **_market_row("2020-01-06", "AAA", 55, 102),
            "in_universe": True,
            "split_factor": 1.0,
            "dividend": 1.0,
        },
        {
            **_market_row("2020-01-06", "BBB", 300, 102),
            "in_universe": False,
            "split_factor": 1.0,
            "dividend": 0.0,
        },
    ]
    factor_rows = compute_factor_rows(
        raw_rows, "momentum_{lookback}", {"lookback": "1"}
    )
    assert [row["symbol"] for row in factor_rows] == ["AAA", "BBB", "AAA", "BBB"]
    assert factor_rows[0]["factor_score"] == pytest.approx(-0.5, abs=1e-12)
    spec = {
        "universe": {"symbols": ["AAA"]},
        "signals": [{"direction": "LONG", "weight": "1"}],
        "rules": {
            "weighting": "EQUAL",
            "rebalance_frequency": "DAILY",
            "long_short": False,
            "leverage_limit": "1",
            "position_limit": "1",
        },
    }
    result = simulation_metrics(raw_rows, 1, CostModel("cost:zero", 1, 0, 0), spec)
    assert result["returns"] == pytest.approx([0.0, 0.12], abs=1e-12)
    assert set(result["final_weights"]) == {"AAA"}

    policy = ValidationPolicy(
        "policy:test",
        1,
        50,
        1.0,
        -0.1,
        50,
        0.5,
        1.0,
        -0.1,
        2,
        10,
        3,
        0.0,
    )
    state, failures = holdout_policy_result(result, policy)
    assert state == "FAIL"
    assert "MIN_OBSERVATIONS" in failures
    bundle = DatasetBundle(
        raw_rows,
        "LOCAL_DETERMINISTIC",
        "local-arrow",
        "1.0.0",
        "UTC",
        "WEEKDAY",
        "0" * 64,
        "AVAILABLE_AT_STRICT_V1",
        "RAW_PRICE_SPLIT_DIVIDEND_V1",
        "POINT_IN_TIME_MEMBERSHIP_V1",
    )
    profile = data_quality_profile(bundle, policy)
    assert profile["state"] == "FAIL"
    assert "SYMBOL_COUNT_BELOW_POLICY" in profile["failures"]


def test_backtest_cost_benchmark_drawdown_portfolio_and_risk_golden() -> None:
    rows = [
        _market_row("2020-01-02", "AAA", 10, 100),
        _market_row("2020-01-02", "BBB", 20, 100),
        _market_row("2020-01-03", "AAA", 11, 101),
        _market_row("2020-01-03", "BBB", 18, 101),
        _market_row("2020-01-06", "AAA", 12, 102),
        _market_row("2020-01-06", "BBB", 21, 102),
    ]
    zero_cost = CostModel("cost:zero", 1, 0.0, 0.0)
    result = simulation_metrics(rows, 1, zero_cost)
    assert simulation_metrics(rows, 1, zero_cost) == result
    assert result["returns"] == pytest.approx([-0.1, 1 / 6], abs=1e-12)
    assert result["total_return"] == pytest.approx(0.05, abs=1e-12)
    assert result["benchmark_total_return"] == pytest.approx(0.02, abs=1e-12)
    assert result["maximum_drawdown"] == pytest.approx(-0.1, abs=1e-12)
    assert result["turnover"] == pytest.approx(1.0, abs=1e-12)
    assert result["trade_count"] == 1
    assert sum(result["final_weights"].values()) + result[
        "cash_weight"
    ] == pytest.approx(1.0, abs=1e-12)
    assert sum(result["risk_contribution"].values()) == pytest.approx(1.0, abs=1e-12)

    charged = simulation_metrics(
        rows, 1, CostModel("COST-00000000-0000-4000-8000-000000000003", 1, 1.0, 2.0)
    )
    assert charged["total_return"] < result["total_return"]
    assert charged["commission"] == pytest.approx(0.0001, abs=1e-12)
    assert charged["slippage"] == pytest.approx(0.0002, abs=1e-12)


def test_validation_can_fail_leakage_and_numerical_rules() -> None:
    periods = {
        "research_period": {"start": "2020-01-01", "end": "2020-03-31"},
        "validation_period": {"start": "2020-04-01", "end": "2020-06-30"},
        "holdout_period": {"start": "2020-07-01", "end": "2020-09-30"},
    }
    rows = [
        _market_row("2020-04-01", "AAA", 100, 100),
        _market_row("2020-04-02", "AAA", 101, 101),
        _market_row("2020-04-03", "AAA", 102, 102),
    ]
    metrics = simulation_metrics(rows, 1, CostModel("cost:zero", 1, 0, 0))
    assert all(state for _, state, _ in validation_checks(metrics, periods, rows))
    robustness = {
        "cost_stress": {**metrics, "total_return": metrics["total_return"] - 0.01},
        "parameter_alternatives": [metrics],
    }
    assert all(
        state for _, state, _ in validation_checks(metrics, periods, rows, robustness)
    )
    failed_robustness = {
        "cost_stress": {**metrics, "total_return": metrics["total_return"] + 0.01},
        "parameter_alternatives": [{**metrics, "maximum_drawdown": float("nan")}],
    }
    failed_checks = {
        key: state
        for key, state, _ in validation_checks(
            metrics, periods, rows, failed_robustness
        )
    }
    assert failed_checks["cost_sensitivity"] is False
    assert failed_checks["parameter_stability"] is False
    contaminated = [*rows, _market_row("2020-04-06", "BBB", 100, 100, "RESEARCH")]
    checks = validation_checks(metrics, periods, contaminated)
    assert {key: state for key, state, _ in checks}["pit_leakage"] is False
    overlapping = {
        **periods,
        "holdout_period": {"start": "2020-06-01", "end": "2020-09-30"},
    }
    checks = validation_checks(metrics, overlapping, rows)
    assert {key: state for key, state, _ in checks}["split_isolation"] is False


def test_metric_properties_and_artifact_hash_verification(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setenv("QF_ARTIFACT_DIR", str(tmp_path))
    storage_key, digest = put_json({"metric": "golden", "value": 1})
    assert read_json(storage_key, digest) == {"metric": "golden", "value": 1}
    repeated_key, repeated_digest = put_json({"metric": "golden", "value": 1})
    assert (repeated_key, repeated_digest) == (storage_key, digest)
    path = tmp_path / storage_key
    assert stat.S_IMODE(path.stat().st_mode) == 0o640
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ArtifactStoreError):
        read_json(storage_key, digest)

    generator = random.Random(20260810)
    cost = CostModel("cost:property", 1, 0.5, 1.0)
    for _ in range(50):
        first = generator.uniform(80, 120)
        second = first * generator.uniform(0.8, 1.2)
        third = second * generator.uniform(0.8, 1.2)
        rows = [
            _market_row("2020-01-02", "AAA", first, 100),
            _market_row("2020-01-03", "AAA", second, 101),
            _market_row("2020-01-06", "AAA", third, 102),
        ]
        result = simulation_metrics(rows, 1, cost)
        assert -1 <= result["maximum_drawdown"] <= 0
        assert result["turnover"] >= 0
        assert result["commission"] >= 0
        assert result["slippage"] >= 0
        assert sum(result["final_weights"].values()) + result[
            "cash_weight"
        ] == pytest.approx(1.0, abs=1e-12)


def test_validation_failure_blocks_approval_without_direct_state_mutation() -> None:
    client = TestClient(app)
    auth = {"Authorization": "Bearer test"}

    def headers(label: str) -> dict[str, str]:
        return auth | {"Idempotency-Key": f"engine-fail-{label}-{uuid.uuid4()}"}

    def drain(job_id: str) -> JobRow:
        for _ in range(32):
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
            assert run_once(identity="engine-fail-worker") == 1
        raise AssertionError(job_id)

    dataset_id = f"DSSET-{uuid.uuid4()}"
    dataset_root = Path(os.environ["QF_DATASET_DIR"])
    dates = [
        ("2020-01-02", "RESEARCH"),
        ("2020-02-03", "RESEARCH"),
        ("2020-04-01", "VALIDATION"),
        ("2020-06-30", "VALIDATION"),
        ("2020-07-01", "HOLDOUT"),
        ("2020-09-30", "HOLDOUT"),
    ]
    rows = [
        {
            "event_time": f"{day}T21:00:00Z",
            "available_at": f"{day}T21:01:00Z",
            "symbol": symbol,
            "close": 100 + index * multiplier,
            "benchmark_close": 100 + index,
            "partition": partition,
        }
        for index, (day, partition) in enumerate(dates)
        for symbol, multiplier in (("AAA", 1), ("BBB", 2))
    ]
    columns = list(rows[0])
    (dataset_root / f"{dataset_id}.csv").write_text(
        ",".join(columns)
        + "\n"
        + "\n".join(",".join(str(row[column]) for column in columns) for row in rows),
        encoding="utf-8",
    )
    _metadata(dataset_root, dataset_id)
    dataset_validation = client.post(
        f"/api/v1/data/datasets/{dataset_id}/validate",
        headers=headers("dataset-validation"),
        json={"check_profile": "RESEARCH_BASELINE"},
    )
    assert dataset_validation.status_code == 202
    assert drain(dataset_validation.json()["job_id"]).status == "COMPLETED"
    snapshot = client.post(
        f"/api/v1/data/datasets/{dataset_id}/snapshots",
        headers=headers("snapshot"),
        json={
            "snapshot_kind": "RESEARCH",
            "as_of_time": "2020-10-01T00:00:00Z",
            "coverage_start": "2020-01-01",
            "coverage_end": "2020-09-30",
        },
    )
    assert snapshot.status_code == 202
    assert drain(snapshot.json()["job_id"]).status == "COMPLETED"
    snapshot_id = snapshot.json()["resource_ref"]["id"]
    research = client.post(
        "/api/v1/research",
        headers=headers("research"),
        json={"title": "Failing validation", "original_user_prompt": "fail closed"},
    )
    assert research.status_code == 201
    factor = client.post(
        "/api/v1/factors",
        headers=headers("factor"),
        json={
            "research_id": research.json()["research_id"],
            "name": "Close",
            "category": "PRICE",
            "description": "Close rank",
            "economic_rationale": "Controlled failure fixture",
            "formula": {"expression": "close", "required_fields": ["close"]},
            "universe": {"asset_class": "EQUITY", "symbols": [], "universe_id": "TEST"},
            "frequency": "DAILY",
        },
    )
    assert factor.status_code == 201
    factor_analysis = client.post(
        f"/api/v1/factors/{factor.json()['factor_id']}/analyses",
        headers=headers("factor-analysis"),
        json={
            "factor_version": 1,
            "snapshot_id": snapshot_id,
            "forward_return_horizons": [1],
        },
    )
    assert factor_analysis.status_code == 202
    assert drain(factor_analysis.json()["job_id"]).status == "COMPLETED"
    strategy = client.post(
        "/api/v1/strategies",
        headers=headers("strategy"),
        json={
            "research_id": research.json()["research_id"],
            "name": "Insufficient validation observations",
            "thesis": "Validation must fail",
            "universe": {"asset_class": "EQUITY", "symbols": [], "universe_id": "TEST"},
            "signals": [
                {
                    "factor_id": factor.json()["factor_id"],
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
            "cost_model_id": "COST-00000000-0000-4000-8000-000000000003",
            "benchmark": "TEST",
            "research_period": {"start": "2020-01-01", "end": "2020-03-31"},
            "validation_period": {"start": "2020-04-01", "end": "2020-06-30"},
            "holdout_period": {"start": "2020-07-01", "end": "2020-09-30"},
            "known_failure_modes": ["insufficient sample"],
        },
    )
    assert strategy.status_code == 201
    strategy_id = strategy.json()["strategy_id"]
    backtest = client.post(
        f"/api/v1/strategies/{strategy_id}/versions/1/backtests",
        headers=headers("backtest"),
        json={
            "snapshot_id": snapshot_id,
            "cost_model_id": "COST-00000000-0000-4000-8000-000000000003",
            "engine_key": "qf-simulation-v1",  # gitleaks:allow
            "engine_version": "1.0.0",
            "parameters": [],
        },
    )
    assert backtest.status_code == 202
    assert drain(backtest.json()["job_id"]).status == "COMPLETED"
    strategy_after_backtest = client.get(
        f"/api/v1/strategies/{strategy_id}/versions/1", headers=auth
    )
    assert strategy_after_backtest.status_code == 200
    frozen = client.post(
        f"/api/v1/strategies/{strategy_id}/versions/1/freeze",
        headers=headers("freeze")
        | {"If-Match": strategy_after_backtest.headers["etag"]},
        json={"expected_spec_sha256": strategy.json()["spec_sha256"]},
    )
    assert frozen.status_code == 200
    validation = client.post(
        "/api/v1/validations",
        headers=headers("validation"),
        json={
            "strategy_id": strategy_id,
            "strategy_version": 1,
            "policy_id": "RP-00000000-0000-4000-8000-000000000004",
            "strict_engine_key": "qf-validation-v1",
            "strict_engine_version": "1.0.0",
            "test_suite_version": "1.0.0",
        },
    )
    assert validation.status_code == 202
    assert drain(validation.json()["job_id"]).status == "COMPLETED"
    validation_id = validation.json()["resource_ref"]["id"]
    result = client.get(f"/api/v1/validations/{validation_id}", headers=auth)
    assert result.status_code == 200
    assert result.json()["result"] == "FAIL"
    assert any(test["state"] == "FAIL" for test in result.json()["tests"])
    approval = client.post(
        f"/api/v1/validations/{validation_id}/holdout-approval-requests",
        headers=headers("approval") | {"If-Match": result.headers["etag"]},
        json={"reason": "must remain blocked"},
    )
    assert approval.status_code == 409
    assert approval.json()["code"] == "HOLDOUT_PREREQUISITES_INCOMPLETE"
    session = SessionLocal()
    assert (
        session.query(HoldoutExposureRow).filter_by(validation_id=validation_id).count()
        == 0
    )
    session.close()
