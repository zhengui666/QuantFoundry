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

# Workers must start after the first domain binding is activated.  Starting
# them before bootstrap makes their durable-heartbeat health checks fail closed
# on a fresh install because the control plane has no ACTIVE binding yet.
docker compose --profile local --env-file "$environment_file" \
  up --build --detach --wait \
  worker agent-worker scheduler
