#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fixture_dir="$(mktemp -d)"
mock_dir="$fixture_dir/mock-bin"
trap 'rm -rf "$fixture_dir"' EXIT
mkdir -p "$mock_dir"

commit_sha='0123456789abcdef0123456789abcdef01234567'
export QF_REVIEW_MOCK_COMMIT="$commit_sha"

python3 - "$fixture_dir" "$commit_sha" <<'PY'
import hashlib
import json
import pathlib
import sys
import zipfile

directory = pathlib.Path(sys.argv[1])
commit = sys.argv[2]
content_type = "application/vnd.quantfoundry.independent-review+json;version=1"

def make_artifact(name, report_commit):
    embedded = {
        "schema_version": "1.0.0",
        "content_type": content_type,
        "commit": report_commit,
        "github_run_id": 100,
        "verifier_role": "Independent Review Agent",
        "result": "approved",
        "reviewed_paths": ["scripts/ci/verify-independent-review-report.sh"],
        "commands": [{"command": "shellcheck scripts/ci/verify-independent-review-report.sh", "exit_code": 0}],
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
  'if [[ "$endpoint" =~ /actions/runs/100$ ]]; then printf "{\\\"head_sha\\\":\\\"%s\\\"}\\n" "$QF_REVIEW_MOCK_COMMIT"; exit 0; fi' \
  'if [[ "$endpoint" =~ /actions/artifacts/200$ ]]; then printf "{\\\"expired\\\":false,\\\"workflow_run\\\":{\\\"id\\\":100}}\\n"; exit 0; fi' \
  'if [[ "$endpoint" =~ /actions/artifacts/200/zip$ ]]; then cp "$QF_REVIEW_MOCK_ARCHIVE" "$output"; exit 0; fi' \
  'exit 1' > "$mock_gh"
chmod +x "$mock_gh"

run_verifier() {
  local locator="$1"
  local archive="$2"
  env PATH="$mock_dir:$PATH" GITHUB_TOKEN='fixture-token' GITHUB_REPOSITORY='acme/quantfoundry' QF_REVIEW_MOCK_ARCHIVE="$archive" "$repo_root/scripts/ci/verify-independent-review-report.sh" "$locator" "$commit_sha"
}

run_verifier "$fixture_dir/positive.json" "$fixture_dir/positive.zip"
if run_verifier "$fixture_dir/wrong-content-commit.json" "$fixture_dir/wrong-content-commit.zip" >/dev/null 2>&1; then
  printf '%s\n' 'Expected artifact content with a stale commit to fail.' >&2
  exit 1
fi

printf '%s\n' '{"result":"pass","gate":"independent-review-report-fixtures"}'
