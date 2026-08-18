"""Isolate unit/API tests from a developer's durable database."""

import atexit
import json
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import inspect

RESEARCH_POLICY_ID = "RP-00000000-0000-4000-8000-000000000001"
RISK_POLICY_ID = "RISK-00000000-0000-4000-8000-000000000002"
COST_MODEL_ID = "COST-00000000-0000-4000-8000-000000000003"
VALIDATION_POLICY_ID = "RP-00000000-0000-4000-8000-000000000004"
MATRIX_RESEARCH_POLICY_ID = "RP-00000000-0000-4000-8000-000000000101"
MATRIX_RISK_POLICY_ID = "RISK-00000000-0000-4000-8000-000000000102"
MATRIX_COST_MODEL_ID = "COST-00000000-0000-4000-8000-000000000103"
MATRIX_VALIDATION_POLICY_ID = "RP-00000000-0000-4000-8000-000000000104"


_test_runtime_parent_value = os.getenv("QF_TEST_RUNTIME_PARENT")
_test_runtime_parent = (
    Path(_test_runtime_parent_value) if _test_runtime_parent_value else None
)
if _test_runtime_parent is not None and not _test_runtime_parent.is_dir():
    raise RuntimeError(
        f"QF_TEST_RUNTIME_PARENT is not an existing directory: {_test_runtime_parent}"
    )
_TEST_RUNTIME_ROOT = Path(
    tempfile.mkdtemp(
        prefix=f"quantfoundry-pytest-{os.getpid()}-",
        dir=_test_runtime_parent,
    )
)
os.environ["QF_TEST_RUNTIME_ROOT"] = str(_TEST_RUNTIME_ROOT)


def _cleanup_test_runtime() -> None:
    if _TEST_RUNTIME_ROOT.exists():
        shutil.rmtree(_TEST_RUNTIME_ROOT)


atexit.register(_cleanup_test_runtime)


def _test_runtime_directory(name: str, environment_name: str) -> Path:
    path = _TEST_RUNTIME_ROOT / name
    path.mkdir(mode=0o750)
    # Test-owned storage must never inherit a developer, CI runner, or service
    # volume.  Besides leaking state, an empty inherited policy/cost directory
    # makes deterministic jobs fail before their intended test boundary.
    os.environ[environment_name] = str(path)
    return path


configured_database_url = os.getenv("QF_DATABASE_URL")
if configured_database_url is None:
    os.environ["QF_DATABASE_URL"] = f"sqlite:///{_TEST_RUNTIME_ROOT / 'database.db'}"
elif os.getenv("QF_ALLOW_EXTERNAL_TEST_DATABASE") != "1":
    raise RuntimeError(
        "QF_DATABASE_URL is externally configured; set "
        "QF_ALLOW_EXTERNAL_TEST_DATABASE=1 only for an explicitly disposable test database"
    )
# Test collection must never inherit production/staging control-plane state;
# the control DB teardown below is intentionally destructive to this test root.
os.environ["QF_ENV"] = "test"
os.environ["QF_ENVIRONMENT"] = "test"
if os.environ["QF_DATABASE_URL"].startswith("sqlite"):
    os.environ["QF_ALLOW_TEST_SCHEMA_BOOTSTRAP"] = "1"
else:
    # PostgreSQL tests are always Alembic-only.  Never let a caller's inherited
    # environment silently turn the suite into a metadata.create_all test.
    os.environ["QF_ALLOW_TEST_SCHEMA_BOOTSTRAP"] = "0"
if os.getenv("QF_CONTROL_DB_URL"):
    raise RuntimeError(
        "QF_CONTROL_DB_URL is forbidden for tests because control-plane teardown is destructive"
    )
os.environ["QF_TEST_AUTH_TOKENS"] = json.dumps(
    {
        "test": {
            "actor_id": "test-owner",
            "workspace_id": "test-workspace",
            "role": "OWNER",
        },
        "matrix": {
            "actor_id": "matrix-owner",
            "workspace_id": "matrix-workspace",
            "role": "OWNER",
        },
        "viewer": {
            "actor_id": "test-viewer",
            "workspace_id": "test-workspace",
            "role": "VIEWER",
        },
    }
)
os.environ["QF_SSE_TEST_CLOSE"] = "1"
os.environ["QF_AGENT_PROVIDER"] = "local-deterministic"
os.environ["QF_AGENT_MODEL"] = "local-test-v1"
os.environ["QF_ENABLE_LOCAL_DETERMINISTIC_PROVIDER"] = "1"
os.environ["QF_CREDENTIAL_ENCRYPTION_KEY_ID"] = "test-key-v1"
os.environ["QF_CREDENTIAL_ENCRYPTION_KEY"] = (
    "AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8="
)
os.environ["QF_CREDENTIAL_FINGERPRINT_KEY"] = (
    "AgMEBQYHCAkKCwwNDg8QERITFBUWFxgZGhscHR4fICE="
)
artifact_root = _test_runtime_directory("artifacts", "QF_ARTIFACT_DIR")
dataset_root = _test_runtime_directory("datasets", "QF_DATASET_DIR")
cost_model_root = _test_runtime_directory("cost-models", "QF_COST_MODEL_DIR")
for cost_model_id in (COST_MODEL_ID, MATRIX_COST_MODEL_ID):
    (cost_model_root / f"{cost_model_id}.json").write_text(
        json.dumps(
            {
                "cost_model_id": cost_model_id,
                "version": 1,
                "commission_bps": 1.0,
                "slippage_bps": 2.0,
            }
        ),
        encoding="utf-8",
    )
