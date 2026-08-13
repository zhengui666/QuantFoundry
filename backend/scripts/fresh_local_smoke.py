"""Fresh Alembic → local seed → Setup → Research smoke without pytest fixtures."""

from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import sys
import tempfile
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import httpx
from alembic.config import Config
from fastapi.testclient import TestClient

from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _key(label: str) -> str:
    return f"fresh-local-{label}-{uuid.uuid4()}"


def _expect(response: httpx.Response, status: int) -> dict[str, object]:
    if response.status_code != status:
        raise RuntimeError(
            f"{response.request.method} {response.request.url.path}: "
            f"{response.status_code} {response.text}"
        )
    value = response.json()
    if not isinstance(value, dict):
        raise RuntimeError("smoke response must be an object")
    return value


@dataclass(frozen=True)
class WorkflowObservation:
    finished: bool
    terminal_failure: bool
    analyze_wait: bool
    diagnostic: dict[str, Any]


def _drive_worker_turns(
    run_agent: Callable[[int], int],
    run_core: Callable[[int], int],
    inspect: Callable[[], WorkflowObservation],
    *,
    max_turns: int = 128,
    max_idle_turns: int = 8,
) -> tuple[bool, dict[str, Any]]:
    """Deterministically alternate queues and fail with redacted durable state."""

    observed_analyze_wait = False
    idle_turns = 0
    last: WorkflowObservation | None = None
    for turn in range(max_turns):
        progressed = run_agent(turn)
        after_agent = inspect()
        observed_analyze_wait |= after_agent.analyze_wait
        progressed += run_core(turn)
        last = inspect()
        observed_analyze_wait |= last.analyze_wait
        if last.finished:
            return observed_analyze_wait, last.diagnostic
        if last.terminal_failure:
            raise RuntimeError(
                "fresh local Research workflow reached a terminal failure: "
                + json.dumps(last.diagnostic, sort_keys=True)
            )
        if progressed:
            idle_turns = 0
            continue
        idle_turns += 1
        if idle_turns >= max_idle_turns:
            raise RuntimeError(
                "fresh local Research workflow stalled: "
                + json.dumps(last.diagnostic, sort_keys=True)
            )
    diagnostic = last.diagnostic if last is not None else {"state": "unobserved"}
    raise RuntimeError(
        "fresh local Research workflow exceeded worker budget: "
        + json.dumps(diagnostic, sort_keys=True)
    )


