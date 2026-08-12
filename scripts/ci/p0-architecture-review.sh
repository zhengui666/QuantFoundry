#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
for directory in \
  backend/src/quantfoundry/api \
  backend/src/quantfoundry/application \
  backend/src/quantfoundry/domain \
  backend/src/quantfoundry/agents \
  backend/src/quantfoundry/engines \
  backend/src/quantfoundry/adapters \
  backend/src/quantfoundry/infrastructure \
  backend/src/quantfoundry/workers \
  backend/src/quantfoundry/scheduler \
  backend/src/quantfoundry/contracts \
  frontend/src/app \
  frontend/src/features \
  frontend/src/domain \
  frontend/src/design-system; do
  test -d "$repo_root/$directory"
done
test ! -e "$repo_root/frontend/src/design-system/domain-components.tsx"
if /usr/bin/grep -R -n -E '^(from|import) app(\.| import)' "$repo_root/backend/src/quantfoundry"; then
  printf '%s\n' 'canonical backend must not import legacy app modules' >&2
  exit 1
fi
printf '%s\n' '{"gate":"p0-architecture-review","result":"pass"}'
