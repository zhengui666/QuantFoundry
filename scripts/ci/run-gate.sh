#!/usr/bin/env bash
set -euo pipefail

script_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
repo_root="${QF_CI_REPO_ROOT:-$script_repo_root}"
orchestrator_root="${QF_CI_TRUSTED_ROOT:-$script_repo_root}"
gate="${1:-}"
report_dir="${QF_CI_REPORT_DIR:-}"
orchestrator_commit="$(git -C "$orchestrator_root" rev-parse HEAD 2>/dev/null || true)"
trusted_commit="${QF_CI_TRUSTED_COMMIT:-}"

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
mkdir -p "$report_dir"
chmod 700 "$report_dir"
report_dir="$(mktemp -d "$report_dir/quantfoundry-${gate}.XXXXXX")"
mkdir -p "$report_dir/logs"
chmod 700 "$report_dir/logs"
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
  set +e
  python3 - "$report_dir/result.json" "$gate" "$commit" "$ref" "$started_at" "$status" "$results_file" "$report_dir/fullstack-diagnostics.json" <<'PY'
import json
import pathlib
import sys

output = pathlib.Path(sys.argv[1])
steps = []
reporting_errors = []
try:
    lines = pathlib.Path(sys.argv[7]).read_text(encoding="utf-8").splitlines()
except OSError as error:
    lines = []
    reporting_errors.append(f"cannot read step records: {error}")
for line_number, line in enumerate(lines, 1):
    try:
        steps.append(json.loads(line))
    except (json.JSONDecodeError, TypeError) as error:
        reporting_errors.append(f"invalid step record at line {line_number}: {error}")
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
    try:
        result["diagnostics"] = {"fullstack": json.loads(diagnostics_path.read_text(encoding="utf-8"))}
    except (OSError, json.JSONDecodeError) as error:
        reporting_errors.append(f"invalid fullstack diagnostics: {error}")
if reporting_errors:
    result["reporting_errors"] = reporting_errors
temporary = output.with_name(f".{output.name}.tmp")
temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
temporary.replace(output)
PY
  local report_status=$?
  set -e
  if [[ "$report_status" != 0 ]]; then
    printf '%s\n' 'CI gate result reporting failed.' >&2
    [[ "$status" != 0 ]] || exit "$report_status"
  fi
  exit "$status"
}

trap 'status=$?; trap - EXIT; finish "$status"' EXIT

run_step() {
  local name="$1"
  shift
  local command_text
  command_text="$(
    QF_CI_REDACTION_DATABASE_URL="${QF_DATABASE_URL:-}" \
    QF_CI_REDACTION_ALEMBIC_URL="${QF_ALEMBIC_URL:-}" \
    QF_CI_REDACTION_POSTGRES_PASSWORD="${QF_POSTGRES_PASSWORD:-}" \
    python3 - "$@" <<'PY'
import os
import shlex
import sys

secrets = [
    os.environ.get("QF_CI_REDACTION_DATABASE_URL", ""),
    os.environ.get("QF_CI_REDACTION_ALEMBIC_URL", ""),
    os.environ.get("QF_CI_REDACTION_POSTGRES_PASSWORD", ""),
]
arguments = []
for argument in sys.argv[1:]:
    for secret in secrets:
        if secret:
            argument = argument.replace(secret, "[REDACTED]")
    arguments.append(shlex.quote(argument))
print(" ".join(arguments))
PY
  )"
  redact_ci_secrets() {
    python3 -c '
import os, sys
secrets = [value for name, value in os.environ.items() if name in {
    "GITHUB_TOKEN", "GH_TOKEN", "QF_CODEX_API_KEY", "QF_OPENAI_API_KEY",
    "QF_CREDENTIAL_ENCRYPTION_KEY", "QF_CREDENTIAL_FINGERPRINT_KEY",
    "QF_POSTGRES_PASSWORD", "PGPASSWORD", "QF_DATABASE_URL", "QF_ALEMBIC_URL",
    "QF_CONTROL_DB_URL", "QF_LOCAL_PROVIDER_API_KEY",
    "QF_LOCAL_DATA_CREDENTIAL",
} and value]
for line in sys.stdin:
    for secret in secrets:
        line = line.replace(secret, "[REDACTED]")
    sys.stdout.write(line)
'
  }
  local status=0 redactor_status=0
  set +e
  (cd "$repo_root" && "$@") 2>&1 \
    | redact_ci_secrets >"$report_dir/logs/$name.log"
  local -a pipeline_status=("${PIPESTATUS[@]}")
  status=${pipeline_status[0]:-1}
  redactor_status=${pipeline_status[1]:-1}
  if [[ "$status" == 0 && "$redactor_status" != 0 ]]; then
    status="$redactor_status"
  fi
  set -e
  write_result "$name" "$command_text" "$status"
  [[ "$status" == 0 ]] || exit "$status"
}

