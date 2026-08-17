#!/usr/bin/env bash
set -euo pipefail

repo_root="${QF_RELEASE_GOVERNANCE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

uv --directory "$repo_root/backend" run --frozen python - "$repo_root" <<'PY'
import ast
import json
import pathlib
import re
import shlex
import sys

import yaml

root = pathlib.Path(sys.argv[1])
errors = []

def read(relative):
    return (root / relative).read_text(encoding="utf-8")

run_gate = read("scripts/ci/run-gate.sh")
run_rc_match = re.search(
    r'(?ms)^run_rc\(\) \{\n(?P<body>.*?)^case "\$gate" in', run_gate
)
run_rc_body = run_rc_match.group("body") if run_rc_match else ""
run_step_entries = re.findall(
    r"(?m)^\s*run_step\s+([A-Za-z0-9_-]+)\s+(.+?)\s*$", run_rc_body
)
run_step_calls = dict(run_step_entries)
run_agent_match = re.search(
    r"(?ms)^run_agent_change\(\) \{\n(?P<body>.*?)^\}\n\n",
    run_gate,
)
run_agent_body = run_agent_match.group("body") if run_agent_match else ""


def shell_command_nodes(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";|&()")
    lexer.commenters = "#"
    lexer.whitespace_split = True
    tokens = list(lexer)
    nodes = []
    current = []
    previous = None
    for token in tokens + [";"]:
        if token in {";", "&&", "||", "|", "(", ")"}:
            if current:
                nodes.append((previous, current))
            current = []
            previous = token
        else:
            current.append(token)
    expanded = []
    for operator, node in nodes:
        if (node[:1] == ["bash"] or node[:1] == ["sh"]) and "-c" in node:
            script = node[node.index("-c") + 1 :]
            if script:
                expanded.extend(shell_command_nodes(" ".join(script)))
        else:
            expanded.append((operator, node))
    return expanded


def contains_command(command, expected):
    wanted = shlex.split(expected, comments=True, posix=True)
    for operator, node in shell_command_nodes(command):
        if not node or node[0] in {"false", "true", "echo", "printf", "exit"}:
            continue
        actual = node[next((index for index, token in enumerate(node) if "=" not in token), 0) :]
        if actual[: len(wanted)] == wanted and operator != "&&":
            return True
        if wanted[0] in actual and actual[actual.index(wanted[0]) :][: len(wanted)] == wanted:
            return True
    return False


required_run_steps = {
    "known-issues-review": "scripts/release-known-issues-check.sh",
    "fresh-compose-migration": "make fullstack",
    "pg18-migration": "make pg18",
    "backup-restore": "tests/test_event_migration_and_bootstrap.py",
    "p0-require-closed-except-supply-chain": "scripts/p0-check.sh",
    "release-governance-static": "scripts/ci/release-governance-static-gate.sh",
}
for name, expected in required_run_steps.items():
    if name not in run_step_calls or not contains_command(run_step_calls[name], expected):
        errors.append(f"run-gate rc path is missing executable run_step {name}: {expected}")
if (
    "QF_INDEPENDENT_REVIEW_REPORT" not in run_agent_body
    or "verify-independent-review-report.sh" not in run_agent_body
):
    errors.append("agent-change gate does not require the bound independent review report")

ci_script = read("scripts/ci.sh")
if 'run_backend mypy --explicit-package-bases src/quantfoundry app workers scheduler' not in ci_script:
    errors.append("backend mypy must run from backend cwd with canonical and compatibility package bases")
if "backend-typecheck|backend-mypy" not in ci_script:
    errors.append("backend typecheck/mypy canonical entrypoint is missing")
makefile = read("Makefile")
for required in ("backend-lint", "backend-typecheck", "backend-mypy"):
    if required not in makefile:
        errors.append(f"Makefile lacks canonical backend gate target {required}")
if "release-check:\n\t@set -eu;" not in makefile or "QF_RELEASE_TAG is required for release-check" not in makefile:
    errors.append("Makefile release-check must fail closed when QF_RELEASE_TAG is missing")

p0_check = read("scripts/p0-check.sh")
p0_check_test = root / "scripts/p0-check-test.sh"
if not p0_check_test.is_file() or not p0_check_test.stat().st_mode & 0o111:
    errors.append("p0-check behavioral security test is missing or not executable")
for required in ("--offline-report", "--require-closed-except-supply-chain", "GITHUB_TOKEN", "actions/artifacts", "releases/assets", "read_embedded_report", "zipfile", "role_content_types", "required_p0_ids", "allowed_verification_workflows", "did not complete successfully", "unauthorized verification workflow", "distinct GitHub Actions runs", "remote_verification", 'else "report"'):
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
try:
    rc_document = yaml.safe_load(rc)
except yaml.YAMLError as error:
    errors.append(f"rc-release is not valid YAML: {error}")
    rc_document = {}
if not isinstance(rc_document, dict) or rc_document.get("permissions") != {"contents": "read"}:
    errors.append("rc-release top-level permissions must default to contents: read")
