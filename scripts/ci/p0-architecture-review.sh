#!/usr/bin/env bash
set -euo pipefail

repo_root="${QF_RELEASE_GOVERNANCE_ROOT:-${QF_CI_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}}"
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
compatibility_modules = {"app.control_plane", "app.generated_api_models"}
for path in root.rglob("*.py"):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as error:
        raise SystemExit(f"cannot parse {path}: {error}") from error
    for node in ast.walk(tree):
        module = ""
        if isinstance(node, ast.ImportFrom) and node.level == 0:
            module = node.module or ""
            if module == "app" and all(
                f"app.{alias.name}" in compatibility_modules for alias in node.names
            ):
                module = ""
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if (alias.name == "app" or alias.name.startswith("app.")) and alias.name not in compatibility_modules:
                    violations.append(f"{path}:{node.lineno}: import {alias.name}")
        if (module == "app" or module.startswith("app.")) and module not in compatibility_modules:
            violations.append(f"{path}:{node.lineno}: from {module} import ...")
        if isinstance(node, ast.Call):
            dynamic_name = None
            if isinstance(node.func, ast.Attribute) and node.func.attr == "import_module":
                dynamic_name = "import_module"
            elif isinstance(node.func, ast.Name) and node.func.id in {"import_module", "__import__"}:
                dynamic_name = node.func.id
            if dynamic_name and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                imported = node.args[0].value
                if (imported == "app" or imported.startswith("app.")) and imported not in compatibility_modules:
                    violations.append(f"{path}:{node.lineno}: dynamic {dynamic_name}({imported!r})")
if violations:
    print("canonical backend must not import legacy app modules", file=sys.stderr)
    print("\n".join(violations), file=sys.stderr)
    raise SystemExit(1)
PY

printf '%s\n' '{"gate":"p0-architecture-review","result":"pass"}'
