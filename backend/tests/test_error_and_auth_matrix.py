import pytest
from fastapi.routing import iter_route_contexts
from fastapi.testclient import TestClient
from starlette.requests import Request

from quantfoundry.api.app import app, problem_payload
from quantfoundry.contracts.openapi.runtime import canonical_openapi, validated_payload

SPEC = canonical_openapi()
ERROR_CODES = SPEC["components"]["schemas"]["CanonicalErrorCode"]["enum"]
UUID_SUFFIX = "550e8400-e29b-41d4-a716-446655440000"


@pytest.mark.parametrize("code", ERROR_CODES)
def test_all_65_canonical_error_codes_build_schema_valid_problems(code: str) -> None:
    request = Request({"type": "http", "method": "GET", "path": "/test", "headers": []})
    payload = problem_payload(409, code, request, "contract proof")
    assert validated_payload("ApiProblem", payload) == payload


def test_unknown_http_error_code_is_fail_closed_to_canonical_problem() -> None:
    response = TestClient(app).get("/api/v1/research")
    assert response.status_code == 401
    body = response.json()
    assert body["code"] in ERROR_CODES
    assert set(body) == {
        "type",
        "title",
        "status",
        "code",
        "detail",
        "instance",
        "request_id",
        "retryable",
        "field_errors",
        "context",
    }


def protected_operations() -> list[tuple[str, str]]:
    result = []
    implemented = {
        (method.lower(), route.path.removeprefix("/api/v1"))
        for route in iter_route_contexts(app.routes)
        for method in getattr(route, "methods", set())
        if getattr(route, "path", "").startswith("/api/v1")
    }
    for path, operations in SPEC["paths"].items():
        for method, operation in operations.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            security = operation.get("security", SPEC.get("security", []))
            if not security or (method, path) not in implemented:
                continue
            result.append(
                (
                    method,
                    path.replace("{dataset_id}", f"DSSET-{UUID_SUFFIX}")
                    .replace("{snapshot_id}", f"DS-{UUID_SUFFIX}")
                    .replace("{research_id}", f"RSCH-{UUID_SUFFIX}")
                    .replace("{experiment_id}", f"EXP-{UUID_SUFFIX}")
                    .replace("{factor_id}", f"FAC-{UUID_SUFFIX}")
                    .replace("{strategy_id}", f"STRAT-{UUID_SUFFIX}")
                    .replace("{version}", "1")
                    .replace("{validation_id}", f"VAL-{UUID_SUFFIX}")
                    .replace("{approval_id}", f"APR-{UUID_SUFFIX}")
                    .replace("{role}", "RESEARCH_DIRECTOR")
                    .replace("{agent_run_id}", f"ARUN-{UUID_SUFFIX}")
                    .replace("{tool_call_id}", f"TCALL-{UUID_SUFFIX}")
                    .replace("{job_id}", f"JOB-{UUID_SUFFIX}"),
                )
            )
    return result


def test_auth_matrix_covers_every_protected_operation() -> None:
    assert len(protected_operations()) == 64


@pytest.mark.parametrize(("method", "path"), protected_operations())
def test_all_cookie_operations_reject_missing_session(method: str, path: str) -> None:
    response = TestClient(app).request(method.upper(), "/api/v1" + path, json={})
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")


@pytest.mark.parametrize(
    "authorization", ["Bearer", "Bearer ", "Bearer arbitrary", "Basic test"]
)
def test_only_explicitly_issued_bearer_tokens_are_accepted(authorization: str) -> None:
    response = TestClient(app).get(
        "/api/v1/research", headers={"Authorization": authorization}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


def test_authenticated_non_owner_is_denied_authority() -> None:
    response = TestClient(app).get(
        "/api/v1/research", headers={"Authorization": "Bearer arbitrary"}
    )
    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
