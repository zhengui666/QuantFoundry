#!/usr/bin/env bash
set -euo pipefail

script_repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
repo_root="${QF_CI_REPO_ROOT:-$script_repo_root}"
orchestrator_root="${QF_CI_TRUSTED_ROOT:-$script_repo_root}"
export QF_CI_REPO_ROOT="$repo_root"
trusted_path="/usr/local/bin:/usr/bin:/bin"
declare -A trusted_commands=()
gate="${1:-}"
report_dir="${QF_CI_REPORT_DIR:-}"
orchestrator_commit="$(git -C "$orchestrator_root" rev-parse HEAD 2>/dev/null || true)"
trusted_commit="${QF_CI_TRUSTED_COMMIT:-}"

usage() {
  printf '%s\n' 'usage: scripts/ci/run-gate.sh <pr-fast|main-full|nightly|agent-change|rc> [REPORT_DIR]' >&2
  exit 2
}

[[ "$gate" =~ ^(pr-fast|main-full|nightly|agent-change|rc)$ ]] || usage
if [[ "${QF_CI_UNTRUSTED_CANDIDATE:-}" == 1 && "$gate" != nightly ]]; then
  printf '%s\n' 'untrusted candidate mode is permitted only for the nightly gate' >&2
  exit 2
fi
if [[ -n "${2:-}" ]]; then
  report_dir="$2"
fi
if [[ -z "$report_dir" ]]; then
  report_dir="$(mktemp -d "${TMPDIR:-/tmp}/quantfoundry-${gate}.XXXXXX")"
else
  [[ ! -e "$report_dir" && ! -L "$report_dir" ]] || {
    printf '%s\n' '{"result":"invalid","reason":"report directory must not pre-exist"}' >&2
    exit 2
  }
  umask 077
  mkdir "$report_dir"
fi
chmod 700 "$report_dir"
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
import os
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
import os
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
    "github_run_id": int(os.environ["GITHUB_RUN_ID"])
    if os.environ.get("GITHUB_RUN_ID", "").isdigit()
    else None,
    "github_run_attempt": int(os.environ["GITHUB_RUN_ATTEMPT"])
    if os.environ.get("GITHUB_RUN_ATTEMPT", "").isdigit()
    else None,
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
    QF_CI_REDACTION_PG18_DATABASE_URL="${QF_PG18_CI_BASE_DATABASE_URL:-}" \
    QF_CI_REDACTION_POSTGRES_PASSWORD="${QF_POSTGRES_PASSWORD:-}" \
    python3 - "$@" <<'PY'
import os
import shlex
import sys

secrets = [
    os.environ.get("QF_CI_REDACTION_DATABASE_URL", ""),
    os.environ.get("QF_CI_REDACTION_ALEMBIC_URL", ""),
    os.environ.get("QF_CI_REDACTION_PG18_DATABASE_URL", ""),
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
    "QF_LOCAL_DATA_CREDENTIAL", "QF_PG18_CI_BASE_DATABASE_URL",
} and value]
for line in sys.stdin:
    for secret in secrets:
        line = line.replace(secret, "[REDACTED]")
    sys.stdout.write(line)
