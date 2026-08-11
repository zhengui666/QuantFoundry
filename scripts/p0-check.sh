#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
registry="${1:-$repo_root/docs/治理/p0-blockers.yaml}"
mode="${2:---require-closed}"

[[ "$mode" == "--report" || "$mode" == "--require-closed" ]] || {
  printf 'Usage: %s [registry] [--report|--require-closed]\n' "$0" >&2
  exit 2
}
[[ -f "$registry" ]] || { printf 'Missing P0 registry: %s\n' "$registry" >&2; exit 2; }
registry="$(cd "$(dirname "$registry")" && pwd)/$(basename "$registry")"
command -v uv >/dev/null || { printf '%s\n' 'uv is required to parse the canonical P0 registry.' >&2; exit 2; }

set +e
QF_RELEASE_COMMIT="${QF_RELEASE_COMMIT:-}" uv --directory "$repo_root/backend" run --frozen python - "$registry" "$mode" <<'PY'
import datetime as dt
import json
import os
import pathlib
import re
import sys
from urllib.parse import urlparse

import yaml

registry_path = pathlib.Path(sys.argv[1])
mode = sys.argv[2]
expected_commit = os.environ.get("QF_RELEASE_COMMIT", "")
sha_pattern = re.compile(r"^[0-9a-f]{40}$")
sha256_pattern = re.compile(r"^[0-9a-f]{64}$")
github_build_pattern = re.compile(r"^github-actions/[1-9][0-9]*$")
placeholder_pattern = re.compile(r"(?i)(placeholder|codeowners|todo|tbd|example|n/?a|unknown)")
allowed_roles = {"Independent Test Agent", "Independent Review Agent"}


def invalid_value(value):
    return not isinstance(value, str) or not value.strip() or bool(placeholder_pattern.search(value))


def valid_artifact_uri(value):
    if invalid_value(value) or value != value.strip():
        return False
    parsed = urlparse(value)
    if parsed.scheme == "https" and parsed.netloc == "github.com" and not parsed.username and not parsed.password:
        return bool(re.fullmatch(r"/[^/]+/[^/]+/(actions/runs/[1-9][0-9]*/artifacts/[1-9][0-9]*|releases/download/[^/]+/[^/]+)", parsed.path))
    return parsed.scheme == "oci" and parsed.netloc == "ghcr.io" and bool(re.fullmatch(r"/[^/]+/[^/@]+@sha256:[0-9a-f]{64}", parsed.path))


