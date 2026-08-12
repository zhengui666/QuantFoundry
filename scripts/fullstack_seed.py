#!/usr/bin/env python3
"""Create deterministic local full-stack seed refs through the real HTTP API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://127.0.0.1:8000/api/v1")
    parser.add_argument("--application-url", required=True)
    return parser.parse_args()


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


def main() -> int:
    args = parse_args()
    bootstrap = json.load(sys.stdin)
    if not isinstance(bootstrap, dict):
        raise TypeError("bootstrap input must be a JSON object")
    token = required_string(bootstrap, "owner_session_token")
    dataset_id = required_string(bootstrap, "dataset_id")
    cost_model_id = required_string(bootstrap, "cost_model_id")
    validation_policy_id = required_string(bootstrap, "validation_policy_id")
    workspace_id = required_string(bootstrap, "workspace_id")
    write_fullstack_dataset(dataset_id)

    auth = {"Authorization": f"Bearer {token}"}
    key_prefix = f"fullstack-{workspace_id}"
    with httpx.Client(base_url=args.api_url, timeout=30) as client:
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
                "QF_FULLSTACK_BEARER_TOKEN": token,
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
