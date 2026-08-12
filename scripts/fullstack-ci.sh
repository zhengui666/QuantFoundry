#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
http_port="${QF_FULLSTACK_HTTP_PORT:-18080}"
case "$http_port" in
  '' | *[!0-9]*) printf '%s\n' 'QF_FULLSTACK_HTTP_PORT must be numeric.' >&2; exit 1 ;;
esac
if ((http_port < 1024 || http_port > 65535)); then
  printf '%s\n' 'QF_FULLSTACK_HTTP_PORT must be between 1024 and 65535.' >&2
  exit 1
fi
command -v docker >/dev/null
command -v openssl >/dev/null
command -v python3 >/dev/null
command -v node >/dev/null
command -v pnpm >/dev/null

required_node_version="v24.19.0"
required_pnpm_version="10.32.1"
actual_node_version="$(node --version)"
actual_pnpm_version="$(pnpm --version)"
[[ "$actual_node_version" == "$required_node_version" ]] || {
  printf 'Full-stack CI requires Node.js %s; got %s.\n' \
    "$required_node_version" "$actual_node_version" >&2
  exit 1
}
[[ "$actual_pnpm_version" == "$required_pnpm_version" ]] || {
  printf 'Full-stack CI requires pnpm %s; got %s.\n' \
    "$required_pnpm_version" "$actual_pnpm_version" >&2
  exit 1
}

fullstack_tmp="$(mktemp -d "${TMPDIR:-/tmp}/quantfoundry-fullstack.XXXXXX")"
environment_file="$fullstack_tmp/local.env"
bootstrap_output="$fullstack_tmp/bootstrap.json"
bootstrap_repeat_output="$fullstack_tmp/bootstrap-repeat.json"
seed_output="$fullstack_tmp/seed.json"
e2e_report="$fullstack_tmp/playwright-report.json"
project_name="qf-fullstack-$$"
phase="bootstrap"
export COMPOSE_PROJECT_NAME="$project_name"

cleanup() {
  local status="$?"
  trap - EXIT INT TERM
  if [[ "$status" != 0 ]]; then
    printf '%s\n' 'Full-stack Compose failure diagnostics:' >&2
    docker compose --project-name "$project_name" --profile local \
      --env-file "$environment_file" ps --all >&2 || true
    docker compose --project-name "$project_name" --profile local \
      --env-file "$environment_file" logs --no-color --tail 300 >&2 || true
    for service in api worker agent-worker scheduler; do
      docker compose --project-name "$project_name" --profile local \
        --env-file "$environment_file" ps --quiet "$service" \
        | xargs -r docker inspect --format '{{.Name}} {{json .State.Health}}' >&2 || true
    done
    if [[ -n "${QF_FULLSTACK_DIAGNOSTICS_FILE:-}" ]]; then
      python3 - "$QF_FULLSTACK_DIAGNOSTICS_FILE" "$status" "$phase" "$project_name" "$environment_file" <<'PY'
import json
import pathlib
import subprocess
import sys

output, exit_code, phase, project_name, environment_file = sys.argv[1:]


def compose(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "docker",
            "compose",
            "--project-name",
            project_name,
            "--profile",
            "local",
            "--env-file",
            environment_file,
            *args,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def service_state(service: str) -> dict[str, object]:
    container_ids = compose("ps", "--quiet", service).stdout.split()
    if len(container_ids) != 1:
        return {"state": "absent"}
    inspected = subprocess.run(
        ["docker", "inspect", container_ids[0]],
        check=False,
        capture_output=True,
        text=True,
    )
    if inspected.returncode != 0:
        return {"state": "inspect-unavailable"}
    state = json.loads(inspected.stdout)[0].get("State", {})
    health = state.get("Health", {})
    return {
        "state": state.get("Status"),
        "exit_code": state.get("ExitCode"),
        "health": health.get("Status"),
    }


diagnostics = {
    "exit_code": int(exit_code),
    "phase": phase,
    "services": {
        service: service_state(service)
        for service in ("postgres", "local-provider", "api", "worker", "agent-worker", "scheduler", "frontend")
    },
}
e2e_report = pathlib.Path(environment_file).with_name("playwright-report.json")
if e2e_report.is_file():
    playwright = json.loads(e2e_report.read_text(encoding="utf-8"))
    failed_tests: list[dict[str, object]] = []
    error_categories: dict[str, int] = {}

    def classify(message: object) -> str:
        value = message if isinstance(message, str) else ""
        if "Executable doesn't exist" in value or "browserType.launch" in value:
            return "browser-launch"
        if "ERR_CONNECTION_REFUSED" in value or "ECONNREFUSED" in value:
            return "connection-refused"
        if "Timeout" in value or "timeout" in value:
            return "timeout"
        if "snapshot" in value.lower():
            return "visual-snapshot"
        return "assertion-or-runtime"

    def collect(suite: dict[str, object], ancestors: list[str]) -> None:
        suite_title = suite.get("title")
        lineage = [*ancestors, suite_title] if isinstance(suite_title, str) and suite_title else ancestors
        for spec in suite.get("specs", []):
            if not isinstance(spec, dict):
                continue
            spec_title = spec.get("title")
            for test in spec.get("tests", []):
                if not isinstance(test, dict):
                    continue
                results = test.get("results", [])
                statuses = [result.get("status") for result in results if isinstance(result, dict)]
                if statuses and all(status == "passed" for status in statuses):
                    continue
                failed_tests.append(
                    {
                        "title": " > ".join([*lineage, spec_title]) if isinstance(spec_title, str) else " > ".join(lineage),
                        "status": statuses[-1] if statuses else "not-run",
                    }
                )
                for result in results:
                    if isinstance(result, dict) and result.get("status") != "passed":
                        errors = result.get("errors")
                        messages = [
                            error.get("message")
                            for error in errors
                            if isinstance(error, dict)
                        ] if isinstance(errors, list) else []
                        if not messages and isinstance(result.get("error"), dict):
                            messages = [result["error"].get("message")]
                        category = classify(messages[0] if messages else None)
                        error_categories[category] = error_categories.get(category, 0) + 1
        for child in suite.get("suites", []):
            if isinstance(child, dict):
                collect(child, lineage)

    for suite in playwright.get("suites", []):
        if isinstance(suite, dict):
            collect(suite, [])
    diagnostics["playwright"] = {
        "failed_tests": failed_tests,
        "error_category_counts": error_categories,
    }
path = pathlib.Path(output)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(diagnostics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
    fi
  fi
  if [[ "$status" != 0 && "${QF_FULLSTACK_KEEP_FAILED:-0}" == "1" ]]; then
    printf 'Preserving failed full-stack Compose project: %s\n' "$project_name" >&2
    exit "$status"
  fi
  docker compose --project-name "$project_name" --profile local \
    --env-file "$environment_file" down --volumes --remove-orphans >/dev/null 2>&1 || true
  case "$fullstack_tmp" in
    "${TMPDIR:-/tmp}"/quantfoundry-fullstack.*) find "$fullstack_tmp" -depth -delete ;;
    *) printf 'Refusing unexpected full-stack temp cleanup path: %s\n' "$fullstack_tmp" >&2 ;;
  esac
  exit "$status"
}
trap cleanup EXIT INT TERM

