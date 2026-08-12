#!/usr/bin/env bash
set -euo pipefail

commit="${1:-}"
output="${2:-}"

[[ "$commit" =~ ^[0-9a-f]{40}$ ]] || { printf '%s\n' 'Expected commit must be a full lowercase SHA.' >&2; exit 2; }
[[ -n "$output" ]] || { printf '%s\n' 'Output locator path is required.' >&2; exit 2; }
[[ -n "${GITHUB_TOKEN:-}" && -n "${GITHUB_REPOSITORY:-}" ]] || { printf '%s\n' 'GITHUB_TOKEN and GITHUB_REPOSITORY are required to fetch independent review evidence.' >&2; exit 2; }
command -v gh >/dev/null || { printf '%s\n' 'gh is required to fetch independent review evidence.' >&2; exit 2; }

mkdir -p "$(dirname "$output")"
GITHUB_TOKEN="$GITHUB_TOKEN" GITHUB_REPOSITORY="$GITHUB_REPOSITORY" python3 - "$commit" "$output" <<'PY'
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import zipfile

commit, output_name = sys.argv[1:]
repository = os.environ["GITHUB_REPOSITORY"]
token = os.environ["GITHUB_TOKEN"]
env = os.environ.copy()
env["GH_TOKEN"] = token

def gh_json(endpoint):
    completed = subprocess.run(
        ["gh", "api", endpoint], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if completed.returncode:
        raise SystemExit(f"gh api failed for {endpoint}: {completed.stderr.strip() or completed.returncode}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise SystemExit(f"gh api returned non-JSON for {endpoint}") from error

runs = gh_json(
    f"/repos/{repository}/actions/workflows/independent-agent-review.yml/runs"
    f"?head_sha={commit}&status=completed&event=workflow_dispatch&per_page=100"
).get("workflow_runs", [])
run = next((item for item in runs if item.get("head_sha") == commit and item.get("conclusion") == "success"), None)
if not isinstance(run, dict) or not isinstance(run.get("id"), int):
    raise SystemExit("no successful independent-agent-review workflow run is bound to the current commit")
if run.get("status") != "completed" or run.get("conclusion") != "success" or run.get("event") != "workflow_dispatch":
    raise SystemExit("independent review run must be a completed successful workflow_dispatch run")
if run.get("path", "").split("@", 1)[0] != ".github/workflows/independent-agent-review.yml":
    raise SystemExit("independent review run used an unauthorized workflow")
run_id = run["id"]
artifacts = gh_json(f"/repos/{repository}/actions/runs/{run_id}/artifacts").get("artifacts", [])
artifact = next(
    (
        item
        for item in artifacts
        if item.get("name") == f"independent-agent-review-{run_id}" and not item.get("expired") and isinstance(item.get("id"), int)
    ),
    None,
)
if not isinstance(artifact, dict):
    raise SystemExit("successful independent review run has no usable review artifact")
artifact_id = artifact["id"]
with tempfile.TemporaryDirectory(prefix="qf-independent-review-fetch-") as directory:
    archive_path = pathlib.Path(directory) / "review.zip"
    with archive_path.open("wb") as archive_file:
        completed = subprocess.run(
            [
                "gh", "api", f"/repos/{repository}/actions/artifacts/{artifact_id}/zip", "--method", "GET",
                "-H", "Accept: application/octet-stream",
            ],
            env=env,
            stdout=archive_file,
            stderr=subprocess.PIPE,
            text=True,
        )
    if completed.returncode:
        raise SystemExit(f"cannot download independent review artifact: {completed.stderr.strip() or completed.returncode}")
    archive = archive_path.read_bytes()
try:
    with zipfile.ZipFile(__import__("io").BytesIO(archive)) as bundle:
        members = [item for item in bundle.infolist() if item.filename == "independent-review-report.json" and not item.is_dir()]
        if len(members) != 1:
            raise SystemExit("independent review artifact must contain exactly one canonical review report")
        payload = bundle.read(members[0])
except (OSError, zipfile.BadZipFile) as error:
    raise SystemExit(f"independent review artifact is not a readable ZIP: {error}") from error
try:
    report = json.loads(payload)
except json.JSONDecodeError as error:
    raise SystemExit(f"independent review artifact report is not JSON: {error}") from error
if not isinstance(report, dict) or report.get("commit") != commit or report.get("github_run_id") != run_id:
    raise SystemExit("independent review artifact report is not bound to the selected run and commit")
locator = {
    "schema_version": "1.0.0",
    "content_type": "application/vnd.quantfoundry.independent-review+json;version=1",
    "commit": commit,
    "verifier_role": "Independent Review Agent",
    "result": "approved",
    "github_run_id": run_id,
    "artifact_uri": f"https://github.com/{repository}/actions/runs/{run_id}/artifacts/{artifact_id}",
    "artifact_sha256": hashlib.sha256(archive).hexdigest(),
    "artifact_report": {"path": "independent-review-report.json", "sha256": hashlib.sha256(payload).hexdigest()},
}
pathlib.Path(output_name).write_text(json.dumps(locator, sort_keys=True) + "\n", encoding="utf-8")
PY