'
  }
  local step_home="$report_dir/home/$name" step_tmp="$report_dir/tmp/$name"
  mkdir -p "$step_home" "$step_tmp" "$step_home/.config" "$step_home/.docker"
  local -a isolated_env=(
    env -i
    "HOME=$step_home"
    "PATH=$trusted_path"
    "TMPDIR=$step_tmp"
    "XDG_CONFIG_HOME=$step_home/.config"
    "XDG_CACHE_HOME=$step_home/.cache"
    "DOCKER_CONFIG=$step_home/.docker"
    "GIT_CONFIG_NOSYSTEM=1"
    "GIT_CONFIG_GLOBAL=/dev/null"
    "GIT_TERMINAL_PROMPT=0"
  )
  local variable_name
  for variable_name in \
    CI GITHUB_ACTIONS GITHUB_REF GITHUB_REPOSITORY GITHUB_RUN_ATTEMPT GITHUB_RUN_ID \
    GITHUB_SERVER_URL GITHUB_SHA QF_ALEMBIC_URL QF_BUILD_ID QF_CI_DISPOSABLE_DATABASE \
    QF_CI_REPO_ROOT \
    QF_CODEX_BASE_URL QF_CODEX_DISPLAY_NAME QF_CODEX_MODELS QF_CONTROL_DB_URL \
    QF_DATABASE_URL QF_ENV QF_ENVIRONMENT QF_FULLSTACK_DIAGNOSTICS_FILE QF_GIT_COMMIT \
    QF_INDEPENDENT_REVIEW_REPORT QF_LOCAL_DATA_CREDENTIAL QF_LOCAL_PROVIDER_API_KEY \
    QF_PG18_CI_BASE_DATABASE_URL QF_PG18_CI_CHILD_STOP_TIMEOUT_SECONDS \
    QF_PG18_CI_READINESS_TIMEOUT_SECONDS QF_RELEASE_COMMIT QF_RELEASE_GOVERNANCE_ROOT \
    QF_RELEASE_REPO_ROOT QF_RELEASE_TAG QF_RELEASE_TRUSTED_VERIFIER_COMMIT \
    QF_RELEASE_TRUSTED_VERIFIER_ROOT QF_SKIP_AUTO_CREATE; do
    if [[ -n "${!variable_name+x}" ]]; then
      isolated_env+=("$variable_name=${!variable_name}")
    fi
  done
  if [[ "${QF_CI_ALLOW_REVIEW_CREDENTIALS:-}" == 1 ]]; then
    [[ -n "${GITHUB_TOKEN:-}" ]] && isolated_env+=("GITHUB_TOKEN=$GITHUB_TOKEN")
    [[ -n "${GH_TOKEN:-}" ]] && isolated_env+=("GH_TOKEN=$GH_TOKEN")
  fi
  local status=0 redactor_status=0
  set +e
  (cd "$repo_root" && "${isolated_env[@]}" "$@") 2>&1 \
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
  local candidate_worktree trusted_worktree candidate_common trusted_common
  candidate_worktree="$(git -C "$repo_root" rev-parse --show-toplevel)"
  trusted_worktree="$(git -C "$orchestrator_root" rev-parse --show-toplevel)"
  candidate_common="$(git -C "$repo_root" rev-parse --path-format=absolute --git-common-dir)"
  trusted_common="$(git -C "$orchestrator_root" rev-parse --path-format=absolute --git-common-dir)"
  [[ "$candidate_worktree" != "$trusted_worktree" && "$candidate_common" != "$trusted_common" ]] || {
    write_result trusted-orchestrator 'trusted orchestrator must be an independent checkout' 2 'candidate and trusted code share a worktree or Git database'
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
  local hidden_flags
  hidden_flags="$(git -C "$orchestrator_root" ls-files -v)" || {
    write_result trusted-orchestrator 'trusted orchestrator file flags can be inspected' 2 'Git hidden-file flag inspection failed'
    exit 2
  }
  if printf '%s\n' "$hidden_flags" | awk '$1 ~ /^[a-zS]$/ { found = 1 } END { exit found ? 0 : 1 }'; then
    write_result trusted-orchestrator 'trusted orchestrator has no hidden tracked changes' 2 'trusted orchestrator checkout has skip-worktree or assume-unchanged files'
    exit 2
  fi
}

