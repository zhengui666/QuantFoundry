#!/usr/bin/env python3
"""Create deterministic local full-stack seed refs through the real HTTP API."""

from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from datetime import UTC, date, datetime, timedelta
from hmac import compare_digest
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

import httpx
from sqlalchemy import select


def ensure_fullstack_compat_setup() -> None:
    """Create the singleton compatibility binding used by domain job effects."""
    from quantfoundry.api.app import (
        CostModelVersionRow,
        ModelProviderConnectionRow,
        Record,
        ResearchPolicyVersionRow,
        RiskPolicyVersionRow,
        SessionLocal,
        SetupBindingRow,
    )
    from quantfoundry.infrastructure.crypto.provider_credentials import (
        CredentialConfigurationError,
        credential_aad,
        decrypt_credential,
        encrypt_credential,
    )
    from quantfoundry.infrastructure.db.schema import canonical_workspace_id
    from quantfoundry.bootstrap.local import _workspace_seed_values

    workspace_id = canonical_workspace_id("system")
    owner_id = "system-owner"
    model_name = os.environ["QF_CODEX_MODEL"]
    credential = os.environ["QF_LOCAL_PROVIDER_API_KEY"]
    timestamp = datetime.now(UTC)
    with SessionLocal.begin() as db:
        active_connections = list(
            db.scalars(
                select(ModelProviderConnectionRow)
                .where(
                    ModelProviderConnectionRow.workspace_id == workspace_id,
                    ModelProviderConnectionRow.owner_actor_id == owner_id,
                    ModelProviderConnectionRow.provider_id == "REMOTE_CODEX",
                    ModelProviderConnectionRow.kind == "AI",
                    ModelProviderConnectionRow.model_name == model_name,
                    ModelProviderConnectionRow.validation_state == "SUCCESS",
                    ModelProviderConnectionRow.status == "ACTIVE",
                )
                .order_by(ModelProviderConnectionRow.validated_at.desc())
            )
        )
        matching_connections = []
        for candidate in active_connections:
            try:
                stored_credential = decrypt_credential(
                    candidate.ciphertext,
                    candidate.nonce,
                    candidate.key_id,
                    aad=credential_aad(
                        connection_id=candidate.id,
                        workspace_id=workspace_id,
                        actor_id=owner_id,
                        provider_id=candidate.provider_id,
                        model_name=candidate.model_name,
                    ),
                )
            except CredentialConfigurationError:
                stored_credential = None
            if stored_credential is not None and compare_digest(
                stored_credential, credential
            ):
                matching_connections.append(candidate)
            else:
                candidate.status = "REVOKED"
        if matching_connections:
            ai = matching_connections[0]
            for duplicate in matching_connections[1:]:
                duplicate.status = "REVOKED"
        else:
            ai = None
        if ai is None:
            connection_id = str(uuid.uuid4())
            ciphertext, nonce, key_id = encrypt_credential(
                credential,
                aad=credential_aad(
                    connection_id=connection_id,
                    workspace_id=workspace_id,
                    actor_id=owner_id,
                    provider_id="REMOTE_CODEX",
                    model_name=model_name,
                ),
            )
            ai = ModelProviderConnectionRow(
                id=connection_id,
                workspace_id=workspace_id,
                owner_actor_id=owner_id,
                provider_id="REMOTE_CODEX",
                kind="AI",
                model_name=model_name,
                ciphertext=ciphertext,
                nonce=nonce,
                key_id=key_id,
                validation_state="SUCCESS",
                status="ACTIVE",
                validated_at=timestamp,
                consumed_at=timestamp,
            )
            db.add(ai)
            db.flush()
        seed_values = _workspace_seed_values(workspace_id)
        research_id = seed_values["research_policy"]["policy_id"]
        risk_id = seed_values["risk_policy"]["policy_id"]
        cost_id = seed_values["cost_model"]["cost_model_id"]
        research = db.scalar(
            select(ResearchPolicyVersionRow).where(
                ResearchPolicyVersionRow.workspace_id == workspace_id,
                ResearchPolicyVersionRow.policy_id == research_id,
            )
        )
        risk = db.scalar(
            select(RiskPolicyVersionRow).where(
                RiskPolicyVersionRow.workspace_id == workspace_id,
                RiskPolicyVersionRow.policy_id == risk_id,
            )
        )
        cost = db.scalar(
            select(CostModelVersionRow).where(
                CostModelVersionRow.workspace_id == workspace_id,
                CostModelVersionRow.cost_model_id == cost_id,
            )
        )
        if (
            research is None
            or research.status != "ACTIVE"
            or risk is None
            or risk.status != "ACTIVE"
            or cost is None
            or cost.status != "ACTIVE"
        ):
            raise RuntimeError("full-stack seed policy/cost rows are missing")
        settings = db.scalar(
            select(Record).where(
                Record.workspace_id == workspace_id,
                Record.record_key == "SETTINGS-DEFAULT",
            )
        )
        settings_body = {
            "settings_id": "SETTINGS-DEFAULT",
            "revision": settings.revision + 1 if settings else 1,
            "ai_connection_id": ai.id,
            "research_policy_id": research.policy_id,
            "risk_policy_id": risk.policy_id,
            "cost_model_id": cost.cost_model_id,
            "language": "en",
            "timezone": "UTC",
            "base_currency": "USD",
            "number_format_locale": "en-US",
            "default_benchmark": "SPY",
            "default_frequency": "DAILY",
            "initial_paper_capital": "100000",
            "created_at": timestamp.isoformat(),
            "updated_at": timestamp.isoformat(),
        }
        if settings is None:
            settings = Record(
                workspace_id=workspace_id,
                record_key="SETTINGS-DEFAULT",
                kind="settings",
                revision=1,
                body=json.dumps(settings_body),
                created_at=timestamp,
                updated_at=timestamp,
            )
            db.add(settings)
        else:
            settings.revision = settings_body["revision"]
            settings.body = json.dumps(settings_body)
            settings.updated_at = timestamp
        binding = db.get(SetupBindingRow, workspace_id)
        if binding is None:
            db.add(
                SetupBindingRow(
                    workspace_id=workspace_id,
                    settings_record_id="SETTINGS-DEFAULT",
                    ai_connection_id=ai.id,
                    research_policy_version_id=research.id,
                    risk_policy_version_id=risk.id,
                    cost_model_version_id=cost.id,
                    revision=1,
                    created_at=timestamp,
                    updated_at=timestamp,
                )
            )
        else:
            binding.ai_connection_id = ai.id
            binding.research_policy_version_id = research.id
            binding.risk_policy_version_id = risk.id
            binding.cost_model_version_id = cost.id
            binding.revision += 1
            binding.updated_at = timestamp


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--application-url", required=True)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    parsed = urlsplit(args.api_url)
    if not parsed.hostname or parsed.username or parsed.password:
        parser.error("--api-url must be an origin without embedded credentials")
    if parsed.scheme != "https" and not (
        parsed.scheme == "http"
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
    ):
        parser.error("--api-url must use HTTPS unless it targets loopback")
    return args


