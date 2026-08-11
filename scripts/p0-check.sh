#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
registry="${1:-$repo_root/docs/治理/p0-blockers.yaml}"
mode="${2:---require-closed}"

[[ "$mode" == "--offline-report" || "$mode" == "--report" || "$mode" == "--require-closed" ]] || {
  printf 'Usage: %s [registry] [--offline-report|--report|--require-closed]\n' "$0" >&2
  exit 2
}
[[ -f "$registry" ]] || { printf 'Missing P0 registry: %s\n' "$registry" >&2; exit 2; }
registry="$(cd "$(dirname "$registry")" && pwd)/$(basename "$registry")"
command -v uv >/dev/null || { printf '%s\n' 'uv is required to parse the canonical P0 registry.' >&2; exit 2; }

if [[ "$mode" == "--report" ]]; then
  mode="--offline-report"
fi

set +e
QF_RELEASE_COMMIT="${QF_RELEASE_COMMIT:-$(git -C "$repo_root" rev-parse HEAD)}" \
  uv --directory "$repo_root/backend" run --frozen python - "$registry" "$mode" <<'PY'
import base64
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from urllib.parse import quote, unquote, urlparse
from urllib.request import Request, urlopen

import yaml

registry_path = pathlib.Path(sys.argv[1])
mode = sys.argv[2]
expected_commit = os.environ["QF_RELEASE_COMMIT"]
sha_pattern = re.compile(r"^[0-9a-f]{40}$")
sha256_pattern = re.compile(r"^[0-9a-f]{64}$")
github_build_pattern = re.compile(r"^github-actions/[1-9][0-9]*$")
placeholder_pattern = re.compile(r"(?i)(placeholder|codeowners|todo|tbd|example|n/?a|unknown)")
allowed_roles = {"Independent Test Agent", "Independent Review Agent"}


def invalid_value(value):
    return not isinstance(value, str) or not value.strip() or bool(placeholder_pattern.search(value))


def valid_artifact_uri(value):
    if invalid_value(value) or value != value.strip():
        return False
    parsed = urlparse(value)
    if parsed.scheme == "https" and parsed.netloc == "github.com" and not parsed.username and not parsed.password:
        return bool(re.fullmatch(
            r"/[^/]+/[^/]+/(actions/runs/[1-9][0-9]*/artifacts/[1-9][0-9]*|releases/download/[^/]+/[^/]+)",
            parsed.path,
        ))
    return parsed.scheme == "oci" and parsed.netloc == "ghcr.io" and bool(
        re.fullmatch(r"/[^/]+/[^/@]+@sha256:[0-9a-f]{64}", parsed.path)
    )


def valid_timestamp(value):
    if invalid_value(value) or not value.endswith("Z"):
        return False
    try:
        dt.datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return True