def _workflow_observation(
    session_factory: Callable[[], Any], research_id: str, workspace_id: str
) -> WorkflowObservation:
    from app.main import (
        AgentRunRow,
        ExperimentRow,
        JobDependencyRow,
        JobRow,
        ResearchRow,
        ToolCallRow,
    )

    session = session_factory()
    try:
        research = session.get(ResearchRow, research_id)
        runs = (
            session.query(AgentRunRow)
            .filter_by(research_id=research_id, workspace_id=workspace_id)
            .order_by(AgentRunRow.id)
            .all()
        )
        run_ids = [row.id for row in runs]
        calls = (
            session.query(ToolCallRow)
            .filter(ToolCallRow.agent_run_id.in_(run_ids))
            .order_by(ToolCallRow.started_at, ToolCallRow.id)
            .all()
            if run_ids
            else []
        )
        jobs = (
            session.query(JobRow)
            .filter_by(workspace_id=workspace_id)
            .order_by(JobRow.queued_at, JobRow.id)
            .all()
        )
        dependencies = (
            session.query(JobDependencyRow)
            .filter_by(workspace_id=workspace_id)
            .order_by(
                JobDependencyRow.job_id,
                JobDependencyRow.depends_on_job_id,
            )
            .all()
        )
        experiments = (
            session.query(ExperimentRow)
            .filter_by(research_id=research_id, workspace_id=workspace_id)
            .order_by(ExperimentRow.id)
            .all()
        )
        diagnostic = {
            "research": (
                {
                    "id": research.id,
                    "status": research.status,
                    "revision": research.revision,
                }
                if research is not None
                else None
            ),
            "agent_runs": [
                {
                    "id": row.id,
                    "role": row.role,
                    "status": row.status,
                    "revision": row.revision,
                    "step_count": row.step_count,
                    "tool_call_count": row.tool_call_count,
                }
                for row in runs
            ],
            "tool_calls": [
                {
                    "id": row.id,
                    "name": row.tool_name,
                    "status": row.status,
                    "job_id": row.job_id,
                }
                for row in calls
            ],
            "jobs": [
                {
                    "id": row.id,
                    "type": row.job_type,
                    "queue": row.queue_name,
                    "status": row.status,
                    "attempt": row.attempt,
                    "fencing_token": row.fencing_token,
                    "current_step": row.current_step_key,
                    "error_code": row.error_code,
                }
                for row in jobs
            ],
            "dependencies": [
                {
                    "job_id": row.job_id,
                    "depends_on_job_id": row.depends_on_job_id,
                    "type": row.dependency_type,
                }
                for row in dependencies
            ],
            "experiments": [
                {
                    "id": row.id,
                    "status": json.loads(row.detail).get("status"),
                    "immutable": row.immutable,
                    "revision": row.revision,
                }
                for row in experiments
            ],
        }
        completed_run = next(
            (row for row in runs if row.role == "RESEARCH_DIRECTOR"), None
        )
        finished = bool(
            completed_run is not None
            and completed_run.status == "COMPLETED"
            and len(experiments) == 1
            and experiments[0].immutable
        )
        terminal_failure = bool(
            completed_run is not None
            and completed_run.status in {"FAILED", "CANCELLED", "WAITING_USER"}
        )
        analyze_wait = any(
            call.tool_name == "analyze_factor"
            and call.status == "RUNNING"
            and any(
                job.id == call.job_id and job.status in {"QUEUED", "RUNNING"}
                for job in jobs
            )
            for call in calls
        )
        return WorkflowObservation(
            finished=finished,
            terminal_failure=terminal_failure,
            analyze_wait=analyze_wait,
            diagnostic=diagnostic,
        )
    finally:
        session.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root")
    args = parser.parse_args()
    root = Path(args.root) if args.root else Path(tempfile.mkdtemp(prefix="qf-local-"))
    root.mkdir(mode=0o750, parents=True, exist_ok=True)
    environment = os.getenv("QF_ENVIRONMENT") or os.getenv("QF_ENV") or "local"
    if environment not in {"local", "development", "test"}:
        raise RuntimeError(
            "fresh local smoke is forbidden outside local/development/test"
        )
    os.environ["QF_ENVIRONMENT"] = environment
    os.environ["QF_ENV"] = environment
    os.environ.setdefault("QF_DATABASE_URL", f"sqlite:///{root / 'quantfoundry.db'}")
    os.environ.setdefault("QF_GIT_COMMIT", "local-smoke")
    os.environ.setdefault("QF_BUILD_ID", "local-smoke")
    os.environ.setdefault("QF_ARTIFACT_DIR", str(root / "artifacts"))
    os.environ.setdefault("QF_DATASET_DIR", str(root / "datasets"))
    os.environ.setdefault("QF_COST_MODEL_DIR", str(root / "cost-models"))
    os.environ.setdefault("QF_POLICY_DIR", str(root / "policies"))
    os.environ.setdefault(
        "QF_AGENT_CHECKPOINT_SQLITE", str(root / "agent-checkpoint.db")
    )
    os.environ.setdefault("QF_ENABLE_LOCAL_DETERMINISTIC_PROVIDER", "1")
    os.environ.setdefault("QF_LOCAL_DATA_CREDENTIAL", secrets.token_urlsafe(32))
    os.environ.setdefault("QF_LOCAL_PROVIDER_API_KEY", secrets.token_urlsafe(32))
    # This smoke owns an in-process Remote Codex transport.  Do not inherit
    # a test runner's model/provider selection: that would validate a different
    # workflow while still writing into the fresh database under test.
    os.environ["QF_AGENT_PROVIDER"] = "remote-codex"
    os.environ["QF_AGENT_MODEL"] = "qf-local-v1"
    os.environ["QF_CODEX_RUNTIME_ID"] = "CODEX-DEFAULT"
    os.environ["QF_CODEX_REMOTE_INSTANCE_ID"] = "CODEX-DEFAULT"
    os.environ["QF_CODEX_MODEL"] = "qf-local-v1"
    os.environ["QF_CODEX_MODELS"] = "qf-local-v1"
    os.environ.setdefault("QF_CREDENTIAL_ENCRYPTION_KEY_ID", "local-smoke-v1")
    os.environ.setdefault(
        "QF_CREDENTIAL_ENCRYPTION_KEY",
        base64.b64encode(secrets.token_bytes(32)).decode(),
    )
    for directory in ("artifacts", "datasets", "cost-models", "policies"):
        (root / directory).mkdir(mode=0o750, exist_ok=True)

    from app.local_provider import create_server

    provider = create_server(
        "127.0.0.1", 0, api_key=os.environ["QF_LOCAL_PROVIDER_API_KEY"]
    )
    provider_thread = threading.Thread(target=provider.serve_forever, daemon=True)
    provider_thread.start()
    provider_url = f"http://127.0.0.1:{provider.server_address[1]}/v1"
    os.environ["QF_CODEX_BASE_URL"] = provider_url
    try:
        health = httpx.get(
            f"http://127.0.0.1:{provider.server_address[1]}/healthz", timeout=2
        )
        health.raise_for_status()
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        config.set_main_option(
            "script_location", str(Path(__file__).resolve().parents[1] / "alembic")
        )
        command.upgrade(config, "head")

        from app.bootstrap import seed_local
        from app.main import (
            AgentRunRow,
            ArtifactRow,
            CostModelVersionRow,
            ExperimentRow,
            JobDependencyRow,
            JobRow,
            ResearchPolicyVersionRow,
            ResearchRow,
            RiskPolicyVersionRow,
            SessionLocal,
            ToolCallRow,
            app,
            content_hash,
        )
        from workers.main import run_agent_once, run_once

        session_token = secrets.token_urlsafe(32)
        seeded = seed_local(
            workspace_id="local-workspace",
            owner_id="local-owner",
            owner_email="owner@local.invalid",
            session_token=session_token,
        )
        replayed_seed = seed_local(
            workspace_id="local-workspace",
            owner_id="local-owner",
            owner_email="owner@local.invalid",
            session_token=session_token,
        )
        if replayed_seed != seeded:
            raise RuntimeError("local seed replay changed stable references")
        policy_ids = {
            str(seeded["research_policy_id"]),
            str(seeded["validation_policy_id"]),
            str(seeded["risk_policy_id"]),
        }
        if len(policy_ids) != 3:
            raise RuntimeError("local policy aggregates share a public ID")
        verification = SessionLocal()
        try:
            research_rows = (
                verification.query(ResearchPolicyVersionRow)
                .filter_by(workspace_id="local-workspace", status="ACTIVE")
                .all()
            )
            by_family: dict[str, ResearchPolicyVersionRow] = {
                cast(str, row.policy_family): row for row in research_rows
            }
            if set(by_family) != {"research", "validation"}:
                raise RuntimeError("local research policy kinds are not exact")
            for family, result_key in (
                ("research", "research_policy_id"),
                ("validation", "validation_policy_id"),
            ):
                row = by_family[family]
                policy_path = root / "policies" / f"{seeded[result_key]}.json"
                value = json.loads(policy_path.read_text(encoding="utf-8"))
                if row.policy_id != seeded[result_key] or row.rules != value:
                    raise RuntimeError("local policy file/DB binding mismatch")
                if row.content_sha256 != content_hash(value):
                    raise RuntimeError("local policy content hash mismatch")
            risk = (
                verification.query(RiskPolicyVersionRow)
                .filter_by(
                    workspace_id="local-workspace",
                    policy_id=seeded["risk_policy_id"],
                    status="ACTIVE",
                )
                .one_or_none()
            )
            cost = (
                verification.query(CostModelVersionRow)
                .filter_by(
                    workspace_id="local-workspace",
                    cost_model_id=seeded["cost_model_id"],
                    status="ACTIVE",
                )
                .one_or_none()
            )
            if risk is None or cost is None:
                raise RuntimeError("local risk/cost binding is unavailable")
        finally:
            verification.close()
        headers = {"Authorization": f"Bearer {session_token}"}
        with TestClient(app) as client:
            ai = _expect(
                client.post(
                    "/api/v1/setup/provider-connections/validate",
                    headers={**headers, "Idempotency-Key": _key("ai")},
                    json={
                        "provider_id": "REMOTE_CODEX",
                        "kind": "AI",
                        "model_name": "qf-local-v1",
                        "credential": os.environ["QF_LOCAL_PROVIDER_API_KEY"],
                    },
                ),
                200,
            )
            data = _expect(
                client.post(
                    "/api/v1/setup/provider-connections/validate",
                    headers={**headers, "Idempotency-Key": _key("data")},
                    json={
                        "provider_id": "LOCAL_DETERMINISTIC_DATA",
                        "kind": "DATA",
                        "credential": os.environ["QF_LOCAL_DATA_CREDENTIAL"],
                    },
                ),
                200,
            )
            if ai.get("state") != "SUCCESS" or data.get("state") != "SUCCESS":
                raise RuntimeError("local provider validation failed")
            _expect(
                client.post(
                    "/api/v1/setup/complete",
                    headers={**headers, "Idempotency-Key": _key("setup")},
                    json={
                        "language": "en",
                        "timezone": "UTC",
                        "base_currency": "USD",
                        "number_format_locale": "en-US",
                        "ai_connection_id": ai["connection_id"],
                        "default_data_provider_id": "LOCAL_DETERMINISTIC_DATA",
                        "default_benchmark": "LOCAL-BENCHMARK",
                        "default_frequency": "DAILY",
                        "initial_paper_capital": "100000",
                        "research_policy_id": seeded["research_policy_id"],
                        "risk_policy_id": seeded["risk_policy_id"],
                        "cost_model_id": seeded["cost_model_id"],
                    },
                ),
                200,
            )
            research_response = client.post(
                "/api/v1/research",
                headers={**headers, "Idempotency-Key": _key("research")},
                json={
                    "title": "Fresh local research",
                    "original_user_prompt": "Verify the fresh local research path",
                },
            )
            research = _expect(research_response, 201)
            started = _expect(
                client.post(
                    f"/api/v1/research/{research['research_id']}/start",
                    headers={
                        **headers,
                        "Idempotency-Key": _key("start"),
                        "If-Match": research_response.headers["etag"],
                    },
                    json={
                        "research_revision_no": 1,
                        "capability_evaluation_confirmed": True,
                    },
                ),
                202,
            )
        observed_analyze_wait, _diagnostic = _drive_worker_turns(
            lambda iteration: run_agent_once(identity=f"fresh-local-agent-{iteration}"),
            lambda iteration: run_once(identity=f"fresh-local-core-{iteration}"),
            lambda: _workflow_observation(
                SessionLocal, str(research["research_id"]), "local-workspace"
            ),
        )
        session = SessionLocal()
        try:
            completed = session.get(JobRow, started["job_id"])
            run = (
                session.query(AgentRunRow)
                .filter_by(
                    research_id=research["research_id"], role="RESEARCH_DIRECTOR"
                )
                .one()
            )
            calls = (
                session.query(ToolCallRow)
                .filter_by(agent_run_id=run.id)
                .order_by(ToolCallRow.started_at)
                .all()
            )
            experiment = (
                session.query(ExperimentRow)
                .filter_by(research_id=research["research_id"])
                .one()
            )
            experiment_detail = json.loads(cast(str, experiment.detail))
            research_row = session.get(ResearchRow, research["research_id"])
            analyze = next(call for call in calls if call.tool_name == "analyze_factor")
            child = session.get(JobRow, analyze.job_id)
            if child is None:
                raise RuntimeError("fresh local analyze_factor child job disappeared")
            resume = (
                session.query(JobRow)
                .filter_by(job_type="AGENT_RESUME", workspace_id="local-workspace")
                .join(
                    JobDependencyRow,
                    JobDependencyRow.job_id == JobRow.id,
                )
                .filter(JobDependencyRow.depends_on_job_id == child.id)
                .one()
            )
            artifact_id = experiment_detail["artifacts"][0]["artifact"]["id"]
            artifact = (
                session.query(ArtifactRow)
                .filter_by(artifact_id=artifact_id, workspace_id="local-workspace")
                .one_or_none()
            )
            if completed is None or completed.status != "COMPLETED":
                raise RuntimeError("fresh local Agent admission job did not complete")
            if not observed_analyze_wait:
                raise RuntimeError("analyze_factor did not durably wait on its child")
            if [call.tool_name for call in calls] != [
                "validate_dataset",
                "create_data_snapshot",
                "define_factor",
                "analyze_factor",
            ] or any(call.status != "SUCCESS" for call in calls):
                raise RuntimeError("fresh local canonical ToolCall chain is incomplete")
            if (
                child is None
                or child.status != "COMPLETED"
                or resume.status != "COMPLETED"
                or resume.current_step_key != "RESUME_CONSUMED"
            ):
                raise RuntimeError("fresh local child/resume lineage is incomplete")
            if (
                not experiment.immutable
                or experiment_detail["status"] != "COMPLETED"
                or experiment_detail["provenance"] is None
                or artifact is None
                or artifact.publication_state != "PUBLISHED"
            ):
                raise RuntimeError("fresh local Experiment evidence is incomplete")
            if research_row is None:
                raise RuntimeError("fresh local Research disappeared")
            research_detail = json.loads(cast(str, research_row.detail))
            linked_experiments = research_detail["experiments"]["items"]
            if (
                research_row.status != "COMPLETED"
                or research_detail["status"] != "COMPLETED"
                or len(linked_experiments) != 1
                or linked_experiments[0]["experiment"]["id"] != experiment.id
                or experiment.id not in run.decision_summary
            ):
                raise RuntimeError("fresh local Research summary is inconsistent")
            experiment_id = experiment.id
            agent_run_id = run.id
            tool_call_count = run.tool_call_count
        finally:
            session.close()
        if run_agent_once(identity="fresh-local-replay-agent") != 0:
            raise RuntimeError("completed Agent workflow replayed unexpectedly")
        if run_once(identity="fresh-local-replay-core") != 0:
            raise RuntimeError("completed core workflow replayed unexpectedly")
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "root": str(root.resolve()),
                    "research_id": research["research_id"],
                    "job_id": started["job_id"],
                    "agent_run_id": agent_run_id,
                    "experiment_id": experiment_id,
                    "tool_call_count": tool_call_count,
                    "provider_health": health.json()["status"],
                },
                sort_keys=True,
            )
        )
    finally:
        provider.shutdown()
        provider.server_close()
        provider_thread.join(timeout=2)


if __name__ == "__main__":
    main()
