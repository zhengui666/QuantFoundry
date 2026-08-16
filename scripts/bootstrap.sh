#!/usr/bin/env bash
set -euo pipefail

environment_file="${QF_ENV_FILE:-.env}"

environment_value() {
  local key="$1"
  local count
  local line
  count="$(grep -Ec "^[[:space:]]*${key}=" "$environment_file" || true)"
  if [[ "$count" != "1" ]]; then
    printf 'Expected exactly one %s entry in %s.\n' "$key" "$environment_file" >&2
    exit 1
  fi
  line="$(grep -E "^[[:space:]]*${key}=" "$environment_file")"
  printf '%s' "${line#*=}"
}

if [[ ! -f "$environment_file" ]]; then
  cp .env.example "$environment_file"
  printf 'Created %s from .env.example.\n' "$environment_file" >&2
  printf '%s\n' 'Set the database password and generated credential-encryption key, then run make bootstrap again.' >&2
  exit 1
fi

qf_env="$(environment_value QF_ENV)"
qf_environment="$(environment_value QF_ENVIRONMENT)"
if [[ "$qf_env" != "$qf_environment" ]]; then
  printf '%s\n' 'QF_ENV and QF_ENVIRONMENT must be identical.' >&2
  exit 1
fi
case "$qf_env" in
  local | development | test | staging | production) ;;
  *) printf '%s\n' 'QF_ENV must be local, test, staging, or production.' >&2; exit 1 ;;
esac

git_commit="$(environment_value QF_GIT_COMMIT)"
build_id="$(environment_value QF_BUILD_ID)"
if [[ -z "$git_commit" || -z "$build_id" ]]; then
  printf '%s\n' 'QF_GIT_COMMIT and QF_BUILD_ID must be non-empty.' >&2
  exit 1
fi
if [[ "$qf_env" == "production" ]] && {
  [[ "$git_commit" == "unknown" || "$git_commit" == "local-worktree" ]] ||
    [[ "$build_id" == "unknown" || "$build_id" == "local-dev" ]]
}; then
  printf '%s\n' 'Production requires immutable non-placeholder build identity.' >&2
  exit 1
fi

password_value="$(environment_value QF_POSTGRES_PASSWORD)"
if [[ -z "$password_value" || "$password_value" == "change-me-before-use" ]]; then
  printf 'Refusing placeholder or empty QF_POSTGRES_PASSWORD in %s.\n' "$environment_file" >&2
  exit 1
fi
if [[ ! "$password_value" =~ ^[A-Za-z0-9._~-]+$ ]]; then
  printf '%s\n' 'QF_POSTGRES_PASSWORD must be URL-safe: letters, digits, dot, underscore, tilde, or hyphen.' >&2
  exit 1
fi

credential_key_id="$(environment_value QF_CREDENTIAL_ENCRYPTION_KEY_ID)"
credential_key="$(environment_value QF_CREDENTIAL_ENCRYPTION_KEY)"
if [[ -z "$credential_key_id" || "$credential_key" == "replace-with-url-safe-base64-32-byte-key" ]]; then
  printf '%s\n' 'Refusing placeholder or empty credential encryption configuration.' >&2
  exit 1
fi
if [[ ! "$credential_key" =~ ^[A-Za-z0-9_-]{43}=?$ ]]; then
  printf '%s\n' 'QF_CREDENTIAL_ENCRYPTION_KEY must be URL-safe base64 for exactly 32 bytes.' >&2
  exit 1
fi

if [[ "$qf_env" == "local" || "$qf_env" == "development" ]]; then
  local_provider_key="$(environment_value QF_LOCAL_PROVIDER_API_KEY)"
  if ((${#local_provider_key} < 20)); then
    printf '%s\n' 'Local provider credential must contain at least 20 characters.' >&2
    exit 1
  fi
fi

if [[ "$qf_env" == "local" || "$qf_env" == "development" ]]; then
  docker compose --profile local --env-file "$environment_file" config --quiet
  printf '%s\n' 'Compose configuration is valid. Run make local-bootstrap.'
else
  docker compose --env-file "$environment_file" config --quiet
  printf '%s\n' 'Compose configuration is valid.'
fi
