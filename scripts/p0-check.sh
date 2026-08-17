#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
registry="${1:-$repo_root/docs/治理/p0-blockers.yaml}"
mode="${2:---require-closed}"

[[ "$mode" == "--offline-report" || "$mode" == "--report" || "$mode" == "--require-closed" || "$mode" == "--require-closed-except-supply-chain" ]] || {
  printf 'Usage: %s [registry] [--offline-report|--report|--require-closed|--require-closed-except-supply-chain]\n' "$0" >&2
  exit 2
}
[[ -f "$registry" ]] || { printf 'Missing P0 registry: %s\n' "$registry" >&2; exit 2; }
registry="$(cd "$(dirname "$registry")" && pwd)/$(basename "$registry")"
command -v uv >/dev/null || { printf '%s\n' 'uv is required to parse the canonical P0 registry.' >&2; exit 2; }

if [[ "$mode" == "--report" ]]; then
  mode="--offline-report"
fi

set +e
QF_RELEASE_REPO_ROOT="${QF_RELEASE_REPO_ROOT:-$repo_root}" QF_RELEASE_COMMIT="${QF_RELEASE_COMMIT:-$(git -C "$repo_root" rev-parse HEAD)}" \
  uv --directory "$repo_root/backend" run --frozen python - "$registry" "$mode" <<'PY'
import datetime as dt
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import zipfile
from urllib.parse import quote, urlparse

import yaml

registry_path = pathlib.Path(sys.argv[1])
mode = sys.argv[2]
strict_mode = mode in {"--require-closed", "--require-closed-except-supply-chain"}
bootstrap_mode = mode == "--require-closed-except-supply-chain"
expected_commit = os.environ["QF_RELEASE_COMMIT"]
repo_root = pathlib.Path(os.environ["QF_RELEASE_REPO_ROOT"])
sha_pattern = re.compile(r"^[0-9a-f]{40}$")
sha256_pattern = re.compile(r"^[0-9a-f]{64}$")
MAX_EVIDENCE_BYTES = 64 * 1024 * 1024
MAX_REPORT_BYTES = 8 * 1024 * 1024
github_build_pattern = re.compile(r"^github-actions/([1-9][0-9]*)$")
repository_pattern = re.compile(r"^[^/\s]+/[^/\s]+$")
placeholder_pattern = re.compile(r"(?i)^(?:placeholder|codeowners|todo|tbd|example|n/?a|unknown)$")
placeholder_token_pattern = re.compile(r"(?i)(?:\b(?:placeholder|codeowners|todo|tbd|example|unknown)\b|(?<![A-Za-z])n/?a(?![A-Za-z]))")
allowed_roles = {"Independent Test Agent", "Independent Review Agent"}
role_content_types = {
    "Independent Test Agent": "application/vnd.quantfoundry.p0-test-evidence+json;version=1",
    "Independent Review Agent": "application/vnd.quantfoundry.p0-review-evidence+json;version=1",
}
required_owner_roles = {
    "P0-PRODUCT-PAPER-DAILY-SCHEDULER": "Backend Agent",
    "P0-CONTRACT-OPENAPI-45": "API / Contract Agent",
    "P0-CONTRACT-TOOLS-13": "Agent-System Agent",
    "P0-SCHEMA-ALEMBIC-AUTHORITY": "Database Agent",
    "P0-ARCHITECTURE-TARGET-LAYERS": "Architecture / Implementation Agent",
    "P0-SECURITY-RESEARCH-INTEGRITY": "Security Agent",
    "P0-CI-REPRODUCIBILITY": "Test Agent",
    "P0-SUPPLY-CHAIN-RELEASE-EVIDENCE": "Release Agent",
}
required_p0_ids = {
    "P0-PRODUCT-PAPER-DAILY-SCHEDULER",
    "P0-CONTRACT-OPENAPI-45",
    "P0-CONTRACT-TOOLS-13",
    "P0-SCHEMA-ALEMBIC-AUTHORITY",
    "P0-ARCHITECTURE-TARGET-LAYERS",
    "P0-SECURITY-RESEARCH-INTEGRITY",
    "P0-CI-REPRODUCIBILITY",
    "P0-SUPPLY-CHAIN-RELEASE-EVIDENCE",
}
allowed_verification_workflows = {
    "Independent Test Agent": {".github/workflows/independent-agent-test.yml"},
    "Independent Review Agent": {".github/workflows/independent-agent-review.yml"},
}
trusted_verification_workflow_blobs = {
    ".github/workflows/independent-agent-test.yml": "697e21c0cf03b7f1605ca7eb40b9a0281ff7f399",
    ".github/workflows/independent-agent-review.yml": "51bf6299bb3c1a290530efe7a99a6e043a43359d",
}

