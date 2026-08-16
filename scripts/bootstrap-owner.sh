#!/usr/bin/env bash
set -euo pipefail

environment_file="${QF_ENV_FILE:-.env}"
[[ -f "$environment_file" ]] || {
  printf 'Missing %s; run make bootstrap first.\n' "$environment_file" >&2
  exit 1
}

key_label="${QF_BOOTSTRAP_KEY_LABEL:-primary}"
[[ -n "$key_label" && ${#key_label} -le 80 ]] || {
  printf '%s\n' 'QF_BOOTSTRAP_KEY_LABEL must contain 1 to 80 characters.' >&2
  exit 1
}

docker compose --env-file "$environment_file" run --rm api \
  python /workspace/scripts/bootstrap-general-key.py \
  --label "$key_label"
