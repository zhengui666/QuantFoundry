"""Authority-lock negatives for the staged semantic Tool registry."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import ValidationError
from sqlalchemy import event

from app import main
from quantfoundry.agents.runtime.runtime import AgentRuntimeError, ToolRegistry
from quantfoundry.api.app import (
    AgentRunRow,
    ApprovalRow,
    SessionLocal,
    SnapshotRow,
    ToolCallRow,
    app,
)

CANONICAL = (
    Path(__file__).resolve().parents[2]
    / "docs/后端系统技术方案/contracts/tools/v1-p0.yaml"
)


def _fixture(tmp_path: Path, mutate) -> tuple[Path, str]:
    contract = yaml.safe_load(CANONICAL.read_text(encoding="utf-8"))
    mutate(contract)
    path = tmp_path / "registry.yaml"
    path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")
    return path, hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "mutate",
    [
        lambda contract: contract["tools"].pop(),
        lambda contract: contract["tools"].append(dict(contract["tools"][0])),
        lambda contract: contract["tools"].__setitem__(
            0, {**contract["tools"][0], "name": "renamed"}
        ),
        lambda contract: contract["tools"].__setitem__(
            0, {**contract["tools"][0], "version": "1.1"}
        ),
        lambda contract: contract.__setitem__("unexpected", True),
        lambda contract: contract["tools"][0].__setitem__("unexpected", True),
    ],
)
def test_test_fixture_rejects_registry_authority_changes(
    tmp_path: Path, mutate
) -> None:
    path, digest = _fixture(tmp_path, mutate)
    with pytest.raises(AgentRuntimeError):
        ToolRegistry.load(path, test_only=True, expected_sha256=digest)


def test_environment_override_cannot_replace_canonical_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _digest = _fixture(tmp_path, lambda contract: contract["tools"].pop())
    monkeypatch.setenv("QF_TOOL_CONTRACT_PATH", str(path))
    registry = ToolRegistry.load()
    assert set(registry.tools) == {
        name for name, _version in ToolRegistry._EXPECTED_TOOLS
    }


def test_test_fixture_requires_declared_content_hash(tmp_path: Path) -> None:
    path, _digest = _fixture(tmp_path, lambda _contract: None)
    with pytest.raises(AgentRuntimeError, match="content hash"):
        ToolRegistry.load(path, test_only=True, expected_sha256="0" * 64)


def test_tool_input_and_output_instances_fail_closed() -> None:
    registry = ToolRegistry.load()
    session = SessionLocal()
    try:
        definition = registry.validate_request(
            session,
            "validate_dataset",
            "RESEARCH_DIRECTOR",
            {"dataset_id": "DSSET-550e8400-e29b-41d4-a716-446655440000"},
            {"data_capability"},
        )
        with pytest.raises(ValidationError):
            registry.validate_request(
                session,
                "validate_dataset",
                "RESEARCH_DIRECTOR",
                {"dataset_id": "bad"},
                {"data_capability"},
            )
        with pytest.raises(ValidationError):
            registry.validate_output(definition, {"job_id": "bad"})
    finally:
        session.close()


def test_workspace_owned_resolver_normalizes_foreign_and_absent_ids() -> None:
    client = TestClient(app)
    created = client.post(
        "/api/v1/research",
        headers={
            "Authorization": "Bearer test",
            "Idempotency-Key": "scope-proof-key-0001",
        },
        json={"title": "scope proof", "original_user_prompt": "scope proof"},
    )
    assert created.status_code == 201
    foreign = client.get(
        f"/api/v1/research/{created.json()['research_id']}",
        headers={"Authorization": "Bearer matrix"},
    )
    absent = client.get(
        "/api/v1/research/RSCH-550e8400-e29b-41d4-a716-446655440000",
        headers={"Authorization": "Bearer matrix"},
    )
    assert (foreign.status_code, foreign.json()["code"]) == (404, "RESOURCE_NOT_FOUND")
    assert (absent.status_code, absent.json()["code"]) == (404, "RESOURCE_NOT_FOUND")


def test_workspace_locked_mutation_normalizes_foreign_and_absent_ids() -> None:
    client = TestClient(app)
    created = client.post(
        "/api/v1/research",
        headers={
            "Authorization": "Bearer test",
            "Idempotency-Key": "scope-locked-mutation-key-01",
        },
        json={"title": "locked scope", "original_user_prompt": "locked scope"},
    )
    assert created.status_code == 201
    payload = {"research_revision_no": 1, "capability_evaluation_confirmed": True}
    headers = {
        "Authorization": "Bearer matrix",
        "Idempotency-Key": "scope-locked-mutation-key-02",
        "If-Match": 'W/"ignored:1"',
    }
    foreign = client.post(
        f"/api/v1/research/{created.json()['research_id']}/start",
        headers=headers,
        json=payload,
    )
    absent = client.post(
        "/api/v1/research/RSCH-550e8400-e29b-41d4-a716-446655440000/start",
        headers=headers,
        json=payload,
    )
    assert (foreign.status_code, foreign.json()["code"]) == (404, "RESOURCE_NOT_FOUND")
    assert (absent.status_code, absent.json()["code"]) == (404, "RESOURCE_NOT_FOUND")


def test_workspace_resolver_first_lookup_is_sql_scoped() -> None:
    client = TestClient(app)
    created = client.post(
        "/api/v1/research",
        headers={
            "Authorization": "Bearer test",
            "Idempotency-Key": "scope-query-shape-key-01",
        },
        json={"title": "query scope", "original_user_prompt": "query scope"},
    )
    assert created.status_code == 201
    statements: list[str] = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many) -> None:
        statements.append(statement.lower())

    event.listen(main.engine, "before_cursor_execute", capture)
    try:
        response = client.get(
            f"/api/v1/research/{created.json()['research_id']}",
            headers={"Authorization": "Bearer matrix"},
        )
    finally:
        event.remove(main.engine, "before_cursor_execute", capture)
    assert response.status_code == 404
    lookup = next(
        statement for statement in statements if "from research_cases" in statement
    )
    assert re.search(r"\bwhere\b.*\bworkspace_id\b\s*=", lookup, re.S)


def test_internal_public_reference_lookups_are_sql_scoped() -> None:
    session = SessionLocal()
    statements: list[str] = []

    def capture(_connection, _cursor, statement, _parameters, _context, _many) -> None:
        statements.append(statement.lower())

    event.listen(main.engine, "before_cursor_execute", capture)
    try:
        for model, public_id in [
            (SnapshotRow, "DS-550e8400-e29b-41d4-a716-446655440000"),
            (ApprovalRow, "APR-550e8400-e29b-41d4-a716-446655440000"),
            (AgentRunRow, "ARUN-550e8400-e29b-41d4-a716-446655440000"),
            (ToolCallRow, "TCALL-550e8400-e29b-41d4-a716-446655440000"),
        ]:
            assert (
                main._public_row(session, model, public_id, "matrix-workspace") is None
            )
    finally:
        event.remove(main.engine, "before_cursor_execute", capture)
        session.close()
    assert len(statements) == 4
    assert all(
        re.search(r"\bwhere\b.*\bworkspace_id\b", statement, re.S)
        for statement in statements
    )