head_commit = subprocess.run(
    ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
    check=True,
    text=True,
    stdout=subprocess.PIPE,
).stdout.strip()
if not sha_pattern.fullmatch(expected_commit) or expected_commit != head_commit:
    raise SystemExit("QF_RELEASE_COMMIT must be the full lowercase checked-out HEAD SHA")


def invalid_value(value):
    return not isinstance(value, str) or not value.strip() or bool(placeholder_pattern.fullmatch(value.strip()))


def valid_timestamp(value):
    if invalid_value(value) or "T" not in value or not value.endswith("Z"):
        return False
    try:
        dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


def safe_report_path(value):
    return isinstance(value, str) and bool(value) and not value.startswith("/") and all(part not in {"", ".", ".."} for part in value.split("/"))


def parse_artifact_uri(value):
    if invalid_value(value) or value != value.strip():
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.netloc != "github.com" or parsed.username or parsed.password:
        return None
    action_match = re.fullmatch(r"/([^/]+/[^/]+)/actions/runs/([1-9][0-9]*)/artifacts/([1-9][0-9]*)", parsed.path)
    if action_match:
        return ("actions", action_match.group(1), action_match.group(2), action_match.group(3))
    return None


def validate_commands(prefix, commands, errors):
    if not isinstance(commands, list) or not commands:
        errors.append(f"{prefix}.commands must contain verified commands")
        return
    for command_index, command in enumerate(commands):
        command_prefix = f"{prefix}.commands[{command_index}]"
        if not isinstance(command, dict):
            errors.append(f"{command_prefix} must be an object")
            continue
        command_text = command.get("command")
        if invalid_value(command_text) or "\n" in command_text:
            errors.append(f"{command_prefix}.command must be a non-placeholder single command")
        if invalid_value(command.get("result")):
            errors.append(f"{command_prefix}.result is required")
        if command.get("exit_code") != 0:
            errors.append(f"{command_prefix}.exit_code must be 0")


def validate_report_metadata(prefix, record, role, run_id, errors):
    report = record.get("report")
    if not isinstance(report, dict) or set(report) != {"path", "sha256", "content_type"}:
        errors.append(f"{prefix}.report must contain exactly path, sha256, and content_type")
        return None
    if not safe_report_path(report["path"]):
        errors.append(f"{prefix}.report.path must be a safe relative ZIP member path")
    if not isinstance(report["sha256"], str) or not sha256_pattern.fullmatch(report["sha256"]):
        errors.append(f"{prefix}.report.sha256 must be a lowercase SHA-256")
    if report["content_type"] != role_content_types.get(role):
        errors.append(f"{prefix}.report.content_type must match verifier_role")
    return report


def validate_attestation(prefix, record, run_id, report_sha256, repository, errors):
    attestation = record.get("attestation")
    required_keys = {"provider", "issuer", "repository", "run_id", "subject_uri", "subject_sha256"}
    if not isinstance(attestation, dict) or set(attestation) != required_keys:
        errors.append(f"{prefix}.attestation must contain the canonical GitHub Actions metadata")
        return None
    if attestation.get("provider") != "github-actions":
        errors.append(f"{prefix}.attestation.provider must be github-actions")
    if attestation.get("issuer") != "https://token.actions.githubusercontent.com":
        errors.append(f"{prefix}.attestation.issuer is invalid")
    if not isinstance(attestation.get("repository"), str) or not repository_pattern.fullmatch(attestation["repository"]):
        errors.append(f"{prefix}.attestation.repository must be an owner/repository value")
    if attestation.get("run_id") != run_id:
        errors.append(f"{prefix}.attestation.run_id must match build_id")
    run_uri = f"https://github.com/{repository}/actions/runs/{run_id}"
    if attestation.get("subject_uri") != run_uri:
        errors.append(f"{prefix}.attestation.subject_uri must match the stable GitHub Actions run URI")
    if attestation.get("subject_sha256") != report_sha256:
        errors.append(f"{prefix}.attestation.subject_sha256 must match report.sha256")
    return attestation


