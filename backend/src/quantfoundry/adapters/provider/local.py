"""Self-hostable deterministic OpenAI-compatible provider for local deployments."""

from __future__ import annotations

import argparse
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any


class LocalProviderServer(ThreadingHTTPServer):
    actions: list[dict[str, Any]]
    action_index: int
    deterministic_research_plan: bool
    api_key: str
    model_name: str
    failure_statuses: list[int]
    request_log: list[dict[str, Any]]
    state_lock: Lock


class LocalProviderHandler(BaseHTTPRequestHandler):
    server: LocalProviderServer

    def _json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _authorized(self) -> bool:
        return self.headers.get("Authorization") == f"Bearer {self.server.api_key}"

    @staticmethod
    def _checkpoint(request: dict[str, Any]) -> dict[str, Any]:
        messages = request.get("messages")
        if not isinstance(messages, list):
            raise ValueError("messages must be an array")
        for message in reversed(messages):
            if not isinstance(message, dict) or message.get("role") != "user":
                continue
            content = message.get("content")
            if not isinstance(content, str):
                break
            checkpoint = json.loads(content)
            if isinstance(checkpoint, dict):
                return checkpoint
            break
        raise ValueError("durable checkpoint is missing")

    @staticmethod
    def _result_object_id(
        tool_results: list[dict[str, Any]], object_type: str
    ) -> str | None:
        for result in reversed(tool_results):
            result_ref = result.get("result_ref")
            if (
                isinstance(result_ref, dict)
                and result_ref.get("object_type") == object_type
                and isinstance(result_ref.get("object_id"), str)
            ):
                return result_ref["object_id"]
            summary = result.get("result_summary")
            refs = summary.get("object_refs") if isinstance(summary, dict) else None
            if not isinstance(refs, list):
                continue
            for ref in refs:
                if (
                    isinstance(ref, dict)
                    and ref.get("type") == object_type
                    and isinstance(ref.get("id"), str)
                ):
                    return ref["id"]
        return None

    def _deterministic_action(self, request: dict[str, Any]) -> dict[str, Any]:
        checkpoint = self._checkpoint(request)
        context = checkpoint.get("context")
        if not isinstance(context, dict) or context.get("role") != "RESEARCH_DIRECTOR":
            return {
                "type": "conclude",
                "summary": "Local deterministic specialist run completed",
            }
        research = context.get("research")
        research_id = (
            research.get("research_id") if isinstance(research, dict) else None
        )
        dataset_ids = context.get("dataset_ids")
        tool_results = checkpoint.get("tool_results", [])
        if (
            not isinstance(research_id, str)
            or not isinstance(dataset_ids, list)
            or not dataset_ids
            or not isinstance(dataset_ids[0], str)
            or not isinstance(tool_results, list)
            or not all(isinstance(item, dict) for item in tool_results)
        ):
            # Invalid output is intentional here: the Agent boundary records a
            # durable failure instead of falsely completing without evidence.
            return {"type": "blocked", "reason": "LOCAL_RESEARCH_INPUT_MISSING"}
        names = [str(item.get("tool_name")) for item in tool_results]
        dataset_id = dataset_ids[0]
        if "validate_dataset" not in names:
            return {
                "type": "tool",
                "name": "validate_dataset",
                "arguments": {"dataset_id": dataset_id},
            }
        if "create_data_snapshot" not in names:
            return {
                "type": "tool",
                "name": "create_data_snapshot",
                "arguments": {"dataset_id": dataset_id},
            }
        if "define_factor" not in names:
            return {
                "type": "tool",
                "name": "define_factor",
                "arguments": {
                    "research_id": research_id,
                    "definition": {
                        "name": "Local deterministic close factor",
                        "category": "MOMENTUM",
                        "description": "PIT close-price cross-sectional signal",
                        "economic_rationale": (
                            "Deterministic local evidence for the research workflow"
                        ),
                        "formula": {
                            "expression": "close",
                            "required_fields": ["close"],
                        },
                        "universe": {
                            "asset_class": "EQUITY",
                            "symbols": [],
                            "universe_id": "LOCAL-EQUITY",
                        },
                        "frequency": "DAILY",
                    },
                },
            }
        if "analyze_factor" not in names:
            factor_id = self._result_object_id(tool_results, "factor")
            snapshot_id = self._result_object_id(tool_results, "snapshot")
            if factor_id is None or snapshot_id is None:
                return {"type": "blocked", "reason": "LOCAL_TOOL_RESULT_MISSING"}
            return {
                "type": "tool",
                "name": "analyze_factor",
                "arguments": {
                    "factor_id": factor_id,
                    "factor_version": 1,
                    "snapshot_id": snapshot_id,
                },
            }
        experiment_id = self._result_object_id(tool_results, "experiment")
        if experiment_id is None:
            return {"type": "blocked", "reason": "LOCAL_EXPERIMENT_MISSING"}
        return {
            "type": "conclude",
            "summary": f"Local deterministic research produced {experiment_id}",
        }

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler contract
        self.server.request_log.append(
            {
                "method": "GET",
                "path": self.path,
                "authorized": self._authorized(),
            }
        )
        if self.path == "/healthz":
            self._json(HTTPStatus.OK, {"status": "ok"})
            return
        if self.path == "/v1/models":
            if not self._authorized():
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            self._json(
                HTTPStatus.OK,
                {"object": "list", "data": [{"id": self.server.model_name}]},
            )
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
        if self.path != "/v1/chat/completions":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        if not self._authorized():
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        try:
            raw_length = self.headers.get("Content-Length")
            length = int(raw_length) if raw_length is not None else -1
            if length < 0:
                raise ValueError("Content-Length is required")
            if length > 4 * 1024 * 1024:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "body_too_large"})
                return
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError("incomplete request body")
            request = json.loads(body)
        except (ValueError, json.JSONDecodeError):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
            return
        if not isinstance(request, dict) or not isinstance(request.get("model"), str):
            self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "invalid_request"})
            return
        request_log = {
            "method": "POST",
            "path": self.path,
            "authorized": True,
            "model": request["model"],
        }
        remote_headers = {
            "runtime": self.headers.get("X-QF-Codex-Runtime"),
            "instance": self.headers.get("X-QF-Codex-Instance"),
            "invocation": self.headers.get("X-QF-Codex-Invocation"),
        }
        if any(value is not None for value in remote_headers.values()):
            request_log.update(
                {
                    key: value
                    for key, value in remote_headers.items()
                    if value is not None
                }
            )
        self.server.request_log.append(request_log)
        with self.server.state_lock:
            if self.server.failure_statuses:
                failure_status = self.server.failure_statuses.pop(0)
                self._json(
                    HTTPStatus(failure_status), {"error": "injected_provider_failure"}
                )
                return
            if self.server.deterministic_research_plan and not self.server.actions:
                try:
                    action = self._deterministic_action(request)
                except (ValueError, json.JSONDecodeError):
                    self._json(
                        HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "invalid_request"}
                    )
                    return
            else:
                index = min(self.server.action_index, len(self.server.actions) - 1)
                action = self.server.actions[index]
            self.server.action_index += 1
        self._json(
            HTTPStatus.OK,
            {
                "id": f"local-{self.server.action_index}",
                "object": "chat.completion",
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(action, separators=(",", ":")),
                        },
                    }
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            },
        )

    def log_message(self, format: str, *args: object) -> None:
        if os.getenv("QF_LOCAL_PROVIDER_ACCESS_LOG") == "1":
            super().log_message(format, *args)


