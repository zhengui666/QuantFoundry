"""Fresh local bootstrap policy identity, binding and smoke gates."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException

from quantfoundry.api.app import (
    CostModelVersionRow,
    ResearchPolicyVersionRow,
    RiskPolicyVersionRow,
    SessionLocal,
    content_hash,
    resolve_research_policy,
)
from quantfoundry.bootstrap.local import seed_local
from quantfoundry.domain.value_objects.public_ids import is_public_id
from scripts.fresh_local_smoke import WorkflowObservation, _drive_worker_turns

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _seed(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    workspace_id: str,
    owner_id: str,
    session_token: str,
) -> dict[str, object]:
    monkeypatch.setenv("QF_COST_MODEL_DIR", str(root / "cost-models"))
    monkeypatch.setenv("QF_POLICY_DIR", str(root / "policies"))
    monkeypatch.setenv("QF_DATASET_DIR", str(root / "datasets"))
    return seed_local(
        workspace_id=workspace_id,
        owner_id=owner_id,
        owner_email=f"{owner_id}@local.invalid",
        session_token=session_token,
    )


def _file_payload(root: Path, directory: str, public_id: object) -> dict[str, object]:
    value = json.loads(
        (root / directory / f"{public_id}.json").read_text(encoding="utf-8")
    )
    assert isinstance(value, dict)
    return value


def test_seed_local_replay_and_cross_workspace_policy_isolation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    workspace_a = f"bootstrap-a-{uuid.uuid4()}"
    workspace_b = f"bootstrap-b-{uuid.uuid4()}"
    owner_a = f"owner-a-{uuid.uuid4()}"
    owner_b = f"owner-b-{uuid.uuid4()}"
    first = _seed(
        tmp_path,
        monkeypatch,
        workspace_id=workspace_a,
        owner_id=owner_a,
        session_token=f"token-a-{uuid.uuid4()}",
    )
    replay = _seed(
        tmp_path,
        monkeypatch,
        workspace_id=workspace_a,
        owner_id=owner_a,
        session_token=str(first["session_token"]),
    )
    second = _seed(
        tmp_path,
        monkeypatch,
        workspace_id=workspace_b,
        owner_id=owner_b,
        session_token=f"token-b-{uuid.uuid4()}",
    )
    assert replay == first

    public_kinds = {
        "research_policy_id": "research_policy",
        "validation_policy_id": "research_policy",
        "risk_policy_id": "risk_policy",
        "cost_model_id": "cost_model",
        "dataset_id": "dataset",
    }
    for result in (first, second):
        for field, kind in public_kinds.items():
            assert is_public_id(kind, str(result[field]))
        assert len({str(result[field]) for field in public_kinds}) == len(public_kinds)
    assert {str(first[field]) for field in public_kinds}.isdisjoint(
        {str(second[field]) for field in public_kinds}
    )

    session = SessionLocal()
    try:
        for workspace_id, result in (
            (workspace_a, first),
            (workspace_b, second),
        ):
            rows = (
                session.query(ResearchPolicyVersionRow)
                .filter_by(workspace_id=workspace_id, status="ACTIVE")
                .all()
            )
            by_family = {row.policy_family: row for row in rows}
            assert set(by_family) == {"research", "validation"}
            for family, field in (
                ("research", "research_policy_id"),
                ("validation", "validation_policy_id"),
            ):
                payload = _file_payload(tmp_path, "policies", result[field])
                row = by_family[family]
                assert row.policy_id == result[field]
                assert row.rules == payload
                assert row.content_sha256 == content_hash(payload)
            risk = (
                session.query(RiskPolicyVersionRow)
                .filter_by(
                    workspace_id=workspace_id,
                    policy_id=result["risk_policy_id"],
                )
                .one()
            )
            risk_payload = _file_payload(tmp_path, "policies", result["risk_policy_id"])
            assert risk.content_sha256 == content_hash(risk_payload)
            cost = (
                session.query(CostModelVersionRow)
                .filter_by(
                    workspace_id=workspace_id,
                    cost_model_id=result["cost_model_id"],
                )
                .one()
            )
            cost_payload = _file_payload(
                tmp_path, "cost-models", result["cost_model_id"]
            )
            assert cost.content_sha256 == content_hash(cost_payload)

        assert (
            resolve_research_policy(
                session, workspace_a, str(first["research_policy_id"])
            ).policy_family
            == "research"
        )
        failures: list[HTTPException] = []
        for invalid_id in (
            first["validation_policy_id"],
            second["research_policy_id"],
        ):
            with pytest.raises(HTTPException) as caught:
                resolve_research_policy(session, workspace_a, str(invalid_id))
            failures.append(caught.value)
        normalized = [
            (
                error.status_code,
                error.detail["code"],
                error.detail["detail"],
                error.detail["field_errors"],
                error.detail["context"],
            )
            for error in failures
        ]
        assert normalized == [normalized[0], normalized[0]]
    finally:
        session.close()

    validation_path = tmp_path / "policies" / f"{first['validation_policy_id']}.json"
    validation_path.write_text("{}\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="refusing to overwrite different"):
        _seed(
            tmp_path,
            monkeypatch,
            workspace_id=workspace_a,
            owner_id=owner_a,
            session_token=str(first["session_token"]),
        )


def test_worker_driver_tolerates_bounded_slow_scheduling() -> None:
    turns = {"agent": 0}

    def run_agent(_turn: int) -> int:
        turns["agent"] += 1
        return 1 if turns["agent"] == 4 else 0

    observed, diagnostic = _drive_worker_turns(
        run_agent,
        lambda _turn: 0,
        lambda: WorkflowObservation(
            finished=turns["agent"] >= 4,
            terminal_failure=False,
            analyze_wait=turns["agent"] == 2,
            diagnostic={"agent_runs": [{"status": "RUNNING"}]},
        ),
        max_turns=8,
        max_idle_turns=4,
    )
    assert observed is True
    assert diagnostic == {"agent_runs": [{"status": "RUNNING"}]}


def test_worker_driver_reports_redacted_terminal_failure() -> None:
    diagnostic = {
        "agent_runs": [{"status": "WAITING_USER", "credential": "secret"}],
        "jobs": [{"status": "FAILED", "error_code": "JOB_FAILED"}],
    }
    with pytest.raises(RuntimeError, match="terminal failure") as caught:
        _drive_worker_turns(
            lambda _turn: 1,
            lambda _turn: 0,
            lambda: WorkflowObservation(
                finished=False,
                terminal_failure=True,
                analyze_wait=False,
                diagnostic=diagnostic,
            ),
        )
    assert '"credential": "[REDACTED]"' in str(caught.value)
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("repeat", range(3))
def test_fresh_local_smoke_runs_without_test_fixture_state(
    tmp_path: Path, repeat: int
) -> None:
    smoke_root = tmp_path / f"run-{repeat}"
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("QF_") and key != "PYTHONPATH"
    }
    environment.update(
        {
            "QF_ENV": "local",
            "QF_ENVIRONMENT": "local",
            # Reproduce root CI's inherited pytest provider settings.  The
            # standalone smoke must still exercise its own HTTP provider.
            "QF_AGENT_PROVIDER": "local-deterministic",
            "QF_AGENT_MODEL": "inherited-test-model",
            "QF_OPENAI_BASE_URL": "http://127.0.0.1:1/v1",
        }
    )
    result = subprocess.run(
        [
            sys.executable,
            str(BACKEND_ROOT / "scripts/fresh_local_smoke.py"),
            "--root",
            str(smoke_root),
        ],
        cwd=BACKEND_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["status"] == "PASS"
    assert payload["root"] == str(smoke_root.resolve())
    assert payload["experiment_id"].startswith("EXP-")
    assert payload["tool_call_count"] == 4