def valid_timestamp(value):
    if invalid_value(value) or not value.endswith("Z"):
        return False
    try:
        dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def validate_closed_evidence(blocker_id, item):
    errors = []
    criteria = item.get("closure_criteria")
    evidence = item.get("evidence")
    if not isinstance(criteria, list) or not criteria or any(invalid_value(value) for value in criteria):
        return [f"{blocker_id}: closed blocker requires non-empty closure_criteria strings"]
    if not isinstance(evidence, list) or not evidence:
        return [f"{blocker_id}: closed release blocker requires structured closure evidence"]

    covered_criteria = set()
    roles = set()
    for index, record in enumerate(evidence):
        prefix = f"{blocker_id}: evidence[{index}]"
        if not isinstance(record, dict):
            errors.append(f"{prefix} must be an object")
            continue
        role = record.get("verifier_role")
        if role not in allowed_roles or role == item.get("owner_role"):
            errors.append(f"{prefix}.verifier_role must be an independent Test or Review Agent")
        else:
            roles.add(role)
        if not valid_timestamp(record.get("verified_at_utc")):
            errors.append(f"{prefix}.verified_at_utc must be a non-placeholder UTC timestamp")
        commit_sha = record.get("commit_sha")
        if not isinstance(commit_sha, str) or not sha_pattern.fullmatch(commit_sha):
            errors.append(f"{prefix}.commit_sha must be a full lowercase 40-character SHA")
        elif expected_commit and commit_sha != expected_commit:
            errors.append(f"{prefix}.commit_sha does not match release commit")
        build_id = record.get("build_id")
        if not isinstance(build_id, str) or not github_build_pattern.fullmatch(build_id):
            errors.append(f"{prefix}.build_id must be a GitHub Actions run identity")
        if not valid_artifact_uri(record.get("artifact_uri")):
            errors.append(f"{prefix}.artifact_uri must be an immutable remote HTTPS or GHCR OCI locator")
        artifact_sha256 = record.get("artifact_sha256")
        if not isinstance(artifact_sha256, str) or not sha256_pattern.fullmatch(artifact_sha256):
            errors.append(f"{prefix}.artifact_sha256 must be a lowercase SHA-256")
        elif isinstance(record.get("artifact_uri"), str) and record["artifact_uri"].startswith("oci://"):
            if not record["artifact_uri"].endswith(f"@sha256:{artifact_sha256}"):
                errors.append(f"{prefix}.artifact_sha256 must match the GHCR OCI digest")
        if isinstance(build_id, str) and github_build_pattern.fullmatch(build_id) and isinstance(record.get("artifact_uri"), str):
            run_id = build_id.split("/", 1)[1]
            if f"/actions/runs/{run_id}/" not in record["artifact_uri"]:
                errors.append(f"{prefix}.artifact_uri must bind to build_id's GitHub Actions run")
        record_criteria = record.get("closure_criteria")
        if not isinstance(record_criteria, list) or not record_criteria:
            errors.append(f"{prefix}.closure_criteria must cover one or more canonical criteria")
        else:
            for criterion in record_criteria:
                if criterion not in criteria:
                    errors.append(f"{prefix}.closure_criteria contains a non-canonical criterion")
                else:
                    covered_criteria.add(criterion)
        commands = record.get("commands")
        if not isinstance(commands, list) or not commands:
            errors.append(f"{prefix}.commands must contain verified commands")
        else:
            for command_index, command in enumerate(commands):
                command_prefix = f"{prefix}.commands[{command_index}]"
                if not isinstance(command, dict):
                    errors.append(f"{command_prefix} must be an object")
                    continue
                if invalid_value(command.get("command")) or "\n" in command["command"]:
                    errors.append(f"{command_prefix}.command must be a non-placeholder single command")
                if invalid_value(command.get("result")):
                    errors.append(f"{command_prefix}.result is required")
                if command.get("exit_code") != 0:
                    errors.append(f"{command_prefix}.exit_code must be 0")
    missing_criteria = set(criteria) - covered_criteria
    if missing_criteria:
        errors.append(f"{blocker_id}: evidence does not cover every closure criterion")
    if roles != allowed_roles:
        errors.append(f"{blocker_id}: evidence requires separate Independent Test Agent and Independent Review Agent records")
    return errors


try:
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
except (OSError, yaml.YAMLError) as error:
    print(json.dumps({"registry": str(registry_path), "result": "invalid", "error": str(error)}, ensure_ascii=False))
    raise SystemExit(2)

if not isinstance(registry, dict) or not isinstance(registry.get("blockers"), list):
    print(json.dumps({"registry": str(registry_path), "result": "invalid", "error": "blockers list is required"}, ensure_ascii=False))
    raise SystemExit(2)

invalid = []
blocking = []
for item in registry["blockers"]:
    if not isinstance(item, dict):
        invalid.append("non-object blocker")
        continue
    blocker_id = item.get("id")
    status = item.get("status")
    release_blocking = item.get("release_blocking")
    if not isinstance(blocker_id, str) or status not in {"open", "blocked", "closed"} or not isinstance(release_blocking, bool):
        invalid.append(str(blocker_id or "unknown"))
        continue
    if release_blocking:
        if status == "closed":
            invalid.extend(validate_closed_evidence(blocker_id, item))
        blocking.append({"id": blocker_id, "status": status, "evidence_count": len(item.get("evidence", [])) if isinstance(item.get("evidence", []), list) else 0})

unclosed = [item for item in blocking if item["status"] != "closed"]
summary = {
    "registry": str(registry_path),
    "result": "pass" if not invalid and not unclosed else "blocked",
    "release_blocking_total": len(blocking),
    "closed": sum(item["status"] == "closed" for item in blocking),
    "unclosed": unclosed,
    "invalid": invalid,
}
print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
if invalid or (mode == "--require-closed" and unclosed):
    raise SystemExit(1)
PY
status="$?"
set -e
exit "$status"
