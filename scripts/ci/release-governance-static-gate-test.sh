#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fixture_root="$(mktemp -d)"
trap 'rm -rf "$fixture_root"' EXIT

if ! QF_RELEASE_GOVERNANCE_SKIP_FIXTURES=1 "$repo_root/scripts/ci/release-governance-static-gate.sh" >"$fixture_root/real-config.out" 2>&1; then
  cat "$fixture_root/real-config.out" >&2
  printf '%s\n' 'Expected the real RC permissions configuration to pass.' >&2
  exit 1
fi

git -C "$repo_root" archive --format=tar HEAD | tar --extract --file - --directory "$fixture_root"
cp "$repo_root/.github/workflows/rc-release.yml" "$fixture_root/.github/workflows/rc-release.yml"
for job in preflight rc; do
  python3 - "$fixture_root/.github/workflows/rc-release.yml" "$job" <<'PY'
import pathlib
import re
import sys

workflow = pathlib.Path(sys.argv[1])
job = sys.argv[2]
source = workflow.read_text(encoding="utf-8")
pattern = rf"(?ms)^(  {re.escape(job)}:\n.*?^    permissions:\n      contents: read\n)      actions: read\n"
if not re.search(pattern, source):
    raise SystemExit(f"fixture setup could not locate rc-release {job} actions: read permission")
workflow.write_text(re.sub(pattern, r"\1", source, count=1), encoding="utf-8")
PY

  if QF_RELEASE_GOVERNANCE_ROOT="$fixture_root" QF_RELEASE_GOVERNANCE_SKIP_FIXTURES=1 \
    "$repo_root/scripts/ci/release-governance-static-gate.sh" >"$fixture_root/$job-gate.out" 2>&1; then
    printf 'Expected RC %s permission fixture to fail.\n' "$job" >&2
    exit 1
  fi
  if ! grep -Fq "rc-release $job job must request only contents: read and actions: read for online P0 artifact verification" "$fixture_root/$job-gate.out"; then
    cat "$fixture_root/$job-gate.out" >&2
    exit 1
  fi

  cp "$repo_root/.github/workflows/rc-release.yml" "$fixture_root/.github/workflows/rc-release.yml"
done

python3 - "$fixture_root/.github/workflows/rc-release.yml" <<'PY'
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
text = text.replace("    permissions:\n      contents: read\n      actions: read\n", "    permissions:\n      contents: read\n      actions: read\n      packages: write\n", 1)
path.write_text(text, encoding="utf-8")
PY
if QF_RELEASE_GOVERNANCE_ROOT="$fixture_root" QF_RELEASE_GOVERNANCE_SKIP_FIXTURES=1 \
  "$repo_root/scripts/ci/release-governance-static-gate.sh" >"$fixture_root/extra-permission-gate.out" 2>&1; then
  printf '%s\n' 'Expected extra permission fixture to fail.' >&2
  exit 1
fi
grep -Fq 'rc-release preflight job must request only contents: read and actions: read' "$fixture_root/extra-permission-gate.out" || {
  cat "$fixture_root/extra-permission-gate.out" >&2
  exit 1
}

printf '%s\n' '{"result":"pass","gate":"release-governance-static-fixtures"}'