class RemoteVerifier:
    def __init__(self):
        self.repository = os.environ.get("GITHUB_REPOSITORY", "")
        self.token = os.environ.get("GITHUB_TOKEN", "")
        if not repository_pattern.fullmatch(self.repository):
            raise RuntimeError("GITHUB_REPOSITORY is required for online P0 closure verification")
        if not self.token:
            raise RuntimeError("GITHUB_TOKEN is required for online P0 closure verification")
        if not shutil_which("gh"):
            raise RuntimeError("gh is required for online P0 closure verification")
        self.env = os.environ.copy()
        self.env["GH_TOKEN"] = self.token

    def gh_json(self, endpoint):
        completed = subprocess.run(
            ["gh", "api", endpoint], env=self.env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        if completed.returncode:
            raise RuntimeError(f"gh api failed for {endpoint}: {completed.stderr.strip() or completed.returncode}")
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise RuntimeError(f"gh api returned non-JSON for {endpoint}") from error

    def gh_download(self, endpoint):
        with tempfile.TemporaryDirectory(prefix="qf-p0-evidence-") as directory:
            destination = pathlib.Path(directory) / "evidence.zip"
            with tempfile.TemporaryFile() as stderr_file, destination.open("wb") as archive_file:
                process = subprocess.Popen(
                    [
                        "gh",
                        "api",
                        endpoint,
                        "--method",
                        "GET",
                        *(["--header", "Accept: application/octet-stream"] if "/actions/artifacts/" in endpoint else []),
                    ],
                    env=self.env,
                    stdout=archive_file,
                    stderr=stderr_file,
                )
                return_code = process.wait()
                stderr_file.seek(0)
                stderr = stderr_file.read(64 * 1024).decode(errors="replace").strip()
            if destination.stat().st_size > MAX_EVIDENCE_BYTES:
                raise RuntimeError("downloaded evidence exceeds the size limit")
            if return_code:
                raise RuntimeError(f"gh api download failed for {endpoint}: {stderr or return_code}")
            if destination.stat().st_size > MAX_EVIDENCE_BYTES:
                raise RuntimeError("downloaded evidence exceeds the size limit")
            try:
                return destination.read_bytes()
            except OSError as error:
                raise RuntimeError(f"gh api did not create downloaded evidence for {endpoint}") from error

    def require_run(self, run_id, commit, role):
        run = self.gh_json(f"/repos/{self.repository}/actions/runs/{run_id}")
        if run.get("head_sha") != commit:
            raise RuntimeError(f"GitHub Actions run {run_id} is not bound to commit {commit}")
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            raise RuntimeError(f"GitHub Actions run {run_id} did not complete successfully")
        workflow_path = run.get("path", "")
        if workflow_path not in allowed_verification_workflows[role] or run.get("head_branch") != "main":
            raise RuntimeError(f"GitHub Actions run {run_id} used an unauthorized verification workflow")
        workflow_source = self.gh_json(
            f"/repos/{self.repository}/contents/{quote(workflow_path, safe='')}"
            f"?ref={quote(commit, safe='')}"
        )
        if workflow_source.get("sha") != trusted_verification_workflow_blobs[workflow_path]:
            raise RuntimeError(f"GitHub Actions run {run_id} used an untrusted workflow revision")

    def resolve_tag_commit(self, tag):
        ref = self.gh_json(f"/repos/{self.repository}/git/ref/tags/{quote(tag, safe='')}")
        obj = ref.get("object", {})
        while obj.get("type") == "tag":
            obj = self.gh_json(f"/repos/{self.repository}/git/tags/{obj.get('sha', '')}").get("object", {})
        if obj.get("type") != "commit" or not sha_pattern.fullmatch(obj.get("sha", "")):
            raise RuntimeError(f"tag {tag} does not resolve to a commit")
        return obj["sha"]

    @staticmethod
    def require_sha256(blob, expected):
        actual = hashlib.sha256(blob).hexdigest()
        if actual != expected:
            raise RuntimeError(f"download SHA-256 mismatch: expected {expected}, got {actual}")

    def download_evidence(self, uri, commit, run_id, role, expected_sha256):
        parsed = parse_artifact_uri(uri)
        if not parsed:
            raise RuntimeError("unsupported remote evidence URI")
        transport, repository, first, second = parsed
        if repository != self.repository:
            raise RuntimeError("remote evidence URI repository does not match GITHUB_REPOSITORY")
        if transport != "actions":
            raise RuntimeError("P0 closure evidence must use a GitHub Actions artifact")
        self.require_run(run_id, commit, role)
        if transport == "actions":
            artifact_run_id, artifact_id = first, second
            if artifact_run_id != str(run_id):
                raise RuntimeError("artifact URL run id does not match build_id")
            artifact = self.gh_json(f"/repos/{self.repository}/actions/artifacts/{artifact_id}")
            if (
                artifact.get("expired")
                or artifact.get("workflow_run", {}).get("id") != run_id
                or not isinstance(artifact.get("size_in_bytes"), int)
                or artifact["size_in_bytes"] > MAX_EVIDENCE_BYTES
            ):
                raise RuntimeError(f"Actions artifact {artifact_id} is missing, expired, or not bound to run {run_id}")
            blob = self.gh_download(f"/repos/{self.repository}/actions/artifacts/{artifact_id}/zip")
        self.require_sha256(blob, expected_sha256)
        return blob


def shutil_which(name):
    for candidate in os.environ.get("PATH", "").split(os.pathsep):
        path = pathlib.Path(candidate) / name
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return None


def read_embedded_report(blob, report_path, expected_sha256):
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            matches = [member for member in archive.infolist() if member.filename == report_path and not member.is_dir()]
            if len(matches) != 1:
                raise RuntimeError("evidence ZIP must contain exactly one declared report_path")
            if matches[0].file_size > MAX_REPORT_BYTES:
                raise RuntimeError("embedded evidence report exceeds the size limit")
            payload = archive.read(matches[0])
    except (OSError, zipfile.BadZipFile) as error:
        raise RuntimeError(f"evidence object is not a readable ZIP: {error}") from error
    if hashlib.sha256(payload).hexdigest() != expected_sha256:
        raise RuntimeError("embedded evidence report SHA-256 does not match registry")
    try:
        report = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise RuntimeError(f"embedded evidence report is not JSON: {error}") from error
    if not isinstance(report, dict):
        raise RuntimeError("embedded evidence report must be a JSON object")
    return report


def validate_embedded_report(prefix, report, record, role, run_id, remote, errors):
    expected_fields = {
        "schema_version", "content_type", "commit_sha", "github_run_id", "verifier_role", "verified_at_utc",
        "closure_criteria", "commands", "artifact", "attestation",
    }
    if set(report) != expected_fields:
        errors.append(f"{prefix}.embedded_report has an invalid field set")
        return
    report_meta = record["report"]
    if report.get("schema_version") != "1.0.0":
        errors.append(f"{prefix}.embedded_report.schema_version must be 1.0.0")
    if report.get("content_type") != report_meta["content_type"]:
        errors.append(f"{prefix}.embedded_report.content_type does not match registry")
    if report.get("commit_sha") != record.get("commit_sha"):
        errors.append(f"{prefix}.embedded_report.commit_sha does not match verification commit")
    if report.get("github_run_id") != run_id:
        errors.append(f"{prefix}.embedded_report.github_run_id does not match build_id")
    if report.get("verifier_role") != role:
        errors.append(f"{prefix}.embedded_report.verifier_role does not match registry")
    if report.get("verified_at_utc") != record.get("verified_at_utc"):
        errors.append(f"{prefix}.embedded_report.verified_at_utc does not match registry")
    if report.get("closure_criteria") != record.get("closure_criteria"):
        errors.append(f"{prefix}.embedded_report.closure_criteria does not match registry")
    if report.get("commands") != record.get("commands"):
        errors.append(f"{prefix}.embedded_report.commands does not match registry")
    run_uri = f"https://github.com/{remote.repository}/actions/runs/{run_id}"
    if report.get("artifact") != {"run_uri": run_uri}:
        errors.append(f"{prefix}.embedded_report.artifact does not match the stable run URI")
    embedded_attestation = {key: value for key, value in record["attestation"].items() if key != "subject_sha256"}
    if report.get("attestation") != embedded_attestation:
        errors.append(f"{prefix}.embedded_report.attestation does not match registry")
    if record["attestation"].get("repository") != remote.repository:
        errors.append(f"{prefix}.attestation.repository does not match GITHUB_REPOSITORY")


def validate_closed_evidence(blocker_id, item, remote):
    errors = []
    criteria = item.get("closure_criteria")
    evidence = item.get("evidence")
    if not isinstance(criteria, list) or not criteria or any(invalid_value(value) for value in criteria):
        return [f"{blocker_id}: closed blocker requires non-empty closure_criteria strings"]
    if not isinstance(evidence, list) or not evidence:
        return [f"{blocker_id}: closed release blocker requires structured closure evidence"]

    covered_criteria = set()
    roles = set()
    role_runs = {role: set() for role in allowed_roles}
    role_criteria = {role: set() for role in allowed_roles}
    for index, record in enumerate(evidence):
        prefix = f"{blocker_id}: evidence[{index}]"
        record_error_count = len(errors)
        if not isinstance(record, dict):
            errors.append(f"{prefix} must be an object")
            continue
        owner_role = item.get("owner_role")
        expected_owner_role = required_owner_roles.get(blocker_id)
        if owner_role != expected_owner_role:
            errors.append(
                f"{blocker_id}: owner_role must be {expected_owner_role!r}"
            )
        role = record.get("verifier_role")
        if role not in allowed_roles or role == owner_role:
            errors.append(f"{prefix}.verifier_role must be an independent Test or Review Agent")
        else:
            roles.add(role)
        if not valid_timestamp(record.get("verified_at_utc")):
            errors.append(f"{prefix}.verified_at_utc must be a non-placeholder UTC timestamp")
        commit_sha = record.get("commit_sha")
        if not isinstance(commit_sha, str) or not sha_pattern.fullmatch(commit_sha):
            errors.append(f"{prefix}.commit_sha must be a full lowercase 40-character SHA")
        elif commit_sha != expected_commit:
            errors.append(f"{prefix}.commit_sha must equal the current release commit")
        build_id = record.get("build_id")
        build_match = github_build_pattern.fullmatch(build_id) if isinstance(build_id, str) else None
        if not build_match:
            errors.append(f"{prefix}.build_id must be a GitHub Actions run identity")
            run_id = None
        else:
            run_id = int(build_match.group(1))
            if role in allowed_roles:
                role_runs[role].add(run_id)
        uri = record.get("artifact_uri")
        parsed_uri = parse_artifact_uri(uri)
        if not parsed_uri:
            errors.append(f"{prefix}.artifact_uri must be a GitHub Actions artifact URI")
        artifact_sha256 = record.get("artifact_sha256")
        if not isinstance(artifact_sha256, str) or not sha256_pattern.fullmatch(artifact_sha256):
            errors.append(f"{prefix}.artifact_sha256 must be a lowercase SHA-256")
        report = validate_report_metadata(prefix, record, role, run_id, errors)
        attestation = validate_attestation(
            prefix, record, run_id, report["sha256"] if report else None, remote.repository if remote else "", errors
        )
        record_criteria = record.get("closure_criteria")
        if not isinstance(record_criteria, list) or not record_criteria:
            errors.append(f"{prefix}.closure_criteria must cover one or more canonical criteria")
        else:
            for criterion in record_criteria:
                if criterion not in criteria:
                    errors.append(f"{prefix}.closure_criteria contains a non-canonical criterion")
                else:
                    covered_criteria.add(criterion)
                    if role in allowed_roles and role != item.get("owner_role"):
                        role_criteria[role].add(criterion)
        validate_commands(prefix, record.get("commands"), errors)
        if remote and len(errors) == record_error_count:
            try:
                blob = remote.download_evidence(uri, commit_sha, run_id, role, artifact_sha256)
                embedded_report = read_embedded_report(blob, report["path"], report["sha256"])
                validate_embedded_report(prefix, embedded_report, record, role, run_id, remote, errors)
            except (RuntimeError, OSError) as error:
                errors.append(f"{prefix}.remote_verification failed: {error}")
    missing_criteria = set(criteria) - covered_criteria
    if missing_criteria:
        errors.append(f"{blocker_id}: evidence does not cover every closure criterion")
    if roles != allowed_roles:
        errors.append(f"{blocker_id}: evidence requires separate Independent Test Agent and Independent Review Agent records")
    for role in allowed_roles:
        missing_for_role = set(criteria) - role_criteria[role]
        if missing_for_role:
            errors.append(f"{blocker_id}: {role} evidence does not cover every closure criterion")
    if role_runs["Independent Test Agent"] & role_runs["Independent Review Agent"]:
        errors.append(f"{blocker_id}: Independent Test and Review evidence must use distinct GitHub Actions runs")
    return errors


try:
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
except (OSError, UnicodeError, yaml.YAMLError) as error:
    print(json.dumps({"registry": str(registry_path), "result": "invalid", "error": str(error)}, ensure_ascii=False))
    raise SystemExit(2)

if (
    not isinstance(registry, dict)
    or registry.get("version") != "1.0.0"
    or not isinstance(registry.get("blockers"), list)
):
    print(json.dumps({"registry": str(registry_path), "result": "invalid", "error": "blockers list is required"}, ensure_ascii=False))
    raise SystemExit(2)

invalid = []
registry_ids = []
for index, item in enumerate(registry["blockers"]):
    if not isinstance(item, dict):
        invalid.append(f"blockers[{index}] must be an object")
        continue
    blocker_id = item.get("id")
    if not isinstance(blocker_id, str) or not blocker_id:
        invalid.append(f"blockers[{index}] has an invalid id")
        continue
    registry_ids.append(blocker_id)
    if blocker_id not in required_p0_ids:
        invalid.append(f"{blocker_id}: unknown P0 ID")
    if item.get("release_blocking") is not True:
        invalid.append(f"{blocker_id}: release_blocking must be true")
    if item.get("status") not in {"open", "blocked", "closed"}:
        invalid.append(f"{blocker_id}: unknown status")
duplicate_ids = {blocker_id for blocker_id in registry_ids if registry_ids.count(blocker_id) > 1}
if duplicate_ids:
    invalid.extend(f"{blocker_id}: duplicate P0 ID" for blocker_id in sorted(duplicate_ids))
missing_ids = required_p0_ids - set(registry_ids)
if missing_ids:
    invalid.extend(f"{blocker_id}: required P0 ID is missing" for blocker_id in sorted(missing_ids))

closed_items = [item for item in registry["blockers"] if isinstance(item, dict) and item.get("release_blocking") and item.get("status") == "closed"]
remote = None
remote_error = None
if strict_mode and closed_items:
    try:
        remote = RemoteVerifier()
    except RuntimeError as error:
        remote_error = str(error)

blocking = []
for item in registry["blockers"]:
    if not isinstance(item, dict):
        invalid.append("non-object blocker")
        continue
    blocker_id = item.get("id")
    status = item.get("status")
    release_blocking = item.get("release_blocking")
    if not isinstance(blocker_id, str) or status not in {"open", "blocked", "closed"} or not isinstance(release_blocking, bool):
        invalid.append(str(blocker_id or "unknown"))
        continue
    if release_blocking:
        if strict_mode and status == "closed":
            if remote_error:
                invalid.append(f"{blocker_id}: remote closure verification unavailable: {remote_error}")
            invalid.extend(validate_closed_evidence(blocker_id, item, remote))
        blocking.append({"id": blocker_id, "status": status, "evidence_count": len(item.get("evidence", [])) if isinstance(item.get("evidence", []), list) else 0})

unclosed = [item for item in blocking if item["status"] != "closed"]
non_supply_unclosed = [item for item in unclosed if item["id"] != "P0-SUPPLY-CHAIN-RELEASE-EVIDENCE"]
supply_unclosed = [item for item in unclosed if item["id"] == "P0-SUPPLY-CHAIN-RELEASE-EVIDENCE"]
bootstrap_eligible = bootstrap_mode and not invalid and not non_supply_unclosed and (
    not supply_unclosed
    or (len(supply_unclosed) == 1 and supply_unclosed[0]["status"] == "blocked")
)
summary = {
    "registry": str(registry_path),
    "mode": mode,
    "commit": expected_commit,
    "result": (
        "invalid"
        if invalid
        else "report"
        if mode == "--offline-report"
        else "pass"
        if not unclosed
        else "bootstrap-pass"
        if bootstrap_eligible
        else "blocked"
    ),
    "release_eligible": mode == "--require-closed" and not invalid and not unclosed,
    "bootstrap_eligible": bootstrap_eligible,
    "remote_verification": "performed" if remote else ("not-required" if not closed_items else "unavailable"),
    "release_blocking_total": len(blocking),
    "closed": sum(item["status"] == "closed" for item in blocking),
    "unclosed": unclosed,
    "invalid": invalid,
}
print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
if invalid or (mode == "--require-closed" and unclosed) or (bootstrap_mode and not bootstrap_eligible):
    raise SystemExit(1)
PY
status="$?"
set -e
exit "$status"
