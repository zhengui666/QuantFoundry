#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

uv --directory "$repo_root/backend" run --frozen python - "$repo_root" <<'PY'
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
if "fetch-independent-review-report.sh" not in run_gate:
    errors.append("agent-change gate does not fetch an independent review artifact when no locator is supplied")

ci_script = read("scripts/ci.sh")
if 'run_backend mypy --explicit-package-bases app workers scheduler' not in ci_script:
    errors.append("backend mypy must run from backend cwd with explicit package bases")
if "backend-typecheck|backend-mypy" not in ci_script:
    errors.append("backend typecheck/mypy canonical entrypoint is missing")
makefile = read("Makefile")
for required in ("backend-lint", "backend-typecheck", "backend-mypy"):
    if required not in makefile:
        errors.append(f"Makefile lacks canonical backend gate target {required}")
if "release-check:\n\t@set -eu;" not in makefile or "QF_RELEASE_TAG is required for release-check" not in makefile:
    errors.append("Makefile release-check must fail closed when QF_RELEASE_TAG is missing")

p0_check = read("scripts/p0-check.sh")
for required in ("--offline-report", "GITHUB_TOKEN", "actions/artifacts", "releases/assets", "read_embedded_report", "zipfile", "role_content_types", "required_p0_ids", "allowed_verification_workflows", "did not complete successfully", "unauthorized verification workflow", "distinct GitHub Actions runs", "remote_verification", 'else "report"'):
    if required not in p0_check:
        errors.append(f"p0-check lacks required remote verification control: {required}")

release_script = read("scripts/release-evidence.sh")
for required in ('"checksums": {"algorithm": "sha256", "path": "SHA256SUMS"}', '"name": name, "source": source', "package-assets", "create-or-validate-draft", "create_or_validate_draft", "verify-remote-assets", "remote release assets do not exactly match the manifest inventory", "release asset inventory name collision", 'run-gate.sh" rc'):
    if required not in release_script:
        errors.append(f"release evidence manifest is missing {required}")

template = json.loads(read("docs/治理/release-evidence-manifest.template.json"))
if template.get("checksums") != {"algorithm": "sha256", "path": "SHA256SUMS"}:
    errors.append("release evidence template checksums field is not canonical")
release_assets = template.get("release_assets")
if not isinstance(release_assets, list) or not {"release-manifest.json", "SHA256SUMS"}.issubset({item.get("name") for item in release_assets if isinstance(item, dict)}):
    errors.append("release evidence template does not enumerate manifest and SHA256SUMS assets")
if any(not isinstance(item, dict) or set(item) != {"name", "source"} for item in release_assets or []):
    errors.append("release evidence template asset inventory is not canonical")

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
if "scripts/release-evidence.sh package-assets evidence" not in rc or "evidence/release-assets" not in rc or "--clobber" in rc:
    errors.append("rc-release does not package and upload unique release assets safely")
if "create-or-validate-draft" not in publish or "verify-remote-assets" not in rc or "gh release edit \"$TAG\" --draft=false" not in rc:
    errors.append("rc-release does not create-or-validate, remotely verify, and publish a draft release")
if "Create commit-bound draft release" in rc or "gh release create" in rc.split("  rc:", 1)[1].split("  publish:", 1)[0]:
    errors.append("rc-release must not create a draft from the read-only rc job")
if publish.index("create-or-validate-draft") > publish.index("docker/build-push-action"):
    errors.append("rc-release must create or validate the draft before image publication")

agent = read(".github/workflows/agent-change-gate.yml")
for required in ("AGENTS.md", "PROJECT_BACKGROUND.md", "docs/治理/**", ".github/workflows/**", "scripts/ci/**", "scripts/release*"):
    if required not in agent:
        errors.append(f"agent-change-gate path coverage misses {required}")
if "paths-ignore:" in agent or "independent_review_evidence" in agent or "review required" in agent:
    errors.append("agent-change-gate contains an unsafe exclusion or self-generated review placeholder")
if "QF_INDEPENDENT_REVIEW_REPORT" in agent or "docs/治理/independent-review-report.json" in agent:
    errors.append("agent-change-gate must not trust a repository-local review locator")
if not re.search(r"(?m)^permissions:\n  contents: read\n  actions: read$", agent):
    errors.append("agent-change-gate must request only the required actions: read permission for artifact verification")

independent_review = read(".github/workflows/independent-agent-review.yml")
if "workflow_dispatch:" not in independent_review or "independent-agent-review-${{ github.run_id }}" not in independent_review:
    errors.append("independent-agent-review workflow must produce a dispatch-only run-bound artifact")
for required in ("review_scope_sha256", "Independent Review Agent", "criteria", "commands", "actions/upload-artifact"):
    if required not in independent_review:
        errors.append(f"independent-agent-review workflow lacks {required}")

review_fetcher = read("scripts/ci/fetch-independent-review-report.sh")
for required in ("actions/workflows/independent-agent-review.yml/runs", "head_sha", "independent-agent-review-", "artifact_sha256"):
    if required not in review_fetcher:
        errors.append(f"independent review artifact fetcher lacks {required}")

review_verifier = read("scripts/ci/verify-independent-review-report.sh")
for required in ("artifact_report", "zipfile", "reviewed_paths", "review_scope_sha256", "criteria", 'run.get("status") != "completed"', 'run.get("conclusion") != "success"', "unauthorized workflow", "artifact report is not bound to the current commit and run"):
    if required not in review_verifier:
        errors.append(f"independent review verifier lacks artifact-content validation: {required}")

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
"$repo_root/scripts/p0-check-test.sh"
"$repo_root/scripts/ci/release-evidence-assets-test.sh"
"$repo_root/scripts/ci/verify-independent-review-report-test.sh"