policy_root = _test_runtime_directory("policies", "QF_POLICY_DIR")
for validation_policy_id in (VALIDATION_POLICY_ID, MATRIX_VALIDATION_POLICY_ID):
    (policy_root / f"{validation_policy_id}.json").write_text(
        json.dumps(
            {
                "policy_id": validation_policy_id,
                "version": 1,
                "validation": {
                    "min_observations": 2,
                    "min_sharpe": -1000,
                    "max_drawdown_floor": -1,
                },
                "holdout": {
                    "min_observations": 2,
                    "min_total_return": -1,
                    "min_sharpe": -1000,
                    "max_drawdown_floor": -1,
                },
                "multiple_testing_max_evaluations": 25,
                "data_quality": {
                    "min_rows": 1,
                    "min_symbols": 1,
                    "max_late_release_fraction": 1,
                },
            }
        ),
        encoding="utf-8",
    )
os.environ["QF_DEFAULT_VALIDATION_POLICY_ID"] = VALIDATION_POLICY_ID


def pytest_sessionfinish() -> None:
    """Remove test-owned runtime files after pass, failure, or pytest interrupt."""

    _cleanup_test_runtime()


@pytest.fixture(scope="session", autouse=True)
def configured_test_principals() -> None:
    from quantfoundry.api.app import (
        AgentConfigRow,
        CostModelVersionRow,
        ResearchPolicyVersionRow,
        RiskPolicyVersionRow,
        SessionLocal,
        User,
        Workspace,
        content_hash,
    )

    configured = json.loads(os.environ["QF_TEST_AUTH_TOKENS"])
    session = SessionLocal()
    try:
        for value in configured.values():
            actor_id = value["actor_id"]
            role = value["role"]
            if role == "OWNER" and session.get(User, actor_id) is None:
                session.add(
                    User(
                        id=actor_id,
                        email=f"{actor_id}@test.invalid",
                        role=role,
                        revision=1,
                    )
                )
        session.flush()
        owners = {
            value["workspace_id"]: value["actor_id"]
            for value in configured.values()
            if value["role"] == "OWNER"
        }
        for workspace_id, owner_id in owners.items():
            if session.get(Workspace, workspace_id) is None:
                session.add(
                    Workspace(
                        id=workspace_id,
                        owner_id=owner_id,
                        name=f"Test {workspace_id}",
                        revision=1,
                    )
                )
        session.flush()
        now = datetime.now(UTC)
        for workspace_id, owner_id in owners.items():
            research_policy_id = (
                MATRIX_RESEARCH_POLICY_ID
                if workspace_id == "matrix-workspace"
                else RESEARCH_POLICY_ID
            )
            validation_policy_id = (
                MATRIX_VALIDATION_POLICY_ID
                if workspace_id == "matrix-workspace"
                else VALIDATION_POLICY_ID
            )
            risk_policy_id = (
                MATRIX_RISK_POLICY_ID
                if workspace_id == "matrix-workspace"
                else RISK_POLICY_ID
            )
            cost_model_id = (
                MATRIX_COST_MODEL_ID
                if workspace_id == "matrix-workspace"
                else COST_MODEL_ID
            )
            if (
                session.query(ResearchPolicyVersionRow)
                .filter_by(workspace_id=workspace_id, policy_id=research_policy_id)
                .one_or_none()
                is None
            ):
                session.add(
                    ResearchPolicyVersionRow(
                        id=f"RPV-{workspace_id}",
                        workspace_id=workspace_id,
                        policy_id=research_policy_id,
                        policy_family="research",
                        version=1,
                        status="ACTIVE",
                        rules={"kind": "research_policy", "version": 1},
                        max_research_steps=25,
                        max_tool_calls=50,
                        content_sha256=content_hash(
                            {"kind": "research_policy", "version": 1}
                        ),
                        created_by=owner_id,
                        created_at=now,
                        activated_at=now,
                    )
                )
            if (
                session.query(ResearchPolicyVersionRow)
                .filter_by(
                    workspace_id=workspace_id,
                    policy_id=validation_policy_id,
                )
                .one_or_none()
                is None
            ):
                validation_rules = json.loads(
                    (policy_root / f"{validation_policy_id}.json").read_text()
                )
                session.add(
                    ResearchPolicyVersionRow(
                        id=f"VPV-{workspace_id}",
                        workspace_id=workspace_id,
                        policy_id=validation_policy_id,
                        policy_family="validation",
                        version=1,
                        status="ACTIVE",
                        rules=validation_rules,
                        max_research_steps=25,
                        max_tool_calls=50,
                        content_sha256=content_hash(validation_rules),
                        created_by=owner_id,
                        created_at=now,
                        activated_at=now,
                    )
                )
            if (
                session.query(RiskPolicyVersionRow)
                .filter_by(workspace_id=workspace_id, policy_id=risk_policy_id)
                .one_or_none()
                is None
            ):
                session.add(
                    RiskPolicyVersionRow(
                        id=f"RISKPV-{workspace_id}",
                        workspace_id=workspace_id,
                        policy_id=risk_policy_id,
                        version=1,
                        status="ACTIVE",
                        max_single_position=1,
                        max_strategy_weight=1,
                        max_paper_drawdown=1,
                        rules={},
                        content_sha256=content_hash(
                            {"kind": "risk_policy", "version": 1}
                        ),
                        created_at=now,
                        activated_at=now,
                    )
                )
            if (
                session.query(CostModelVersionRow)
                .filter_by(workspace_id=workspace_id, cost_model_id=cost_model_id)
                .one_or_none()
                is None
            ):
                session.add(
                    CostModelVersionRow(
                        id=f"COSTV-{workspace_id}",
                        workspace_id=workspace_id,
                        cost_model_id=cost_model_id,
                        version=1,
                        status="ACTIVE",
                        commission_model={"type": "BPS", "value": 1},
                        slippage_model={"type": "BPS", "value": 2},
                        rebalance_timing="NEXT_OPEN",
                        fill_assumption="NEXT_OPEN",
                        content_sha256=content_hash(
                            {
                                "cost_model_id": cost_model_id,
                                "version": 1,
                                "commission_bps": 1.0,
                                "slippage_bps": 2.0,
                            }
                        ),
                        created_at=now,
                        activated_at=now,
                    )
                )
            for agent_role in (
                "RESEARCH_DIRECTOR",
                "FACTOR_SCIENTIST",
                "STRATEGY_SCIENTIST",
                "PORTFOLIO_ANALYST",
                "RED_TEAM_RESEARCHER",
                "PERFORMANCE_ANALYST",
            ):
                if session.get(AgentConfigRow, (workspace_id, agent_role)) is None:
                    session.add(
                        AgentConfigRow(
                            workspace_id=workspace_id,
                            role=agent_role,
                            enabled=True,
                            revision=1,
                            model_provider="local-deterministic",
                            model_name="local-test-v1",
                            runtime_profile="DEFAULT",
                            tool_timeout_seconds=30,
                            created_at=now,
                            updated_at=now,
                        )
                    )
        session.commit()
    finally:
        session.close()


