#!/usr/bin/env bash
set -euo pipefail

environment_file="${QF_ENV_FILE:-.env}"
key_label="${QF_BOOTSTRAP_KEY_LABEL:-local}"

QF_ENV_FILE="$environment_file" ./scripts/bootstrap.sh

docker compose --profile local --env-file "$environment_file" \
  up --build --detach --wait \
  local-provider api

docker compose --profile local --env-file "$environment_file" run --rm --no-deps api \
  python /workspace/scripts/bootstrap-general-key.py --label "$key_label"

# Workers must start after the first domain binding is activated.  Full-stack
# CI activates that binding after this script returns, so it explicitly
# defers this final start until after its seed step.
if [[ "${QF_BOOTSTRAP_DEFER_WORKERS:-0}" != 1 ]]; then
  docker compose --profile local --env-file "$environment_file" \
    up --build --detach --wait \
    worker agent-worker scheduler
fi
