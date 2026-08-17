#!/usr/bin/env bash
set -euo pipefail

environment_file="${QF_ENV_FILE:-.env}"
key_label="${QF_BOOTSTRAP_KEY_LABEL:-local}"

QF_ENV_FILE="$environment_file" ./scripts/bootstrap.sh

qf_env="$(sed -n 's/^[[:space:]]*QF_ENV=//p' "$environment_file")"
qf_environment="$(sed -n 's/^[[:space:]]*QF_ENVIRONMENT=//p' "$environment_file")"
if [[ "$qf_env" != "$qf_environment" || ( "$qf_env" != local && "$qf_env" != development ) ]]; then
  printf '%s\n' 'Local bootstrap is allowed only in local/development.' >&2
  exit 1
fi

docker compose --profile local --env-file "$environment_file" \
  up --build --detach --wait \
  local-provider api

if docker compose --profile local --env-file "$environment_file" run --rm --no-deps api \
  python /workspace/scripts/bootstrap-general-key.py --check; then
  docker compose --profile local --env-file "$environment_file" run --rm --no-deps api \
    python /workspace/scripts/bootstrap-general-key.py --label "$key_label"
else
  check_status="$?"
  if [[ "$check_status" != 3 ]]; then
    exit "$check_status"
  fi
fi

# Workers must start after the first domain binding is activated.  Full-stack
# CI activates that binding after this script returns, so it explicitly
# defers this final start until after its seed step.
if [[ "${QF_BOOTSTRAP_DEFER_WORKERS:-1}" != 1 ]]; then
  docker compose --profile local --env-file "$environment_file" \
    up --build --detach --wait \
    worker agent-worker scheduler
else
  printf '%s\n' 'Workers remain stopped until the domain binding is activated; set QF_BOOTSTRAP_DEFER_WORKERS=0 to start them.' >&2
fi