require_trusted_orchestrator() {
  [[ "$trusted_commit" =~ ^[0-9a-f]{40}$ && "$trusted_commit" != "0000000000000000000000000000000000000000" ]] || {
    write_result trusted-orchestrator 'trusted orchestrator commit must be an explicit full SHA' 2 'missing trusted orchestrator commit anchor'
    exit 2
  }
  [[ -n "$orchestrator_commit" && "$orchestrator_commit" == "$trusted_commit" ]] || {
    write_result trusted-orchestrator 'trusted orchestrator checkout is required' 2 'missing trusted orchestrator checkout'
    exit 2
  }
  [[ "$(git -C "$orchestrator_root" rev-parse HEAD)" == "$orchestrator_commit" ]] || {
    write_result trusted-orchestrator 'trusted orchestrator commit changed' 2 'trusted orchestrator checkout was modified'
    exit 2
  }
  git -C "$orchestrator_root" diff --quiet || {
    write_result trusted-orchestrator 'trusted orchestrator worktree is clean' 2 'trusted orchestrator checkout was modified'
    exit 2
  }
  [[ -z "$(git -C "$orchestrator_root" status --porcelain --untracked-files=all)" ]] || {
    write_result trusted-orchestrator 'trusted orchestrator has no untracked files' 2 'trusted orchestrator checkout was modified'
    exit 2
  }
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
  if [[ "${QF_CI_DISPOSABLE_DATABASE:-}" != 1 || "${QF_DATABASE_URL:-}" != postgresql+psycopg://* || "${QF_ALEMBIC_URL:-}" != "$QF_DATABASE_URL" || "${QF_SKIP_AUTO_CREATE:-}" != 1 ]]; then
    write_result ci-postgres 'QF_CI_DISPOSABLE_DATABASE/QF_DATABASE_URL/QF_ALEMBIC_URL/QF_SKIP_AUTO_CREATE are required' 2 'missing explicitly disposable real PostgreSQL CI configuration'
    exit 2
  fi
  run_step ci-disposable-database "$orchestrator_root/scripts/ci/verify-disposable-ci-database.py" "$QF_DATABASE_URL"
}

run_pr_fast() {
  require_ci_environment
  require_common_tooling
  run_step governance make governance
  run_step release-governance-static "$orchestrator_root/scripts/ci/release-governance-static-gate.sh"
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
  run_step release-governance-static "$orchestrator_root/scripts/ci/release-governance-static-gate.sh"
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
  require_trusted_orchestrator
  run_step release-governance-static "$orchestrator_root/scripts/ci/release-governance-static-gate.sh"
  run_step tool-registry-exact make tools
  run_step agent-contract-and-policy make backend-ci
  local review_locator="${QF_INDEPENDENT_REVIEW_REPORT:-$report_dir/independent-review-locator.json}"
  if [[ -z "${QF_INDEPENDENT_REVIEW_REPORT:-}" ]]; then
    run_step independent-review-locator "$orchestrator_root/scripts/ci/fetch-independent-review-report.sh" "$commit" "$review_locator"
  fi
  require_trusted_orchestrator
  run_step independent-review-report "$orchestrator_root/scripts/ci/verify-independent-review-report.sh" "$review_locator" "$commit"
}

verify_remote_release_tag() {
  local refs remote_commit
  refs="$(git -C "$repo_root" ls-remote --exit-code origin \
    "refs/tags/$QF_RELEASE_TAG" "refs/tags/$QF_RELEASE_TAG^{}")" || return 1
  remote_commit="$(printf '%s\n' "$refs" | awk -v tag="$QF_RELEASE_TAG" '
    $2 == "refs/tags/" tag "^{}" { peeled = $1 }
    $2 == "refs/tags/" tag { direct = $1 }
    END { print peeled != "" ? peeled : direct }
  ')"
  [[ -n "$remote_commit" && "$remote_commit" == "$commit" ]] || {
    printf 'remote release tag target %s does not match checkout %s\n' "$remote_commit" "$commit" >&2
    return 1
  }
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
  run_step remote-release-tag verify_remote_release_tag
  run_step release-governance-static "$orchestrator_root/scripts/ci/release-governance-static-gate.sh"
  run_step p0-require-closed-except-supply-chain env "QF_RELEASE_COMMIT=$commit" "$orchestrator_root/scripts/p0-check.sh" "$repo_root/docs/治理/p0-blockers.yaml" --require-closed-except-supply-chain
  run_step known-issues-review "$orchestrator_root/scripts/release-known-issues-check.sh"
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