class RemoteVerifier:
    def __init__(self):
        self.repository = os.environ.get("GITHUB_REPOSITORY", "")
        self.token = os.environ.get("GITHUB_TOKEN", "")
        if not re.fullmatch(r"[^/\s]+/[^/\s]+", self.repository):
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

    def gh_download(self, endpoint, destination):
        completed = subprocess.run(
            ["gh", "api", endpoint, "--method", "GET", "-H", "Accept: application/octet-stream", "--output", str(destination)],
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode:
            raise RuntimeError(f"gh api download failed for {endpoint}: {completed.stderr.strip() or completed.returncode}")

    def require_run(self, run_id, commit):
        run = self.gh_json(f"/repos/{self.repository}/actions/runs/{run_id}")
        if run.get("head_sha") != commit:
            raise RuntimeError(f"GitHub Actions run {run_id} is not bound to commit {commit}")

    def resolve_tag_commit(self, tag):
        ref = self.gh_json(f"/repos/{self.repository}/git/ref/tags/{quote(tag, safe='')}")
        obj = ref.get("object", {})
        while obj.get("type") == "tag":
            obj = self.gh_json(f"/repos/{self.repository}/git/tags/{obj.get('sha', '')}").get("object", {})
        if obj.get("type") != "commit" or not sha_pattern.fullmatch(obj.get("sha", "")):
            raise RuntimeError(f"tag {tag} does not resolve to a commit")
        return obj["sha"]

    @staticmethod
    def require_sha256(path, expected):
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError(f"download SHA-256 mismatch: expected {expected}, got {actual}")

    def verify_actions_artifact(self, run_id, artifact_id, commit, expected_sha256):
        artifact = self.gh_json(f"/repos/{self.repository}/actions/artifacts/{artifact_id}")
        if artifact.get("expired") or artifact.get("workflow_run", {}).get("id") != int(run_id):
            raise RuntimeError(f"Actions artifact {artifact_id} is missing, expired, or not bound to run {run_id}")
        self.require_run(run_id, commit)
        with tempfile.TemporaryDirectory(prefix="qf-p0-artifact-") as directory:
            download = pathlib.Path(directory) / "artifact.zip"
            self.gh_download(f"/repos/{self.repository}/actions/artifacts/{artifact_id}/zip", download)
            self.require_sha256(download, expected_sha256)

    def verify_release_asset(self, tag, asset_name, commit, expected_sha256):
        if self.resolve_tag_commit(tag) != commit:
            raise RuntimeError(f"release tag {tag} is not bound to commit {commit}")
        release = self.gh_json(f"/repos/{self.repository}/releases/tags/{quote(tag, safe='')}")
        asset = next((item for item in release.get("assets", []) if item.get("name") == asset_name), None)
        if not asset or not isinstance(asset.get("id"), int):
            raise RuntimeError(f"release asset {asset_name} is not present on release {tag}")
        with tempfile.TemporaryDirectory(prefix="qf-p0-release-") as directory:
            download = pathlib.Path(directory) / asset_name
            self.gh_download(f"/repos/{self.repository}/releases/assets/{asset['id']}", download)
            self.require_sha256(download, expected_sha256)

    def verify_ghcr(self, uri, commit, expected_sha256):
        parsed = urlparse(uri)
        repository, digest = parsed.path.lstrip("/").split("@", 1)
        if digest.removeprefix("sha256:") != expected_sha256:
            raise RuntimeError("GHCR URI digest and artifact_sha256 differ")
        token_request = Request(
            "https://ghcr.io/token?service=ghcr.io&scope=" + quote(f"repository:{repository}:pull", safe=":"),
            headers={"Authorization": "Basic " + base64.b64encode(f"x-access-token:{self.token}".encode()).decode()},
        )
        try:
            with urlopen(token_request, timeout=20) as response:
                bearer = json.loads(response.read()).get("token")
        except OSError as error:
            raise RuntimeError(f"cannot obtain GHCR read token: {error}") from error
        if not isinstance(bearer, str) or not bearer:
            raise RuntimeError("GHCR token endpoint returned no pull token")

        accept = ", ".join((
            "application/vnd.oci.image.index.v1+json",
            "application/vnd.docker.distribution.manifest.list.v2+json",
            "application/vnd.oci.image.manifest.v1+json",
            "application/vnd.docker.distribution.manifest.v2+json",
        ))

        def get(path, accept_header=accept):
            request = Request(
                f"https://ghcr.io/v2/{repository}/{path}",
                headers={"Authorization": f"Bearer {bearer}", "Accept": accept_header},
            )
            try:
                with urlopen(request, timeout=20) as response:
                    content_digest = response.headers.get("Docker-Content-Digest")
                    return json.loads(response.read()), content_digest
            except OSError as error:
                raise RuntimeError(f"cannot read GHCR object {path}: {error}") from error

        manifest, manifest_digest = get(f"manifests/{digest}")
        if manifest_digest != digest:
            raise RuntimeError(f"GHCR manifest digest mismatch: expected {digest}, got {manifest_digest}")
        if "manifests" in manifest:
            descriptor = next((item for item in manifest["manifests"] if item.get("platform", {}).get("os") == "linux"), None)
            if not descriptor or not isinstance(descriptor.get("digest"), str):
                raise RuntimeError("GHCR index has no Linux image manifest")
            manifest, _ = get(f"manifests/{descriptor['digest']}")
        config = manifest.get("config", {})
        config_digest = config.get("digest")
        if not isinstance(config_digest, str):
            raise RuntimeError("GHCR image manifest has no config digest")
        config_json, _ = get(f"blobs/{config_digest}", "application/vnd.oci.image.config.v1+json")
        revision = config_json.get("config", {}).get("Labels", {}).get("org.opencontainers.image.revision")
        if revision != commit:
            raise RuntimeError(f"GHCR image revision is not bound to commit {commit}")


def shutil_which(name):
    for candidate in os.environ.get("PATH", "").split(os.pathsep):
        path = pathlib.Path(candidate) / name
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return None


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
    for index, record in enumerate(evidence):
        prefix = f"{blocker_id}: evidence[{index}]"
        record_error_count = len(errors)
        if not isinstance(record, dict):
            errors.append(f"{prefix} must be an object")
            continue
        role = record.get("verifier_role")
        if role not in allowed_roles or role == item.get("owner_role"):
            errors.append(f"{prefix}.verifier_role must be an independent Test or Review Agent")
        else:
            roles.add(role)
        if not valid_timestamp(record.get("verified_at_utc")):
            errors.append(f"{prefix}.verified_at_utc must be a non-placeholder UTC timestamp")
        commit_sha = record.get("commit_sha")
        if not isinstance(commit_sha, str) or not sha_pattern.fullmatch(commit_sha):
            errors.append(f"{prefix}.commit_sha must be a full lowercase 40-character SHA")
        elif commit_sha != expected_commit:
            errors.append(f"{prefix}.commit_sha does not match current release commit")
        build_id = record.get("build_id")
        if not isinstance(build_id, str) or not github_build_pattern.fullmatch(build_id):
            errors.append(f"{prefix}.build_id must be a GitHub Actions run identity")
        uri = record.get("artifact_uri")
        if not valid_artifact_uri(uri):
            errors.append(f"{prefix}.artifact_uri must be an immutable remote HTTPS or GHCR OCI locator")
        artifact_sha256 = record.get("artifact_sha256")
        if not isinstance(artifact_sha256, str) or not sha256_pattern.fullmatch(artifact_sha256):
            errors.append(f"{prefix}.artifact_sha256 must be a lowercase SHA-256")
        elif isinstance(uri, str) and uri.startswith("oci://") and not uri.endswith(f"@sha256:{artifact_sha256}"):
            errors.append(f"{prefix}.artifact_sha256 must match the GHCR OCI digest")
        record_criteria = record.get("closure_criteria")
        if not isinstance(record_criteria, list) or not record_criteria:
            errors.append(f"{prefix}.closure_criteria must cover one or more canonical criteria")
        else:
            for criterion in record_criteria:
                if criterion not in criteria:
                    errors.append(f"{prefix}.closure_criteria contains a non-canonical criterion")
                else:
                    covered_criteria.add(criterion)
        commands = record.get("commands")
        if not isinstance(commands, list) or not commands:
            errors.append(f"{prefix}.commands must contain verified commands")
        else:
            for command_index, command in enumerate(commands):
                command_prefix = f"{prefix}.commands[{command_index}]"
                if not isinstance(command, dict):
                    errors.append(f"{command_prefix} must be an object")
                    continue
                if invalid_value(command.get("command")) or "\n" in command["command"]:
                    errors.append(f"{command_prefix}.command must be a non-placeholder single command")
                if invalid_value(command.get("result")):
                    errors.append(f"{command_prefix}.result is required")
                if command.get("exit_code") != 0:
                    errors.append(f"{command_prefix}.exit_code must be 0")
        if remote and len(errors) == record_error_count:
            try:
                run_id = build_id.split("/", 1)[1]
                remote.require_run(run_id, commit_sha)
                if uri.startswith("oci://"):
                    remote.verify_ghcr(uri, commit_sha, artifact_sha256)
                else:
                    parsed = urlparse(uri)
                    action_match = re.fullmatch(r"/[^/]+/[^/]+/actions/runs/([1-9][0-9]*)/artifacts/([1-9][0-9]*)", parsed.path)
                    release_match = re.fullmatch(r"/[^/]+/[^/]+/releases/download/([^/]+)/([^/]+)", parsed.path)
                    if action_match:
                        if action_match.group(1) != run_id:
                            raise RuntimeError("artifact URL run id does not match build_id")
                        remote.verify_actions_artifact(run_id, action_match.group(2), commit_sha, artifact_sha256)
                    elif release_match:
                        remote.verify_release_asset(unquote(release_match.group(1)), unquote(release_match.group(2)), commit_sha, artifact_sha256)
                    else:
                        raise RuntimeError("unsupported remote evidence URI")
            except (RuntimeError, OSError) as error:
                errors.append(f"{prefix}.remote_verification failed: {error}")
    missing_criteria = set(criteria) - covered_criteria
    if missing_criteria:
        errors.append(f"{blocker_id}: evidence does not cover every closure criterion")
    if roles != allowed_roles:
        errors.append(f"{blocker_id}: evidence requires separate Independent Test Agent and Independent Review Agent records")
    return errors


try:
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
except (OSError, yaml.YAMLError) as error:
    print(json.dumps({"registry": str(registry_path), "result": "invalid", "error": str(error)}, ensure_ascii=False))
    raise SystemExit(2)

if not isinstance(registry, dict) or not isinstance(registry.get("blockers"), list):
    print(json.dumps({"registry": str(registry_path), "result": "invalid", "error": "blockers list is required"}, ensure_ascii=False))
    raise SystemExit(2)

closed_items = [item for item in registry["blockers"] if isinstance(item, dict) and item.get("release_blocking") and item.get("status") == "closed"]
remote = None
remote_error = None
if mode == "--require-closed" and closed_items:
    try:
        remote = RemoteVerifier()
    except RuntimeError as error:
        remote_error = str(error)

invalid = []
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
        if status == "closed":
            if remote_error:
                invalid.append(f"{blocker_id}: remote closure verification unavailable: {remote_error}")
            invalid.extend(validate_closed_evidence(blocker_id, item, remote))
        blocking.append({"id": blocker_id, "status": status, "evidence_count": len(item.get("evidence", [])) if isinstance(item.get("evidence", []), list) else 0})

unclosed = [item for item in blocking if item["status"] != "closed"]
summary = {
    "registry": str(registry_path),
    "mode": mode,
    "commit": expected_commit,
    "result": "pass" if not invalid and not unclosed else "blocked",
    "release_eligible": mode == "--require-closed" and not invalid and not unclosed,
    "remote_verification": "performed" if remote else ("not-required" if not closed_items else "unavailable"),
    "release_blocking_total": len(blocking),
    "closed": sum(item["status"] == "closed" for item in blocking),
    "unclosed": unclosed,
    "invalid": invalid,
}
print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
if invalid or (mode == "--require-closed" and unclosed):
    raise SystemExit(1)
PY
status="$?"
set -e
exit "$status"
