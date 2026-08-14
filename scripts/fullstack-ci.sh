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
seed_output="$fullstack_tmp/seed.json"
project_name="qf-fullstack-$$"
export COMPOSE_PROJECT_NAME="$project_name"
keep_failed="${QF_FULLSTACK_KEEP_FAILED:-0}"

cleanup() {
  local status="$?"
  trap - EXIT INT TERM
  if [[ "$status" != 0 && "$keep_failed" == "1" ]]; then
    printf 'Full-stack failure preserved for diagnosis: project=%s temp=%s\n' \
      "$project_name" "$fullstack_tmp" >&2
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
QF_CODEX_API_KEY="$QF_LOCAL_PROVIDER_API_KEY"
export QF_ENV=local
export QF_ENVIRONMENT=local
export QF_GIT_COMMIT=fullstack-local
export QF_BUILD_ID="fullstack-ci"
export QF_POSTGRES_DB=quantfoundry
export QF_POSTGRES_USER=quantfoundry
export QF_POSTGRES_PASSWORD
QF_FULLSTACK_DATABASE_URL="postgresql+psycopg://${QF_POSTGRES_USER}:${QF_POSTGRES_PASSWORD}@postgres:5432/${QF_POSTGRES_DB}"
export QF_ARTIFACT_ROOT=/var/lib/quantfoundry/artifacts
export QF_DATA_ROOT=/var/lib/quantfoundry/data
export QF_AGENT_PROVIDER=remote-codex
export QF_AGENT_MODEL=qf-local-v1
export QF_CODEX_RUNTIME_ID=CODEX-DEFAULT
export QF_CODEX_REMOTE_INSTANCE_ID=CODEX-DEFAULT
export QF_CODEX_BASE_URL=http://local-provider:8011/v1
export QF_CODEX_MODEL=qf-local-v1
export QF_CODEX_MODELS=qf-local-v1
export QF_CODEX_DISPLAY_NAME='QuantFoundry Remote Codex local transport'
export QF_CODEX_API_KEY
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
  QF_AGENT_PROVIDER QF_AGENT_MODEL QF_CODEX_RUNTIME_ID \
  QF_CODEX_REMOTE_INSTANCE_ID QF_CODEX_BASE_URL QF_CODEX_MODEL \
  QF_CODEX_MODELS QF_CODEX_DISPLAY_NAME QF_CODEX_API_KEY QF_LOCAL_PROVIDER_API_KEY QF_LOCAL_DATA_CREDENTIAL \
  QF_ENABLE_LOCAL_DETERMINISTIC_PROVIDER QF_CREDENTIAL_ENCRYPTION_KEY_ID \
  QF_CREDENTIAL_ENCRYPTION_KEY QF_LOG_LEVEL QF_HTTP_PORT; do
  printf '%s=%s\n' "$name" "${!name}" >> "$environment_file"
done

general_key="$(QF_ENV_FILE="$environment_file" QF_BOOTSTRAP_KEY_LABEL=fullstack \
  QF_BOOTSTRAP_DEFER_WORKERS=1 \
  "$repo_root/scripts/bootstrap-local.sh" | tail -n 1)"
[[ "$general_key" =~ ^qfk_gak_[a-z0-9]{16,32}\.[A-Za-z0-9_-]{43,}$ ]] || {
  printf '%s\n' 'Bootstrap did not return a valid one-time general access key.' >&2
  exit 1
}
export QF_FULLSTACK_GENERAL_KEY="$general_key"

application_url="http://127.0.0.1:${http_port}"
docker compose --project-name "$project_name" --profile local \
  --env-file "$environment_file" exec -T \
  -e QF_FULLSTACK_GENERAL_KEY="$general_key" \
  -e QF_FULLSTACK_DATABASE_URL="$QF_FULLSTACK_DATABASE_URL" \
  -e QF_CODEX_BASE_URL="$QF_CODEX_BASE_URL" \
  -e QF_CODEX_MODEL="$QF_CODEX_MODEL" \
  -e QF_LOCAL_PROVIDER_API_KEY="$QF_LOCAL_PROVIDER_API_KEY" api \
  python /workspace/scripts/fullstack_seed.py \
  --prepare-only \
  --application-url "$application_url"

docker compose --project-name "$project_name" --profile local \
  --env-file "$environment_file" up --build --detach --wait \
  worker agent-worker scheduler

docker compose --project-name "$project_name" --profile local \
  --env-file "$environment_file" exec -T \
  -e QF_FULLSTACK_GENERAL_KEY="$general_key" \
  -e QF_FULLSTACK_DATABASE_URL="$QF_FULLSTACK_DATABASE_URL" \
  -e QF_CODEX_BASE_URL="$QF_CODEX_BASE_URL" \
  -e QF_CODEX_MODEL="$QF_CODEX_MODEL" \
  -e QF_LOCAL_PROVIDER_API_KEY="$QF_LOCAL_PROVIDER_API_KEY" api \
  python /workspace/scripts/fullstack_seed.py \
  --application-url "$application_url" \
  > "$seed_output"

docker compose --project-name "$project_name" --profile local \
  --env-file "$environment_file" up --build --detach --wait frontend

json_field() {
  python3 -c 'import json,sys; value=json.load(open(sys.argv[1], encoding="utf-8"))[sys.argv[2]]; assert isinstance(value,str) and value; print(value)' "$seed_output" "$1"
}
QF_FULLSTACK_BASE_URL="$(json_field QF_FULLSTACK_BASE_URL)"
QF_FULLSTACK_FACTOR_ID="$(json_field QF_FULLSTACK_FACTOR_ID)"
QF_FULLSTACK_SNAPSHOT_ID="$(json_field QF_FULLSTACK_SNAPSHOT_ID)"
QF_FULLSTACK_COST_MODEL_ID="$(json_field QF_FULLSTACK_COST_MODEL_ID)"
QF_FULLSTACK_VALIDATION_POLICY_ID="$(json_field QF_FULLSTACK_VALIDATION_POLICY_ID)"
export QF_FULLSTACK_BASE_URL QF_FULLSTACK_FACTOR_ID QF_FULLSTACK_GENERAL_KEY
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
pnpm --dir "$repo_root/frontend" run ci
printf '%s\n' 'Full-stack frontend CI passed with all six QF_FULLSTACK_* values.'