def create_server(
    host: str,
    port: int,
    actions: list[dict[str, Any]] | None = None,
    api_key: str | None = None,
    model_name: str = "qf-local-v1",
    failure_statuses: list[int] | None = None,
) -> LocalProviderServer:
    environment = os.getenv("QF_ENVIRONMENT")
    legacy_environment = os.getenv("QF_ENV")
    if environment and legacy_environment and environment != legacy_environment:
        raise RuntimeError("QF_ENVIRONMENT and QF_ENV disagree")
    effective_environment = environment or legacy_environment
    if effective_environment not in {"local", "development", "test"}:
        raise RuntimeError("local provider is forbidden outside local/development/test")
    effective_key = api_key or os.getenv("QF_LOCAL_PROVIDER_API_KEY")
    if not effective_key or len(effective_key) < 20:
        raise RuntimeError(
            "QF_LOCAL_PROVIDER_API_KEY must contain at least 20 characters"
        )
    if actions is not None and not actions:
        raise ValueError("actions must be non-empty when explicitly configured")
    server = LocalProviderServer((host, port), LocalProviderHandler)
    server.deterministic_research_plan = actions is None
    server.actions = list(actions) if actions is not None else []
    server.action_index = 0
    server.api_key = effective_key
    server.model_name = model_name
    server.failure_statuses = list(failure_statuses or [])
    server.request_log = []
    server.state_lock = Lock()
    return server


def _actions_from_environment() -> list[dict[str, Any]] | None:
    value = os.getenv("QF_LOCAL_PROVIDER_ACTIONS")
    if not value:
        return None
    parsed = json.loads(value)
    if (
        not isinstance(parsed, list)
        or not parsed
        or not all(isinstance(item, dict) for item in parsed)
    ):
        raise ValueError("QF_LOCAL_PROVIDER_ACTIONS must be a non-empty JSON array")
    return parsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8011)
    args = parser.parse_args()
    server = create_server(args.host, args.port, _actions_from_environment())
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
