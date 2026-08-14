import os

from fastapi.testclient import TestClient

from app.control_plane import ControlSessionLocal, GeneralAccessKey, issue_access_key
from app.main import app


def test_general_key_cookie_csrf_and_database_backed_configuration_flow() -> None:
    client = TestClient(app)
    raw_key = os.getenv("QF_TEST_GENERAL_KEY")
    if raw_key is None:
        raw_key = issue_access_key("primary")

    login = client.post("/api/v1/auth/login", json={"key": raw_key})
    assert login.status_code == 200
    session = login.json()["session"]
    csrf = session["csrf_token"]
    assert session["principal"] == "OWNER"
    assert raw_key not in login.text
    with ControlSessionLocal() as control:
        stored = control.get(GeneralAccessKey, session["key_id"])
        assert stored is not None
        assert raw_key not in stored.verifier_phc

    current = client.get("/api/v1/auth/session")
    assert current.status_code == 200
    assert current.json()["key_id"] == session["key_id"]
    csrf = current.json()["csrf_token"]

    catalog = client.get("/api/v1/configuration/catalog")
    active = client.get("/api/v1/configuration/active")
    assert catalog.status_code == active.status_code == 200
    assert {entry["key"] for entry in catalog.json()["entries"]} >= {
        "access.session",
        "ai.remote_codex",
    }
    active_revision = active.json()["active_revision"]
    etag = active.headers["etag"]

    no_csrf = client.post(
        "/api/v1/auth/access-keys",
        headers={"Idempotency-Key": "ux001-no-csrf-00000001"},
        json={"label": "rejected"},
    )
    assert no_csrf.status_code == 403
    assert no_csrf.json()["code"] == "CSRF_REQUIRED"

    issued = client.post(
        "/api/v1/auth/access-keys",
        headers={"Idempotency-Key": "ux001-create-key-000001", "X-CSRF-Token": csrf},
        json={"label": "secondary"},
    )
    assert issued.status_code == 201
    issued_secret = issued.json()["secret"]
    assert issued_secret.startswith("qfk_gak_")
    listed = client.get("/api/v1/auth/access-keys")
    assert listed.status_code == 200
    assert issued_secret not in listed.text

    candidate = client.put(
        "/api/v1/configuration/candidate",
        headers={
            "If-Match": etag,
            "Idempotency-Key": "ux001-config-candidate-0001",
            "X-CSRF-Token": csrf,
        },
        json={
            "base_revision": active_revision,
            "values": [
                {
                    "key": "access.session",
                    "value": {
                        "idle_ttl_seconds": 900,
                        "absolute_ttl_seconds": 86400,
                        "rate_limit_per_minute": 8,
                    },
                },
                {
                    "key": "ai.remote_codex",
                    "secret": '{"endpoint":"https://codex.example/v1","model":"qf-test","timeout_seconds":30,"max_retries":1,"concurrency":2,"credential":"one-time-secret"}',
                },
            ],
        },
    )
    assert candidate.status_code == 200
    candidate_revision = candidate.json()["revision"]

    validated = client.post(
        "/api/v1/configuration/candidate/validate",
        headers={"Idempotency-Key": "ux001-config-validate-0001", "X-CSRF-Token": csrf},
    )
    assert validated.status_code == 200
    assert validated.json()["status"] == "VALID"

    activated = client.post(
        "/api/v1/setup/complete",
        headers={
            "If-Match": etag,
            "Idempotency-Key": "ux001-setup-complete-0001",
            "X-CSRF-Token": csrf,
        },
        json={"configuration_revision": candidate_revision},
    )
    assert activated.status_code == 200
    assert activated.json()["active_revision"] == candidate_revision
    assert "one-time-secret" not in activated.text
    assert activated.headers["etag"] == f'W/"config:{candidate_revision}"'

    logout = client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": csrf},
    )
    assert logout.status_code == 204
    assert client.get("/api/v1/configuration/catalog").status_code == 401
