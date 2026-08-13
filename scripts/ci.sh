#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="${1:?target required}"
ci_tmp="$(mktemp -d "${TMPDIR:-/tmp}/quantfoundry-ci.XXXXXX")"

cleanup_ci_tmp() {
  case "$ci_tmp" in
    "${TMPDIR:-/tmp}"/quantfoundry-ci.*) rm -rf -- "$ci_tmp" ;;
    *) printf 'Refusing unexpected CI temp cleanup path: %s\n' "$ci_tmp" >&2 ;;
  esac
}
trap cleanup_ci_tmp EXIT

require_file() { [[ -f "$repo_root/$1" ]] || { printf 'Missing required file: %s\n' "$1" >&2; exit 1; }; }
require_dir() { [[ -d "$repo_root/$1" ]] || { printf 'Missing required directory: %s\n' "$1" >&2; exit 1; }; }
run_backend() { (cd "$repo_root/backend" && uv run --frozen "$@"); }
run_backend_no_create() { (cd "$repo_root/backend" && QF_SKIP_AUTO_CREATE=1 uv run --frozen "$@"); }
run_frontend() { pnpm --dir "$repo_root/frontend" "$@"; }

platform_static() {
  command -v docker >/dev/null
  command -v shellcheck >/dev/null
  command -v actionlint >/dev/null
  docker compose --project-directory "$repo_root" --env-file "$repo_root/.env.example" config --quiet
  docker compose --project-directory "$repo_root" --profile local \
    --env-file "$repo_root/.env.example" config --quiet
  shellcheck "$repo_root"/scripts/*.sh
  actionlint "$repo_root"/.github/workflows/*.yml
}

governance_check() {
  "$repo_root/scripts/p0-check.sh" "$repo_root/docs/治理/p0-blockers.yaml" --report
}

hygiene_check() {
  "$repo_root/scripts/hygiene-check.sh"
}

require_toolchains() {
  local python_version
  local node_version
  local pnpm_version
  python_version="$(run_backend python -c 'import platform; print(platform.python_version())')"
  node_version="$(node --version)"
  pnpm_version="$(pnpm --version)"
  [[ "$python_version" == "3.14.0" ]] || {
    printf 'Python 3.14.0 is required; found %s.\n' "$python_version" >&2
    exit 1
  }
  [[ "$node_version" == "v24.19.0" ]] || {
    printf 'Node v24.19.0 is required; found %s.\n' "$node_version" >&2
    exit 1
  }
  [[ "$pnpm_version" == "10.32.1" ]] || {
    printf 'pnpm 10.32.1 is required; found %s.\n' "$pnpm_version" >&2
    exit 1
  }
}

require_runtime_identity() {
  [[ -n "${QF_ENV:-}" && "$QF_ENV" == "${QF_ENVIRONMENT:-}" ]] || {
    printf '%s\n' 'QF_ENV and QF_ENVIRONMENT must be present and identical.' >&2
    exit 1
  }
  [[ -n "${QF_GIT_COMMIT:-}" && -n "${QF_BUILD_ID:-}" ]] || {
    printf '%s\n' 'QF_GIT_COMMIT and QF_BUILD_ID are required.' >&2
    exit 1
  }
}

backend_format() {
  run_backend ruff format --check app workers scheduler tests alembic
  run_backend ruff format --check "$repo_root/scripts"
}

frontend_format() {
  run_frontend format:check
}

backend_lint() {
  require_file backend/pyproject.toml
  run_backend ruff check app workers scheduler tests alembic
  run_backend ruff check "$repo_root/scripts"
}

backend_typecheck() {
  require_file backend/pyproject.toml
  run_backend mypy --explicit-package-bases app workers scheduler
}

frontend_static() {
  require_file frontend/package.json
  run_frontend lint
  run_frontend typecheck
}

require_postgres() {
  [[ "${QF_DATABASE_URL:-}" == postgresql+psycopg://* ]] || {
    printf '%s\n' 'QF_DATABASE_URL must target real PostgreSQL for integration and migration gates.' >&2
    exit 1
  }
  [[ "${QF_ALEMBIC_URL:-}" == "$QF_DATABASE_URL" ]] || {
    printf '%s\n' 'QF_ALEMBIC_URL must exactly match QF_DATABASE_URL.' >&2
    exit 1
  }
  [[ "${QF_SKIP_AUTO_CREATE:-}" == "1" ]] || {
    printf '%s\n' 'QF_SKIP_AUTO_CREATE=1 is required so Alembic exclusively owns CI schema creation.' >&2
    exit 1
  }
}

migration_check() {
  require_postgres
  run_backend alembic upgrade head
  run_backend alembic check
}

backend_test() {
  require_postgres
  run_backend pytest
}

backend_pg18_full() {
  require_postgres
  require_file backend/scripts/pg18_ci.sh
  (
    cd "$repo_root/backend"
    env \
      -u QF_ARTIFACT_ROOT \
      -u QF_ARTIFACT_DIR \
      -u QF_DATA_ROOT \
      -u QF_DATASET_DIR \
      -u QF_COST_MODEL_DIR \
      -u QF_POLICY_DIR \
      -u QF_AGENT_PROVIDER \
      -u QF_AGENT_MODEL \
      -u QF_ENABLE_LOCAL_DETERMINISTIC_PROVIDER \
      -u QF_CODEX_RUNTIME_ID \
      -u QF_CODEX_REMOTE_INSTANCE_ID \
      -u QF_CODEX_BASE_URL \
      -u QF_CODEX_API_KEY \
      -u QF_CODEX_MODEL \
      -u QF_CODEX_MODELS \
      -u QF_CODEX_DISPLAY_NAME \
      -u QF_CODEX_MAX_ATTEMPTS \
      -u QF_AGENT_CHECKPOINT_URL \
      -u QF_AGENT_CHECKPOINT_SQLITE \
      -u QF_CODEX_RUNTIME_ID \
      -u QF_CODEX_REMOTE_INSTANCE_ID \
      -u QF_CODEX_BASE_URL \
      -u QF_CODEX_API_KEY \
      -u QF_CODEX_MODEL \
      -u QF_CODEX_MODELS \
      -u QF_CODEX_DISPLAY_NAME \
      -u QF_CODEX_MAX_ATTEMPTS \
      -u QF_OPENAI_BASE_URL \
      -u QF_OPENAI_API_KEY \
      -u QF_OPENAI_MODELS \
      -u QF_LOCAL_PROVIDER_API_KEY \
      -u QF_LOCAL_DATA_CREDENTIAL \
      -u QF_CREDENTIAL_ENCRYPTION_KEY_ID \
      -u QF_CREDENTIAL_ENCRYPTION_KEY \
      -u QF_GIT_COMMIT \
      -u QF_BUILD_ID \
      sh scripts/pg18_ci.sh
  )
}

fresh_local_smoke() {
  require_file backend/scripts/fresh_local_smoke.py
  (
    cd "$repo_root/backend"
    env \
      -u QF_DATABASE_URL \
      -u QF_ALEMBIC_URL \
      -u QF_AGENT_CHECKPOINT_URL \
      -u QF_AGENT_CHECKPOINT_SQLITE \
      -u QF_ARTIFACT_ROOT \
      -u QF_ARTIFACT_DIR \
      -u QF_DATA_ROOT \
      -u QF_DATASET_DIR \
      -u QF_COST_MODEL_DIR \
      -u QF_POLICY_DIR \
      -u QF_OPENAI_BASE_URL \
      -u QF_OPENAI_API_KEY \
      -u QF_OPENAI_MODELS \
      -u QF_LOCAL_PROVIDER_API_KEY \
      -u QF_LOCAL_DATA_CREDENTIAL \
      QF_ENV=local \
      QF_ENVIRONMENT=local \
      QF_GIT_COMMIT=local-smoke \
      QF_BUILD_ID=local-smoke \
      uv run --frozen python -m scripts.fresh_local_smoke \
        --root "$ci_tmp/fresh-local"
  )
}

schema_manifest_check() {
  require_file backend/scripts/generate_schema_manifest.py
  require_file backend/scripts/schema_manifest_check.py
  require_file backend/schema/section14_manifest.json
  run_backend_no_create python scripts/generate_schema_manifest.py --check
  run_backend_no_create python scripts/schema_manifest_check.py
}

frontend_test() { run_frontend test -- --run; }
frontend_e2e() { run_frontend test:e2e; }
frontend_visual() { run_frontend test:e2e:visual; }
frontend_fullstack_ci() { "$repo_root/scripts/fullstack-ci.sh"; }

openapi_check() {
  require_file docs/后端系统技术方案/contracts/openapi-v1.yaml
  require_file backend/scripts/runtime_contract_diff.py
  require_dir backend/tests/contracts
  require_file frontend/src/api/generated.ts
  run_backend_no_create python scripts/runtime_contract_diff.py
  run_backend_no_create pytest tests/contracts
  run_frontend exec openapi-typescript "$repo_root/docs/后端系统技术方案/contracts/openapi-v1.yaml" --output "$ci_tmp/generated.ts"
  if ! cmp -s "$repo_root/frontend/src/api/generated.ts" "$ci_tmp/generated.ts"; then
    diff -u "$repo_root/frontend/src/api/generated.ts" "$ci_tmp/generated.ts" || true
    printf '%s\n' 'Frontend generated OpenAPI types are stale.' >&2
    exit 1
  fi
}

tool_check() {
  require_file docs/后端系统技术方案/contracts/tools/README.md
  require_file docs/后端系统技术方案/contracts/tools/v1-p0.yaml
  run_backend python "$repo_root/scripts/tool_contract_check.py" \
    --schema-out "$ci_tmp/tool-contract.schema.json"
  (cd "$repo_root/frontend" && pnpm dlx ajv-cli@5.0.0 compile \
    --spec=draft2020 --strict=false -s "$ci_tmp/tool-contract.schema.json")
  run_backend python "$repo_root/scripts/tool_contract_check.py" \
    --schema-out "$ci_tmp/tool-contract.schema.json" --validate-instance
}

build_all() {
  run_backend python -m compileall -q app workers scheduler
  run_frontend build
}

case "$target" in
  format) backend_format; frontend_format ;;
  lint) backend_lint; run_frontend lint ;;
  typecheck) backend_typecheck; run_frontend typecheck ;;
  backend-lint) backend_lint ;;
  backend-typecheck|backend-mypy) backend_typecheck ;;
  migration) migration_check ;;
  test) backend_test; frontend_test ;;
  build) build_all ;;
  e2e) frontend_e2e ;;
  visual) frontend_visual ;;
  browser) run_frontend exec playwright install chromium ;;
  fresh-smoke) fresh_local_smoke ;;
  schema) schema_manifest_check ;;
  openapi) openapi_check ;;
  tools) tool_check ;;
  contract) openapi_check; tool_check ;;
  pg18) backend_pg18_full ;;
  fullstack) require_toolchains; frontend_fullstack_ci ;;
  platform) platform_static ;;
  governance) governance_check ;;
  p0-check) "$repo_root/scripts/p0-check-test.sh" && "$repo_root/scripts/p0-check.sh" "$repo_root/docs/治理/p0-blockers.yaml" --require-closed ;;
  release-check) "$repo_root/scripts/release-check.sh" "${QF_RELEASE_TAG:?QF_RELEASE_TAG is required}" ;;
  release-known-issues) "$repo_root/scripts/release-known-issues-check.sh" ;;
  hygiene|secrets|licenses) hygiene_check ;;
  backend-ci)
    migration_check
    backend_format
    backend_lint
    backend_typecheck
    schema_manifest_check
    openapi_check
    tool_check
    fresh_local_smoke
    backend_pg18_full
    ;;
  frontend-ci) require_toolchains; frontend_fullstack_ci ;;
  ci)
    require_toolchains
    require_runtime_identity
    platform_static
    hygiene_check
    migration_check
    backend_format
    backend_lint
    backend_typecheck
    schema_manifest_check
    openapi_check
    tool_check
    fresh_local_smoke
    backend_pg18_full
    frontend_fullstack_ci
    ;;
  *) printf 'Unknown CI target: %s\n' "$target" >&2; exit 2 ;;
esac
