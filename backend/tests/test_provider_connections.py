from __future__ import annotations

import json
import threading
import uuid

import httpx
import pytest
from fastapi.testclient import TestClient

from app.local_provider import LocalProviderServer, create_server
from app.main import ModelProviderConnectionRow, SessionLocal, app

OWNER = {"Authorization": "Bearer test"}


def _key(label: str) -> dict[str, str]:
    return {"Idempotency-Key": f"provider-{label}-{uuid.uuid4()}"}


def _setup_payload(connection_id: str) -> dict[str, object]:
    return {
        "language": "zh-CN",
        "timezone": "Asia/Shanghai",
        "base_currency": "CNY",
        "number_format_locale": "zh-CN",
        "ai_connection_id": connection_id,
        "default_benchmark": "CSI300",
        "default_frequency": "DAILY",
        "initial_paper_capital": "100000",
        "research_policy_id": "RP-00000000-0000-4000-8000-000000000001",
        "risk_policy_id": "RISK-00000000-0000-4000-8000-000000000002",
        "cost_model_id": "COST-00000000-0000-4000-8000-000000000003",
    }


def _start_provider(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
    *,
    api_key: str,
    model_name: str,
) -> LocalProviderServer:
    server = create_server(
        "127.0.0.1",
        0,
        api_key=api_key,
        model_name=model_name,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def stop() -> None:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    request.addfinalizer(stop)
    host, port = server.server_address
    monkeypatch.setenv("QF_OPENAI_BASE_URL", f"http://{host}:{port}/v1")
    return server


def test_local_provider_is_environment_and_bearer_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    request: pytest.FixtureRequest,
) -> None:
    monkeypatch.setenv("QF_ENVIRONMENT", "production")
    monkeypatch.setenv("QF_ENV", "production")
    with pytest.raises(RuntimeError, match="forbidden"):
        create_server("127.0.0.1", 0, api_key="local-provider-credential")
    monkeypatch.setenv("QF_ENVIRONMENT", "local")
    monkeypatch.setenv("QF_ENV", "development")
    with pytest.raises(RuntimeError, match="disagree"):
        create_server("127.0.0.1", 0, api_key="local-provider-credential")
    monkeypatch.setenv("QF_ENV", "local")
    api_key = "local-provider-credential"
    provider = _start_provider(
        monkeypatch,
        request,
        api_key=api_key,
        model_name="local-model",
    )
    host, port = provider.server_address
    base_url = f"http://{host}:{port}"
    assert httpx.get(f"{base_url}/v1/models").status_code == 401
    assert (
        httpx.get(
            f"{base_url}/v1/models",
            headers={"Authorization": "Bearer"},
        ).status_code
        == 401
    )
    models = httpx.get(
        f"{base_url}/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    assert models.status_code == 200
    assert models.json()["data"] == [{"id": "local-model"}]
    assert (
        httpx.post(
            f"{base_url}/v1/chat/completions",
            headers={"Authorization": "Bearer"},
            json={"model": "local-model", "messages": []},
        ).status_code
        == 401
    )
    completion_request = {
        "model": "local-model",
        "messages": [
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "context": {
                            "role": "RESEARCH_DIRECTOR",
                            "research": {
                                "research_id": (
                                    "RSCH-00000000-0000-4000-8000-000000000301"
                                )
                            },
                            "dataset_ids": [
                                "DSSET-00000000-0000-4000-8000-000000000302"
                            ],
                        },
                        "tool_results": [],
                    }
                ),
            }
        ],
    }
    completion = httpx.post(
        f"{base_url}/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json=completion_request,
    )
    assert completion.status_code == 200
    action = json.loads(completion.json()["choices"][0]["message"]["content"])
    assert action == {
        "type": "tool",
        "name": "validate_dataset",
        "arguments": {"dataset_id": "DSSET-00000000-0000-4000-8000-000000000302"},
    }
    replay = httpx.post(
        f"{base_url}/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json=completion_request,
    )
    assert replay.status_code == 200
    assert json.loads(replay.json()["choices"][0]["message"]["content"]) == action


def test_openai_connection_validation_calls_provider_and_encrypts_at_rest(
    monkeypatch,
    request: pytest.FixtureRequest,
) -> None:
    credential = "setup-secret-never-persist-plaintext"
    provider = _start_provider(
        monkeypatch,
        request,
        api_key=credential,
        model_name="model-a",
    )
    monkeypatch.setenv("QF_OPENAI_MODELS", "model-a,model-b")
    monkeypatch.delenv("QF_OPENAI_API_KEY", raising=False)
    response = TestClient(app).post(
        "/api/v1/setup/provider-connections/validate",
        headers=OWNER | _key("encrypted"),
        json={
            "provider_id": "OPENAI_COMPATIBLE",
            "kind": "AI",
            "model_name": "model-a",
            "credential": credential,
        },
    )
    assert response.status_code == 200
    assert response.json()["state"] == "SUCCESS"
    assert credential not in response.text
    assert provider.request_log == [
        {"method": "GET", "path": "/v1/models", "authorized": True}
    ]
    session = SessionLocal()
    row = session.get(ModelProviderConnectionRow, response.json()["connection_id"])
    assert row is not None
    assert credential.encode() not in row.ciphertext
    assert row.nonce and row.key_id == "test-key-v1"
    assert row.status == "VALIDATED"
    session.close()


