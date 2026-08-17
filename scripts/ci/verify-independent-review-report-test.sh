#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fixture_dir="$(mktemp -d)"
mock_dir="$fixture_dir/mock-bin"
trap 'rm -rf "$fixture_dir"' EXIT
mkdir -p "$mock_dir"

commit_sha="$(git -C "$repo_root" rev-parse HEAD)"
export QF_REVIEW_MOCK_COMMIT="$commit_sha"

python3 - "$fixture_dir" "$commit_sha" "$repo_root" <<'PY'
import hashlib
import json
import pathlib
import subprocess
import sys
import zipfile

directory = pathlib.Path(sys.argv[1])
commit = sys.argv[2]
repository_root = sys.argv[3]
content_type = "application/vnd.quantfoundry.independent-review+json;version=1"
criteria = [
    "Agent/governance change conforms to canonical contracts and fail-closed CI policy.",
    "Independent review commands completed successfully on the reviewed commit.",
]
scope_paths = [
    "AGENTS.md", "PROJECT_BACKGROUND.md", "backend/src/quantfoundry", "backend/workers",
    "docs/Agent技术方案", "docs/后端系统技术方案/contracts/tools", "docs/治理",
    ".github/workflows", "scripts/ci", "scripts/release-evidence.sh", "scripts/release-check.sh",
]
scope_digest = hashlib.sha256(subprocess.check_output([
    "git", "-C", repository_root, "ls-tree", "-r", "--full-tree", commit, "--", *scope_paths,
])).hexdigest()

def make_artifact(name, report_commit, report_scope_digest=scope_digest):
    embedded = {
        "schema_version": "1.0.0",
        "content_type": content_type,
        "commit": report_commit,
        "github_run_id": 100,
        "verifier_role": "Independent Review Agent",
        "result": "approved",
        "criteria": criteria,
        "reviewed_paths": scope_paths,
        "review_scope_sha256": report_scope_digest,
        "commands": [{"command": "shellcheck scripts/ci/verify-independent-review-report.sh", "result": "pass", "exit_code": 0}],
    }
    payload = json.dumps(embedded, sort_keys=True, separators=(",", ":")).encode()
    archive = directory / f"{name}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("independent-review-report.json", payload)
    locator = {
        "schema_version": "1.0.0",
        "content_type": content_type,
        "commit": commit,
        "verifier_role": "Independent Review Agent",
        "result": "approved",
        "github_run_id": 100,
        "artifact_uri": "https://github.com/acme/quantfoundry/actions/runs/100/artifacts/200",
        "artifact_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "artifact_report": {"path": "independent-review-report.json", "sha256": hashlib.sha256(payload).hexdigest()},
    }
    (directory / f"{name}.json").write_text(json.dumps(locator), encoding="utf-8")

make_artifact("positive", commit)
make_artifact("wrong-content-commit", "ffffffffffffffffffffffffffffffffffffffff")
make_artifact("wrong-scope-digest", commit, "f" * 64)
PY

mock_gh="$mock_dir/gh"
# shellcheck disable=SC2016 # The quoted arguments are literal source for the mock gh executable.
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'set -euo pipefail' \
  '[[ "${1:-}" == api ]] || exit 2' \
  'endpoint="${2:-}"' \
  'output=""' \
  'for ((index = 1; index <= $#; index++)); do' \
  '  if [[ "${!index}" == --output ]]; then next=$((index + 1)); output="${!next}"; fi' \
  'done' \
  'if [[ "$endpoint" =~ /actions/runs/100$ ]]; then printf "{\"head_sha\":\"%s\",\"status\":\"%s\",\"conclusion\":\"%s\",\"event\":\"%s\",\"path\":\"%s\",\"head_branch\":\"%s\",\"workflow_id\":300}\n" "$QF_REVIEW_MOCK_COMMIT" "${QF_REVIEW_MOCK_STATUS:-completed}" "${QF_REVIEW_MOCK_CONCLUSION:-success}" "${QF_REVIEW_MOCK_EVENT:-workflow_dispatch}" "${QF_REVIEW_MOCK_PATH:-.github/workflows/independent-agent-review.yml}" "${QF_REVIEW_MOCK_BRANCH:-main}"; exit 0; fi' \
  'if [[ "$endpoint" == /repos/acme/quantfoundry/actions/workflows/independent-agent-review.yml ]]; then printf "{\"id\":300,\"path\":\".github/workflows/independent-agent-review.yml\"}\n"; exit 0; fi' \
  'if [[ "$endpoint" == /repos/acme/quantfoundry ]]; then printf "{\"default_branch\":\"main\"}\n"; exit 0; fi' \
  'if [[ "$endpoint" == "/repos/acme/quantfoundry/contents/.github/workflows/independent-agent-review.yml?ref=$QF_REVIEW_MOCK_COMMIT" ]]; then printf "{\"sha\":\"106fe374a92e902b4f0e119533680b51a640822d\"}\n"; exit 0; fi' \
  'if [[ "$endpoint" =~ /actions/artifacts/200$ ]]; then printf "{\"name\":\"independent-agent-review-100\",\"expired\":false,\"workflow_run\":{\"id\":100}}\n"; exit 0; fi' \
  'if [[ "$endpoint" =~ /actions/artifacts/200/zip$ ]]; then if [[ -n "$output" ]]; then cp "$QF_REVIEW_MOCK_ARCHIVE" "$output"; else cat "$QF_REVIEW_MOCK_ARCHIVE"; fi; exit 0; fi' \
  'exit 1' > "$mock_gh"
