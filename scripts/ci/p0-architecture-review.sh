#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
required_directories=(
  backend/src/quantfoundry/api
  backend/src/quantfoundry/application
  backend/src/quantfoundry/domain
  backend/src/quantfoundry/agents
  backend/src/quantfoundry/engines
  backend/src/quantfoundry/adapters
  backend/src/quantfoundry/infrastructure
  backend/src/quantfoundry/workers
  backend/src/quantfoundry/scheduler
  backend/src/quantfoundry/contracts
  frontend/src/app
  frontend/src/features
  frontend/src/domain
  frontend/src/design-system
)
for directory in "${required_directories[@]}"; do
  if [[ ! -d "$repo_root/$directory" ]]; then
    printf 'missing required architecture directory: %s\n' "$directory" >&2
    exit 1
  fi
done

legacy_component="$repo_root/frontend/src/design-system/domain-components.tsx"
if [[ -e "$legacy_component" ]]; then
  printf 'legacy design-system component boundary still exists: %s\n' "$legacy_component" >&2
  exit 1
fi

legacy_imports="$(
  /usr/bin/grep -R -n -E '^(from|import) app(\.| import)' "$repo_root/backend/src/quantfoundry" || true
)"
if [[ -n "$legacy_imports" ]]; then
  printf '%s\n' 'canonical backend must not import legacy app modules' >&2
  printf '%s\n' "$legacy_imports" >&2
  exit 1
fi

printf '%s\n' '{"gate":"p0-architecture-review","result":"pass"}'
