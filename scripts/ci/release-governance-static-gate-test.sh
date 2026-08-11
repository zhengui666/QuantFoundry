#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fixture_root="$(mktemp -d)"
trap 'rm -rf "$fixture_root"' EXIT

git -C "$repo_root" archive --format=tar HEAD | tar --extract --file - --directory "$fixture_root"
cp "$repo_root/.github/workflows/rc-release.yml" "$fixture_root/.github/workflows/rc-release.yml"
python3 - "$fixture_root/.github/workflows/rc-release.yml" <<'PY'
import pathlib
import sys

workflow = pathlib.Path(sys.argv[1])
source = workflow.read_text(encoding="utf-8")
target = "  preflight:\n    permissions:\n      contents: read\n      actions: read\n"
if target not in source:
    raise SystemExit("fixture setup could not locate rc-release preflight actions: read permission")
workflow.write_text(source.replace(target, target.replace("      actions: read\n", ""), 1), encoding="utf-8")
PY

if QF_RELEASE_GOVERNANCE_ROOT="$fixture_root" QF_RELEASE_GOVERNANCE_SKIP_FIXTURES=1 \
  "$repo_root/scripts/ci/release-governance-static-gate.sh" >"$fixture_root/gate.out" 2>&1; then
  printf '%s\n' 'Expected RC preflight permission fixture to fail.' >&2
  exit 1
fi
if ! rg -Fq 'rc-release preflight job must request only contents: read and actions: read for online P0 artifact verification' "$fixture_root/gate.out"; then
  cat "$fixture_root/gate.out" >&2
  exit 1
fi

printf '%s\n' '{"result":"pass","gate":"release-governance-static-fixtures"}'