def test_remote_codex_catalog_and_validation_use_codex_transport(
    monkeypatch,
    request: pytest.FixtureRequest,
) -> None:
    credential = "remote-codex-secret-never-persist-plaintext"
    provider = _start_provider(
        monkeypatch,
        request,
        api_key=credential,
        model_name="codex-model",
    )
    host, port = provider.server_address
    monkeypatch.setenv("QF_CODEX_BASE_URL", f"http://{host}:{port}/v1")
    monkeypatch.setenv("QF_CODEX_MODELS", "codex-model")
    monkeypatch.setenv("QF_CODEX_DISPLAY_NAME", "Remote Codex test")
    monkeypatch.delenv("QF_OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("QF_OPENAI_MODELS", raising=False)
    catalog = TestClient(app).get("/api/v1/setup/capabilities", headers=OWNER)
    assert catalog.status_code == 200
    ai_providers = [
        provider
        for provider in catalog.json()["providers"]
        if provider["kind"] == "AI" and provider["provider_id"] != "TEST_AI"
    ]
    assert ai_providers == [
        {
            "provider_id": "REMOTE_CODEX",
            "display_name": "Remote Codex test",
            "kind": "AI",
            "connection_test_supported": True,
            "models": [
                {"model_name": "codex-model", "connection_test_supported": True}
            ],
            "data_capabilities": [],
        }
    ]
    response = TestClient(app).post(
        "/api/v1/setup/provider-connections/validate",
        headers=OWNER | _key("remote-codex"),
        json={
            "provider_id": "REMOTE_CODEX",
            "kind": "AI",
            "model_name": "codex-model",
            "credential": credential,
        },
    )
    assert response.status_code == 200
    assert response.json()["state"] == "SUCCESS"
    assert provider.request_log == [
        {"method": "GET", "path": "/v1/models", "authorized": True}
    ]


def test_remote_codex_agent_config_projects_singleton_and_rejects_override(
    monkeypatch,
) -> None:
    monkeypatch.setenv("QF_AGENT_PROVIDER", "remote-codex")
    monkeypatch.setenv("QF_CODEX_BASE_URL", "https://codex.example/v1")
    monkeypatch.setenv("QF_CODEX_MODEL", "codex-model")
    client = TestClient(app)
    current = client.get("/api/v1/agents/RESEARCH_DIRECTOR/config", headers=OWNER)
    assert current.status_code == 200
    assert current.json()["model_provider"] == "remote-codex"
    projected_model = current.json()["model_name"]
    assert projected_model != "codex-model"
    rejected = client.put(
        "/api/v1/agents/RESEARCH_DIRECTOR/config",
        headers=OWNER | {"If-Match": current.headers["etag"]},
        json={"model_name": "second-model"},
    )
    assert rejected.status_code == 422
    accepted = client.put(
        "/api/v1/agents/RESEARCH_DIRECTOR/config",
        headers=OWNER | {"If-Match": current.headers["etag"]},
        json={"enabled": False},
    )
    assert accepted.status_code == 200
    assert accepted.json()["model_provider"] == "remote-codex"
    assert accepted.json()["model_name"] == projected_model
    restored = client.put(
        "/api/v1/agents/RESEARCH_DIRECTOR/config",
        headers=OWNER | {"If-Match": accepted.headers["etag"]},
        json={"enabled": True},
    )
    assert restored.status_code == 200


def test_provider_failure_has_no_connection_ref_or_persisted_credential(
    monkeypatch,
    request: pytest.FixtureRequest,
) -> None:
    provider = _start_provider(
        monkeypatch,
        request,
        api_key="valid-provider-credential",
        model_name="model-a",
    )
    monkeypatch.setenv("QF_OPENAI_MODELS", "model-a")
    session = SessionLocal()
    before = session.query(ModelProviderConnectionRow).count()
    session.close()
    response = TestClient(app).post(
        "/api/v1/setup/provider-connections/validate",
        headers=OWNER | _key("denied"),
        json={
            "provider_id": "OPENAI_COMPATIBLE",
            "kind": "AI",
            "model_name": "model-a",
            "credential": "bad-credential",
        },
    )
    assert response.status_code == 200
    assert response.json()["state"] == "FAILED"
    assert response.json()["error_code"] == "CREDENTIAL_INVALID"
    assert "connection_id" not in response.json()
    assert provider.request_log == [
        {"method": "GET", "path": "/v1/models", "authorized": False}
    ]
    session = SessionLocal()
    assert session.query(ModelProviderConnectionRow).count() == before
    session.close()


def test_missing_encryption_key_hides_unusable_catalog_and_fails_closed(
    monkeypatch,
) -> None:
    monkeypatch.delenv("QF_CREDENTIAL_ENCRYPTION_KEY")
    monkeypatch.delenv("QF_CREDENTIAL_ENCRYPTION_KEY_ID")
    client = TestClient(app)
    catalog = client.get("/api/v1/setup/capabilities", headers=OWNER)
    assert catalog.status_code == 200
    assert catalog.json()["providers"] == []
    validation = client.post(
        "/api/v1/setup/provider-connections/validate",
        headers=OWNER | _key("missing-key"),
        json={
            "provider_id": "TEST_AI",
            "kind": "AI",
            "model_name": "test-model",
            "credential": "valid-test-credential",
        },
    )
    assert validation.status_code == 200
    assert validation.json()["state"] == "FAILED"
    assert validation.json()["error_code"] == "CREDENTIAL_NOT_CONFIGURED"
    assert "connection_id" not in validation.json()


def test_legacy_connection_setup_payload_is_rejected() -> None:
    response = TestClient(app).post(
        "/api/v1/setup/complete",
        headers=OWNER | _key("legacy-setup"),
        json=_setup_payload(str(uuid.uuid4())),
    )
    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_REQUEST"
