#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

for file in LICENSE backend/pyproject.toml frontend/package.json; do
  [[ -s "$repo_root/$file" ]] || { printf 'Required license metadata is missing: %s\n' "$file" >&2; exit 1; }
done
if ! /usr/bin/grep -Eq '^license = "AGPL-3\.0-only"$' "$repo_root/backend/pyproject.toml" \
  || ! /usr/bin/grep -Eq '"license"\s*:\s*"AGPL-3\.0-only"' "$repo_root/frontend/package.json"; then
  printf '%s\n' 'Package license metadata must declare AGPL-3.0-only.' >&2
  exit 1
fi

if git -C "$repo_root" grep -n -I -E -i \
  'github_pat_[a-z0-9_]{20,}|ghp_[a-z0-9]{30,}|xox[baprs]-[a-z0-9-]{20,}|-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----' \
  -- . ':(exclude).env.example' ':(exclude)docs/**' \
  ':(exclude)**/*.lock' ':(exclude)**/fixtures/**'; then
  printf '%s\n' 'Potential committed secret detected.' >&2
  exit 1
fi
printf '%s\n' '{"result":"pass","checks":["license-metadata-agpl-3.0-only","secret-patterns"]}'