@pytest.fixture(autouse=True)
def isolate_control_plane_between_tests():
    """Keep one test's activated remote endpoint from leaking into the next."""
    yield
    from app.control_plane import (
        CONTROL_ENGINE,
        ActiveConfiguration,
        BootstrapState,
        ConfigurationRevision,
        ConfigurationValue,
        ControlSessionLocal,
        _control_path,
    )
    from quantfoundry.api.app import AgentConfigRow, SessionLocal

    try:
        control_path = _control_path().resolve()
        bound_url = CONTROL_ENGINE.url
        bound_path = Path(bound_url.database or "").resolve()
        if bound_url.get_backend_name() != "sqlite" or bound_path != control_path:
            raise RuntimeError(
                f"refusing destructive control DB teardown against {CONTROL_ENGINE.url}"
            )
        try:
            control_path.relative_to(_TEST_RUNTIME_ROOT.resolve())
        except ValueError as error:
            raise RuntimeError(
                f"refusing destructive control DB teardown outside test runtime: {control_path}"
            ) from error
        with ControlSessionLocal.begin() as control:
            if inspect(control.bind).has_table("configuration_revisions"):
                baseline = (
                    control.query(ConfigurationRevision)
                    .order_by(ConfigurationRevision.revision)
                    .first()
                )
                if baseline is not None:
                    active = control.get(ActiveConfiguration, "CONFIGURATION-DEFAULT")
                    if active is not None:
                        active.active_revision = baseline.revision
                        active.last_known_good_revision = baseline.revision
                    state = control.get(BootstrapState, "BOOTSTRAP-DEFAULT")
                    if state is not None:
                        state.active_configuration_revision = baseline.revision
                        state.last_known_good_configuration_revision = baseline.revision
                control.query(ConfigurationValue).delete()
    finally:
        with SessionLocal.begin() as session:
            session.query(AgentConfigRow).update(
                {
                    AgentConfigRow.enabled: True,
                    AgentConfigRow.model_provider: "local-deterministic",
                    AgentConfigRow.model_name: "local-test-v1",
                    AgentConfigRow.runtime_profile: "DEFAULT",
                    AgentConfigRow.tool_timeout_seconds: 30,
                    AgentConfigRow.max_steps_override: None,
                    AgentConfigRow.max_tool_calls_override: None,
                },
                synchronize_session=False,
            )
