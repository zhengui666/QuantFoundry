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

optional_environment_value() {
  local key="$1"
  local count
  local line
  count="$(grep -Ec "^[[:space:]]*${key}=" "$environment_file" || true)"
  if [[ "$count" == "0" ]]; then
    return 0
  fi
  if [[ "$count" != "1" ]]; then
    printf 'Expected at most one %s entry in %s.\n' "$key" "$environment_file" >&2
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

provider="$(environment_value QF_AGENT_PROVIDER)"
agent_model="$(environment_value QF_AGENT_MODEL)"
local_provider_enabled="$(environment_value QF_ENABLE_LOCAL_DETERMINISTIC_PROVIDER)"
if [[ "$provider" == "local-deterministic" && "$local_provider_enabled" != "1" ]]; then
  printf '%s\n' 'The local deterministic provider requires QF_ENABLE_LOCAL_DETERMINISTIC_PROVIDER=1.' >&2
  exit 1
fi
if [[ "$qf_env" == "staging" || "$qf_env" == "production" ]] &&
  [[ "$local_provider_enabled" != "0" ]]; then
  printf '%s\n' 'Local deterministic providers must be disabled in staging/production.' >&2
  exit 1
fi

codex_base_url="$(optional_environment_value QF_CODEX_BASE_URL)"
codex_models="$(optional_environment_value QF_CODEX_MODELS)"
codex_runtime_id="$(optional_environment_value QF_CODEX_RUNTIME_ID)"
codex_instance_id="$(optional_environment_value QF_CODEX_REMOTE_INSTANCE_ID)"
openai_base_url="$(optional_environment_value QF_OPENAI_BASE_URL)"
openai_models="$(optional_environment_value QF_OPENAI_MODELS)"
effective_provider_url="$codex_base_url"
effective_provider_models="$codex_models"
if [[ -z "$effective_provider_url" ]]; then
  effective_provider_url="$openai_base_url"
  effective_provider_models="$openai_models"
fi
if [[ "$provider" == "remote-codex" || -n "$codex_base_url" ]]; then
  [[ "$provider" == "remote-codex" ]] || {
    printf '%s\n' 'QF_CODEX_BASE_URL requires QF_AGENT_PROVIDER=remote-codex.' >&2
    exit 1
  }
  [[ "$codex_runtime_id" == "CODEX-DEFAULT" ]] || {
    printf '%s\n' 'QF_CODEX_RUNTIME_ID must be CODEX-DEFAULT.' >&2
    exit 1
  }
  [[ -n "$codex_instance_id" ]] || {
    printf '%s\n' 'QF_CODEX_REMOTE_INSTANCE_ID must be non-empty.' >&2
    exit 1
  }
  [[ -n "$effective_provider_url" && -n "$agent_model" ]] || {
    printf '%s\n' 'Remote Codex requires a base URL and QF_AGENT_MODEL.' >&2
    exit 1
  }
  [[ "$effective_provider_url" == http://* || "$effective_provider_url" == https://* ]] || {
    printf '%s\n' 'Remote Codex base URL must use http or https.' >&2
    exit 1
  }
fi
if [[ "$effective_provider_url" == "http://local-provider:8011/v1" ]]; then
  local_provider_key="$(environment_value QF_LOCAL_PROVIDER_API_KEY)"
  local_data_credential="$(environment_value QF_LOCAL_DATA_CREDENTIAL)"
  if [[ "$qf_env" != "local" && "$qf_env" != "development" ]]; then
    printf '%s\n' 'The bundled local provider is permitted only in local/development.' >&2
    exit 1
  fi
  [[ ( "$provider" == "openai-compatible" || "$provider" == "remote-codex" ) && "$effective_provider_models" == *"qf-local-v1"* ]] || {
    printf '%s\n' 'The bundled local provider requires remote-codex/qf-local-v1.' >&2
    exit 1
  }
  if ((${#local_provider_key} < 20 || ${#local_data_credential} < 20)); then
    printf '%s\n' 'Local provider and data credentials must contain at least 20 characters.' >&2
    exit 1
  fi
elif [[ "$qf_env" == "local" || "$qf_env" == "development" ]]; then
  printf '%s\n' 'Local bootstrap requires QF_CODEX_BASE_URL=http://local-provider:8011/v1.' >&2
  exit 1
fi

if [[ "$qf_env" == "local" || "$qf_env" == "development" ]]; then
  docker compose --profile local --env-file "$environment_file" config --quiet
  printf '%s\n' 'Compose configuration is valid. Run make local-bootstrap.'
else
  docker compose --env-file "$environment_file" config --quiet
  printf '%s\n' 'Compose configuration is valid.'
fi
