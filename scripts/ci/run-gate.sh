#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
gate="${1:-}"
report_dir="${QF_CI_REPORT_DIR:-}"

usage() {
  printf '%s\n' 'usage: scripts/ci/run-gate.sh <pr-fast|main-full|nightly|agent-change|rc> [REPORT_DIR]' >&2
  exit 2
}

[[ "$gate" =~ ^(pr-fast|main-full|nightly|agent-change|rc)$ ]] || usage
if [[ -n "${2:-}" ]]; then
  report_dir="$2"
fi
if [[ -z "$report_dir" ]]; then
  report_dir="$(mktemp -d "${TMPDIR:-/tmp}/quantfoundry-${gate}.XXXXXX")"
fi
mkdir -p "$report_dir/logs"
report_dir="$(cd "$report_dir" && pwd)"

commit="$(git -C "$repo_root" rev-parse HEAD)"
ref="${GITHUB_REF:-$(git -C "$repo_root" symbolic-ref --short -q HEAD || printf 'detached')}"
started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
results_file="$report_dir/steps.ndjson"
: > "$results_file"

write_result() {
  local name="$1" command_text="$2" exit_code="$3" limitation="${4:-}"
  python3 - "$results_file" "$name" "$command_text" "$exit_code" "$limitation" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
record = {
    "name": sys.argv[2],
    "command": sys.argv[3],
    "exit_code": int(sys.argv[4]),
    "environment_limitation": sys.argv[5] or None,
}
with path.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(record, sort_keys=True) + "\n")
PY
}

finish() {
  local status="$1"
  python3 - "$report_dir/result.json" "$gate" "$commit" "$ref" "$started_at" "$status" "$results_file" "$report_dir/fullstack-diagnostics.json" <<'PY'
import json
import pathlib
import sys

output = pathlib.Path(sys.argv[1])
steps = [json.loads(line) for line in pathlib.Path(sys.argv[7]).read_text(encoding="utf-8").splitlines()]
result = {
    "gate": sys.argv[2],
    "commit": sys.argv[3],
    "ref": sys.argv[4],
    "started_at_utc": sys.argv[5],
    "result": "pass" if sys.argv[6] == "0" else "fail",
    "exit_code": int(sys.argv[6]),
    "steps": steps,
    "environment_limitations": [step for step in steps if step["environment_limitation"]],
}
diagnostics_path = pathlib.Path(sys.argv[8])
if diagnostics_path.is_file():
    result["diagnostics"] = {"fullstack": json.loads(diagnostics_path.read_text(encoding="utf-8"))}
output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
  exit "$status"
}

trap 'status=$?; trap - EXIT; finish "$status"' EXIT

run_step() {
  local name="$1"
  shift
  local command_text
  command_text="$(printf '%q ' "$@")"
  local status=0
  set +e
  (cd "$repo_root" && "$@") >"$report_dir/logs/$name.log" 2>&1
  status=$?
  set -e
  write_result "$name" "$command_text" "$status"
  [[ "$status" == 0 ]] || exit "$status"
}

require_command() {
  local command_name="$1"
  if ! command -v "$command_name" >/dev/null 2>&1; then
    write_result "host-${command_name}" "command -v ${command_name}" 127 "missing host dependency: ${command_name}"
    exit 127
  fi
}

require_common_tooling() {
  require_command git
  require_command python3
  require_command uv
  require_command node
  require_command pnpm
  require_command docker
  require_command shellcheck
  require_command actionlint
  if ! docker compose version >/dev/null 2>&1; then
    write_result host-docker-compose 'docker compose version' 127 'missing host dependency: docker compose plugin'
    exit 127
  fi
}

