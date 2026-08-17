#!/usr/bin/env python3
"""Provision local OWNER state, seed governed defaults, and complete Setup."""

from __future__ import annotations

import argparse
import json
import os
import sys

import httpx
from bootstrap_owner import EMAIL_PATTERN, provision

from app.bootstrap import seed_local


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--workspace-name", required=True)
    parser.add_argument("--ttl-hours", type=int, default=24)
    args = parser.parse_args()
    args.email = args.email.strip().lower()
    args.workspace_name = args.workspace_name.strip()
    if len(args.email) > 254 or not EMAIL_PATTERN.fullmatch(args.email):
        parser.error("--email must be a valid address of at most 254 characters")
    if not 1 <= len(args.workspace_name) <= 128:
        parser.error("--workspace-name must contain 1 to 128 characters")
    if not 1 <= args.ttl_hours <= 168:
        parser.error("--ttl-hours must be between 1 and 168")
    return args


def request_json(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    expected: int,
    headers: dict[str, str],
    payload: dict[str, object] | None = None,
) -> dict[str, object]:
    response = client.request(method, path, headers=headers, json=payload)
    if response.status_code != expected:
        raise RuntimeError(f"{method} {path}: {response.status_code} {response.text}")
    result = response.json()
    if not isinstance(result, dict):
        raise TypeError(f"{method} {path}: response is not an object")
    return result


def main() -> int:
    args = parse_args()
    environment = os.getenv("QF_ENVIRONMENT")
    if environment != os.getenv("QF_ENV") or environment not in {
        "local",
        "development",
    }:
        print("Local bootstrap is allowed only in local/development.", file=sys.stderr)
        return 1
    remote_codex = bool(os.getenv("QF_CODEX_BASE_URL"))
    provider_key = (
        os.getenv("QF_CODEX_API_KEY", "")
        if remote_codex
        else os.getenv("QF_LOCAL_PROVIDER_API_KEY", "")
    )
    data_credential = os.getenv("QF_LOCAL_DATA_CREDENTIAL", "")
    if len(provider_key) < 20 or len(data_credential) < 20:
        print("Provider/data credentials are missing or too short.", file=sys.stderr)
        return 1
    provider_id = "REMOTE_CODEX" if remote_codex else "OPENAI_COMPATIBLE"
    model_name = os.getenv("QF_CODEX_MODEL", "qf-local-v1")

    owner_id, workspace_id, session_token = provision(
        args.email, args.workspace_name, args.ttl_hours
    )
    seeded = seed_local(
        workspace_id=workspace_id,
        owner_id=owner_id,
        owner_email=args.email,
        session_token=session_token,
        ttl_hours=args.ttl_hours,
    )
    base_url = os.getenv("QF_BOOTSTRAP_API_URL", "http://api:8000/api/v1")
    auth = {"Authorization": f"Bearer {session_token}"}
    key_prefix = f"local-bootstrap-{workspace_id}"
    try:
        with httpx.Client(base_url=base_url, timeout=15) as client:
            ai = request_json(
                client,
                "POST",
                "/setup/provider-connections/validate",
                expected=200,
                headers={**auth, "Idempotency-Key": f"{key_prefix}-ai"},
                payload={
                    "provider_id": provider_id,
                    "kind": "AI",
                    "model_name": model_name,
                    "credential": provider_key,
                },
            )
            data = request_json(
                client,
                "POST",
                "/setup/provider-connections/validate",
                expected=200,
                headers={**auth, "Idempotency-Key": f"{key_prefix}-data"},
                payload={
                    "provider_id": "LOCAL_DETERMINISTIC_DATA",
                    "kind": "DATA",
                    "credential": data_credential,
                },
            )
            if ai.get("state") != "SUCCESS" or data.get("state") != "SUCCESS":
                raise RuntimeError("local provider validation did not succeed")
            settings = request_json(
                client,
                "POST",
                "/setup/complete",
                expected=200,
                headers={**auth, "Idempotency-Key": f"{key_prefix}-setup"},
                payload={
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
            )
            status = request_json(
                client, "GET", "/setup/status", expected=200, headers=auth
            )
        if status.get("completed") is not True:
            raise RuntimeError("server Setup status is not completed")
    except (httpx.HTTPError, KeyError, RuntimeError, ValueError) as error:
        print(f"Local Setup bootstrap failed: {error}", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "status": "COMPLETED",
                "owner_id": owner_id,
                "workspace_id": workspace_id,
                "owner_session_token": session_token,
                "settings_id": settings["settings_id"],
                "ai_connection_id": ai["connection_id"],
                "data_connection_id": data["connection_id"],
                "research_policy_id": seeded["research_policy_id"],
                "validation_policy_id": seeded["validation_policy_id"],
                "risk_policy_id": seeded["risk_policy_id"],
                "cost_model_id": seeded["cost_model_id"],
                "dataset_id": seeded["dataset_id"],
            },
            sort_keys=True,
        )
    )
    print(
        "Store owner_session_token now; only its SHA-256 verifier is persisted.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
