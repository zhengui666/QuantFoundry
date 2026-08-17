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

python3 - "$repo_root/backend/src/quantfoundry" <<'PY'
import ast
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
violations = []
for path in root.rglob("*.py"):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as error:
        raise SystemExit(f"cannot parse {path}: {error}") from error
    for node in ast.walk(tree):
        module = None
        if isinstance(node, ast.ImportFrom) and node.level == 0:
            module = node.module or ""
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app" or alias.name.startswith("app."):
                    violations.append(f"{path}:{node.lineno}: import {alias.name}")
        if module == "app" or module.startswith("app."):
            violations.append(f"{path}:{node.lineno}: from {module} import ...")
if violations:
    print("canonical backend must not import legacy app modules", file=sys.stderr)
    print("\n".join(violations), file=sys.stderr)
    raise SystemExit(1)
PY

printf '%s\n' '{"gate":"p0-architecture-review","result":"pass"}'