rc_jobs = rc_document.get("jobs", {}) if isinstance(rc_document, dict) else {}
for job in ("preflight", "rc"):
    if not isinstance(rc_jobs, dict) or not isinstance(rc_jobs.get(job), dict) or rc_jobs[job].get("permissions") != {"contents": "read", "actions": "read"}:
        errors.append(f"rc-release {job} job must request only contents: read and actions: read for online P0 artifact verification")
publish_job = rc_jobs.get("publish") if isinstance(rc_jobs, dict) else None
if not isinstance(publish_job, dict):
    errors.append("rc-release publish job is missing")
else:
    expected_publish_permissions = {
        "contents": "write",
        "packages": "write",
        "attestations": "write",
        "id-token": "write",
        "actions": "read",
    }
    if publish_job.get("permissions") != expected_publish_permissions:
        errors.append("rc-release publish job permissions are not the canonical minimal set")
    publish_runs = [
        step.get("run", "")
        for step in publish_job.get("steps", [])
        if isinstance(step, dict) and isinstance(step.get("run", ""), str)
    ]
    for required in (
        "scripts/release-evidence.sh create-or-validate-draft",
        "scripts/release-evidence.sh package-assets evidence",
        "scripts/release-evidence.sh verify-remote-assets",
        'gh release edit "$TAG" --draft=false',
    ):
        if not any(required in run for run in publish_runs):
            errors.append(f"rc-release publish job lacks executable control {required}")
if "scripts/ci/run-gate.sh rc" not in rc:
    errors.append("rc-release does not invoke the canonical rc run-gate entrypoint")
if "scripts/release-evidence.sh package-assets evidence" not in rc or "evidence/release-assets" not in rc or "--clobber" not in rc:
    errors.append("rc-release does not package and upload unique release assets safely")
if "verify-remote-assets" not in rc:
    errors.append("rc-release does not remotely verify the draft release")
if "Create commit-bound draft release" in rc or "gh release create" in rc.split("  rc:", 1)[1].split("  publish:", 1)[0]:
    errors.append("rc-release must not create a draft from the read-only rc job")
draft_step = next(
    (index for index, step in enumerate(publish_job.get("steps", []))
     if isinstance(step, dict) and "create-or-validate-draft" in step.get("run", "")),
    None,
)
image_step = next(
    (index for index, step in enumerate(publish_job.get("steps", []))
     if isinstance(step, dict) and step.get("uses", "").startswith("docker/build-push-action@")),
    None,
)
if draft_step is None or image_step is None or draft_step > image_step:
    errors.append("rc-release must create or validate the draft before image publication")

agent = read(".github/workflows/agent-change-gate.yml")
try:
    agent_document = yaml.safe_load(agent)
except yaml.YAMLError as error:
    errors.append(f"agent-change-gate is not valid YAML: {error}")
    agent_document = {}
for required in ("AGENTS.md", "PROJECT_BACKGROUND.md", "docs/治理/**", ".github/workflows/**", "scripts/ci/**", "scripts/release*"):
    if required not in agent:
        errors.append(f"agent-change-gate path coverage misses {required}")
if "paths-ignore:" in agent or "independent_review_evidence" in agent or "review required" in agent:
    errors.append("agent-change-gate contains an unsafe exclusion or self-generated review placeholder")
if "docs/治理/independent-review-report.json" in agent:
    errors.append("agent-change-gate must not trust a repository-local review locator")
if "actions/download-artifact" not in agent or "QF_INDEPENDENT_REVIEW_REPORT" not in agent or "needs: trusted-independent-review" not in agent:
    errors.append("agent-change-gate must depend on the bound independent review job")
agent_jobs = agent_document.get("jobs", {}) if isinstance(agent_document, dict) else {}
agent_contract_job = agent_jobs.get("agent-contract") if isinstance(agent_jobs, dict) else None
if isinstance(agent_contract_job, dict) and "GITHUB_TOKEN" in agent_contract_job.get("env", {}):
    errors.append("agent-change-gate agent-contract must not expose GITHUB_TOKEN to PR-controlled steps")
if not isinstance(agent_document, dict) or agent_document.get("permissions") != {"contents": "read", "actions": "read"}:
    errors.append("agent-change-gate must request only the required actions: read permission for artifact verification")

independent_review = read(".github/workflows/independent-agent-review.yml")
if "workflow_dispatch:" not in independent_review or "independent-agent-review-${{ github.run_id }}" not in independent_review:
    errors.append("independent-agent-review workflow must produce a dispatch-only run-bound artifact")
for required in ("build-p0-evidence.py", "Independent Review Agent", "qf-p0-review-evidence", "commands", "actions/upload-artifact"):
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

workflow_paths = sorted(
    [*root.joinpath(".github/workflows").glob("*.yml"), *root.joinpath(".github/workflows").glob("*.yaml")]
)
for workflow in workflow_paths:
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
if [[ "${QF_RELEASE_GOVERNANCE_SKIP_FIXTURES:-0}" != 1 ]]; then
  "$repo_root/scripts/ci/release-governance-static-gate-test.sh"
fi
