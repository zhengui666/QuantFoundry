import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import func

from quantfoundry.api.app import Event, SessionLocal, app
from quantfoundry.api.v1.contract_route import CanonicalRoute
from quantfoundry.contracts.openapi.runtime import validated_payload
from quantfoundry.workers.main import cleanup_expired_events


def test_contract_validation_does_not_manufacture_missing_fields() -> None:
    with pytest.raises(ValidationError):
        validated_payload("ResearchDetail", {"research_id": "not-a-complete-response"})


def test_invalid_handler_output_fails_closed_without_normalization() -> None:
    invalid_app = FastAPI()
    invalid_app.router.route_class = CanonicalRoute

    @invalid_app.get("/api/v1/system/health")
    def invalid_health() -> dict[str, str]:
        return {"status": "HEALTHY"}

    response = TestClient(invalid_app).get("/api/v1/system/health")
    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
    assert "checked_at" not in response.json()


@pytest.mark.parametrize(
    "etag",
    [None, "settings:1", 'W/"settings:test-workspace:2"'],
)
def test_complete_setup_etag_corruption_fails_closed(etag: str | None) -> None:
    invalid_app = FastAPI()
    invalid_app.router.route_class = CanonicalRoute
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    response_body = {
        "settings_id": "settings:test-workspace",
        "revision": 1,
        "language": "zh-CN",
        "timezone": "Asia/Shanghai",
        "base_currency": "CNY",
        "number_format_locale": "zh-CN",
        "ai_connection_id": "CONN-test",
        "default_data_provider_id": None,
        "default_benchmark": "CSI300",
        "default_frequency": "DAILY",
        "default_research_start": None,
        "initial_paper_capital": "100000",
        "research_policy_id": "RP-00000000-0000-4000-8000-000000000001",
        "risk_policy_id": "RISK-00000000-0000-4000-8000-000000000002",
        "cost_model_id": "COST-00000000-0000-4000-8000-000000000003",
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    @invalid_app.post("/api/v1/setup/complete")
    def invalid_setup() -> JSONResponse:
        headers = {"ETag": etag} if etag is not None else None
        return JSONResponse(response_body, headers=headers)

    response = TestClient(invalid_app).post(
        "/api/v1/setup/complete",
        headers={"Idempotency-Key": "etag-corruption-proof"},
        json={
            key: value
            for key, value in response_body.items()
            if key
            not in {
                "settings_id",
                "revision",
                "created_at",
                "updated_at",
            }
        },
    )
    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"


def test_request_models_enforce_required_enum_pattern_and_additional_properties() -> (
    None
):
    client = TestClient(app)
    auth = {"Authorization": "Bearer test"}
    cases = [
        (
            "/api/v1/research",
            auth | {"Idempotency-Key": "missing-field-key-0001"},
            {"title": "missing prompt"},
        ),
        (
            "/api/v1/research",
            auth | {"Idempotency-Key": "additional-field-key-1"},
            {
                "title": "extra",
                "original_user_prompt": "extra",
                "undocumented": True,
            },
        ),
        (
            # Invalid public-ID fixture: contract validation must reject this legacy prefix.
            "/api/v1/data/datasets/DSSET-valid/validate",
            auth | {"Idempotency-Key": "test-api-key-unavailable"},
            {"check_profile": "NOT_CANONICAL"},
        ),
        (
            "/api/v1/data/datasets/not-prefixed/validate",
            auth | {"Idempotency-Key": "invalid-path-key-00001"},
            {"check_profile": "RESEARCH_BASELINE"},
        ),
        (
            "/api/v1/research",
            auth | {"Idempotency-Key": "short"},
            {"title": "short key", "original_user_prompt": "short key"},
        ),
    ]
    for path, headers, body in cases:
        response = client.post(path, headers=headers, json=body)
        assert response.status_code == 422
        assert response.json()["code"] == "INVALID_REQUEST"


def test_idempotency_conflict_is_rejected() -> None:
    client = TestClient(app)
    headers = {
        "Authorization": "Bearer test",
        "Idempotency-Key": "conflict-key-00000001",
    }
    assert (
        client.post(
            "/api/v1/research",
            headers=headers,
            json={"title": "one", "original_user_prompt": "one"},
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/api/v1/research",
            headers=headers,
            json={"title": "two", "original_user_prompt": "two"},
        ).status_code
        == 409
    )


def test_sse_replays_persisted_events() -> None:
    client = TestClient(app)
    headers = {
        "Authorization": "Bearer test",
        "Idempotency-Key": "sse-replay-key-000001",
    }
    assert (
        client.post(
            "/api/v1/research",
            headers=headers,
            json={"title": "sse", "original_user_prompt": "sse"},
        ).status_code
        == 201
    )
    response = client.get(
        "/api/v1/events/stream",
        headers={"Authorization": "Bearer test", "Last-Event-ID": "0"},
    )
    assert response.status_code == 200
    assert "event:" in response.text


def test_event_retention_physically_deletes_expired_events() -> None:
    session = SessionLocal()
    event_id = f"EVT-{uuid.uuid4()}"
    sequence = (
        session.query(func.max(Event.sequence))
        .filter_by(workspace_id="test-workspace")
        .scalar()
        or 0
    ) + 1
    session.add(
        Event(
            sequence=sequence,
            event_id=event_id,
            workspace_id="test-workspace",
            request_id="REQ-expired-event",
            event_type="system.health.updated",
            object_type="event_stream",
            object_id=event_id,
            object_revision=sequence,
            revision=sequence,
            payload="{}",
            occurred_at=datetime.now(UTC),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
    )
    session.commit()
    session.close()
    assert cleanup_expired_events() >= 1