chmod +x "$mock_gh"

run_verifier() {
  local locator="$1"
  local archive="$2"
  local status="${3:-completed}"
  local conclusion="${4:-success}"
  local workflow_path="${5:-.github/workflows/independent-agent-review.yml}"
  env PATH="$mock_dir:$PATH" GITHUB_TOKEN='fixture-token' GITHUB_REPOSITORY='acme/quantfoundry' QF_REVIEW_MOCK_ARCHIVE="$archive" QF_REVIEW_MOCK_STATUS="$status" QF_REVIEW_MOCK_CONCLUSION="$conclusion" QF_REVIEW_MOCK_PATH="$workflow_path" "$repo_root/scripts/ci/verify-independent-review-report.sh" "$locator" "$commit_sha"
}

python3 - "$fixture_dir/positive.json" "$fixture_dir/positive-attestation.json" "$commit_sha" <<'PY'
import hashlib
import json
import pathlib
import sys

locator, attestation, commit = map(pathlib.Path, sys.argv[1:])
attestation.write_text(json.dumps({
    "schema_version": "1.0.0",
    "commit": str(commit),
    "locator_sha256": hashlib.sha256(locator.read_bytes()).hexdigest(),
    "result": "verified",
}), encoding="utf-8")
PY

if env QF_INDEPENDENT_REVIEW_OFFLINE=1 QF_INDEPENDENT_REVIEW_ATTESTATION="$fixture_dir/positive-attestation.json" \
  "$repo_root/scripts/ci/verify-independent-review-report.sh" "$fixture_dir/positive.json" "$commit_sha" >/dev/null 2>&1; then
  printf '%s\n' 'Expected forgeable offline verification mode to be disabled.' >&2
  exit 1
fi

run_verifier "$fixture_dir/positive.json" "$fixture_dir/positive.zip"
if run_verifier "$fixture_dir/wrong-content-commit.json" "$fixture_dir/wrong-content-commit.zip" >/dev/null 2>&1; then
  printf '%s\n' 'Expected artifact content with a stale commit to fail.' >&2
  exit 1
fi
if run_verifier "$fixture_dir/wrong-scope-digest.json" "$fixture_dir/wrong-scope-digest.zip" >/dev/null 2>&1; then
  printf '%s\n' 'Expected artifact content with a mismatched review scope digest to fail.' >&2
  exit 1
fi
if run_verifier "$fixture_dir/positive.json" "$fixture_dir/positive.zip" completed failure >/dev/null 2>&1; then
  printf '%s\n' 'Expected failed independent review run to fail.' >&2
  exit 1
fi
if run_verifier "$fixture_dir/positive.json" "$fixture_dir/positive.zip" completed cancelled >/dev/null 2>&1; then
  printf '%s\n' 'Expected cancelled independent review run to fail.' >&2
  exit 1
fi
if run_verifier "$fixture_dir/positive.json" "$fixture_dir/positive.zip" completed success '.github/workflows/untrusted.yml@refs/heads/main' >/dev/null 2>&1; then
  printf '%s\n' 'Expected unauthorized independent review workflow to fail.' >&2
  exit 1
fi

printf '%s\n' '{"result":"pass","gate":"independent-review-report-fixtures"}'
