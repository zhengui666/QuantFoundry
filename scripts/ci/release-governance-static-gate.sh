#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

python3 - "$repo_root" <<'PY'
import ast
import json
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1])
errors = []

def read(relative):
    return (root / relative).read_text(encoding="utf-8")

run_gate = read("scripts/ci/run-gate.sh")
for required in ("known-issues-review", "fresh-compose-migration", "pg18-migration", "backup-restore", "p0-require-closed", "release-governance-static"):
    if required not in run_gate:
        errors.append(f"run-gate rc path is missing {required}")
if "QF_INDEPENDENT_REVIEW_REPORT" not in run_gate or "verify-independent-review-report.sh" not in run_gate:
    errors.append("agent-change gate does not require and validate an independent review report")

p0_check = read("scripts/p0-check.sh")
for required in ("--offline-report", "GITHUB_TOKEN", "actions/artifacts", "releases/assets", "verify_ghcr", "remote_verification"):
    if required not in p0_check:
        errors.append(f"p0-check lacks required remote verification control: {required}")

release_script = read("scripts/release-evidence.sh")
for required in ('"checksums": {"algorithm": "sha256", "path": "SHA256SUMS"}', '"release-manifest.json", "SHA256SUMS"', 'run-gate.sh" rc'):
    if required not in release_script:
        errors.append(f"release evidence manifest is missing {required}")

template = json.loads(read("docs/治理/release-evidence-manifest.template.json"))
if template.get("checksums") != {"algorithm": "sha256", "path": "SHA256SUMS"}:
    errors.append("release evidence template checksums field is not canonical")
if not {"release-manifest.json", "SHA256SUMS"}.issubset(set(template.get("release_assets", []))):
    errors.append("release evidence template does not enumerate manifest and SHA256SUMS assets")

try:
    ast.parse(read("scripts/api_healthcheck.py"))
except SyntaxError as error:
    errors.append(f"api healthcheck is not Python AST-compatible: {error.msg}")

rc = read(".github/workflows/rc-release.yml")
if not re.search(r"(?m)^permissions:\n  contents: read$", rc):
    errors.append("rc-release top-level permissions must default to contents: read")
publish = rc.split("  publish:", 1)[-1]
for required in ("contents: write", "packages: write", "attestations: write", "id-token: write"):
    if required not in publish:
        errors.append(f"rc-release publish job lacks required scoped permission {required}")
if "scripts/ci/run-gate.sh rc" not in rc:
    errors.append("rc-release does not invoke the canonical rc run-gate entrypoint")

agent = read(".github/workflows/agent-change-gate.yml")
for required in ("AGENTS.md", "PROJECT_BACKGROUND.md", "docs/治理/**", ".github/workflows/**", "scripts/ci/**", "scripts/release*"):
    if required not in agent:
        errors.append(f"agent-change-gate path coverage misses {required}")
if "paths-ignore:" in agent or "independent_review_evidence" in agent or "review required" in agent:
    errors.append("agent-change-gate contains an unsafe exclusion or self-generated review placeholder")

for workflow in sorted((root / ".github/workflows").glob("*.yml")):
    text = workflow.read_text(encoding="utf-8")
    if "apt-get install --yes shellcheck" in text:
        errors.append(f"{workflow.relative_to(root)} installs an unpinned apt ShellCheck")
    if "scripts/ci/install-shellcheck.sh" not in text:
        errors.append(f"{workflow.relative_to(root)} does not use the verified ShellCheck installer")

installer = read("scripts/ci/install-shellcheck.sh")
if "shellcheck_version='0.10.0'" not in installer or "sha256sum --check --strict" not in installer:
    errors.append("ShellCheck installer lacks fixed version and checksum verification")

if errors:
    raise SystemExit("\n".join(errors))
print(json.dumps({"gate": "release-governance-static", "result": "pass"}, sort_keys=True))
PY