trusted_step() {
  require_trusted_orchestrator
  local name="$1"
  shift
  local snapshot="$report_dir/trusted/$name"
  [[ ! -e "$snapshot" && ! -L "$snapshot" ]] || {
    write_result "$name" 'trusted snapshot path must not pre-exist' 2 'trusted snapshot path collision'
    exit 2
  }
  mkdir -p "$snapshot"
  git -C "$orchestrator_root" archive --format=tar "$trusted_commit" | tar -xf - -C "$snapshot"
  chmod -R a-w "$snapshot"
  local saved_repo_root="$repo_root"
  local saved_verifier_root="${QF_RELEASE_TRUSTED_VERIFIER_ROOT-}"
  local saved_verifier_commit="${QF_RELEASE_TRUSTED_VERIFIER_COMMIT-}"
  repo_root="$snapshot"
  export QF_RELEASE_TRUSTED_VERIFIER_ROOT="$snapshot"
  export QF_RELEASE_TRUSTED_VERIFIER_COMMIT="$trusted_commit"
  local -a args=()
  local argument
  for argument in "$@"; do
    case "$argument" in
      "$orchestrator_root"/*)
        args+=("$snapshot/${argument#"$orchestrator_root/"}")
        ;;
      QF_RELEASE_TRUSTED_VERIFIER_ROOT=*)
        args+=("QF_RELEASE_TRUSTED_VERIFIER_ROOT=$snapshot")
        ;;
      *)
        args+=("$argument")
        ;;
    esac
  done
  run_step "$name" "${args[@]}"
  repo_root="$saved_repo_root"
  if [[ -n "$saved_verifier_root" ]]; then
    export QF_RELEASE_TRUSTED_VERIFIER_ROOT="$saved_verifier_root"
  else
    unset QF_RELEASE_TRUSTED_VERIFIER_ROOT
  fi
  if [[ -n "$saved_verifier_commit" ]]; then
    export QF_RELEASE_TRUSTED_VERIFIER_COMMIT="$saved_verifier_commit"
  else
    unset QF_RELEASE_TRUSTED_VERIFIER_COMMIT
  fi
}

require_command() {
  local command_name="$1"
  local command_path directory
  command_path="$(PATH="$trusted_path" command -v "$command_name" 2>/dev/null || true)"
  if [[ ! "$command_path" = /* || ! -x "$command_path" || -L "$command_path" ]]; then
    write_result "host-${command_name}" "command -v ${command_name}" 127 "missing host dependency: ${command_name}"
    exit 127
  fi
  directory="$command_path"
  while [[ "$directory" != / ]]; do
    [[ ! -w "$directory" ]] || {
      write_result "host-${command_name}" "command -v ${command_name}" 126 "host dependency path is writable: ${command_path}"
      exit 126
    }
    directory="$(dirname "$directory")"
  done
  trusted_commands["$command_name"]="$command_path"
  case ":$trusted_path:" in
    *":$(dirname "$command_path"):"*) ;;
    *) trusted_path="$trusted_path:$(dirname "$command_path")" ;;
  esac
}

require_common_tooling() {
  require_command git
  require_command /usr/bin/python3.12
  require_command uv
  require_command node
  require_command pnpm
  require_command docker
  require_command shellcheck
  require_command actionlint
  if ! "${trusted_commands[docker]}" compose version >/dev/null 2>&1; then
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
  run_step ci-disposable-database bash -c 'cd backend && uv run --frozen python ../scripts/ci/verify-disposable-ci-database.py "$QF_DATABASE_URL"'
}

run_pr_fast() {
  require_common_tooling
  require_ci_environment
  run_step governance make governance
  trusted_step release-governance-static "$orchestrator_root/scripts/ci/release-governance-static-gate.sh"
  run_step platform make platform
  run_step hygiene make hygiene
  run_step migration scripts/ci.sh migration
  run_step schema make schema
  run_step contracts make contract
  run_step backend-fast make backend-ci
  run_step frontend-fast make frontend-ci
}

run_main_full() {
  require_common_tooling
  require_ci_environment
  trusted_step p0-registry-snapshot env \
    QF_RELEASE_REPO_ROOT="$repo_root" \
    QF_RELEASE_TRUSTED_VERIFIER_ROOT="$orchestrator_root" \
    QF_RELEASE_TRUSTED_VERIFIER_COMMIT="$trusted_commit" \
    "$orchestrator_root/scripts/p0-check.sh" "$repo_root/docs/治理/p0-blockers.yaml" --offline-report
  trusted_step release-governance-static "$orchestrator_root/scripts/ci/release-governance-static-gate.sh"
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
  require_common_tooling
  require_ci_environment
  run_step fresh-compose-roundtrip make fullstack
  run_step pg18-roundtrip make pg18
  run_step backup-restore bash -c 'cd backend && uv run --frozen pytest -q tests/test_event_migration_and_bootstrap.py -k "restore or roundtrip"'
  run_step e2e-a11y-visual-bundle make frontend-ci
}

run_agent_change() {
  local review_token="${GITHUB_TOKEN:-}" review_gh_token="${GH_TOKEN:-}"
  unset GITHUB_TOKEN GH_TOKEN
  require_common_tooling
  require_ci_environment
  run_step governance make governance
  trusted_step release-governance-static "$orchestrator_root/scripts/ci/release-governance-static-gate.sh"
  run_step tool-registry-exact make tools
  run_step agent-contract-and-policy make backend-ci
  local review_locator="${QF_INDEPENDENT_REVIEW_REPORT:-$report_dir/independent-review-locator.json}"
  if [[ -z "${QF_INDEPENDENT_REVIEW_REPORT:-}" ]]; then
    trusted_step independent-review-locator "$orchestrator_root/scripts/ci/fetch-independent-review-report.sh" "$commit" "$review_locator"
  fi
  require_trusted_orchestrator
  [[ -n "$review_token" && -n "$review_gh_token" ]] || {
    write_result independent-review-report 'GITHUB_TOKEN and GH_TOKEN are required for independent review verification' 2 'missing independent review verification credentials'
    exit 2
  }
  export GITHUB_TOKEN="$review_token" GH_TOKEN="$review_gh_token"
  export QF_CI_ALLOW_REVIEW_CREDENTIALS=1
  trusted_step independent-review-report "$orchestrator_root/scripts/ci/verify-independent-review-report.sh" "$review_locator" "$commit"
  unset QF_CI_ALLOW_REVIEW_CREDENTIALS GITHUB_TOKEN GH_TOKEN
}

run_agent_change_verify() {
  local review_token="${GITHUB_TOKEN:-}" review_gh_token="${GH_TOKEN:-}"
  local review_locator="${QF_INDEPENDENT_REVIEW_REPORT:-}"
  local review_attestation="${QF_INDEPENDENT_REVIEW_ATTESTATION:-}"
  require_trusted_orchestrator
  [[ -n "$review_locator" ]] || {
    write_result independent-review-report 'QF_INDEPENDENT_REVIEW_REPORT is required' 2 'missing independent review verification artifact'
    exit 2
  }
  [[ -f "$review_attestation" ]] || {
    write_result independent-review-attestation 'independent review attestation is required' 2 'missing independent review attestation artifact'
    exit 2
  }
  python3 - "$review_locator" "$review_attestation" "$commit" <<'PY'
import hashlib
import json
import pathlib
import sys

locator, attestation, commit = map(pathlib.Path, sys.argv[1:])
payload = json.loads(locator.read_text(encoding="utf-8"))
proof = json.loads(attestation.read_text(encoding="utf-8"))
if payload.get("commit") != str(commit):
    raise SystemExit("independent review locator commit mismatch")
if proof.get("schema_version") != "1.0.0" or proof.get("commit") != str(commit):
    raise SystemExit("independent review attestation commit binding is invalid")
if proof.get("result") != "verified" or proof.get("locator_sha256") != hashlib.sha256(locator.read_bytes()).hexdigest():
    raise SystemExit("independent review attestation does not bind the downloaded locator")
PY
  [[ -n "$review_token" && -n "$review_gh_token" ]] || {
    write_result independent-review-report 'GITHUB_TOKEN and GH_TOKEN are required for independent review verification' 2 'missing independent review verification credentials'
    exit 2
  }
  export GITHUB_TOKEN="$review_token" GH_TOKEN="$review_gh_token"
  export QF_CI_ALLOW_REVIEW_CREDENTIALS=1
  trusted_step release-governance-static env \
    QF_RELEASE_GOVERNANCE_ROOT="$repo_root" \
    "$orchestrator_root/scripts/ci/release-governance-static-gate.sh" --skip-fixtures
  trusted_step independent-review-report \
    "$orchestrator_root/scripts/ci/verify-independent-review-report.sh" \
    "$review_locator" "$commit"
  unset QF_CI_ALLOW_REVIEW_CREDENTIALS GITHUB_TOKEN GH_TOKEN
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
  run_step remote-release-tag python3 -c '
import subprocess
import sys

tag, expected = sys.argv[1:]
refs = subprocess.check_output(
    ["git", "ls-remote", "--exit-code", "https://github.com/zhengui666/QuantFoundry.git", f"refs/tags/{tag}", f"refs/tags/{tag}^{{}}"],
    text=True,
)
direct = peeled = ""
for line in refs.splitlines():
    sha, ref = line.split("\t", 1)
    if ref == f"refs/tags/{tag}":
        direct = sha
    elif ref == f"refs/tags/{tag}^{{}}":
        peeled = sha
remote = peeled or direct
if remote != expected:
    raise SystemExit(f"remote release tag target {remote} does not match checkout {expected}")
' "$QF_RELEASE_TAG" "$commit"
  trusted_step release-governance-static "$orchestrator_root/scripts/ci/release-governance-static-gate.sh"
  trusted_step p0-require-closed-except-supply-chain env "QF_RELEASE_COMMIT=$commit" "$orchestrator_root/scripts/p0-check.sh" "$repo_root/docs/治理/p0-blockers.yaml" --require-closed-except-supply-chain
  trusted_step known-issues-review "$orchestrator_root/scripts/release-known-issues-check.sh"
  run_step rc-full-ci make ci
  run_step fresh-compose-migration make fullstack
  run_step pg18-migration make pg18
  run_step backup-restore bash -c 'cd backend && uv run --frozen pytest -q tests/test_event_migration_and_bootstrap.py -k "restore or roundtrip"'
  run_step release-input-snapshot scripts/release-evidence.sh collect-inputs "$report_dir"
}

if [[ "${QF_CI_UNTRUSTED_CANDIDATE:-}" != 1 ]]; then
  require_trusted_orchestrator
fi

case "$gate" in
  pr-fast) run_pr_fast ;;
  main-full) run_main_full ;;
  nightly) run_nightly ;;
  agent-change)
    if [[ "${QF_AGENT_CHANGE_VERIFY_ONLY:-}" == 1 ]]; then
      run_agent_change_verify
    else
      run_agent_change
    fi
    ;;
  rc) run_rc ;;
esac
