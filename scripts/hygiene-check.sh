#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for file in LICENSE backend/pyproject.toml frontend/package.json; do
  [[ -s "$repo_root/$file" ]] || { printf 'Required license metadata is missing: %s\n' "$file" >&2; exit 1; }
done
if ! python3 - "$repo_root/backend/pyproject.toml" "$repo_root/frontend/package.json" <<'PY'
import json
import pathlib
import sys
import tomllib

backend, frontend = map(pathlib.Path, sys.argv[1:])
with backend.open("rb") as stream:
    backend_data = tomllib.load(stream)
if backend_data.get("project", {}).get("license") != "AGPL-3.0-only":
    raise SystemExit(1)
if json.loads(frontend.read_text(encoding="utf-8")).get("license") != "AGPL-3.0-only":
    raise SystemExit(1)
PY
then
  printf '%s\n' 'Package license metadata must declare AGPL-3.0-only.' >&2
  exit 1
fi

set +e
secret_pattern='(^|[^a-z0-9_])(github_pat_[a-z0-9_]{20,}|gh[pousr]_[a-z0-9]{20,}|glpat-[a-z0-9_-]{20,}|xox[baprs]-[a-z0-9-]{20,}|npm_[a-z0-9]{20,}|(akia|asia)[a-z0-9]{16}|sk-[a-z0-9_-]{20,}|eyj[a-z0-9_-]{20,}\.[a-z0-9_-]{10,}\.[a-z0-9_-]{10,}|-----BEGIN ([A-Z0-9]+ )*PRIVATE KEY-----)'
git -C "$repo_root" grep --cached -q -I -E -i \
  "$secret_pattern" -- .
index_secret_scan_status=$?
git -C "$repo_root" grep -q -I -E -i \
  "$secret_pattern" -- .
worktree_secret_scan_status=$?
if [[ "$index_secret_scan_status" -ne 0 && "$index_secret_scan_status" -ne 1 ]] || \
  [[ "$worktree_secret_scan_status" -ne 0 && "$worktree_secret_scan_status" -ne 1 ]]; then
  printf '%s\n' 'Secret scan failed to execute.' >&2
  exit 1
fi
if [[ "$index_secret_scan_status" -eq 0 || "$worktree_secret_scan_status" -eq 0 ]]; then
  printf '%s\n' 'Potential committed or working-tree secret detected.' >&2
  exit 1
fi
set -e
printf '%s\n' '{"result":"pass","checks":["license-metadata-agpl-3.0-only","secret-patterns"]}'
