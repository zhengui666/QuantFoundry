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
    module_aliases = set()
    dynamic_aliases = {"__import__"}
    constants = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "importlib":
                    module_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module in {"importlib", "builtins"}:
            for alias in node.names:
                if node.module == "importlib" and alias.name == "import_module":
                    dynamic_aliases.add(alias.asname or alias.name)
                if node.module == "builtins" and alias.name == "__import__":
                    dynamic_aliases.add(alias.asname or alias.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            value = node.value
            try:
                constant = ast.literal_eval(value)
            except (ValueError, TypeError):
                constant = None
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Name):
                    if isinstance(value, ast.Name) and value.id in dynamic_aliases:
                        dynamic_aliases.add(target.id)
                    elif isinstance(constant, str):
                        constants[target.id] = constant
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
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "import_module"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id in module_aliases
            ):
                dynamic_name = "import_module"
            elif isinstance(node.func, ast.Name) and node.func.id in dynamic_aliases:
                dynamic_name = node.func.id
            if dynamic_name:
                imported = None
                if node.args:
                    argument = node.args[0]
                    if isinstance(argument, ast.Name):
                        imported = constants.get(argument.id)
                    else:
                        try:
                            imported = ast.literal_eval(argument)
                        except (ValueError, TypeError):
                            imported = None
                if isinstance(imported, str) and imported.startswith("."):
                    package = next(
                        (keyword.value for keyword in node.keywords if keyword.arg == "package"),
                        None,
                    )
                    if isinstance(package, ast.Name):
                        package = constants.get(package.id)
                    try:
                        package = ast.literal_eval(package) if isinstance(package, ast.AST) else package
                    except (ValueError, TypeError):
                        package = None
                    if isinstance(package, str):
                        imported = package + imported
                if not isinstance(imported, str):
                    violations.append(f"{path}:{node.lineno}: unresolved dynamic {dynamic_name} call")
                elif imported == "app" or imported.startswith("app."):
                    if imported not in compatibility_modules:
                        violations.append(f"{path}:{node.lineno}: dynamic {dynamic_name}({imported!r})")
if violations:
    print("canonical backend must not import legacy app modules", file=sys.stderr)
    print("\n".join(violations), file=sys.stderr)
    raise SystemExit(1)
PY

printf '%s\n' '{"gate":"p0-architecture-review","result":"pass"}'
