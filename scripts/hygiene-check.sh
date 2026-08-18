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
git -C "$repo_root" grep --cached -q --text -E -i \
  "$secret_pattern" -- .
index_secret_scan_status=$?
git -C "$repo_root" grep -q --text -E -i \
  "$secret_pattern" -- .
worktree_secret_scan_status=$?
python3 - "$repo_root" "$secret_pattern" <<'PY'
import re
import os
import stat
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1])
pattern = re.compile(sys.argv[2].encode(), re.IGNORECASE)
max_file_bytes = 16 * 1024 * 1024
try:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard", "-z"],
        check=True,
        stdout=subprocess.PIPE,
    )
except (OSError, subprocess.CalledProcessError) as error:
    print(f"Untracked secret scan failed: {error}", file=sys.stderr)
    raise SystemExit(2)
matched = False
for raw_path in result.stdout.split(b"\0"):
    if not raw_path:
        continue
    path = root / raw_path.decode(sys.getfilesystemencoding(), "surrogateescape")
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                continue
            if metadata.st_size > max_file_bytes:
                raise OSError("untracked file exceeds the secret-scan size limit")
            with os.fdopen(descriptor, "rb") as stream:
                descriptor = -1
                if pattern.search(stream.read()):
                    matched = True
        finally:
            if descriptor != -1:
                os.close(descriptor)
    except OSError as error:
        print(f"Untracked secret scan failed for {path}: {error}", file=sys.stderr)
        raise SystemExit(2)
if matched:
    print("Potential secret detected in an untracked regular file.", file=sys.stderr)
    raise SystemExit(0)
raise SystemExit(1)
PY
untracked_secret_scan_status=$?
if [[ "$index_secret_scan_status" -ne 0 && "$index_secret_scan_status" -ne 1 ]] || \
  [[ "$worktree_secret_scan_status" -ne 0 && "$worktree_secret_scan_status" -ne 1 ]] || \
  [[ "$untracked_secret_scan_status" -ne 0 && "$untracked_secret_scan_status" -ne 1 ]]; then
  printf '%s\n' 'Secret scan failed to execute.' >&2
  exit 1
fi
if [[ "$index_secret_scan_status" -eq 0 || "$worktree_secret_scan_status" -eq 0 || "$untracked_secret_scan_status" -eq 0 ]]; then
  printf '%s\n' 'Potential committed or working-tree secret detected.' >&2
  exit 1
fi
set -e
printf '%s\n' '{"result":"pass","checks":["license-metadata-agpl-3.0-only","secret-patterns"]}'
