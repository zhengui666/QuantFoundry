import json
import uuid
from datetime import datetime

from fastapi.testclient import TestClient

from quantfoundry.api.app import (
    ResearchRow,
    SessionLocal,
    StrategyRow,
    StrategyVersionRow,
    ValidationRow,
    app,
    strategy_storage_fields,
)
from quantfoundry.contracts.openapi.runtime import now

c = TestClient(app)
H = {"Authorization": "Bearer test"}


def test_health_public_and_auth_guard():
    assert c.get("/api/v1/system/health").status_code == 200
    assert c.get("/api/v1/research").status_code == 401


def test_research_idempotency_and_etag():
    headers = H | {"Idempotency-Key": "test-research-idempotency"}
    payload = {"title": "P0", "original_user_prompt": "test"}
    one = c.post("/api/v1/research", headers=headers, json=payload)
    two = c.post("/api/v1/research", headers=headers, json=payload)
    assert one.status_code == two.status_code == 201
    assert one.json()["research_id"] == two.json()["research_id"]
    assert c.get(f"/api/v1/research/{one.json()['research_id']}", headers=H).headers[
        "etag"
    ]


def test_holdout_cannot_run_without_approval():
    research_id = f"RSCH-{uuid.uuid4()}"
    strategy_id = f"STRAT-{uuid.uuid4()}"
    created_at = now()
    created_at_value = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    research_detail = {
        "research_id": research_id,
        "title": "Holdout fixture",
        "original_user_prompt": "Verify approval guard",
        "normalized_question": None,
        "research_policy_id": "RP-00000000-0000-4000-8000-000000000001",
        "status": "DRAFT",
        "evidence_status": "INSUFFICIENT",
        "current_revision_no": 1,
        "active_plan_version": None,
        "director_agent_version": None,
        "current_agent_run_id": None,
        "current_job_id": None,
        "revision": 1,
        "action_capabilities": [],
        "created_at": created_at,
        "updated_at": created_at,
        "completed_at": None,
    }
    session = SessionLocal()
    session.add(
        ResearchRow(
            id=research_id,
            workspace_id="test-workspace",
            status="DRAFT",
            revision=1,
            title="Holdout fixture",
            original_user_prompt="Holdout fixture",
            created_at=created_at_value,
            updated_at=created_at_value,
            detail=json.dumps(research_detail),
        )
    )
    session.add(
        StrategyRow(
            id=strategy_id,
            workspace_id="test-workspace",
            research_id=research_id,
            name="Holdout fixture",
            revision=1,
            detail="{}",
        )
    )
    strategy_version_id = f"SV-{uuid.uuid4()}"
    strategy_detail = {
        "thesis": "holdout fixture",
        "universe": {"asset_class": "EQUITY", "symbols": ["AAA"]},
        "signals": [],
        "rules": {
            "selection_count": 1,
            "weighting": "EQUAL",
            "rebalance_frequency": "DAILY",
            "long_short": False,
            "leverage_limit": "1",
            "position_limit": "1",
        },
        "benchmark": "SPY",
        "known_failure_modes": [],
        "cost_model_id": "COST-00000000-0000-4000-8000-000000000003",
        "research_period": {"start": "2020-01-01", "end": "2020-06-30"},
        "validation_period": {"start": "2020-07-01", "end": "2020-09-30"},
        "holdout_period": {"start": "2020-10-01", "end": "2020-12-31"},
    }
    session.add(
        StrategyVersionRow(
            id=strategy_version_id,
            workspace_id="test-workspace",
            strategy_id=strategy_id,
            **strategy_storage_fields(
                strategy_detail, lifecycle_state="FROZEN", is_frozen=True
            ),
            version=1,
            state="FROZEN",
            spec_sha256="0" * 64,
            revision=1,
            detail=json.dumps(strategy_detail),
        )
    )
    validation_id = f"VAL-{uuid.uuid4()}"
    session.add(
        ValidationRow(
            id=validation_id,
            workspace_id="test-workspace",
            strategy_version_id=strategy_version_id,
            status="QUEUED",
            holdout_state="LOCKED",
            exposure_count=0,
            revision=1,
            detail="{}",
        )
    )
    session.commit()
    session.close()
    blocked = c.post(
        f"/api/v1/validations/{validation_id}/holdout-runs",
        headers=H
        | {
            "Idempotency-Key": "test-holdout-run-0001",
            "If-Match": f'W/"{validation_id}:1"',
        },
        json={"approval_id": "APR-00000000-0000-4000-8000-000000000099"},
    )
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "HOLDOUT_APPROVAL_REQUIRED"
