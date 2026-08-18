"""Small durable Agent graph with canonical tool policy and checkpoint gates."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, TypedDict
from urllib.parse import urlsplit

import httpx
import psycopg
import yaml
from jsonschema import Draft202012Validator
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from psycopg.rows import dict_row
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from quantfoundry.api.app import (
    AgentConfigRow,
    AgentRunRow,
    DataSource,
    ExperimentRow,
    JobDependencyRow,
    JobRow,
    ModelProviderConnectionRow,
    ResearchPolicyVersionRow,
    ResearchRow,
    SetupBindingRow,
    SnapshotRow,
    StrategyVersionRow,
    ToolCallRow,
    content_hash,
    create_provenance,
    emit,
    new_id,
)
from quantfoundry.api.app import (
    job as enqueue_job,
)
from quantfoundry.contracts.events.locator import job_result_ref_valid
from quantfoundry.contracts.openapi.runtime import validated_payload
from quantfoundry.infrastructure.crypto.provider_credentials import (
    CredentialConfigurationError,
    credential_aad,
    decrypt_credential,
)
from quantfoundry.infrastructure.jobs.queue import (
    JobNotCancellable,
    request_cancellation,
)

DEFAULT_MAX_STEPS = 25
DEFAULT_MAX_TOOL_CALLS = 50


class AgentRuntimeError(RuntimeError):
    pass


class ToolPolicyDenied(AgentRuntimeError):
    pass


class ToolExecutionFailure(AgentRuntimeError):
    """Carries the rolled-back call identity into the worker failure transaction."""

    def __init__(
        self,
        *,
        tool_call_id: str,
        tool_name: str,
        tool_version: str,
        input_payload: str,
        input_sha256: str,
        semantic_scope: str,
        agent_run_id: str,
        workspace_id: str | None,
        research_id: str | None,
        objective: str,
        started_at: datetime,
        cause: Exception,
        policy_version_ref: str,
    ):
        super().__init__(f"{tool_name} failed: {type(cause).__name__}")
        self.tool_call_id = tool_call_id
        self.tool_name = tool_name
        self.tool_version = tool_version
        self.input_payload = input_payload
        self.input_sha256 = input_sha256
        self.semantic_scope = semantic_scope
        self.agent_run_id = agent_run_id
        self.workspace_id = workspace_id
        self.research_id = research_id
        self.objective = objective
        self.started_at = started_at
        self.cause_type = type(cause).__name__
        self.policy_version_ref = policy_version_ref


class Model(Protocol):
    def next_action(self, checkpoint: dict[str, Any]) -> dict[str, Any]: ...


class DeterministicModel:
    """Explicit local adapter; never enabled by an implicit production fallback."""

    def next_action(self, checkpoint: dict[str, Any]) -> dict[str, Any]:
        del checkpoint
        return {"type": "conclude", "summary": "Research run initialized"}


CODEX_RUNTIME_KEY = "CODEX-DEFAULT"


@dataclass(frozen=True)
class CodexRuntimeConfig:
    """One logical remote Codex runtime shared by every runtime Role."""

    runtime_key: str
    remote_instance_id: str
    url: str
    api_key: str
    model_name: str
    timeout_seconds: int
    max_attempts: int

    @classmethod
    def from_environment(
        cls,
        *,
        model_name: str,
        timeout_seconds: int,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> CodexRuntimeConfig:
        runtime_key = os.getenv("QF_CODEX_RUNTIME_ID", CODEX_RUNTIME_KEY)
        if runtime_key != CODEX_RUNTIME_KEY:
            raise AgentRuntimeError("only CODEX-DEFAULT remote runtime is supported")
        base_url = (
            base_url
            or os.getenv("QF_CODEX_BASE_URL")
            or os.getenv("QF_OPENAI_BASE_URL")
            or ""
        ).rstrip("/")
        resolved_api_key = (
            api_key
            or os.getenv("QF_CODEX_API_KEY")
            or os.getenv("QF_OPENAI_API_KEY", "")
        )
        resolved_model = model_name or os.getenv("QF_CODEX_MODEL", "")
        if not base_url or not resolved_api_key or not resolved_model:
            raise AgentRuntimeError("Remote Codex runtime credentials are absent")
        try:
            parsed_url = urlsplit(base_url)
        except ValueError as error:
            raise AgentRuntimeError("Remote Codex endpoint is invalid") from error
        is_local_http = parsed_url.scheme == "http" and parsed_url.hostname in {
            "localhost",
            "127.0.0.1",
            "::1",
        }
        if (
            (parsed_url.scheme != "https" and not is_local_http)
            or not parsed_url.netloc
            or parsed_url.username is not None
            or parsed_url.password is not None
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise AgentRuntimeError("Remote Codex endpoint is invalid")
        try:
            max_attempts = max(
                1,
                min(
                    5,
                    int(
                        os.getenv(
                            "QF_CODEX_MAX_ATTEMPTS",
                            os.getenv("QF_AGENT_PROVIDER_MAX_ATTEMPTS", "3"),
                        )
                    ),
                ),
            )
        except ValueError as error:
            raise AgentRuntimeError(
                "Remote Codex retry configuration is invalid"
            ) from error
        remote_instance_id = (
            os.getenv("QF_CODEX_REMOTE_INSTANCE_ID") or CODEX_RUNTIME_KEY
        )
        if not remote_instance_id.strip():
            raise AgentRuntimeError("Remote Codex instance identity is absent")
        endpoint = (
            base_url
            if base_url.endswith("/chat/completions")
            else f"{base_url}/chat/completions"
        )
        return cls(
            runtime_key=runtime_key,
            remote_instance_id=remote_instance_id,
            url=endpoint,
            api_key=resolved_api_key,
            model_name=resolved_model,
            timeout_seconds=timeout_seconds,
            max_attempts=max_attempts,
        )


class RemoteCodexModel:
    """Remote Codex adapter; all Roles resolve to the same logical runtime."""

    def __init__(
        self,
        *,
        model_name: str,
        timeout_seconds: int,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.runtime = CodexRuntimeConfig.from_environment(
            model_name=model_name,
            timeout_seconds=timeout_seconds,
            api_key=api_key,
            base_url=base_url,
        )

    @staticmethod
    def _invocation_id(checkpoint: dict[str, Any]) -> str:
        context = checkpoint.get("context")
        context = context if isinstance(context, dict) else {}
        run_id = str(context.get("agent_run_id") or "unknown-run")
        action_index = checkpoint.get("model_action_index", 0)
        digest = hashlib.sha256(
            f"{CODEX_RUNTIME_KEY}:{run_id}:{action_index}".encode()
        ).hexdigest()
        return f"codex-{digest}"

    def next_action(self, checkpoint: dict[str, Any]) -> dict[str, Any]:
        invocation_id = self._invocation_id(checkpoint)
        request = {
            "model": self.runtime.model_name,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "metadata": {
                "qf_runtime_key": self.runtime.runtime_key,
                "qf_remote_instance_id": self.runtime.remote_instance_id,
                "qf_invocation_id": invocation_id,
            },
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are the QuantFoundry remote Codex runtime. Return one JSON "
                        "object: either {type:'tool',name,arguments} or "
                        "{type:'conclude',summary}. Never request holdout data. "
                        "Tools are intents only; the server authorizes and executes them."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(checkpoint, sort_keys=True),
                },
            ],
        }
        attempts = self.runtime.max_attempts
        last_error: Exception | None = None
        for _attempt in range(attempts):
            try:
                response = httpx.post(
                    self.runtime.url,
                    headers={
                        "Authorization": f"Bearer {self.runtime.api_key}",
                        "X-QF-Codex-Runtime": self.runtime.runtime_key,
                        "X-QF-Codex-Instance": self.runtime.remote_instance_id,
                        "X-QF-Codex-Invocation": invocation_id,
                    },
                    json=request,
                    timeout=self.runtime.timeout_seconds,
                )
                response.raise_for_status()
                payload = response.json()
                response_instance = response.headers.get("X-QF-Codex-Instance")
                if (
                    response_instance
                    and response_instance != self.runtime.remote_instance_id
                ):
                    raise AgentRuntimeError(
                        "Remote Codex instance identity changed during invocation"
                    )
                content = payload["choices"][0]["message"]["content"]
                action = json.loads(content)
                break
            except (
                httpx.HTTPError,
                KeyError,
                IndexError,
                TypeError,
                json.JSONDecodeError,
            ) as error:
                last_error = error
        else:
            raise AgentRuntimeError(
                f"Remote Codex failed after {self.runtime.max_attempts} attempts"
            ) from last_error
        if not isinstance(action, dict):
            raise AgentRuntimeError("Remote Codex action is not a JSON object")
        usage = payload.get("usage") if isinstance(payload, dict) else None
        if not isinstance(usage, dict):
            raise AgentRuntimeError("Remote Codex usage metadata is missing")
        input_tokens = usage.get("prompt_tokens", usage.get("input_tokens", 0))
        output_tokens = usage.get("completion_tokens", usage.get("output_tokens", 0))
        if any(
            not isinstance(value, int)
            or isinstance(value, bool)
            or not 0 <= value <= 10_000_000
            for value in (input_tokens, output_tokens)
        ):
            raise AgentRuntimeError("Remote Codex usage metadata is invalid")
        action["input_tokens"] = input_tokens
        action["output_tokens"] = output_tokens
        return action


# Compatibility name for existing test harnesses. Runtime construction always
# returns RemoteCodexModel and therefore cannot select another provider.
OpenAICompatibleModel = RemoteCodexModel


class LocalDeterministicModel(DeterministicModel):
    """Explicit non-production adapter used only when configured by name."""


def _active_setup_provider(
    session: Session, config: AgentConfigRow
) -> tuple[str, str] | None:
    binding = session.get(SetupBindingRow, config.workspace_id)
    if binding is None:
        return None
    connection = session.execute(
        select(ModelProviderConnectionRow).where(
            ModelProviderConnectionRow.id == binding.ai_connection_id,
            ModelProviderConnectionRow.workspace_id == config.workspace_id,
        )
    ).scalar_one_or_none()
    if connection is None:
        raise AgentRuntimeError("configured provider connection is unavailable")
    expires_at = connection.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if (
        connection.provider_id not in {"OPENAI_COMPATIBLE", "REMOTE_CODEX"}
        or connection.kind != "AI"
        or connection.validation_state != "SUCCESS"
        or connection.status != "ACTIVE"
        or (expires_at is not None and expires_at <= datetime.now(UTC))
    ):
        return None
    aad = credential_aad(
        connection_id=connection.id,
        workspace_id=connection.workspace_id,
        actor_id=connection.owner_actor_id,
        provider_id=connection.provider_id,
        model_name=connection.model_name,
    )
    try:
        return (
            decrypt_credential(
                connection.ciphertext, connection.nonce, connection.key_id, aad=aad
            ),
            connection.model_name,
        )
    except CredentialConfigurationError as error:
        raise AgentRuntimeError(
            "configured provider credential is unavailable"
        ) from error


def _active_control_plane_connection() -> dict[str, str] | None:
    try:
        from app.control_plane import active_remote_codex_connection

        value = active_remote_codex_connection()
    except (ImportError, OSError, RuntimeError, ValueError):
        return None
    if not isinstance(value, dict):
        return None
    endpoint = value.get("endpoint")
    credential = value.get("credential")
    model = value.get("model")
    if not isinstance(endpoint, str) or not endpoint:
        return None
    if not isinstance(credential, str) or not credential:
        return None
    if not isinstance(model, str) or not model:
        return None
    return {"endpoint": endpoint, "credential": credential, "model": model}


def _control_plane_remote_mode() -> bool:
    try:
        from app.control_plane import active_runtime_snapshot

        snapshot = active_runtime_snapshot()
        return str(snapshot.get("model_provider") or "").lower() in {
            "openai-compatible",
            "remote-codex",
        }
    except (ImportError, OSError, RuntimeError, ValueError, TypeError):
        return False


def configured_model(config: AgentConfigRow, session: Session | None = None) -> Model:
    remote_mode = (
        os.getenv("QF_AGENT_PROVIDER", "").lower()
        in {
            "openai-compatible",
            "remote-codex",
        }
        or bool(os.getenv("QF_CODEX_BASE_URL"))
        or _control_plane_remote_mode()
    )
    if remote_mode or config.model_provider in {"openai-compatible", "remote-codex"}:
        control = _active_control_plane_connection()
        setup_provider = (
            _active_setup_provider(session, config) if session is not None else None
        )
        api_key = setup_provider[0] if setup_provider is not None else None
        if control is not None:
            api_key = control["credential"]
        elif (
            session is not None
            and not api_key
            and not (
                os.getenv("QF_ENV") == "test" and os.getenv("QF_TEST_RUNTIME_ROOT")
            )
        ):
            raise AgentRuntimeError(
                "workspace provider credential is unavailable; refusing process fallback"
            )
        return RemoteCodexModel(
            model_name=(
                control["model"]
                if control is not None
                else setup_provider[1]
                if setup_provider is not None
                else config.model_name
            ),
            timeout_seconds=config.tool_timeout_seconds,
            api_key=api_key,
            base_url=control["endpoint"] if control is not None else None,
        )
    if config.model_provider == "local-deterministic":
        if os.getenv("QF_ENABLE_LOCAL_DETERMINISTIC_PROVIDER") != "1":
            raise AgentRuntimeError("local deterministic provider is disabled")
        return LocalDeterministicModel()
    raise AgentRuntimeError("agent model provider is not configured")


@dataclass(frozen=True)
class AgentStep:
    terminal: bool
    result_ref: dict[str, Any] | None


def _agent_run_result_ref(row: AgentRunRow) -> dict[str, Any]:
    return {
        "object_type": "agent_run",
        "object_id": row.id,
        "object_version": None,
        "object_revision": row.revision,
        "artifact_id": None,
    }


class AgentGraphState(TypedDict, total=False):
    phase: str
    checkpoint: dict[str, Any]
    action: dict[str, Any]
    wait: dict[str, Any]
    resume_result: dict[str, Any]
    resume_job_id: str
    model_action_index: int


@contextmanager
def _checkpoint_saver() -> Iterator[BaseCheckpointSaver[str]]:
    from quantfoundry.api import app as domain_main

    if not getattr(domain_main.app.state, "domain_database_available", True):
        raise AgentRuntimeError("Agent checkpoint database is not ready")
    database_url = domain_main.engine.url.render_as_string(hide_password=False)
    if database_url.startswith("sqlite"):
        configured = os.getenv("QF_AGENT_CHECKPOINT_SQLITE")
        if configured:
            path = configured
        else:
            artifact_root = os.getenv("QF_ARTIFACT_DIR")
            if not artifact_root:
                raise AgentRuntimeError(
                    "SQLite Agent checkpoint path is not configured"
                )
            path = str(Path(artifact_root) / "agent-checkpoints.sqlite3")
        sqlite_connection = sqlite3.connect(path, check_same_thread=False)
        try:
            saver = SqliteSaver(sqlite_connection)
            saver.setup()
            yield saver
        finally:
            sqlite_connection.close()
        return
    normalized = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    postgres_connection = psycopg.connect(
        normalized, autocommit=True, prepare_threshold=0, row_factory=dict_row
    )
    try:
        postgres_connection.execute("SET search_path TO agent_checkpoint")
        postgres_saver = PostgresSaver(postgres_connection)
        installed = postgres_connection.execute(
            "SELECT max(v) FROM checkpoint_migrations"
        ).fetchone()
        expected = len(postgres_saver.MIGRATIONS) - 1
        if installed is None or installed["max"] != expected:
            raise AgentRuntimeError(
                "Agent checkpoint schema is not at the Alembic-managed version"
            )
        yield postgres_saver
    finally:
        postgres_connection.close()


def _compiled_graph(model: Model, saver: BaseCheckpointSaver[str]) -> Any:
    def dispatch(state: AgentGraphState) -> AgentGraphState:
        if state.get("phase") == "MODEL":
            return {"action": model.next_action(state["checkpoint"])}
        if state.get("phase") == "WAITING_JOB":
            resumed = interrupt(state["wait"])
            if not isinstance(resumed, dict):
                raise AgentRuntimeError("Agent resume payload is invalid")
            job_id = resumed.get("job_id")
            if not isinstance(job_id, str) or not job_id:
                raise AgentRuntimeError("Agent resume job identity is invalid")
            return {"resume_result": resumed, "resume_job_id": job_id}
        raise AgentRuntimeError("Agent graph phase is invalid")

    builder = StateGraph(AgentGraphState)
    builder.add_node("dispatch", dispatch)
    builder.add_edge(START, "dispatch")
    builder.add_edge("dispatch", END)
    return builder.compile(checkpointer=saver, name="quantfoundry-agent-v1")


def _graph_action(
    model: Model, row: AgentRunRow, checkpoint: dict[str, Any]
) -> dict[str, Any]:
    thread_id = row.checkpoint_thread_id or f"agent:{row.id}"
    row.checkpoint_thread_id = thread_id
    with _checkpoint_saver() as saver:
        graph = _compiled_graph(model, saver)
        config = {"configurable": {"thread_id": thread_id}}
        saved = graph.get_state(config)
        values = saved.values if saved is not None else {}
        if (
            isinstance(values, dict)
            and values.get("model_action_index") == checkpoint.get("model_action_index")
            and isinstance(values.get("action"), dict)
        ):
            return values["action"]
        result = graph.invoke(
            {
                "phase": "MODEL",
                "checkpoint": checkpoint,
                "model_action_index": checkpoint.get("model_action_index", 0),
            },
            config,
        )
    action = result.get("action")
    if not isinstance(action, dict):
        raise AgentRuntimeError("Agent graph did not produce an action")
    return action


def _graph_resume(row: AgentRunRow, result: dict[str, Any]) -> dict[str, Any]:
    checkpoint = _checkpoint(row)
    if row.status in {"COMPLETED", "CANCELLED", "FAILED"} or checkpoint.get(
        "pending_job_id"
    ) != result.get("job_id"):
        raise AgentRuntimeError("AGENT_RESUME_CONFLICT")
    return result


class ToolRegistry:
    _CANONICAL_PATH = (
        Path(__file__).resolve().parents[5]
        / "docs/后端系统技术方案/contracts/tools/v1-p0.yaml"
    )
    _CANONICAL_SHA256 = (
        "d13e3c4b60b6dd7232bd6fd3bd96fedb964b07846e502b249beb16b95b840633"
    )
    _EXPECTED_TOOLS = frozenset(
        {
            ("get_market_data", "1.0"),
            ("validate_dataset", "1.0"),
            ("create_data_snapshot", "1.0"),
            ("define_factor", "1.0"),
            ("analyze_factor", "1.0"),
            ("calculate_factor", "1.0"),
            ("compare_factors", "1.0"),
            ("define_strategy", "1.0"),
            ("run_fast_backtest", "1.0"),
            ("compare_backtests", "1.0"),
            ("run_parameter_sensitivity", "1.0"),
            ("freeze_strategy", "1.0"),
            ("run_validation_suite", "1.0"),
        }
    )
    _DOCUMENT_SCHEMA = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "$schema",
            "title",
            "schema_version",
            "contract_stage",
            "additionalProperties",
            "required",
            "properties",
            "tools",
        ],
        "properties": {
            "$schema": {"const": "https://json-schema.org/draft/2020-12/schema"},
            "title": {"type": "string"},
            "schema_version": {"const": 1},
            "contract_stage": {"const": "P0_P0_5_EXECUTABLE"},
            "additionalProperties": {"const": False},
            "required": {"type": "array"},
            "properties": {"type": "object"},
            "tools": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "name",
                        "version",
                        "input_schema",
                        "output_schema",
                        "allowed_agent_roles",
                        "idempotency_class",
                        "side_effect_class",
                        "execution_mode",
                        "timeout_seconds",
                        "requires_policy_checks",
                        "requires_snapshot",
                    ],
                    "properties": {
                        "name": {"type": "string"},
                        "version": {"type": "string", "pattern": "^1\\.0$"},
                        "input_schema": {"type": "object"},
                        "output_schema": {"type": "object"},
                        "allowed_agent_roles": {"type": "array"},
                        "idempotency_class": {"type": "string"},
                        "side_effect_class": {"type": "string"},
                        "execution_mode": {"type": "string"},
                        "timeout_seconds": {"type": "integer", "minimum": 1},
                        "requires_policy_checks": {"type": "array"},
                        "requires_snapshot": {"type": "boolean"},
                    },
                },
            },
        },
    }

    def __init__(self, contract: dict[str, Any]):
        self._validate_contract(contract)
        self.schema_version = contract["schema_version"]
        self.tools = {item["name"]: item for item in contract["tools"]}
        actual = {(item["name"], item["version"]) for item in contract["tools"]}
        if len(actual) != len(contract["tools"]) or actual != self._EXPECTED_TOOLS:
            raise AgentRuntimeError(
                "tool registry does not match canonical name@version set"
            )

    @classmethod
    def _validate_contract(cls, contract: dict[str, Any]) -> None:
        try:
            Draft202012Validator(cls._DOCUMENT_SCHEMA).validate(contract)
            registry_schema = contract["properties"]["tools"]["items"]
            Draft202012Validator.check_schema(registry_schema)
            for item in contract["tools"]:
                Draft202012Validator(registry_schema).validate(item)
                Draft202012Validator.check_schema(item["input_schema"])
                Draft202012Validator.check_schema(item["output_schema"])
        except Exception as error:
            raise AgentRuntimeError("tool registry schema validation failed") from error

    @classmethod
    def load(
        cls,
        path: Path | None = None,
        *,
        test_only: bool = False,
        expected_sha256: str | None = None,
    ) -> ToolRegistry:
        if path is not None and not test_only:
            raise AgentRuntimeError("production tool registry path is immutable")
        source = path if test_only and path is not None else cls._CANONICAL_PATH
        try:
            raw = source.read_bytes()
        except OSError as error:
            raise AgentRuntimeError("canonical tool registry is unavailable") from error
        actual_sha256 = hashlib.sha256(raw).hexdigest()
        required_sha256 = expected_sha256 if test_only else cls._CANONICAL_SHA256
        if actual_sha256 != required_sha256:
            raise AgentRuntimeError(
                "tool registry content hash does not match authority"
            )
        try:
            contract = yaml.safe_load(raw)
        except yaml.YAMLError as error:
            raise AgentRuntimeError("tool registry is not valid YAML") from error
        if not isinstance(contract, dict):
            raise AgentRuntimeError("tool contract is not an object")
        return cls(contract)

    def definition(self, name: str) -> dict[str, Any]:
        try:
            return self.tools[name]
        except KeyError as error:
            raise ToolPolicyDenied(f"tool is not registered: {name}") from error

    def validate_request(
        self,
        session: Session,
        name: str,
        role: str,
        arguments: dict[str, Any],
        passed_policy_checks: set[str],
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        definition = self.definition(name)
        if role not in definition["allowed_agent_roles"]:
            raise ToolPolicyDenied(f"{role} is not allowed to call {name}")
        Draft202012Validator(
            definition["input_schema"],
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        ).validate(arguments)
        missing = set(definition["requires_policy_checks"]) - passed_policy_checks
        if missing:
            raise ToolPolicyDenied(f"missing policy checks: {sorted(missing)}")
        if definition["requires_snapshot"]:
            snapshot_ids = self._required_snapshot_ids(
                session, name, arguments, workspace_id
            )
            if not snapshot_ids or any(
                (
                    snapshot := session.execute(
                        select(SnapshotRow).where(
                            SnapshotRow.id == snapshot_id,
                            SnapshotRow.workspace_id == workspace_id,
                        )
                    ).scalar_one_or_none()
                )
                is None
                or not snapshot.immutable
                or snapshot.workspace_id != workspace_id
                for snapshot_id in snapshot_ids
            ):
                raise ToolPolicyDenied("a durable immutable snapshot is required")
        return definition

    @staticmethod
    def _required_snapshot_ids(
        session: Session,
        name: str,
        arguments: dict[str, Any],
        workspace_id: str | None,
    ) -> set[str]:
        explicit = arguments.get("snapshot_id")
        if isinstance(explicit, str):
            return {explicit}
        if name == "compare_backtests":
            snapshot_ids: set[str] = set()
            for experiment_id in arguments.get("experiment_ids", []):
                experiment = session.execute(
                    select(ExperimentRow).where(
                        ExperimentRow.id == experiment_id,
                        ExperimentRow.workspace_id == workspace_id,
                    )
                ).scalar_one_or_none()
                if experiment is None:
                    return set()
                snapshot_id = json.loads(experiment.detail).get("data_snapshot_id")
                if not isinstance(snapshot_id, str):
                    return set()
                snapshot_ids.add(snapshot_id)
            return snapshot_ids
        if name == "run_validation_suite":
            version = session.execute(
                select(StrategyVersionRow).where(
                    StrategyVersionRow.strategy_id == arguments.get("strategy_id"),
                    StrategyVersionRow.version == arguments.get("strategy_version"),
                    StrategyVersionRow.workspace_id == workspace_id,
                )
            ).scalar_one_or_none()
            if version is None:
                return set()
            version_detail = json.loads(version.detail)
            latest_backtest = version_detail.get("latest_backtest")
            result = (
                latest_backtest.get("result")
                if isinstance(latest_backtest, dict)
                else None
            )
            experiment = result.get("experiment") if isinstance(result, dict) else None
            job_id = experiment.get("id") if isinstance(experiment, dict) else None
            if not isinstance(job_id, str):
                return set()
            candidate = session.execute(
                select(JobRow).where(
                    JobRow.id == job_id,
                    JobRow.workspace_id == workspace_id,
                    JobRow.job_type == "FAST_BACKTEST",
                    JobRow.status == "COMPLETED",
                )
            ).scalar_one_or_none()
            if candidate is None:
                return set()
            inputs = json.loads(candidate.input_payload)
            snapshot_id = inputs.get("snapshot_id")
            if (
                inputs.get("strategy_version_id") == version.id
                and inputs.get("strategy_spec_sha256") == version.spec_sha256
                and isinstance(snapshot_id, str)
            ):
                return {snapshot_id}
        return set()

    def validate_output(
        self, definition: dict[str, Any], output: dict[str, Any]
    ) -> None:
        Draft202012Validator(
            definition["output_schema"],
            format_checker=Draft202012Validator.FORMAT_CHECKER,
        ).validate(output)


REGISTRY = ToolRegistry.load()


def evaluated_policy_checks(
    session: Session,
    name: str,
    arguments: dict[str, Any],
    run: AgentRunRow,
) -> set[str]:
    """Evaluate policy facts from durable rows; model claims are never trusted."""
    passed: set[str] = set()
    snapshot_id = arguments.get("snapshot_id")
    if (
        isinstance(snapshot_id, str)
        and (
            snapshot := session.execute(
                select(SnapshotRow).where(
                    SnapshotRow.id == snapshot_id,
                    SnapshotRow.workspace_id == run.workspace_id,
                )
            ).scalar_one_or_none()
        )
        is not None
        and snapshot.immutable
    ):
        passed.add("data_snapshot_access")
    dataset_id = arguments.get("dataset_id")
    if isinstance(dataset_id, str):
        source = session.get(DataSource, (dataset_id, run.workspace_id))
        if (
            source is not None
            and source.workspace_id == run.workspace_id
            and source.status == "ACTIVE"
        ):
            passed.add("data_capability")
        if (
            source is not None
            and source.workspace_id == run.workspace_id
            and source.status == "VALID"
        ):
            passed.update({"data_capability", "dataset_valid"})
    research_id = arguments.get("research_id") or run.research_id
    if isinstance(research_id, str):
        research = session.execute(
            select(ResearchRow).where(
                ResearchRow.id == research_id,
                ResearchRow.workspace_id == run.workspace_id,
            )
        ).scalar_one_or_none()
        if research is not None and research.status not in {"COMPLETED", "ARCHIVED"}:
            passed.add("research_writable")
    strategy_id = arguments.get("strategy_id")
    strategy_version = arguments.get("strategy_version")
    strategy = None
    if isinstance(strategy_id, str) and isinstance(strategy_version, int):
        strategy = session.execute(
            select(StrategyVersionRow).where(
                StrategyVersionRow.strategy_id == strategy_id,
                StrategyVersionRow.version == strategy_version,
                StrategyVersionRow.workspace_id == run.workspace_id,
            )
        ).scalar_one_or_none()
    if strategy is not None and strategy.state == "CANDIDATE":
        passed.update({"strategy_candidate", "strategy_freeze_eligible"})
    if strategy is not None and strategy.state == "FROZEN":
        passed.update({"strategy_frozen", "validation_allowed"})
    experiment_ids = arguments.get("experiment_ids")
    if (
        isinstance(experiment_ids, list)
        and experiment_ids
        and all(
            isinstance(item, str)
            and session.execute(
                select(ExperimentRow.id).where(
                    ExperimentRow.id == item,
                    ExperimentRow.workspace_id == run.workspace_id,
                )
            ).scalar_one_or_none()
            is not None
            for item in experiment_ids
        )
    ):
        passed.add("experiment_read")
    # owner_intent is intentionally never granted to an autonomous Agent run.
    return passed


def _checkpoint(row: AgentRunRow) -> dict[str, Any]:
    value = json.loads(row.checkpoint or "{}")
    value.setdefault("schema_version", 1)
    value.setdefault("model_action_index", 0)
    value.setdefault("semantic_call_hashes", [])
    value.setdefault("result_refs", [])
    value.setdefault("tool_results", [])
    return value


def _context_pack(session: Session, row: AgentRunRow) -> dict[str, Any]:
    """Build a bounded, holdout-free durable context from workspace-owned facts."""

    research = (
        session.execute(
            select(ResearchRow).where(
                ResearchRow.id == row.research_id,
                ResearchRow.workspace_id == row.workspace_id,
            )
        ).scalar_one_or_none()
        if row.research_id
        else None
    )
    if row.research_id is not None and research is None:
        raise AgentRuntimeError("agent context crossed a workspace boundary")
    detail = json.loads(research.detail) if research is not None else {}
    dataset_ids = sorted(
        session.execute(
            select(DataSource.id).where(DataSource.workspace_id == row.workspace_id)
        ).scalars()
    )
    return {
        "agent_run_id": row.id,
        "workspace_id": row.workspace_id,
        "role": row.role,
        "objective": row.objective,
        "dataset_ids": dataset_ids,
        "research": (
            {
                "research_id": research.id,
                "revision": research.revision,
                "status": research.status,
                "title": research.title,
                "normalized_question": detail.get("normalized_question"),
                "evidence_status": detail.get("evidence_status"),
            }
            if research is not None
            else None
        ),
    }


def _research_policy_version_ref(session: Session, row: AgentRunRow) -> str:
    policy_id = None
    if row.research_id is not None:
        research = session.execute(
            select(ResearchRow).where(
                ResearchRow.id == row.research_id,
                ResearchRow.workspace_id == row.workspace_id,
            )
        ).scalar_one_or_none()
        if research is None:
            raise AgentRuntimeError("agent research policy scope is unavailable")
        detail = json.loads(research.detail)
        policy_id = detail.get("research_policy_id")
    if isinstance(policy_id, str):
        policy = session.execute(
            select(ResearchPolicyVersionRow).where(
                ResearchPolicyVersionRow.workspace_id == row.workspace_id,
                ResearchPolicyVersionRow.policy_id == policy_id,
                ResearchPolicyVersionRow.policy_family == "research",
                ResearchPolicyVersionRow.status == "ACTIVE",
            )
        ).scalar_one_or_none()
    else:
        binding = session.get(SetupBindingRow, row.workspace_id)
        policy = (
            session.execute(
                select(ResearchPolicyVersionRow).where(
                    ResearchPolicyVersionRow.id == binding.research_policy_version_id,
                    ResearchPolicyVersionRow.workspace_id == row.workspace_id,
                )
            ).scalar_one_or_none()
            if binding is not None and binding.research_policy_version_id is not None
            else None
        )
        if policy is not None and (
            policy.workspace_id != row.workspace_id
            or policy.policy_family != "research"
            or policy.status != "ACTIVE"
        ):
            policy = None
        if policy is None:
            active = (
                session.execute(
                    select(ResearchPolicyVersionRow).where(
                        ResearchPolicyVersionRow.workspace_id == row.workspace_id,
                        ResearchPolicyVersionRow.policy_family == "research",
                        ResearchPolicyVersionRow.status == "ACTIVE",
                    )
                )
                .scalars()
                .all()
            )
            policy = active[0] if len(active) == 1 else None
    if policy is None or policy.workspace_id != row.workspace_id:
        raise AgentRuntimeError("research policy version is unavailable")
    return str(policy.id)


def _research_status(session: Session, row: AgentRunRow, status: str) -> None:
    if not row.research_id:
        return
    research = session.execute(
        select(ResearchRow).where(
            ResearchRow.id == row.research_id,
            ResearchRow.workspace_id == row.workspace_id,
        )
    ).scalar_one_or_none()
    if research is None:
        return
    research.status = status
    research.revision += 1
    detail = json.loads(research.detail)
    updated_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    detail.update(
        {
            "status": status,
            "revision": research.revision,
            "updated_at": updated_at,
            "completed_at": updated_at if status == "COMPLETED" else None,
            "action_capabilities": []
            if status == "COMPLETED"
            else detail.get("action_capabilities", []),
        }
    )
    research.detail = json.dumps(validated_payload("ResearchDetail", detail))
    emit(
        session,
        "research",
        research.id,
        research.revision,
        "research.updated",
        payload={"state": status, "status": status},
        agent_run_id=row.id,
    )


def _finish_run(
    session: Session,
    row: AgentRunRow,
    checkpoint: dict[str, Any],
    status: str,
    summary: str,
) -> AgentStep:
    now = datetime.now(UTC)
    checkpoint["safe_checkpoint"] = status
    checkpoint["checkpointed_at"] = now.isoformat().replace("+00:00", "Z")
    row.checkpoint = json.dumps(checkpoint)
    row.status = status
    row.decision_summary = summary
    row.ended_at = now
    row.revision += 1
    if (
        row.role == "RESEARCH_DIRECTOR"
        and row.parent_agent_run_id is None
        and row.root_agent_run_id is None
    ):
        research_status = "COMPLETED" if status == "COMPLETED" else "WAITING_USER"
        _research_status(session, row, research_status)
    emit(
        session,
        "agent_run",
        row.id,
        row.revision,
        "agent.run.updated",
        payload={
            "state": status,
            "status": status,
            "agent_run_id": row.id,
            "role": row.role,
            "objective": row.objective,
            "research_id": row.research_id,
            "object_type": row.object_type,
            "object_id": row.object_id,
            "object_version": row.object_version,
            "object_revision": row.object_revision,
        },
        agent_run_id=row.id,
    )
    return AgentStep(
        True,
        _agent_run_result_ref(row),
    )


def _require_research_completion_evidence(session: Session, row: AgentRunRow) -> None:
    """A Research Director cannot declare success without durable evidence."""

    if row.role != "RESEARCH_DIRECTOR" or row.research_id is None:
        return
    experiments = session.execute(
        select(ExperimentRow).where(
            ExperimentRow.workspace_id == row.workspace_id,
            ExperimentRow.research_id == row.research_id,
            ExperimentRow.immutable.is_(True),
        )
    ).scalars()
    found = False
    for experiment in experiments:
        found = True
        detail = json.loads(experiment.detail)
        if (
            detail.get("status") == "COMPLETED"
            and detail.get("validity_state") == "VALID"
            and detail.get("artifacts")
            and isinstance(detail.get("provenance"), dict)
        ):
            return
    raise AgentRuntimeError(
        "RESEARCH_COMPLETION_EVIDENCE_INVALID"
        if found
        else "RESEARCH_COMPLETION_EVIDENCE_MISSING"
    )


def _suspend_for_child_job(
    session: Session,
    parent_job: JobRow,
    row: AgentRunRow,
    tool_call: ToolCallRow,
    checkpoint: dict[str, Any],
    child_job_id: str,
) -> AgentStep:
    child = session.execute(
        select(JobRow).where(
            JobRow.id == child_job_id,
            JobRow.workspace_id == row.workspace_id,
        )
    ).scalar_one_or_none()
    if child is None:
        raise AgentRuntimeError("Agent child job is unavailable")
    token_hash = hashlib.sha256(secrets.token_bytes(32)).hexdigest()
    row.resume_fencing_token += 1
    row.pending_resume_token_hash = token_hash
    accepted = enqueue_job(
        session,
        "AGENT_RESUME",
        {"type": "agent_run", "id": row.id, "version": None, "revision": row.revision},
        input_payload={
            "agent_run_id": row.id,
            "checkpoint_thread_id": row.checkpoint_thread_id or f"agent:{row.id}",
            "tool_call_id": tool_call.id,
            "awaited_job_id": child_job_id,
            "resume_token_hash": token_hash,
            "resume_fencing_token": row.resume_fencing_token,
            "reason": "TOOL_TERMINAL",
        },
        queue_name="agent",
        retry_safe=True,
        max_attempts=3,
    )
    resume_job = session.execute(
        select(JobRow).where(
            JobRow.id == accepted["job_id"],
            JobRow.workspace_id == row.workspace_id,
        )
    ).scalar_one_or_none()
    if resume_job is None:
        raise AgentRuntimeError("Agent resume job was not persisted")
    resume_job.resume_token_hash = token_hash
    resume_job.resume_fencing_token = row.resume_fencing_token
    session.add(
        JobDependencyRow(
            job_id=resume_job.id,
            depends_on_job_id=child_job_id,
            workspace_id=row.workspace_id,
            dependency_type="TERMINAL",
        )
    )
    checkpoint.update(
        {
            "safe_checkpoint": "WAITING_JOB",
            "graph_status": "WAITING_JOB",
            "pending_tool_call_id": tool_call.id,
            "pending_job_id": child_job_id,
            "pending_resume_job_id": resume_job.id,
            "resume_fencing_token": row.resume_fencing_token,
            "checkpointed_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        }
    )
    row.checkpoint = json.dumps(checkpoint)
    row.status = "RUNNING"
    row.revision += 1
    emit(
        session,
        "agent_run",
        row.id,
        row.revision,
        "agent.run.updated",
        payload={
            "state": "RUNNING",
            "status": "RUNNING",
            "agent_run_id": row.id,
            "current_step_key": "WAITING_JOB",
        },
        job_id=parent_job.id,
        agent_run_id=row.id,
        tool_call_id=tool_call.id,
        correlation_id=parent_job.correlation_id,
    )
    return AgentStep(
        True,
        _agent_run_result_ref(row),
    )


def _consume_resume(
    session: Session,
    resume_job: JobRow,
    row: AgentRunRow,
    checkpoint: dict[str, Any],
) -> AgentStep | None:
    if row.status in {"COMPLETED", "CANCELLED", "FAILED"}:
        raise AgentRuntimeError("AGENT_RESUME_CONFLICT")
    inputs = json.loads(resume_job.input_payload)
    token_hash = inputs.get("resume_token_hash")
    fencing_token = inputs.get("resume_fencing_token")
    if (
        resume_job.resume_token_hash != token_hash
        or resume_job.resume_fencing_token != fencing_token
        or row.pending_resume_token_hash != token_hash
        or row.resume_fencing_token != fencing_token
        or checkpoint.get("resume_fencing_token") != fencing_token
        or checkpoint.get("pending_resume_job_id") != resume_job.id
        or checkpoint.get("pending_tool_call_id") != inputs.get("tool_call_id")
        or checkpoint.get("pending_job_id") != inputs.get("awaited_job_id")
    ):
        raise AgentRuntimeError("AGENT_RESUME_CONFLICT")
    tool_call = session.execute(
        select(ToolCallRow)
        .where(
            ToolCallRow.id == inputs.get("tool_call_id"),
            ToolCallRow.agent_run_id == row.id,
            ToolCallRow.workspace_id == row.workspace_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    child = session.execute(
        select(JobRow)
        .where(
            JobRow.id == inputs.get("awaited_job_id"),
            JobRow.workspace_id == row.workspace_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if (
        tool_call is None
        or child is None
        or tool_call.status != "RUNNING"
        or tool_call.job_id != child.id
    ):
        raise AgentRuntimeError("AGENT_RESUME_CONFLICT")
    if child.status not in {"COMPLETED", "FAILED", "CANCELLED"}:
        raise AgentRuntimeError("Agent child job is not terminal")
    child_result_ref = json.loads(child.result_ref) if child.result_ref else None
    if child_result_ref is not None and not job_result_ref_valid(child_result_ref):
        raise AgentRuntimeError("Agent child result_ref is not canonical")
    result = {
        "job_id": child.id,
        "status": child.status,
        "result_ref": child_result_ref,
        "error_code": child.error_code,
    }
    resumed = _graph_resume(row, result)
    if resumed != result:
        raise AgentRuntimeError("Agent checkpoint result mismatch")
    now = datetime.now(UTC)
    tool_call.status = (
        "SUCCESS"
        if child.status == "COMPLETED"
        else "CANCELLED"
        if child.status == "CANCELLED"
        else "ERROR"
    )
    tool_call.result_summary = json.dumps(result)
    provenance = create_provenance(
        session,
        input_value={
            "tool_name": tool_call.tool_name,
            "arguments": json.loads(tool_call.input_payload),
        },
        output_sha256=content_hash(result),
        engine_name="semantic-tool-runtime",
        tool_call_id=tool_call.id,
    )
    tool_call.provenance = json.dumps(provenance)
    tool_call.warnings = json.dumps(
        []
        if child.status == "COMPLETED"
        else [{"code": child.error_code or "TOOL_EXECUTION_FAILED"}]
    )
    tool_call.finished_at = now
    started_at = tool_call.started_at or now
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)
    tool_call.duration_ms = max(0, int((now - started_at).total_seconds() * 1000))
    if (
        child.status == "COMPLETED"
        and isinstance(child_result_ref, dict)
        and child_result_ref.get("object_type") == "experiment"
        and isinstance(child_result_ref.get("object_id"), str)
        and row.research_id is not None
    ):
        research = session.execute(
            select(ResearchRow)
            .where(
                ResearchRow.id == row.research_id,
                ResearchRow.workspace_id == row.workspace_id,
            )
            .with_for_update()
        ).scalar_one_or_none()
        experiment = session.execute(
            select(ExperimentRow).where(
                ExperimentRow.id == child_result_ref["object_id"],
                ExperimentRow.workspace_id == row.workspace_id,
                ExperimentRow.research_id == row.research_id,
            )
        ).scalar_one_or_none()
        if research is None or experiment is None or not experiment.immutable:
            raise AgentRuntimeError("completed Agent experiment lineage is unavailable")
        research_detail = json.loads(research.detail)
        experiment_detail = json.loads(experiment.detail)
        item = validated_payload(
            "ResearchExperimentItem",
            {
                "experiment": {
                    "type": "experiment",
                    "id": experiment.id,
                    "version": None,
                    "revision": experiment.revision,
                },
                "objective": experiment_detail["objective"],
                "experiment_type": experiment_detail["experiment_type"],
                "status": experiment_detail["status"],
                "validity_state": experiment_detail["validity_state"],
                "job_id": child.id,
                "provenance": {
                    "provenance_id": experiment_detail["provenance"]["provenance_id"]
                },
                "created_at": experiment_detail["created_at"],
            },
        )
        items = research_detail["experiments"]["items"]
        items[:] = [
            existing
            for existing in items
            if existing["experiment"]["id"] != experiment.id
        ]
        items.append(item)
        research.revision += 1
        research_detail["revision"] = research.revision
        research_detail["updated_at"] = now.isoformat().replace("+00:00", "Z")
        research.detail = json.dumps(
            validated_payload("ResearchDetail", research_detail)
        )
        refreshed_context = _context_pack(session, row)
        refreshed_context_sha256 = content_hash(refreshed_context)
        row.context_sha256 = refreshed_context_sha256
        checkpoint["context"] = refreshed_context
        checkpoint["context_sha256"] = refreshed_context_sha256
    row.pending_resume_token_hash = None
    resume_job.current_step_key = "RESUME_CONSUMED"
    resume_job.current_step_label = "Child terminal result consumed"
    checkpoint.pop("pending_tool_call_id", None)
    checkpoint.pop("pending_job_id", None)
    checkpoint.pop("pending_resume_job_id", None)
    checkpoint["graph_status"] = "RUNNING"
    checkpoint["safe_checkpoint"] = "AFTER_TOOL"
    checkpoint["checkpointed_at"] = now.isoformat().replace("+00:00", "Z")
    checkpoint["result_refs"].append(result)
    checkpoint["tool_results"].append(
        {"tool_name": tool_call.tool_name, "result_ref": child_result_ref, **result}
    )
    row.checkpoint = json.dumps(checkpoint)
    row.revision += 1
    emit(
        session,
        "tool_call",
        tool_call.id,
        1,
        "tool.call.updated",
        payload={"state": tool_call.status, "status": tool_call.status},
        job_id=child.id,
        agent_run_id=row.id,
        tool_call_id=tool_call.id,
        correlation_id=resume_job.correlation_id,
    )
    if child.status != "COMPLETED":
        return _finish_run(
            session,
            row,
            checkpoint,
            "WAITING_USER",
            child.error_code or "TOOL_EXECUTION_FAILED",
        )
    return None


def advance_agent_run(
    session: Session,
    job: JobRow,
) -> AgentStep:
    inputs = json.loads(job.input_payload)
    run_id = inputs.get("agent_run_id")
    row = session.execute(
        select(AgentRunRow)
        .where(
            AgentRunRow.id == run_id,
            AgentRunRow.workspace_id == job.workspace_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if row is None:
        raise AgentRuntimeError("agent run is missing")
    config = session.get(AgentConfigRow, (row.workspace_id or "system", row.role))
    if config is None:
        raise AgentRuntimeError("agent configuration is missing")
    checkpoint = _checkpoint(row)
    context_pack = _context_pack(session, row)
    context_sha256 = content_hash(context_pack)
    if row.context_sha256 and checkpoint.get("context_sha256") not in {
        None,
        context_sha256,
    }:
        raise AgentRuntimeError("agent context changed outside a safe checkpoint")
    row.context_sha256 = context_sha256
    checkpoint["context_sha256"] = context_sha256
    checkpoint["context"] = context_pack
    if job.job_type == "AGENT_RESUME" and job.current_step_key != "RESUME_CONSUMED":
        resumed_step = _consume_resume(session, job, row, checkpoint)
        if resumed_step is not None:
            return resumed_step
    if not config.enabled:
        return _finish_run(
            session, row, checkpoint, "CANCELLED", "AGENT_DISABLED at safe checkpoint"
        )
    if row.status in {"COMPLETED", "CANCELLED", "FAILED", "WAITING_USER"}:
        return AgentStep(
            True,
            _agent_run_result_ref(row),
        )
    max_steps = min(DEFAULT_MAX_STEPS, config.max_steps_override or DEFAULT_MAX_STEPS)
    max_tools = min(
        DEFAULT_MAX_TOOL_CALLS,
        config.max_tool_calls_override or DEFAULT_MAX_TOOL_CALLS,
    )
    if row.step_count >= max_steps or row.tool_call_count >= max_tools:
        return _finish_run(
            session, row, checkpoint, "WAITING_USER", "AGENT_BUDGET_EXCEEDED"
        )
    now = datetime.now(UTC)
    row.status = "RUNNING"
    row.started_at = row.started_at or now
    expected_revision = row.revision
    session.flush()
    # Hold the row lock across the model call; committing here permits two
    # workers to issue the same paid invocation before the revision fence.
    # ponytail: one row lock is sufficient for this single-run execution lane.
    action = _graph_action(configured_model(config, session), row, checkpoint)
    session.refresh(row, with_for_update=True)
    if row.revision != expected_revision:
        raise AgentRuntimeError("AGENT_CONTEXT_STALE")
    action_type = action.get("type")
    row.model_call_count += 1
    row.step_count += 1
    input_tokens = action.get("input_tokens", 0)
    output_tokens = action.get("output_tokens", 0)
    if any(
        not isinstance(value, int)
        or isinstance(value, bool)
        or not 0 <= value <= 10_000_000
        for value in (input_tokens, output_tokens)
    ):
        raise AgentRuntimeError("model usage accounting is invalid")
    row.input_tokens += input_tokens
    row.output_tokens += output_tokens
    checkpoint["model_action_index"] += 1
    if action_type == "conclude":
        _require_research_completion_evidence(session, row)
        return _finish_run(
            session,
            row,
            checkpoint,
            "COMPLETED",
            str(action.get("summary") or "Research concluded"),
        )
    if action_type != "tool":
        raise AgentRuntimeError("model action must be tool or conclude")
    if row.tool_call_count >= max_tools:
        return _finish_run(
            session, row, checkpoint, "WAITING_USER", "AGENT_BUDGET_EXCEEDED"
        )
    name = str(action.get("name"))
    arguments = action.get("arguments")
    if not isinstance(arguments, dict):
        raise AgentRuntimeError("tool arguments must be an object")
    definition = REGISTRY.validate_request(
        session,
        name,
        row.role,
        arguments,
        evaluated_policy_checks(session, name, arguments, row),
        workspace_id=row.workspace_id,
    )
    policy_version_ref = _research_policy_version_ref(session, row)
    semantic_hash = content_hash(
        {
            "tool_name": name,
            "arguments": arguments,
            "policy_version_ref": policy_version_ref,
        }
    )
    semantic_scope = (
        f"research:{row.research_id}"
        if row.research_id is not None
        else f"run:{row.id}"
    )

    def replay(existing: ToolCallRow) -> None:
        summary = json.loads(existing.result_summary or "{}")
        checkpoint["semantic_call_hashes"].append(semantic_hash)
        checkpoint["result_refs"].append(summary)
        if {"job_id", "status", "result_ref"} <= set(summary):
            checkpoint["tool_results"].append(
                {"tool_name": existing.tool_name, **summary}
            )
        else:
            checkpoint["tool_results"].append(
                {"tool_name": existing.tool_name, "result_summary": summary}
            )

    def wait_for(existing: ToolCallRow) -> AgentStep | None:
        if not existing.job_id:
            raise AgentRuntimeError("active semantic tool call has no child job")
        waiting_call = existing
        if existing.agent_run_id != row.id:
            wait_scope = f"wait:{row.id}:{semantic_hash[:12]}"
            waiting_call = session.execute(
                select(ToolCallRow)
                .where(
                    ToolCallRow.workspace_id == row.workspace_id,
                    ToolCallRow.agent_run_id == row.id,
                    ToolCallRow.semantic_scope == wait_scope,
                    ToolCallRow.status.in_({"RUNNING", "SUCCESS"}),
                )
                .with_for_update()
            ).scalar_one_or_none()
            if waiting_call is None:
                waiting_call = ToolCallRow(
                    id=new_id("TCALL"),
                    workspace_id=row.workspace_id,
                    agent_run_id=row.id,
                    tool_name=name,
                    tool_version=definition["version"],
                    status="RUNNING",
                    input_payload=json.dumps(arguments),
                    input=arguments,
                    input_sha256=semantic_hash,
                    semantic_scope=wait_scope,
                    objective=row.objective,
                    research_id=row.research_id,
                    policy_version_ref=policy_version_ref,
                    job_id=existing.job_id,
                    warnings=json.dumps([{"code": "SEMANTIC_DEDUP_WAIT"}]),
                    started_at=now,
                )
                try:
                    with session.begin_nested():
                        session.add(waiting_call)
                        session.flush()
                except IntegrityError:
                    waiting_call = session.execute(
                        select(ToolCallRow)
                        .where(
                            ToolCallRow.workspace_id == row.workspace_id,
                            ToolCallRow.agent_run_id == row.id,
                            ToolCallRow.semantic_scope == wait_scope,
                            ToolCallRow.status.in_({"RUNNING", "SUCCESS"}),
                        )
                        .with_for_update()
                    ).scalar_one()
            if waiting_call.status == "SUCCESS":
                replay(waiting_call)
                return None
        row.tool_call_count += 1
        return _suspend_for_child_job(
            session,
            job,
            row,
            waiting_call,
            checkpoint,
            existing.job_id,
        )

    prior = session.execute(
        select(ToolCallRow).where(
            ToolCallRow.workspace_id == row.workspace_id,
            ToolCallRow.semantic_scope == semantic_scope,
            ToolCallRow.tool_name == name,
            ToolCallRow.input_sha256 == semantic_hash,
            ToolCallRow.status.in_({"RUNNING", "SUCCESS"}),
        )
    ).scalar_one_or_none()
    tool_call: ToolCallRow | None = None
    if prior is not None and prior.status == "SUCCESS":
        replay(prior)
    elif prior is not None:
        step = wait_for(prior)
        if step is not None:
            return step
    else:
        from quantfoundry.agents.tools.executors import execute_tool

        candidate = ToolCallRow(
            id=new_id("TCALL"),
            workspace_id=row.workspace_id,
            agent_run_id=row.id,
            tool_name=name,
            tool_version=definition["version"],
            status="RUNNING",
            input_payload=json.dumps(arguments),
            input=arguments,
            input_sha256=semantic_hash,
            semantic_scope=semantic_scope,
            objective=row.objective,
            research_id=row.research_id,
            policy_version_ref=policy_version_ref,
            warnings="[]",
            started_at=now,
        )
        try:
            with session.begin_nested():
                session.add(candidate)
                session.flush()
        except IntegrityError:
            winner = session.execute(
                select(ToolCallRow)
                .where(
                    ToolCallRow.workspace_id == row.workspace_id,
                    ToolCallRow.semantic_scope == semantic_scope,
                    ToolCallRow.tool_name == name,
                    ToolCallRow.input_sha256 == semantic_hash,
                    ToolCallRow.status.in_({"RUNNING", "SUCCESS"}),
                )
                .with_for_update()
            ).scalar_one_or_none()
            if winner is None:
                raise
            if winner.status == "SUCCESS":
                replay(winner)
            else:
                step = wait_for(winner)
                if step is not None:
                    return step
        else:
            tool_call = candidate
    if tool_call is not None:
        expected_revision = row.revision
        session.flush()
        # Keep the claimed ToolCall and AgentRun lock private until execute_tool
        # assigns the child job, so contenders cannot observe an incomplete call.
        try:
            output = execute_tool(
                session,
                row,
                job,
                name,
                arguments,
                {
                    "agent_run_id": row.id,
                    "tool_call_id": tool_call.id,
                    "job_id": job.id,
                },
            )
            REGISTRY.validate_output(definition, output)
            session.refresh(row, with_for_update=True)
            if row.revision != expected_revision:
                raise AgentRuntimeError("AGENT_CONTEXT_STALE")
        except Exception as error:
            raise ToolExecutionFailure(
                tool_call_id=tool_call.id,
                tool_name=name,
                tool_version=definition["version"],
                input_payload=json.dumps(arguments, sort_keys=True),
                input_sha256=semantic_hash,
                semantic_scope=semantic_scope,
                agent_run_id=row.id,
                workspace_id=row.workspace_id,
                research_id=row.research_id,
                objective=row.objective,
                started_at=now,
                cause=error,
                policy_version_ref=policy_version_ref,
            ) from error
        child_job_id = output.get("job_id")
        if isinstance(child_job_id, str):
            tool_call.job_id = child_job_id
            row.tool_call_count += 1
            return _suspend_for_child_job(
                session,
                job,
                row,
                tool_call,
                checkpoint,
                child_job_id,
            )
        object_refs = [
            {
                "type": key.removesuffix("_id"),
                "id": value,
                "version": output.get("version"),
                "revision": output.get("revision", 1),
            }
            for key, value in output.items()
            if key.endswith("_id") and isinstance(value, str)
        ]
        metric_keys = [
            key
            for key, value in output.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        ]
        result_summary = {
            "output": output,
            "object_refs": object_refs,
            "metric_keys": metric_keys,
        }
        provenance = create_provenance(
            session,
            input_value={"tool_name": name, "arguments": arguments},
            output_sha256=content_hash(output),
            engine_name="semantic-tool-runtime",
            tool_call_id=tool_call.id,
        )
        finished = datetime.now(UTC)
        tool_call.status = "SUCCESS"
        tool_call.result_summary = json.dumps(result_summary)
        tool_call.job_id = output.get("job_id")
        tool_call.output_artifact_id = output.get("artifact_id")
        tool_call.provenance = json.dumps(provenance)
        tool_call.finished_at = finished
        tool_call.duration_ms = max(0, int((finished - now).total_seconds() * 1000))
        row.tool_call_count += 1
        checkpoint["semantic_call_hashes"].append(semantic_hash)
        checkpoint["result_refs"].append(result_summary)
        checkpoint["tool_results"].append(
            {"tool_name": name, "status": "SUCCESS", "result_summary": result_summary}
        )
        emit(
            session,
            "tool_call",
            tool_call.id,
            1,
            "tool.call.updated",
            payload={"state": "SUCCESS", "status": "SUCCESS"},
            job_id=job.id,
            agent_run_id=row.id,
            tool_call_id=tool_call.id,
            correlation_id=job.correlation_id,
        )
    checkpoint["safe_checkpoint"] = "AFTER_TOOL"
    checkpoint["checkpointed_at"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")
    row.checkpoint = json.dumps(checkpoint)
    row.revision += 1
    emit(
        session,
        "agent_run",
        row.id,
        row.revision,
        "agent.run.updated",
        payload={
            "state": "RUNNING",
            "status": "RUNNING",
            "agent_run_id": row.id,
            "role": row.role,
            "objective": row.objective,
            "research_id": row.research_id,
            "object_type": row.object_type,
            "object_id": row.object_id,
            "object_version": row.object_version,
            "object_revision": row.object_revision,
            "current_step_key": "AFTER_TOOL",
        },
        job_id=job.id,
        agent_run_id=row.id,
        correlation_id=job.correlation_id,
    )
    return AgentStep(False, None)


def _revoke_pending_jobs(
    session: Session, row: AgentRunRow, now: datetime, *, owner_job_id: str
) -> None:
    checkpoint = _checkpoint(row)
    pending_ids = {
        checkpoint.get("pending_job_id"),
        checkpoint.get("pending_resume_job_id"),
    }
    for pending_id in pending_ids:
        if not isinstance(pending_id, str):
            continue
        pending = session.execute(
            select(JobRow).where(
                JobRow.id == pending_id,
                JobRow.workspace_id == row.workspace_id,
            )
        ).scalar_one_or_none()
        if pending is None or pending.status not in {"QUEUED", "RUNNING"}:
            continue
        try:
            pending_inputs = json.loads(pending.input_payload)
        except (TypeError, json.JSONDecodeError):
            continue
        if pending_id == checkpoint.get("pending_job_id"):
            if pending_inputs.get("parent_job_id") != owner_job_id:
                continue
        elif pending_inputs.get("agent_run_id") != row.id:
            continue
        try:
            request_cancellation(session, pending.id, now=now)
        except JobNotCancellable:
            continue


def fail_agent_run(session: Session, job: JobRow, error: Exception) -> None:
    inputs = json.loads(job.input_payload)
    run_id = inputs.get("agent_run_id")
    row = session.execute(
        select(AgentRunRow)
        .where(
            AgentRunRow.id == run_id,
            AgentRunRow.workspace_id == job.workspace_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if (
        row is None
        or row.workspace_id != job.workspace_id
        or row.status in {"COMPLETED", "CANCELLED", "FAILED", "WAITING_USER"}
    ):
        return
    now = datetime.now(UTC)
    failure = type(error).__name__
    reason_code = _agent_failure_reason(error)
    checkpoint = _checkpoint(row)
    checkpoint.update(
        {
            "safe_checkpoint": "FAILED",
            "failure_type": failure,
            "checkpointed_at": now.isoformat().replace("+00:00", "Z"),
        }
    )
    row.checkpoint = json.dumps(checkpoint)
    row.status = "FAILED"
    row.decision_summary = failure
    row.ended_at = now
    row.revision += 1
    row.pending_resume_token_hash = None
    _revoke_pending_jobs(session, row, now, owner_job_id=job.id)
    if (
        row.role == "RESEARCH_DIRECTOR"
        and row.parent_agent_run_id is None
        and row.root_agent_run_id is None
    ):
        _research_status(session, row, "WAITING_USER")
    running_calls = (
        session.execute(
            select(ToolCallRow).where(
                ToolCallRow.agent_run_id == row.id,
                ToolCallRow.workspace_id == row.workspace_id,
                ToolCallRow.status == "RUNNING",
            )
        )
        .scalars()
        .all()
    )
    for tool_call in running_calls:
        tool_call.status = "ERROR"
        tool_call.warnings = json.dumps(
            [{"code": "TOOL_EXECUTION_FAILED", "detail": failure}]
        )
        tool_call.finished_at = now
        started_at = tool_call.started_at or now
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=UTC)
        tool_call.duration_ms = max(
            0,
            int((now - started_at).total_seconds() * 1000),
        )
    emit(
        session,
        "agent_run",
        row.id,
        row.revision,
        "agent.run.updated",
        payload={
            "state": "FAILED",
            "status": "FAILED",
            "reason_code": reason_code,
        },
        job_id=job.id,
        agent_run_id=row.id,
        correlation_id=job.correlation_id,
    )


def _agent_failure_reason(error: Exception) -> str:
    if isinstance(error, ToolExecutionFailure):
        return "TOOL_EXECUTION_FAILED"
    if isinstance(error, ToolPolicyDenied):
        return "AGENT_TOOL_FORBIDDEN"
    message = str(error)
    if "AGENT_RESUME_CONFLICT" in message:
        return "AGENT_RESUME_CONFLICT"
    if "AGENT_CONTEXT_STALE" in message or "context changed" in message:
        return "AGENT_CONTEXT_STALE"
    if "budget" in message.lower():
        return "AGENT_BUDGET_EXCEEDED"
    if "Remote Codex" in message or "provider" in message.lower():
        return "AGENT_MODEL_UNAVAILABLE"
    if "tool arguments" in message or "tool input" in message.lower():
        return "TOOL_INPUT_INVALID"
    return "AGENT_OUTPUT_INVALID"


def cancel_agent_run(session: Session, job: JobRow) -> None:
    """Close an agent run when its owning job is cancelled."""
    inputs = json.loads(job.input_payload)
    run_id = inputs.get("agent_run_id")
    row = session.execute(
        select(AgentRunRow)
        .where(
            AgentRunRow.id == run_id,
            AgentRunRow.workspace_id == job.workspace_id,
        )
        .with_for_update()
    ).scalar_one_or_none()
    if row is None or row.status in {"COMPLETED", "CANCELLED", "FAILED"}:
        return
    now = datetime.now(UTC)
    checkpoint = _checkpoint(row)
    checkpoint.update(
        {
            "safe_checkpoint": "CANCELLED",
            "checkpointed_at": now.isoformat().replace("+00:00", "Z"),
        }
    )
    row.checkpoint = json.dumps(checkpoint)
    row.status = "CANCELLED"
    row.decision_summary = "JOB_CANCELLED"
    row.ended_at = now
    row.revision += 1
    row.pending_resume_token_hash = None
    _revoke_pending_jobs(session, row, now, owner_job_id=job.id)
    if row.role == "RESEARCH_DIRECTOR" and row.parent_agent_run_id is None:
        _research_status(session, row, "WAITING_USER")
    for tool_call in session.execute(
        select(ToolCallRow).where(
            ToolCallRow.agent_run_id == row.id,
            ToolCallRow.workspace_id == row.workspace_id,
            ToolCallRow.status == "RUNNING",
        )
    ).scalars():
        tool_call.status = "ERROR"
        tool_call.warnings = json.dumps([{"code": "JOB_CANCELLED"}])
        tool_call.finished_at = now
    emit(
        session,
        "agent_run",
        row.id,
        row.revision,
        "agent.run.updated",
        payload={
            "state": "CANCELLED",
            "status": "CANCELLED",
            "reason_code": "JOB_CANCELLED",
        },
        job_id=job.id,
        agent_run_id=row.id,
        correlation_id=job.correlation_id,
    )


def persist_tool_failure(
    session: Session, job: JobRow, error: ToolExecutionFailure
) -> None:
    """Persist failure only after the tool/domain transaction has rolled back."""

    if error.workspace_id != job.workspace_id:
        raise AgentRuntimeError("tool failure crossed a workspace boundary")
    finished = datetime.now(UTC)
    tool_call = session.execute(
        select(ToolCallRow).where(
            ToolCallRow.id == error.tool_call_id,
            ToolCallRow.workspace_id == error.workspace_id,
        )
    ).scalar_one_or_none()
    if tool_call is None:
        tool_call = ToolCallRow(
            id=error.tool_call_id,
            workspace_id=error.workspace_id,
            agent_run_id=error.agent_run_id,
            tool_name=error.tool_name,
            tool_version=error.tool_version,
            status="ERROR",
            input_payload=error.input_payload,
            input=json.loads(error.input_payload),
            input_sha256=error.input_sha256,
            semantic_scope=error.semantic_scope,
            objective=error.objective,
            research_id=error.research_id,
            policy_version_ref=error.policy_version_ref,
            warnings="[]",
            started_at=error.started_at,
        )
        session.add(tool_call)
    else:
        if tool_call.agent_run_id != error.agent_run_id:
            raise AgentRuntimeError("tool failure crossed an agent-run boundary")
    tool_call.job_id = job.id
    tool_call.status = "ERROR"
    tool_call.warnings = json.dumps(
        [{"code": "TOOL_EXECUTION_FAILED", "detail": error.cause_type}]
    )
    tool_call.finished_at = finished
    tool_call.duration_ms = max(
        0, int((finished - error.started_at).total_seconds() * 1000)
    )
    emit(
        session,
        "tool_call",
        error.tool_call_id,
        1,
        "tool.call.updated",
        payload={
            "state": "ERROR",
            "status": "ERROR",
            "reason_code": "TOOL_EXECUTION_FAILED",
        },
        job_id=job.id,
        agent_run_id=error.agent_run_id,
        tool_call_id=error.tool_call_id,
        correlation_id=job.correlation_id,
    )
