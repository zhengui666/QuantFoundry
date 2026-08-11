#!/usr/bin/env bash
set -euo pipefail

report_path="${1:-}"
expected_commit="${2:-}"

[[ -n "$report_path" && -f "$report_path" ]] || { printf '%s\n' 'Independent review report is required and must be an existing file.' >&2; exit 2; }
[[ "$expected_commit" =~ ^[0-9a-f]{40}$ ]] || { printf '%s\n' 'Expected commit must be a full lowercase SHA.' >&2; exit 2; }
[[ -n "${GITHUB_TOKEN:-}" && -n "${GITHUB_REPOSITORY:-}" ]] || { printf '%s\n' 'GITHUB_TOKEN and GITHUB_REPOSITORY are required to verify independent review evidence.' >&2; exit 2; }
command -v gh >/dev/null || { printf '%s\n' 'gh is required to verify independent review evidence.' >&2; exit 2; }

GITHUB_TOKEN="$GITHUB_TOKEN" GITHUB_REPOSITORY="$GITHUB_REPOSITORY" python3 - "$report_path" "$expected_commit" <<'PY'
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from urllib.parse import urlparse

report_path = pathlib.Path(sys.argv[1])
expected_commit = sys.argv[2]
repository = os.environ["GITHUB_REPOSITORY"]
token = os.environ["GITHUB_TOKEN"]
try:
    report = json.loads(report_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as error:
    raise SystemExit(f"invalid independent review report: {error}")
if not isinstance(report, dict):
    raise SystemExit("independent review report must be a JSON object")
if report.get("schema_version") != "1.0.0" or report.get("commit") != expected_commit:
    raise SystemExit("independent review report schema_version or commit binding is invalid")
if report.get("verifier_role") != "Independent Review Agent" or report.get("result") != "approved":
    raise SystemExit("independent review report is not an approved Independent Review Agent result")
run_id, artifact_uri, artifact_sha256 = report.get("github_run_id"), report.get("artifact_uri"), report.get("artifact_sha256")
if not isinstance(run_id, int) or run_id < 1 or not isinstance(artifact_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", artifact_sha256):
    raise SystemExit("independent review report requires github_run_id and artifact_sha256")
parsed = urlparse(artifact_uri if isinstance(artifact_uri, str) else "")
match = re.fullmatch(r"/[^/]+/[^/]+/actions/runs/([1-9][0-9]*)/artifacts/([1-9][0-9]*)", parsed.path)
if parsed.scheme != "https" or parsed.netloc != "github.com" or not match or int(match.group(1)) != run_id:
    raise SystemExit("independent review report artifact_uri must bind to github_run_id")
env = os.environ.copy()
env["GH_TOKEN"] = token

def gh_json(endpoint):
    result = subprocess.run(["gh", "api", endpoint], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise SystemExit(f"gh api failed for {endpoint}: {result.stderr.strip() or result.returncode}")
    return json.loads(result.stdout)

run = gh_json(f"/repos/{repository}/actions/runs/{run_id}")
if run.get("head_sha") != expected_commit:
    raise SystemExit("independent review report run is not bound to the current commit")
artifact_id = match.group(2)
artifact = gh_json(f"/repos/{repository}/actions/artifacts/{artifact_id}")
if artifact.get("expired") or artifact.get("workflow_run", {}).get("id") != run_id:
    raise SystemExit("independent review report artifact is missing, expired, or not bound to its run")
with tempfile.TemporaryDirectory(prefix="qf-independent-review-") as directory:
    output = pathlib.Path(directory) / "report.zip"
    result = subprocess.run(["gh", "api", f"/repos/{repository}/actions/artifacts/{artifact_id}/zip", "--method", "GET", "-H", "Accept: application/octet-stream", "--output", str(output)], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise SystemExit(f"cannot download independent review artifact: {result.stderr.strip() or result.returncode}")
    if hashlib.sha256(output.read_bytes()).hexdigest() != artifact_sha256:
        raise SystemExit("independent review artifact SHA-256 does not match report")
PY
