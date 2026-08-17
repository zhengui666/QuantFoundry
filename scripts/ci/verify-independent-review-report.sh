#!/usr/bin/env bash
set -euo pipefail

report_path="${1:-}"
expected_commit="${2:-}"
repo_root="${QF_CI_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

[[ -n "$report_path" && -f "$report_path" ]] || { printf '%s\n' 'Independent review report is required and must be an existing file.' >&2; exit 2; }
[[ "$expected_commit" =~ ^[0-9a-f]{40}$ ]] || { printf '%s\n' 'Expected commit must be a full lowercase SHA.' >&2; exit 2; }
if [[ "$report_path" != /* ]]; then
  report_path="$PWD/$report_path"
fi
report_path="$(cd "$(dirname "$report_path")" && pwd)/$(basename "$report_path")"

if [[ "${QF_INDEPENDENT_REVIEW_OFFLINE:-0}" == 1 ]]; then
  printf '%s\n' 'Offline independent-review verification is disabled; use the trusted verification job dependency.' >&2
  exit 2
fi

[[ -n "${GITHUB_TOKEN:-}" && -n "${GITHUB_REPOSITORY:-}" ]] || { printf '%s\n' 'GITHUB_TOKEN and GITHUB_REPOSITORY are required to verify independent review evidence.' >&2; exit 2; }
command -v gh >/dev/null || { printf '%s\n' 'gh is required to verify independent review evidence.' >&2; exit 2; }

cd "$repo_root"
GITHUB_TOKEN="$GITHUB_TOKEN" GITHUB_REPOSITORY="$GITHUB_REPOSITORY" python3 - "$report_path" "$expected_commit" <<'PY'
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import zipfile
from urllib.parse import quote, urlparse

report_path = pathlib.Path(sys.argv[1])
expected_commit = sys.argv[2]
repository = os.environ["GITHUB_REPOSITORY"]
token = os.environ["GITHUB_TOKEN"]
content_type = "application/vnd.quantfoundry.independent-review+json;version=1"
sha256_pattern = re.compile(r"^[0-9a-f]{64}$")
criteria = [
    "Agent/governance change conforms to canonical contracts and fail-closed CI policy.",
    "Independent review commands completed successfully on the reviewed commit.",
]
scope_paths = [
    "AGENTS.md",
    "PROJECT_BACKGROUND.md",
    "Makefile",
    "backend/pyproject.toml",
    "backend/uv.lock",
    "backend/src/quantfoundry",
    "backend/app/agent_runtime.py",
    "backend/workers",
    "frontend/package.json",
    "frontend/pnpm-lock.yaml",
    "frontend/src",
    "docs/Agent技术方案",
    "docs/后端系统技术方案/contracts/tools",
    "docs/治理",
    ".github/workflows",
    "scripts/ci",
    "scripts/ci.sh",
    "scripts/api_healthcheck.py",
    "scripts/p0-check.sh",
    "scripts/p0-check-test.sh",
    "scripts/tool_contract_check.py",
    "scripts/release-check.sh",
    "scripts/release-evidence.sh",
    "scripts/release-known-issues-check.sh",
]
trusted_workflow_blob_sha = "51bf6299bb3c1a290530efe7a99a6e043a43359d"

def review_scope_sha256():
    for path in scope_paths:
        if subprocess.run(["git", "cat-file", "-e", f"{expected_commit}:{path}"]).returncode:
            raise SystemExit(f"reviewed path is missing at reviewed commit: {path}")
    completed = subprocess.run(
        ["git", "ls-tree", "-r", "--full-tree", expected_commit, "--", *scope_paths],
        text=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode:
        raise SystemExit(f"cannot calculate independent review scope digest: {completed.stderr.decode().strip() or completed.returncode}")
    return hashlib.sha256(completed.stdout).hexdigest()
try:
    report = json.loads(report_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as error:
    raise SystemExit(f"invalid independent review report: {error}")
if not isinstance(report, dict):
    raise SystemExit("independent review report must be a JSON object")
if report.get("schema_version") != "1.0.0" or report.get("commit") != expected_commit:
    raise SystemExit("independent review report schema_version or commit binding is invalid")
if report.get("content_type") != content_type:
    raise SystemExit("independent review report content_type is invalid")
if report.get("verifier_role") != "Independent Review Agent" or report.get("result") != "approved":
    raise SystemExit("independent review report is not an approved Independent Review Agent result")
run_id, artifact_uri, artifact_sha256 = report.get("github_run_id"), report.get("artifact_uri"), report.get("artifact_sha256")
artifact_report = report.get("artifact_report")
if not isinstance(run_id, int) or run_id < 1 or not isinstance(artifact_sha256, str) or not sha256_pattern.fullmatch(artifact_sha256):
    raise SystemExit("independent review report requires github_run_id and artifact_sha256")
if not isinstance(artifact_report, dict) or set(artifact_report) != {"path", "sha256"}:
    raise SystemExit("independent review report requires artifact_report path and sha256")
artifact_report_path, artifact_report_sha256 = artifact_report["path"], artifact_report["sha256"]
if not isinstance(artifact_report_path, str) or not artifact_report_path or artifact_report_path.startswith("/") or any(part in {"", ".", ".."} for part in artifact_report_path.split("/")):
    raise SystemExit("independent review artifact_report path is invalid")
if artifact_report_path != "independent-review-report.json":
    raise SystemExit("independent review artifact_report path is not canonical")
if not isinstance(artifact_report_sha256, str) or not sha256_pattern.fullmatch(artifact_report_sha256):
    raise SystemExit("independent review artifact_report sha256 is invalid")
parsed = urlparse(artifact_uri if isinstance(artifact_uri, str) else "")
match = re.fullmatch(r"/([^/]+/[^/]+)/actions/runs/([1-9][0-9]*)/artifacts/([1-9][0-9]*)", parsed.path)
if parsed.scheme != "https" or parsed.netloc != "github.com" or not match or match.group(1) != repository or int(match.group(2)) != run_id:
    raise SystemExit("independent review report artifact_uri must bind to repository and github_run_id")
env = os.environ.copy()
env["GH_TOKEN"] = token

def gh_json(endpoint):
    result = subprocess.run(["gh", "api", endpoint], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode:
        raise SystemExit(f"gh api failed for {endpoint}: {result.stderr.strip() or result.returncode}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise SystemExit(f"gh api returned non-JSON for {endpoint}") from error

run = gh_json(f"/repos/{repository}/actions/runs/{run_id}")
if run.get("head_sha") != expected_commit:
    raise SystemExit("independent review report run is not bound to the current commit")
if run.get("status") != "completed" or run.get("conclusion") != "success" or run.get("event") != "workflow_dispatch":
    raise SystemExit("independent review report run did not complete successfully as workflow_dispatch")
run_actor = run.get("actor", {}).get("login") if isinstance(run.get("actor"), dict) else None
triggering_actor = (
    run.get("triggering_actor", {}).get("login") if isinstance(run.get("triggering_actor"), dict) else None
)
if not isinstance(run_actor, str) or not isinstance(triggering_actor, str):
    raise SystemExit("independent review report run has no actor identity")
commit_payload = gh_json(f"/repos/{repository}/commits/{expected_commit}")
commit_authors = {
    item.get("login")
    for field in ("author", "committer")
    for item in (commit_payload.get(field),)
    if isinstance(item, dict) and isinstance(item.get("login"), str)
}
if run_actor in commit_authors or triggering_actor in commit_authors:
    raise SystemExit("independent review actor must be independent from the reviewed commit")
if report.get("actor") != run_actor or report.get("triggering_actor") != triggering_actor:
    raise SystemExit("independent review report actor identity is not bound to the GitHub run")
workflow_path = run.get("path", "")
if workflow_path != ".github/workflows/independent-agent-review.yml":
    raise SystemExit("independent review report run used an unauthorized workflow")
workflow_id = run.get("workflow_id")
if not isinstance(workflow_id, int) or workflow_id < 1:
    raise SystemExit("independent review report run has no workflow identity")
workflow = gh_json(f"/repos/{repository}/actions/workflows/independent-agent-review.yml")
if workflow.get("id") != workflow_id or workflow.get("path") != ".github/workflows/independent-agent-review.yml":
    raise SystemExit("independent review report run workflow identity is not canonical")
workflow_source = gh_json(
    f"/repos/{repository}/contents/.github/workflows/independent-agent-review.yml"
    f"?ref={quote(expected_commit, safe='')}"
)
if workflow_source.get("sha") != trusted_workflow_blob_sha:
    raise SystemExit("independent review workflow is not the trusted revision")
artifact_id = match.group(3)
artifact = gh_json(f"/repos/{repository}/actions/artifacts/{artifact_id}")
if (
    artifact.get("name") != f"independent-agent-review-{run_id}"
    or artifact.get("expired")
    or artifact.get("workflow_run", {}).get("id") != run_id
):
    raise SystemExit("independent review report artifact is missing, expired, or not bound to its run")
with tempfile.TemporaryDirectory(prefix="qf-independent-review-") as directory:
    output = pathlib.Path(directory) / "report.zip"
    with output.open("wb") as archive_file:
        result = subprocess.run(
            ["gh", "api", f"/repos/{repository}/actions/artifacts/{artifact_id}/zip", "--method", "GET"],
            env=env,
            stdout=archive_file,
            stderr=subprocess.PIPE,
            text=True,
        )
    if result.returncode:
        raise SystemExit(f"cannot download independent review artifact: {result.stderr.strip() or result.returncode}")
    archive = output.read_bytes()
if len(archive) > 100 * 1024 * 1024:
    raise SystemExit("independent review artifact exceeds the compressed size limit")
if hashlib.sha256(archive).hexdigest() != artifact_sha256:
    raise SystemExit("independent review artifact SHA-256 does not match report")
try:
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        members = bundle.infolist()
        if len(members) > 32 or sum(member.file_size for member in members) > 100 * 1024 * 1024:
            raise SystemExit("independent review artifact exceeds the uncompressed size limit")
        matching_members = [member for member in bundle.infolist() if member.filename == artifact_report_path and not member.is_dir()]
        if len(matching_members) != 1:
            raise SystemExit("independent review artifact must contain exactly one declared review report")
        if matching_members[0].file_size > 1024 * 1024:
            raise SystemExit("independent review artifact report exceeds the size limit")
        embedded_bytes = bundle.read(matching_members[0])
except (OSError, zipfile.BadZipFile) as error:
    raise SystemExit(f"independent review artifact is not a readable ZIP: {error}") from error
if hashlib.sha256(embedded_bytes).hexdigest() != artifact_report_sha256:
    raise SystemExit("independent review artifact report SHA-256 does not match locator")
try:
    embedded = json.loads(embedded_bytes)
except json.JSONDecodeError as error:
    raise SystemExit(f"independent review artifact report is not JSON: {error}") from error
if not isinstance(embedded, dict):
    raise SystemExit("independent review artifact report must be a JSON object")
if embedded.get("schema_version") != "1.0.0" or embedded.get("content_type") != content_type:
    raise SystemExit("independent review artifact report schema or content_type is invalid")
if embedded.get("commit") != expected_commit or embedded.get("github_run_id") != run_id:
    raise SystemExit("independent review artifact report is not bound to the current commit and run")
if embedded.get("actor") != run_actor or embedded.get("triggering_actor") != triggering_actor:
    raise SystemExit("independent review artifact report actor identity is not bound to the GitHub run")
if embedded.get("verifier_role") != "Independent Review Agent" or embedded.get("result") != "approved":
    raise SystemExit("independent review artifact report is not an approved independent review")
if embedded.get("criteria") != criteria:
    raise SystemExit("independent review artifact report criteria do not match the canonical review contract")
reviewed_paths = embedded.get("reviewed_paths")
if reviewed_paths != scope_paths:
    raise SystemExit("independent review artifact report reviewed_paths do not match the canonical review scope")
scope_digest = embedded.get("review_scope_sha256")
if not isinstance(scope_digest, str) or not sha256_pattern.fullmatch(scope_digest) or scope_digest != review_scope_sha256():
    raise SystemExit("independent review artifact report review_scope_sha256 does not match the current commit")
commands = embedded.get("commands")
if not isinstance(commands, list) or not commands:
    raise SystemExit("independent review artifact report requires successful review commands")
for command in commands:
    if (
        not isinstance(command, dict)
        or set(command) != {"command", "result", "exit_code"}
        or not isinstance(command.get("command"), str)
        or not command["command"].strip()
        or command.get("result") != "pass"
        or command.get("exit_code") != 0
    ):
        raise SystemExit("independent review artifact report contains an invalid review command")
PY