umask 077
QF_POSTGRES_PASSWORD="$(openssl rand -hex 24)"
QF_CREDENTIAL_ENCRYPTION_KEY="$(openssl rand -base64 32 | tr '+/' '-_' | tr -d '\n')"
QF_LOCAL_PROVIDER_API_KEY="$(openssl rand -hex 24)"
QF_LOCAL_DATA_CREDENTIAL="$(openssl rand -hex 24)"
export QF_ENV=local
export QF_ENVIRONMENT=local
export QF_GIT_COMMIT=fullstack-local
export QF_BUILD_ID="fullstack-ci"
export QF_POSTGRES_DB=quantfoundry
export QF_POSTGRES_USER=quantfoundry
export QF_POSTGRES_PASSWORD
export QF_ARTIFACT_ROOT=/var/lib/quantfoundry/artifacts
export QF_DATA_ROOT=/var/lib/quantfoundry/data
export QF_AGENT_PROVIDER=openai-compatible
export QF_AGENT_MODEL=qf-local-v1
export QF_OPENAI_BASE_URL=http://local-provider:8011/v1
export QF_OPENAI_MODELS=qf-local-v1
export QF_OPENAI_DISPLAY_NAME='QuantFoundry local deterministic provider'
export QF_LOCAL_PROVIDER_API_KEY
export QF_LOCAL_DATA_CREDENTIAL
export QF_ENABLE_LOCAL_DETERMINISTIC_PROVIDER=1
export QF_CREDENTIAL_ENCRYPTION_KEY_ID=fullstack-local-key-v1
export QF_CREDENTIAL_ENCRYPTION_KEY
export QF_LOG_LEVEL=INFO
export QF_HTTP_PORT="$http_port"

for name in \
  QF_ENV QF_ENVIRONMENT QF_GIT_COMMIT QF_BUILD_ID QF_POSTGRES_DB \
  QF_POSTGRES_USER QF_POSTGRES_PASSWORD QF_ARTIFACT_ROOT QF_DATA_ROOT \
  QF_AGENT_PROVIDER QF_AGENT_MODEL QF_OPENAI_BASE_URL QF_OPENAI_MODELS \
  QF_OPENAI_DISPLAY_NAME QF_LOCAL_PROVIDER_API_KEY QF_LOCAL_DATA_CREDENTIAL \
  QF_ENABLE_LOCAL_DETERMINISTIC_PROVIDER QF_CREDENTIAL_ENCRYPTION_KEY_ID \
  QF_CREDENTIAL_ENCRYPTION_KEY QF_LOG_LEVEL QF_HTTP_PORT; do
  printf '%s=%s\n' "$name" "${!name}" >> "$environment_file"
done

