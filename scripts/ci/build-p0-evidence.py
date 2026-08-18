#!/usr/bin/env python3
"""Build immutable, run-bound P0 closure reports for the independent agents."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import shutil
import subprocess
from typing import Any

import yaml

TEST_BLOCKERS = (
    "P0-PRODUCT-PAPER-DAILY-SCHEDULER",
    "P0-CONTRACT-OPENAPI-45",
    "P0-CONTRACT-TOOLS-13",
    "P0-SCHEMA-ALEMBIC-AUTHORITY",
    "P0-ARCHITECTURE-TARGET-LAYERS",
    "P0-CI-REPRODUCIBILITY",
    "P0-SECURITY-RESEARCH-INTEGRITY",
)
REVIEW_BLOCKERS = (
    "P0-PRODUCT-PAPER-DAILY-SCHEDULER",
    "P0-CONTRACT-OPENAPI-45",
    "P0-CONTRACT-TOOLS-13",
    "P0-SCHEMA-ALEMBIC-AUTHORITY",
    "P0-ARCHITECTURE-TARGET-LAYERS",
    "P0-CI-REPRODUCIBILITY",
    "P0-SECURITY-RESEARCH-INTEGRITY",
)
SUPPLY_BLOCKER = "P0-SUPPLY-CHAIN-RELEASE-EVIDENCE"
CONTENT_TYPES = {
    "test": "application/vnd.quantfoundry.p0-test-evidence+json;version=1",
    "review": "application/vnd.quantfoundry.p0-review-evidence+json;version=1",
}
ROLES = {"test": "Independent Test Agent", "review": "Independent Review Agent"}


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=CONTENT_TYPES)
    parser.add_argument("commit_sha")
    parser.add_argument("output_dir", type=pathlib.Path)
    parser.add_argument("--result-file", type=pathlib.Path)
    parser.add_argument("--command", action="append", default=[])
    parser.add_argument("--blocker", action="append")
    return parser.parse_args()


def read_commands(options: argparse.Namespace) -> list[dict[str, Any]]:
    if options.result_file:
        result = json.loads(options.result_file.read_text(encoding="utf-8"))
        expected_run_id = os.environ.get("GITHUB_RUN_ID")
        expected_attempt = os.environ.get("GITHUB_RUN_ATTEMPT")
        if (
            not expected_run_id
            or not expected_attempt
            or result.get("github_run_id") != int(expected_run_id)
            or result.get("github_run_attempt") != int(expected_attempt)
        ):
            raise SystemExit("P0 evidence gate result is not bound to this run attempt")
        expected_gate = (
            "supply-chain-review"
            if options.blocker == [SUPPLY_BLOCKER]
            else "main-full"
            if options.role == "test"
            else "independent-review"
        )
        if (
            result.get("result") != "pass"
            or result.get("exit_code") != 0
            or result.get("commit") != options.commit_sha
            or result.get("gate") != expected_gate
        ):
            raise SystemExit(
                f"P0 evidence requires a passing {expected_gate} gate result"
            )
        steps = result.get("steps")
        if not isinstance(steps, list) or not steps:
            raise SystemExit("P0 evidence requires structured gate steps")
        commands = []
        for step in steps:
            if (
                not isinstance(step, dict)
                or step.get("result") != "pass"
                or step.get("exit_code") != 0
            ):
                raise SystemExit("P0 evidence refuses a failed or malformed gate step")
            command = step.get("command")
            if not isinstance(command, str) or not command.strip() or "\n" in command:
                raise SystemExit("P0 evidence requires single-line command records")
            commands.append(
                {
                    "command": command,
                    "result": step["result"],
                    "exit_code": step["exit_code"],
                }
            )
        return commands
    raise SystemExit("P0 evidence must be built from a structured gate result file")


def main() -> None:
    options = args()
    if len(options.commit_sha) != 40 or any(
        char not in "0123456789abcdef" for char in options.commit_sha
    ):
        raise SystemExit("commit_sha must be a full lowercase Git SHA")
    repository = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if not repository or not run_id or not run_id.isdigit() or int(run_id) < 1:
        raise SystemExit("GITHUB_REPOSITORY and GITHUB_RUN_ID are required")
    github_sha = os.environ.get("GITHUB_SHA", "")
    if github_sha != options.commit_sha:
        raise SystemExit("commit_sha must equal the GitHub Actions commit")
    registry_path = pathlib.Path(
        os.environ.get(
            "QF_P0_REGISTRY_PATH",
            str(
                pathlib.Path(__file__).resolve().parents[2]
                / "docs/治理/p0-blockers.yaml"
            ),
        )
    )
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if not isinstance(registry, dict) or not isinstance(registry.get("blockers"), list):
        raise SystemExit("P0 blocker registry shape is invalid")
    by_id: dict[str, dict[str, Any]] = {}
    for item in registry["blockers"]:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("id"), str)
            or not item["id"]
            or not isinstance(item.get("closure_criteria"), (str, list, dict))
            or item["id"] in by_id
        ):
            raise SystemExit(
                "P0 blocker registry contains malformed or duplicate entries"
            )
        by_id[item["id"]] = item
    blocker_ids = options.blocker or list(
        TEST_BLOCKERS if options.role == "test" else REVIEW_BLOCKERS
    )
    allowed = set(TEST_BLOCKERS if options.role == "test" else REVIEW_BLOCKERS)
    if options.role in {"test", "review"}:
        allowed.add(SUPPLY_BLOCKER)
    if not blocker_ids or any(value not in allowed for value in blocker_ids):
        raise SystemExit("requested blocker is not assigned to this evidence role")
    if SUPPLY_BLOCKER in blocker_ids and blocker_ids != [SUPPLY_BLOCKER]:
        raise SystemExit(
            "supply-chain evidence cannot be mixed with ordinary P0 blockers"
        )
    if len(set(blocker_ids)) != len(blocker_ids):
        raise SystemExit("requested blockers must be unique")

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if (
        os.environ.get("GITHUB_ACTIONS") != "true"
        or not token
        or not shutil.which("gh")
    ):
        raise SystemExit("P0 evidence requires an authenticated GitHub Actions runner")
    gh_env = os.environ.copy()
    gh_env["GH_TOKEN"] = token
    run_payload = subprocess.run(
        ["gh", "api", f"/repos/{repository}/actions/runs/{int(run_id)}"],
        env=gh_env,
        check=True,
        text=True,
        capture_output=True,
    )
    try:
        run = json.loads(run_payload.stdout)
    except json.JSONDecodeError as error:
        raise SystemExit("GitHub Actions run lookup returned invalid JSON") from error
    expected_workflow = {
        "test": ".github/workflows/independent-agent-test.yml",
        "review": ".github/workflows/independent-agent-review.yml",
    }[options.role]
    if (
        run.get("id") != int(run_id)
        or run.get("head_sha") != options.commit_sha
        or run.get("path") != expected_workflow
        or run.get("run_attempt") != int(os.environ.get("GITHUB_RUN_ATTEMPT", "0"))
        or run.get("status") not in {"queued", "in_progress", "completed"}
        or (run.get("status") == "completed" and run.get("conclusion") != "success")
    ):
        raise SystemExit(
            "P0 evidence is not bound to the authenticated current workflow run"
        )
    commands = read_commands(options)
    timestamp = (
        dt.datetime.now(dt.UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    run_uri = f"https://github.com/{repository}/actions/runs/{run_id}"
    run_attempt = int(os.environ.get("GITHUB_RUN_ATTEMPT", "0"))
    if run_attempt < 1:
        raise SystemExit("GITHUB_RUN_ATTEMPT must be a positive integer")
    options.output_dir.mkdir(parents=True, exist_ok=True)
    content_type = CONTENT_TYPES[options.role]
    role = ROLES[options.role]
    reports: list[tuple[pathlib.Path, bytes]] = []
    for blocker_id in blocker_ids:
        item = by_id.get(blocker_id)
        if item is None:
            raise SystemExit(f"P0 blocker registry entry is missing: {blocker_id}")
        report = {
            "schema_version": "1.0.0",
            "content_type": content_type,
            "commit_sha": options.commit_sha,
            "github_run_id": int(run_id),
            "github_run_attempt": run_attempt,
            "verifier_role": role,
            "verified_at_utc": timestamp,
            "closure_criteria": item["closure_criteria"],
            "commands": commands,
            "artifact": {"run_uri": run_uri},
            "attestation": {
                "provider": "github-actions",
                "issuer": "https://token.actions.githubusercontent.com",
                "repository": repository,
                "run_id": int(run_id),
                "subject_uri": run_uri,
            },
        }
        destination = options.output_dir / f"{blocker_id}.json"
        payload = (
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True).encode(
                "utf-8"
            )
            + b"\n"
        )
        if destination.exists():
            raise SystemExit(f"refusing to overwrite immutable evidence: {destination}")
        reports.append((destination, payload))
    created: list[pathlib.Path] = []
    try:
        for destination, payload in reports:
            with destination.open("xb") as handle:
                created.append(destination)
                handle.write(payload)
    except Exception as error:
        for destination in created:
            destination.unlink(missing_ok=True)
        raise SystemExit(f"P0 evidence publication failed: {error}") from error


if __name__ == "__main__":
    main()
