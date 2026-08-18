#!/usr/bin/env bash
set -euo pipefail

environment_file="${QF_ENV_FILE:-.env}"
[[ -f "$environment_file" ]] || {
  printf 'Missing %s; run make bootstrap first.\n' "$environment_file" >&2
  exit 1
}

QF_ENV_FILE="$environment_file" ./scripts/bootstrap.sh >/dev/null

key_label="${QF_BOOTSTRAP_KEY_LABEL:-primary}"
[[ -n "$key_label" && ${#key_label} -le 80 ]] || {
  printf '%s\n' 'QF_BOOTSTRAP_KEY_LABEL must contain 1 to 80 characters.' >&2
  exit 1
}
[[ -t 1 || "${QF_ALLOW_INSECURE_BOOTSTRAP_OUTPUT:-}" == 1 ]] || {
  printf '%s\n' 'refusing to print an owner key to a non-interactive output; use a terminal or explicitly set QF_ALLOW_INSECURE_BOOTSTRAP_OUTPUT=1.' >&2
  exit 1
}

docker compose --env-file "$environment_file" run --rm api \
  python /workspace/scripts/bootstrap-general-key.py \
  --label "$key_label"
