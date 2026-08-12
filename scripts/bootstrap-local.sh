#!/usr/bin/env bash
set -euo pipefail

environment_file="${QF_ENV_FILE:-.env}"
owner_email="${QF_BOOTSTRAP_OWNER_EMAIL:-owner@local.invalid}"
workspace_name="${QF_BOOTSTRAP_WORKSPACE_NAME:-QuantFoundry Local}"
ttl_hours="${QF_BOOTSTRAP_TOKEN_TTL_HOURS:-24}"
bootstrap_output="${QF_BOOTSTRAP_OUTPUT_FILE:-}"

QF_ENV_FILE="$environment_file" ./scripts/bootstrap.sh

docker compose --profile local --env-file "$environment_file" \
  up --build --detach --wait \
  local-provider api worker agent-worker scheduler

bootstrap_command=(
  docker compose --profile local --env-file "$environment_file" run
  --rm --no-deps api python /workspace/scripts/bootstrap_local.py
  --email "$owner_email"
  --workspace-name "$workspace_name"
  --ttl-hours "$ttl_hours"
)
if [[ -n "$bootstrap_output" ]]; then
  umask 077
  if [[ -L "$bootstrap_output" ]]; then
    printf 'Refusing symlink bootstrap output: %s\n' "$bootstrap_output" >&2
    exit 1
  fi
  "${bootstrap_command[@]}" > "$bootstrap_output"
  chmod 0600 "$bootstrap_output"
else
  "${bootstrap_command[@]}"
fi
