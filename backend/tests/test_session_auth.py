"""Single-owner Control DB cookie-session authentication proofs."""

from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from app.control_plane import ControlSessionLocal, OwnerSession, issue_access_key
from app.main import app

_RAW_KEY: str | None = None


def _login(client: TestClient) -> str:
    global _RAW_KEY
    if _RAW_KEY is None:
        _RAW_KEY = issue_access_key("session-auth")
        os.environ["QF_TEST_GENERAL_KEY"] = _RAW_KEY
    raw_key = _RAW_KEY
    response = client.post("/api/v1/auth/login", json={"key": raw_key})
    assert response.status_code == 200
    return str(client.cookies.get("qf_session"))


def test_database_session_accepts_owner_and_rejects_revocation() -> None:
    client = TestClient(app)
    token = _login(client)
    assert client.get("/api/v1/research").status_code == 200

    with ControlSessionLocal.begin() as control:
        row = (
            control.query(OwnerSession)
            .filter_by(token_sha256=hashlib.sha256(token.encode()).hexdigest())
            .one_or_none()
        )
        assert row is not None
        row.revoked_at = datetime.now(UTC)
        row.revoke_reason = "TEST"
    assert client.get("/api/v1/research").status_code == 401


def test_database_session_enforces_expiry_and_single_owner_principal() -> None:
    client = TestClient(app)
    token = _login(client)
    with ControlSessionLocal.begin() as control:
        row = (
            control.query(OwnerSession)
            .filter_by(token_sha256=hashlib.sha256(token.encode()).hexdigest())
            .one_or_none()
        )
        assert row is not None
        row.absolute_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert client.get("/api/v1/research").status_code == 401


def test_bearer_tokens_cannot_bypass_cookie_session() -> None:
    client = TestClient(app)
    _login(client)
    unauthenticated = TestClient(app)
    response = unauthenticated.get(
        "/api/v1/research",
        headers={"Authorization": "Bearer opaque-session-not-a-cookie"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