def request_json(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    expected: int,
    headers: dict[str, str],
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    response = client.request(method, path, headers=headers, json=payload)
    if response.status_code != expected:
        raise RuntimeError(f"{method} {path}: {response.status_code} {response.text}")
    result = response.json()
    if not isinstance(result, dict):
        raise TypeError(f"{method} {path}: response is not an object")
    return result


def wait_for_job(
    client: httpx.Client, job_id: str, auth: dict[str, str], timeout: float = 180
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = request_json(client, "GET", f"/jobs/{job_id}", expected=200, headers=auth)
        status = job.get("status")
        if status == "COMPLETED":
            return
        if status in {"FAILED", "CANCELLED"}:
            raise RuntimeError(f"job {job_id} terminated as {status}: {job}")
        time.sleep(0.25)
    raise TimeoutError(f"job {job_id} did not complete within {timeout:.0f}s")


def business_dates(start: date, count: int) -> list[date]:
    result: list[date] = []
    current = start
    while len(result) < count:
        if current.weekday() < 5:
            result.append(current)
        current += timedelta(days=1)
    return result


def write_fullstack_dataset(dataset_id: str) -> None:
    dataset_root = Path(os.environ["QF_DATASET_DIR"])
    dataset_root.mkdir(mode=0o750, parents=True, exist_ok=True)
    header = (
        "event_time,available_at,symbol,close,benchmark_close,partition,"
        "split_factor,dividend,in_universe,sector"
    )
    rows = [header]
    partitions = (
        ("RESEARCH", date(2010, 1, 4), 100),
        ("VALIDATION", date(2019, 1, 2), 140),
        ("HOLDOUT", date(2023, 1, 3), 180),
    )
    for partition, start, base in partitions:
        for index, day in enumerate(business_dates(start, 35)):
            for symbol, multiplier, sector in (
                ("AAA", 1, "TECH"),
                ("BBB", 2, "FINANCE"),
                ("SPY", 1, "BENCHMARK"),
            ):
                close = base + index * multiplier
                benchmark = base + index
                rows.append(
                    f"{day.isoformat()}T21:00:00Z,{day.isoformat()}T21:01:00Z,"
                    f"{symbol},{close},{benchmark},{partition},1,0,true,{sector}"
                )
    path = dataset_root / f"{dataset_id}.csv"
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    path.chmod(0o640)


def required_string(value: dict[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise RuntimeError(f"bootstrap output is missing {key}")
    return result


def activate_fullstack_database(
    client: httpx.Client, auth: dict[str, str], prefix: str
) -> None:
    raw_url = os.environ.get("QF_FULLSTACK_DATABASE_URL")
    if not raw_url:
        raise RuntimeError("QF_FULLSTACK_DATABASE_URL is required")
    parsed = urlsplit(raw_url)
    if (
        parsed.scheme not in {"postgresql", "postgres", "postgresql+psycopg"}
        or not parsed.hostname
        or not parsed.username
        or not parsed.path.strip("/")
    ):
        raise RuntimeError("QF_FULLSTACK_DATABASE_URL is invalid")
    status = client.get("/database/connection", headers=auth)
    if status.status_code != 200:
        raise RuntimeError(
            f"GET /database/connection: {status.status_code} {status.text}"
        )
    current = status.json()
    database_name = parsed.path.strip("/").split("/", 1)[0]
    desired = {
        "host": parsed.hostname,
        "port": parsed.port or 5432,
        "database": database_name,
        "tls_mode": "DISABLED",
        "pool_profile": "fullstack-ci",
    }
    etag = status.headers.get("etag")
    if not etag:
        raise RuntimeError("database status is missing ETag")
    candidate = request_json(
        client,
        "PUT",
        "/database/connection/candidate",
        expected=200,
        headers={
            **auth,
            "If-Match": etag,
            "Idempotency-Key": f"{prefix}-db-candidate",
        },
        payload={
            "base_revision": max(int(current.get("active_revision") or 0), 1),
            "connection": {
                "host": parsed.hostname,
                "port": parsed.port or 5432,
                "database": database_name,
                "tls_mode": desired["tls_mode"],
                "username": unquote(parsed.username),
                "password": unquote(parsed.password or ""),
                "pool_profile": "fullstack-ci",
            },
        },
    )
    if not isinstance(candidate.get("revision"), int):
        raise RuntimeError("database candidate is missing revision")
    request_json(
        client,
        "POST",
        "/database/connection/candidate/validate",
        expected=200,
        headers={
            **auth,
            "X-Candidate-Revision": str(candidate["revision"]),
            "Idempotency-Key": f"{prefix}-db-validate",
        },
    )
    request_json(
        client,
        "POST",
        "/database/connection/activate",
        expected=200,
        headers={
            **auth,
            "If-Match": etag,
            "X-Candidate-Revision": str(candidate["revision"]),
            "Idempotency-Key": f"{prefix}-db-activate",
        },
    )


def main() -> int:
    args = parse_args()
    general_key = os.environ.get("QF_FULLSTACK_GENERAL_KEY")
    if not general_key:
        raise RuntimeError("QF_FULLSTACK_GENERAL_KEY is required")
    run_id = uuid.uuid4().hex[:12]
    with httpx.Client(base_url=args.api_url, timeout=30) as client:
        login = request_json(
            client,
            "POST",
            "/auth/login",
            expected=200,
            headers={},
            payload={"key": general_key},
        )
        session = login.get("session")
        if not isinstance(session, dict):
            raise RuntimeError("login response is missing session")
        csrf = session.get("csrf_token")
        if not isinstance(csrf, str) or len(csrf) < 32:
            raise RuntimeError("login response is missing CSRF token")
        auth = {"X-CSRF-Token": csrf}
        activate_fullstack_database(client, auth, f"fullstack-db-{run_id}")
        from app.control_plane import restore_active_domain_database

        restore_active_domain_database()
        # Immutable policy/cost content is seeded into the mounted runtime
        # data store and bound in the singleton compatibility namespace.
        # Mutable installation settings remain Control-DB-only.
        from app.bootstrap import seed_local

        seeded = seed_local(
            workspace_id="system",
            owner_id="system-owner",
            owner_email="owner@system.invalid",
            session_token=f"fullstack-seed-{os.urandom(16).hex()}",
        )
        ensure_fullstack_compat_setup()
        dataset_id = required_string(seeded, "dataset_id")
        cost_model_id = required_string(seeded, "cost_model_id")
        validation_policy_id = required_string(seeded, "validation_policy_id")
        key_prefix = f"fullstack-{dataset_id}-{run_id}"
        active_response = client.get("/configuration/active", headers=auth)
        if active_response.status_code != 200:
            raise RuntimeError(
                f"GET /configuration/active: {active_response.status_code} {active_response.text}"
            )
        active = active_response.json()
        active_revision = active.get("active_revision")
        etag = active_response.headers.get("etag")
        if not isinstance(active_revision, int) or not etag:
            raise RuntimeError("active configuration is missing revision or ETag")
        candidate = client.put(
            "/configuration/candidate",
            headers={
                **auth,
                "If-Match": etag,
                "Idempotency-Key": f"{key_prefix}-locale",
            },
            json={
                "base_revision": active_revision,
                "values": [
                    {
                        "key": "appearance.locale",
                        "value": {
                            "language": "en",
                            "timezone": "UTC",
                            "number_format_locale": "en-US",
                            "theme": "SYSTEM",
                            "density": "COMFORTABLE",
                        },
                    },
                    {
                        # The production runtime is Control-DB-only.  The
                        # harness may source these deterministic values from
                        # its environment, but workers must consume the
                        # encrypted active revision rather than env fallback.
                        "key": "ai.remote_codex",
                        "secret": json.dumps(
                            {
                                "endpoint": os.environ["QF_CODEX_BASE_URL"],
                                "credential": os.environ["QF_LOCAL_PROVIDER_API_KEY"],
                                "model": os.environ["QF_CODEX_MODEL"],
                                "timeout_seconds": 60,
                                "max_retries": 3,
                                "concurrency": 2,
                            },
                            separators=(",", ":"),
                        ),
                    },
                ],
            },
        )
        if candidate.status_code != 200:
            raise RuntimeError(
                f"PUT /configuration/candidate: {candidate.status_code} {candidate.text}"
            )
        candidate_revision = candidate.json().get("revision")
        if not isinstance(candidate_revision, int):
            raise RuntimeError("configuration candidate is missing revision")
        request_json(
            client,
            "POST",
            "/configuration/candidate/validate",
            expected=200,
            headers={**auth, "Idempotency-Key": f"{key_prefix}-locale-validate"},
        )
        request_json(
            client,
            "POST",
            "/configuration/activate",
            expected=200,
            headers={
                **auth,
                "If-Match": etag,
                "Idempotency-Key": f"{key_prefix}-locale-activate",
            },
            payload={"revision": candidate_revision},
        )
        if args.prepare_only:
            return 0
        write_fullstack_dataset(dataset_id)
        validation = request_json(
            client,
            "POST",
            f"/data/datasets/{dataset_id}/validate",
            expected=202,
            headers={**auth, "Idempotency-Key": f"{key_prefix}-dataset-validate"},
            payload={"check_profile": "RESEARCH_BASELINE"},
        )
        wait_for_job(client, required_string(validation, "job_id"), auth)
        snapshot = request_json(
            client,
            "POST",
            f"/data/datasets/{dataset_id}/snapshots",
            expected=202,
            headers={**auth, "Idempotency-Key": f"{key_prefix}-snapshot"},
            payload={
                "snapshot_kind": "RESEARCH",
                "as_of_time": "2026-01-01T00:00:00Z",
                "coverage_start": "2010-01-01",
                "coverage_end": "2025-12-31",
            },
        )
        wait_for_job(client, required_string(snapshot, "job_id"), auth)
        resource_ref = snapshot.get("resource_ref")
        if not isinstance(resource_ref, dict):
            raise TypeError("snapshot response is missing resource_ref")
        snapshot_id = required_string(resource_ref, "id")
        request_json(
            client, "GET", f"/data/snapshots/{snapshot_id}", expected=200, headers=auth
        )
        research = request_json(
            client,
            "POST",
            "/research",
            expected=201,
            headers={**auth, "Idempotency-Key": f"{key_prefix}-factor-research"},
            payload={
                "title": "Full-stack canonical factor seed",
                "original_user_prompt": "Create a deterministic factor seed.",
            },
        )
        factor = request_json(
            client,
            "POST",
            "/factors",
            expected=201,
            headers={**auth, "Idempotency-Key": f"{key_prefix}-factor"},
            payload={
                "research_id": required_string(research, "research_id"),
                "name": "Full-stack close factor",
                "category": "VALUE",
                "description": "Deterministic close-price factor for real E2E.",
                "economic_rationale": "Controlled price persistence signal.",
                "formula": {"expression": "close", "required_fields": ["close"]},
                "universe": {
                    "asset_class": "EQUITY",
                    "symbols": [],
                    "universe_id": "LOCAL-FULLSTACK",
                },
                "frequency": "DAILY",
            },
        )
        factor_id = required_string(factor, "factor_id")
        factor_analysis = request_json(
            client,
            "POST",
            f"/factors/{factor_id}/analyses",
            expected=202,
            headers={**auth, "Idempotency-Key": f"{key_prefix}-factor-analysis"},
            payload={
                "factor_version": 1,
                "snapshot_id": snapshot_id,
                "forward_return_horizons": [1, 5],
            },
        )
        wait_for_job(client, required_string(factor_analysis, "job_id"), auth)

    print(
        json.dumps(
            {
                "QF_FULLSTACK_BASE_URL": args.application_url,
                "QF_FULLSTACK_FACTOR_ID": factor_id,
                "QF_FULLSTACK_SNAPSHOT_ID": snapshot_id,
                "QF_FULLSTACK_COST_MODEL_ID": cost_model_id,
                "QF_FULLSTACK_VALIDATION_POLICY_ID": validation_policy_id,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
