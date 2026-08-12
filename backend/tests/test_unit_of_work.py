"""Atomic domain/audit/event/idempotency Unit of Work proofs."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from quantfoundry.api.app import (
    Audit,
    Event,
    Idempotency,
    ResearchRow,
    SessionLocal,
    User,
    Workspace,
    app,
    emit,
    problem,
)
from quantfoundry.infrastructure.db.idempotency import execute


def test_success_commits_domain_audit_event_and_replay_result_together() -> None:
    key = f"uow-success-{uuid.uuid4()}"
    response = TestClient(app).post(
        "/api/v1/research",
        headers={"Authorization": "Bearer test", "Idempotency-Key": key},
        json={"title": "Atomic success", "original_user_prompt": "Prove commit"},
    )
    assert response.status_code == 201
    research_id = response.json()["research_id"]

    session = SessionLocal()
    try:
        record = session.get(
            Idempotency,
            ("test-owner", "test-workspace", "POST", "/research", key),
        )
        assert record is not None and record.state == "SUCCEEDED"
        assert record.lease_owner_id is None
        assert record.lease_expires_at is None
        assert record.completed_at is not None
        assert json.loads(record.response)["research_id"] == research_id
        assert session.get(ResearchRow, research_id) is not None
        assert session.query(Event).filter_by(object_id=research_id).count() == 1
        assert session.query(Audit).filter_by(object_id=research_id).count() == 1
    finally:
        session.close()


def test_failure_rolls_back_domain_audit_event_and_idempotency_result() -> None:
    key = f"uow-rollback-{uuid.uuid4()}"
    research_id = f"RSCH-{uuid.uuid4()}"
    session = SessionLocal()

    def failing_operation() -> tuple[int, dict[str, str]]:
        session.add(
            ResearchRow(
                id=research_id,
                status="DRAFT",
                revision=1,
                title="Must roll back",
                detail="{}",
            )
        )
        session.flush()
        emit(session, "research", research_id, 1, "CREATED")
        raise RuntimeError("worker failure after all domain writes")

    with pytest.raises(RuntimeError):
        execute(
            session,
            Idempotency,
            key,
            {"title": "Must roll back"},
            "/research",
            failing_operation,
            problem,
            actor_id="test-owner",
            workspace_id="test-workspace",
            method="POST",
        )
    session.close()

    verification = SessionLocal()
    try:
        assert (
            verification.get(
                Idempotency,
                ("test-owner", "test-workspace", "POST", "/research", key),
            )
            is None
        )
        assert verification.get(ResearchRow, research_id) is None
        assert verification.query(Event).filter_by(object_id=research_id).count() == 0
        assert verification.query(Audit).filter_by(object_id=research_id).count() == 0
    finally:
        verification.close()


def test_idempotency_scope_and_expired_record_cleanup() -> None:
    key = f"uow-scoped-{uuid.uuid4()}"
    actor_a = f"USR-{uuid.uuid4()}"
    actor_b = f"USR-{uuid.uuid4()}"
    workspace_a = str(uuid.uuid4())
    workspace_b = str(uuid.uuid4())
    executions: list[str] = []
    setup = SessionLocal()
    setup.add_all(
        [
            User(id=actor_a, email=f"{actor_a}@unit.invalid", role="OWNER"),
            User(id=actor_b, email=f"{actor_b}@unit.invalid", role="OWNER"),
        ]
    )
    setup.flush()
    setup.add_all(
        [
            Workspace(id=workspace_a, owner_id=actor_a, name="Workspace A"),
            Workspace(id=workspace_b, owner_id=actor_a, name="Workspace B"),
        ]
    )
    setup.commit()
    setup.close()

    def invoke(
        actor: str,
        workspace: str,
        method: str,
        path: str,
        idempotency_key: str = key,
    ) -> None:
        session = SessionLocal()

        def operation() -> tuple[int, dict[str, str]]:
            scope = f"{actor}:{workspace}:{method}:{path}"
            executions.append(scope)
            return 201, {"scope": scope}

        response = execute(
            session,
            Idempotency,
            idempotency_key,
            {"same": True},
            path,
            operation,
            problem,
            actor_id=actor,
            workspace_id=workspace,
            method=method,
        )
        assert response.status_code == 201
        session.close()

    scopes = [
        (actor_a, workspace_a, "POST", "/one"),
        (actor_b, workspace_a, "POST", "/one"),
        (actor_a, workspace_b, "POST", "/one"),
        (actor_a, workspace_a, "PUT", "/one"),
        (actor_a, workspace_a, "POST", "/two"),
    ]
    for scope in scopes:
        invoke(*scope)
    assert len(executions) == len(scopes)
    invoke(*scopes[0])
    assert len(executions) == len(scopes)

    expired_key = f"uow-expired-{uuid.uuid4()}"
    session = SessionLocal()
    session.add(
        Idempotency(
            actor_id=actor_a,
            workspace_id=workspace_a,
            method="POST",
            path="/expired",
            key=expired_key,
            request_hash="0" * 64,
            status=201,
            response='{"expired":true}',
            state="SUCCEEDED",
            lease_expires_at=None,
            created_at=datetime.now(UTC) - timedelta(days=8),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
    )
    session.commit()
    session.close()
    invoke(actor_a, workspace_a, "POST", "/expired", expired_key)
    verification = SessionLocal()
    record = verification.get(
        Idempotency,
        (actor_a, workspace_a, "POST", "/expired", expired_key),
    )
    assert record is not None and record.state == "SUCCEEDED"
    assert json.loads(record.response)["scope"].endswith("POST:/expired")
    verification.close()