require_ci_environment() {
  if [[ -z "${QF_ENV:-}" || "$QF_ENV" != "${QF_ENVIRONMENT:-}" ]]; then
    write_result ci-environment 'QF_ENV and QF_ENVIRONMENT must be identical' 2 'missing or inconsistent CI environment identity'
    exit 2
  fi
  if [[ -z "${QF_GIT_COMMIT:-}" || -z "${QF_BUILD_ID:-}" ]]; then
    write_result ci-build-identity 'QF_GIT_COMMIT and QF_BUILD_ID are required' 2 'missing CI commit or build identity'
    exit 2
  fi
  if [[ "$QF_GIT_COMMIT" != "$commit" ]]; then
    write_result ci-build-identity 'QF_GIT_COMMIT must equal checkout HEAD' 2 'CI commit identity does not match checkout HEAD'
    exit 2
  fi
  if [[ "${QF_DATABASE_URL:-}" != postgresql+psycopg://* || "${QF_ALEMBIC_URL:-}" != "$QF_DATABASE_URL" || "${QF_SKIP_AUTO_CREATE:-}" != 1 ]]; then
    write_result ci-postgres 'QF_DATABASE_URL/QF_ALEMBIC_URL/QF_SKIP_AUTO_CREATE are required' 2 'missing real PostgreSQL CI configuration'
    exit 2
  fi
}

run_pr_fast() {
  require_ci_environment
  require_common_tooling
  run_step governance make governance
  run_step release-governance-static scripts/ci/release-governance-static-gate.sh
  run_step platform make platform
  run_step hygiene make hygiene
  run_step migration scripts/ci.sh migration
  run_step schema make schema
  run_step contracts make contract
  run_step backend-fast make backend-ci
  run_step frontend-fast make frontend-ci
}

run_main_full() {
  require_ci_environment
  require_common_tooling
  run_step p0-registry-snapshot bash -c 'scripts/p0-check.sh docs/治理/p0-blockers.yaml --report'
  run_step release-governance-static scripts/ci/release-governance-static-gate.sh
  run_step full-ci-platform make platform
  run_step full-ci-hygiene make hygiene
  run_step full-ci-migration scripts/ci.sh migration
  run_step full-ci-backend-format scripts/ci.sh backend-format
  run_step full-ci-backend-lint make backend-lint
  run_step full-ci-backend-mypy make backend-mypy
  run_step full-ci-schema make schema
  run_step full-ci-openapi make openapi
  run_step full-ci-tools make tools
  run_step full-ci-fresh-smoke make fresh-smoke
  run_step full-ci-pg18 make pg18
  run_step full-ci-fullstack env "QF_FULLSTACK_DIAGNOSTICS_FILE=$report_dir/fullstack-diagnostics.json" make fullstack
}

run_nightly() {
  require_ci_environment
  require_common_tooling
  run_step fresh-compose-roundtrip make fullstack
  run_step pg18-roundtrip make pg18
  run_step backup-restore bash -c 'cd backend && uv run --frozen pytest -q tests/test_event_migration_and_bootstrap.py -k "restore or roundtrip"'
  run_step e2e-a11y-visual-bundle make frontend-ci
}

run_agent_change() {
  require_ci_environment
  require_common_tooling
  run_step governance make governance
  run_step release-governance-static scripts/ci/release-governance-static-gate.sh
  run_step tool-registry-exact make tools
  run_step agent-contract-and-policy make backend-ci
  local review_locator="${QF_INDEPENDENT_REVIEW_REPORT:-$report_dir/independent-review-locator.json}"
  if [[ -z "${QF_INDEPENDENT_REVIEW_REPORT:-}" ]]; then
    run_step independent-review-locator scripts/ci/fetch-independent-review-report.sh "$commit" "$review_locator"
  fi
  run_step independent-review-report scripts/ci/verify-independent-review-report.sh "$review_locator" "$commit"
}

run_rc() {
  require_ci_environment
  require_common_tooling
  [[ -n "${QF_RELEASE_TAG:-}" ]] || {
    write_result release-tag 'QF_RELEASE_TAG is required' 2 'missing release tag'
    exit 2
  }
  [[ "$QF_RELEASE_TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+-alpha$ ]] || {
    write_result release-tag 'QF_RELEASE_TAG must be an alpha release tag' 2 'invalid release tag'
    exit 2
  }
  [[ "$(git -C "$repo_root" rev-parse "refs/tags/$QF_RELEASE_TAG^{commit}")" == "$commit" ]] || {
    write_result release-tag-target 'release tag must resolve to checkout HEAD' 2 'release tag target does not match checkout HEAD'
    exit 2
  }
  run_step remote-release-tag git -C "$repo_root" ls-remote --exit-code --refs origin "refs/tags/$QF_RELEASE_TAG"
  run_step release-governance-static scripts/ci/release-governance-static-gate.sh
  run_step p0-require-closed env "QF_RELEASE_COMMIT=$commit" scripts/p0-check.sh docs/治理/p0-blockers.yaml --require-closed
  run_step known-issues-review scripts/release-known-issues-check.sh
  run_step rc-full-ci make ci
  run_step fresh-compose-migration make fullstack
  run_step pg18-migration make pg18
  run_step backup-restore bash -c 'cd backend && uv run --frozen pytest -q tests/test_event_migration_and_bootstrap.py -k "restore or roundtrip"'
  run_step release-input-snapshot scripts/release-evidence.sh collect-inputs "$report_dir"
}

case "$gate" in
  pr-fast) run_pr_fast ;;
  main-full) run_main_full ;;
  nightly) run_nightly ;;
  agent-change) run_agent_change ;;
  rc) run_rc ;;
esac