QF_ENV_FILE="$environment_file" \
QF_BOOTSTRAP_OUTPUT_FILE="$bootstrap_output" \
QF_BOOTSTRAP_OWNER_EMAIL=fullstack-owner@local.invalid \
QF_BOOTSTRAP_WORKSPACE_NAME='QuantFoundry Full Stack' \
  "$repo_root/scripts/bootstrap-local.sh"

phase="bootstrap-repeat"
QF_ENV_FILE="$environment_file" \
QF_BOOTSTRAP_OUTPUT_FILE="$bootstrap_repeat_output" \
QF_BOOTSTRAP_OWNER_EMAIL=fullstack-owner@local.invalid \
QF_BOOTSTRAP_WORKSPACE_NAME='QuantFoundry Full Stack' \
  "$repo_root/scripts/bootstrap-local.sh"
python3 "$repo_root/scripts/bootstrap_result_check.py" \
  "$bootstrap_output" "$bootstrap_repeat_output"

phase="security-verification"
security_counts="$(
  docker compose --project-name "$project_name" --profile local \
    --env-file "$environment_file" exec -T postgres psql \
    --username quantfoundry --dbname quantfoundry --tuples-only --no-align \
    --command "
      SELECT
        (SELECT count(*) FROM session_tokens
          WHERE length(token_sha256) = 64)::text || ':' ||
        (SELECT count(*) FROM session_tokens
          WHERE revoked_at IS NULL)::text || ':' ||
        (SELECT count(*) FROM model_provider_connections
          WHERE octet_length(ciphertext) > 0
            AND octet_length(nonce) > 0
            AND key_id IS NOT NULL)::text;
    "
)"
[[ "$security_counts" == "2:1:2" ]] || {
  printf 'Expected two hashed/one active session and two encrypted provider connections; got %s.\n' \
    "$security_counts" >&2
  exit 1
}
printf '%s\n' 'Bootstrap persisted only token verifiers and encrypted provider credentials.'

application_url="http://127.0.0.1:${http_port}"
phase="seed"
docker compose --project-name "$project_name" --profile local \
  --env-file "$environment_file" exec -T api \
  python /workspace/scripts/fullstack_seed.py \
  --application-url "$application_url" \
  < "$bootstrap_repeat_output" > "$seed_output"

phase="frontend-compose"
docker compose --project-name "$project_name" --profile local \
  --env-file "$environment_file" up --build --detach --wait frontend

json_field() {
  python3 -c 'import json,sys; value=json.load(open(sys.argv[1], encoding="utf-8"))[sys.argv[2]]; assert isinstance(value,str) and value; print(value)' "$seed_output" "$1"
}
QF_FULLSTACK_BASE_URL="$(json_field QF_FULLSTACK_BASE_URL)"
QF_FULLSTACK_BEARER_TOKEN="$(json_field QF_FULLSTACK_BEARER_TOKEN)"
QF_FULLSTACK_FACTOR_ID="$(json_field QF_FULLSTACK_FACTOR_ID)"
QF_FULLSTACK_SNAPSHOT_ID="$(json_field QF_FULLSTACK_SNAPSHOT_ID)"
QF_FULLSTACK_COST_MODEL_ID="$(json_field QF_FULLSTACK_COST_MODEL_ID)"
QF_FULLSTACK_VALIDATION_POLICY_ID="$(json_field QF_FULLSTACK_VALIDATION_POLICY_ID)"
export QF_FULLSTACK_BASE_URL QF_FULLSTACK_BEARER_TOKEN QF_FULLSTACK_FACTOR_ID
export QF_FULLSTACK_SNAPSHOT_ID QF_FULLSTACK_COST_MODEL_ID
export QF_FULLSTACK_VALIDATION_POLICY_ID

if grep -En 'page\.route|context\.route|browserContext\.route' \
  "$repo_root/frontend/e2e/fullstack.spec.ts"; then
  printf '%s\n' 'Full-stack Playwright must not install route mocks.' >&2
  exit 1
fi

printf 'Full-stack seed ready: factor=%s snapshot=%s cost=%s validation_policy=%s\n' \
  "$QF_FULLSTACK_FACTOR_ID" "$QF_FULLSTACK_SNAPSHOT_ID" \
  "$QF_FULLSTACK_COST_MODEL_ID" "$QF_FULLSTACK_VALIDATION_POLICY_ID"
run_frontend_step() {
  local step="$1"
  phase="frontend-${step}"
  pnpm --dir "$repo_root/frontend" run "$step"
}

run_frontend_step codegen:check
run_frontend_step public-id:check
run_frontend_step format:check
run_frontend_step lint
run_frontend_step typecheck
run_frontend_step test
phase="frontend-test:e2e"
if ! pnpm --dir "$repo_root/frontend" exec playwright test --reporter=json > "$e2e_report"; then
  exit 1
fi
run_frontend_step build
run_frontend_step bundle:check
run_frontend_step storybook:build
printf '%s\n' 'Full-stack frontend CI passed with all six QF_FULLSTACK_* values.'
