#!/usr/bin/env bash
set -euo pipefail

environment_file="${QF_ENV_FILE:-.env}"
[[ -f "$environment_file" ]] || {
  printf 'Missing %s; run make bootstrap first.\n' "$environment_file" >&2
  exit 1
}

owner_email="${QF_BOOTSTRAP_OWNER_EMAIL:-}"
workspace_name="${QF_BOOTSTRAP_WORKSPACE_NAME:-QuantFoundry}"
ttl_hours="${QF_BOOTSTRAP_TOKEN_TTL_HOURS:-24}"

if [[ -z "$owner_email" ]]; then
  read -r -p 'OWNER email: ' owner_email
fi
[[ "$owner_email" =~ ^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$ ]] || {
  printf '%s\n' 'Invalid OWNER email.' >&2
  exit 1
}
[[ -n "$workspace_name" && ${#workspace_name} -le 128 ]] || {
  printf '%s\n' 'Workspace name must contain 1 to 128 characters.' >&2
  exit 1
}
if [[ ! "$ttl_hours" =~ ^[0-9]+$ ]] || ((ttl_hours < 1 || ttl_hours > 168)); then
  printf '%s\n' 'Token TTL must be an integer from 1 to 168 hours.' >&2
  exit 1
fi

docker compose --env-file "$environment_file" run --rm api \
  python /workspace/scripts/bootstrap_owner.py \
  --email "$owner_email" \
  --workspace-name "$workspace_name" \
  --ttl-hours "$ttl_hours"
