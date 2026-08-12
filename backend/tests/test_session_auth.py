"""Database-backed opaque bearer-session authentication proofs."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from quantfoundry.api.app import (
    DataSource,
    JobRow,
    ResearchPolicyVersionRow,
    SessionLocal,
    SessionToken,
    User,
    Workspace,
    app,
    content_hash,
)


def _issue(role: str, *, expired: bool = False) -> tuple[str, str]:
    suffix = uuid.uuid4().hex
    user_id = f"USR-{suffix}"
    workspace_id = f"WS-{suffix}"
    token = f"opaque-session-{suffix}"
    session = SessionLocal()
    session.add(User(id=user_id, email=f"{suffix}@example.test", role=role, revision=1))
    session.add(
        Workspace(
            id=workspace_id,
            owner_id=user_id,
            name="Auth test workspace",
            revision=1,
        )
    )
    session.flush()
    if role == "OWNER":
        now = datetime.now(UTC)
        session.add(
            ResearchPolicyVersionRow(
                id=f"RPV-{suffix}",
                workspace_id=workspace_id,
                policy_id=f"RP-{uuid.uuid4()}",
                version=1,
                status="ACTIVE",
                content_sha256=content_hash({"kind": "research_policy", "version": 1}),
                created_by=user_id,
                created_at=now,
                activated_at=now,
            )
        )
    session.add(
        SessionToken(
            token_sha256=hashlib.sha256(token.encode()).hexdigest(),
            actor_id=user_id,
            workspace_id=workspace_id,
            expires_at=datetime.now(UTC)
            + (timedelta(minutes=-1) if expired else timedelta(minutes=5)),
        )
    )
    session.commit()
    session.close()
    return token, hashlib.sha256(token.encode()).hexdigest()


def test_database_session_accepts_owner_and_rejects_revocation() -> None:
    token, digest = _issue("OWNER")
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/research", headers=headers).status_code == 200

    session = SessionLocal()
    row = session.get(SessionToken, digest)
    assert row is not None
    row.revoked_at = datetime.now(UTC)
    session.commit()
    session.close()
    response = client.get("/api/v1/research", headers=headers)
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


def test_database_session_enforces_expiry_and_role_authority() -> None:
    expired, _ = _issue("OWNER", expired=True)
    viewer, _ = _issue("VIEWER")
    client = TestClient(app)
    assert (
        client.get(
            "/api/v1/research",
            headers={"Authorization": f"Bearer {expired}"},
        ).status_code
        == 401
    )
    denied = client.get(
        "/api/v1/research",
        headers={"Authorization": f"Bearer {viewer}"},
    )
    assert denied.status_code == 403
    assert denied.json()["code"] == "PERMISSION_DENIED"


def test_owner_sessions_cannot_cross_workspace_aggregates_or_dataset_sources() -> None:
    owner_a, digest_a = _issue("OWNER")
    owner_b, digest_b = _issue("OWNER")
    client = TestClient(app)
    auth_a = {"Authorization": f"Bearer {owner_a}"}
    auth_b = {"Authorization": f"Bearer {owner_b}"}
    research = client.post(
        "/api/v1/research",
        headers=auth_a | {"Idempotency-Key": f"cross-research-{uuid.uuid4()}"},
        json={"title": "Workspace A", "original_user_prompt": "Stay scoped"},
    )
    assert research.status_code == 201
    research_id = research.json()["research_id"]
    foreign = client.get(f"/api/v1/research/{research_id}", headers=auth_b)
    absent = client.get(
        f"/api/v1/research/RSCH-{uuid.uuid4()}",
        headers=auth_b,
    )
    assert (foreign.status_code, foreign.json()["code"]) == (
        404,
        "RESOURCE_NOT_FOUND",
    )
    assert (absent.status_code, absent.json()["code"]) == (
        404,
        "RESOURCE_NOT_FOUND",
    )
    assert all(
        item["research_id"] != research_id
        for item in client.get("/api/v1/research", headers=auth_b).json()["items"]
    )

    dataset_id = f"DSSET-{uuid.uuid4()}"
    session = SessionLocal()
    session_a = session.get(SessionToken, digest_a)
    session_b = session.get(SessionToken, digest_b)
    assert session_a is not None and session_b is not None
    session.add(
        DataSource(
            id=dataset_id,
            workspace_id=session_a.workspace_id,
            provider_id="LOCAL_DETERMINISTIC_DATA",
            status="VALID",
            revision=1,
        )
    )
    session.commit()
    workspace_b = session_b.workspace_id
    session.close()
    blocked_snapshot = client.post(
        f"/api/v1/data/datasets/{dataset_id}/snapshots",
        headers=auth_b | {"Idempotency-Key": f"cross-snapshot-{uuid.uuid4()}"},
        json={
            "snapshot_kind": "RESEARCH",
            "as_of_time": "2025-01-31T00:00:00Z",
            "coverage_start": "2025-01-01",
            "coverage_end": "2025-01-31",
        },
    )
    assert blocked_snapshot.status_code == 409
    assert blocked_snapshot.json()["code"] == "DATA_QUALITY_BLOCKED"
    verification = SessionLocal()
    assert (
        verification.query(JobRow)
        .filter_by(workspace_id=workspace_b, job_type="SNAPSHOT_CREATE")
        .count()
        == 0
    )
    verification.close()
