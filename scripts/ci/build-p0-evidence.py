#!/usr/bin/env python3
"""Build immutable, run-bound P0 closure reports for the independent agents."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
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
        if result.get("result") != "pass":
            raise SystemExit("P0 evidence requires a passing gate result")
        steps = result.get("steps")
        if not isinstance(steps, list) or not steps:
            raise SystemExit("P0 evidence requires structured gate steps")
        commands = []
        for step in steps:
            if not isinstance(step, dict) or step.get("exit_code") != 0:
                raise SystemExit("P0 evidence refuses a failed or malformed gate step")
            command = step.get("command")
            if not isinstance(command, str) or not command.strip() or "\n" in command:
                raise SystemExit("P0 evidence requires single-line command records")
            commands.append({"command": command, "result": "pass", "exit_code": 0})
        return commands
    if not options.command:
        raise SystemExit("at least one verified command is required")
    return [
        {"command": value, "result": "pass", "exit_code": 0}
        for value in options.command
    ]


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
    registry_path = (
        pathlib.Path(__file__).resolve().parents[2] / "docs/治理/p0-blockers.yaml"
    )
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    by_id = {item["id"]: item for item in registry["blockers"]}
    blocker_ids = options.blocker or list(
        TEST_BLOCKERS if options.role == "test" else REVIEW_BLOCKERS
    )
    allowed = set(TEST_BLOCKERS if options.role == "test" else REVIEW_BLOCKERS)
    if options.role == "review":
        allowed.add(SUPPLY_BLOCKER)
    if not blocker_ids or any(value not in allowed for value in blocker_ids):
        raise SystemExit("requested blocker is not assigned to this evidence role")
    commands = read_commands(options)
    timestamp = (
        dt.datetime.now(dt.UTC)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )
    run_uri = f"https://github.com/{repository}/actions/runs/{run_id}"
    options.output_dir.mkdir(parents=True, exist_ok=True)
    content_type = CONTENT_TYPES[options.role]
    role = ROLES[options.role]
    for blocker_id in blocker_ids:
        item = by_id[blocker_id]
        report = {
            "schema_version": "1.0.0",
            "content_type": content_type,
            "commit_sha": options.commit_sha,
            "github_run_id": int(run_id),
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
        destination.write_bytes(payload)


if __name__ == "__main__":
    main()
