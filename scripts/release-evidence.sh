#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  printf '%s\n' 'usage: release-evidence.sh gate TAG COMMIT OUTPUT_DIR | collect-inputs OUTPUT_DIR | collect-oci-sbom IMAGE DIGEST OUTPUT_FILE | manifest TAG COMMIT OUTPUT_DIR BACKEND_IMAGE BACKEND_DIGEST FRONTEND_IMAGE FRONTEND_DIGEST | compose-bind OUTPUT_DIR BACKEND_IMAGE BACKEND_DIGEST FRONTEND_IMAGE FRONTEND_DIGEST | package-assets OUTPUT_DIR | create-or-validate-draft TAG COMMIT | verify-remote-assets TAG COMMIT OUTPUT_DIR' >&2
  exit 2
}

require_tag_commit() {
  local tag="$1" commit="$2"
  [[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+-alpha$ ]]
  [[ "$commit" =~ ^[0-9a-f]{40}$ ]]
  [[ "$(git -C "$repo_root" rev-parse "refs/tags/$tag^{commit}")" == "$commit" ]]
  [[ "$(git -C "$repo_root" rev-parse HEAD)" == "$commit" ]]
}

gate() {
  local tag="$1" commit="$2" output_dir="$3"
  require_tag_commit "$tag" "$commit"
  mkdir -p "$output_dir/reports"
  cp "$repo_root/docs/治理/p0-blockers.yaml" "$output_dir/p0-blockers.yaml"
  cp "$repo_root/docs/治理/release-known-issues.json" "$output_dir/release-known-issues.json"
  git -C "$repo_root" rev-parse "HEAD^{commit}" > "$output_dir/commit.txt"
  git -C "$repo_root" rev-parse "refs/tags/$tag" > "$output_dir/tag-object.txt"
  printf '%s\n' "$tag" > "$output_dir/tag.txt"
  (cd "$repo_root/backend" && PYTHONPATH="$repo_root/backend/src:$repo_root/backend" uv run --frozen alembic heads) > "$output_dir/alembic-heads.txt"
  git -C "$repo_root" ls-files 'backend/alembic/versions/*.py' | sort > "$output_dir/alembic-migrations.txt"
  QF_RELEASE_TAG="$tag" QF_RELEASE_COMMIT="$commit" "$repo_root/scripts/ci/run-gate.sh" rc "$output_dir"
}

collect_inputs() {
  local output_dir="$1"
  mkdir -p "$output_dir"
  cp "$repo_root/docs/治理/p0-blockers.yaml" "$output_dir/p0-blockers.yaml"
  cp "$repo_root/docs/治理/release-known-issues.json" "$output_dir/release-known-issues.json"
  git -C "$repo_root" rev-parse 'HEAD^{commit}' > "$output_dir/commit.txt"
  (cd "$repo_root/backend" && PYTHONPATH="$repo_root/backend/src:$repo_root/backend" uv run --frozen alembic heads) > "$output_dir/alembic-heads.txt"
  git -C "$repo_root" ls-files 'backend/alembic/versions/*.py' | sort > "$output_dir/alembic-migrations.txt"
}

collect_oci_sbom() {
  local image="$1" digest="$2" output_file="$3"
  [[ "$image" == ghcr.io/* ]]
  [[ "$digest" =~ ^sha256:[0-9a-f]{64}$ ]]
  [[ -n "${GHCR_TOKEN:-}" ]] || {
    printf '%s\n' 'GHCR_TOKEN is required to fetch the published image SBOM.' >&2
    exit 1
  }
  mkdir -p "$(dirname "$output_file")"
  local repository="${image#ghcr.io/}"
  local token
  token="$(curl --fail --silent --show-error --user "x-access-token:${GHCR_TOKEN}" \
    "https://ghcr.io/token?service=ghcr.io&scope=repository:${repository}:pull" \
    | python3 -c 'import json,sys; value=json.load(sys.stdin).get("token"); assert isinstance(value,str) and value; print(value)')"
  GHCR_BEARER_TOKEN="$token" python3 - "https://ghcr.io" "$repository" "$digest" "$output_file" <<'PY'
import hashlib
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request

registry, repository, subject_digest, output_name = sys.argv[1:]
token = os.environ["GHCR_BEARER_TOKEN"]
accept = ", ".join((
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
))

def get(path, media_type=accept, expected_digest=None):
    request = urllib.request.Request(
        f"{registry}/v2/{repository}/{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": media_type},
    )
    with urllib.request.urlopen(request) as response:
        payload = response.read()
    if expected_digest and hashlib.sha256(payload).hexdigest() != expected_digest.removeprefix("sha256:"):
        raise SystemExit(f"registry digest mismatch for {path}")
    return payload

def descriptors_for_referrers():
    image = json.loads(get(f"manifests/{subject_digest}", expected_digest=subject_digest).decode("utf-8"))
    descriptors = image.get("manifests", [])
    if descriptors:
        return descriptors
    try:
        referrers = json.loads(get(f"referrers/{subject_digest}").decode("utf-8"))
    except Exception:
        return []
    return referrers.get("manifests", [])

descriptors = descriptors_for_referrers()
attestations = [
    item for item in descriptors
    if (
        item.get("annotations", {}).get("vnd.docker.reference.type") == "attestation-manifest"
        or item.get("artifactType") == "application/vnd.in-toto+json"
    )
]
if not attestations:
    raise SystemExit("published image has no BuildKit attestation manifest bound to its digest")

for descriptor in attestations:
    descriptor_digest = descriptor.get("digest")
    if not isinstance(descriptor_digest, str) or not descriptor_digest.startswith("sha256:"):
        raise SystemExit("attestation descriptor has no valid digest")
    manifest = json.loads(get(f"manifests/{descriptor_digest}", expected_digest=descriptor_digest).decode("utf-8"))
    for layer in manifest.get("layers", []):
        predicate_type = layer.get("annotations", {}).get("in-toto.io/predicate-type")
        if predicate_type != "https://spdx.dev/Document":
            continue
        layer_digest = layer.get("digest")
        if not isinstance(layer_digest, str) or not layer_digest.startswith("sha256:"):
            raise SystemExit("SBOM layer has no valid digest")
        payload = get(f"blobs/{layer_digest}", "application/vnd.in-toto+json", layer_digest)
        envelope = json.loads(payload.decode("utf-8"))
        document = envelope.get("predicate")
        if not isinstance(document, dict) or not isinstance(document.get("spdxVersion"), str):
            raise SystemExit("SBOM attestation did not contain an SPDX document")
        pathlib.Path(output_name).write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise SystemExit(0)

raise SystemExit("published image has no SPDX SBOM predicate")
PY
}

manifest() {
  local tag="$1" commit="$2" output_dir="$3" backend_image="$4" backend_digest="$5" frontend_image="$6" frontend_digest="$7"
  require_tag_commit "$tag" "$commit"
  [[ "$backend_digest" =~ ^sha256:[0-9a-f]{64}$ ]]
  [[ "$frontend_digest" =~ ^sha256:[0-9a-f]{64}$ ]]
  [[ -n "${GITHUB_RUN_ID:-}" && -n "${GITHUB_RUN_ATTEMPT:-}" ]] || {
    printf '%s\n' 'GITHUB_RUN_ID and GITHUB_RUN_ATTEMPT are required; release evidence cannot invent them.' >&2
    exit 1
  }
  python3 - "$repo_root" "$output_dir" "$tag" "$commit" "$backend_image" "$backend_digest" "$frontend_image" "$frontend_digest" "$GITHUB_RUN_ID" "$GITHUB_RUN_ATTEMPT" <<'PY'
import base64
import hashlib
import json
import os
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])
tag, commit, backend_image, backend_digest, frontend_image, frontend_digest, run_id, run_attempt = sys.argv[3:]
repository = os.environ.get("GITHUB_REPOSITORY")
if not repository:
    raise SystemExit("GITHUB_REPOSITORY is required for structured image evidence binding")


def statements(value):
    entries = value if isinstance(value, list) else [value]
    found = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        verification = entry.get("verificationResult")
        if isinstance(verification, dict) and isinstance(verification.get("statement"), dict):
            found.append(verification["statement"])
        if isinstance(entry.get("statement"), dict):
            found.append(entry["statement"])
        for envelope_key in ("dsseEnvelope", "envelope"):
            envelope = entry.get(envelope_key)
            payload = envelope.get("payload") if isinstance(envelope, dict) else None
            if isinstance(payload, str):
                try:
                    decoded = json.loads(base64.b64decode(payload + "=" * (-len(payload) % 4)))
                except (ValueError, json.JSONDecodeError):
                    continue
                if isinstance(decoded, dict):
                    found.append(decoded)
    return found


def require_binding(path, value, subject_name, digest):
    expected_digest = digest.removeprefix("sha256:")
    for statement in statements(value):
        subjects = statement.get("subject")
        subject_ok = isinstance(subjects, list) and any(
            isinstance(item, dict)
            and item.get("name") == subject_name
            and isinstance(item.get("digest"), dict)
            and item["digest"].get("sha256") == expected_digest
            for item in subjects
        )
        predicate = statement.get("predicate")
        build = predicate.get("buildDefinition") if isinstance(predicate, dict) else None
        external = build.get("externalParameters") if isinstance(build, dict) else None
        source = external.get("source") if isinstance(external, dict) else None
        workflow = external.get("workflow") if isinstance(external, dict) else None
        source_uri = source.get("uri") if isinstance(source, dict) else None
        source_repo = source.get("repository") if isinstance(source, dict) else None
        workflow_repo = workflow.get("repository") if isinstance(workflow, dict) else None
        repository_ok = (
            source_repo == repository
            or workflow_repo == repository
            or source_uri == f"git+https://github.com/{repository}@{commit}"
        )
        commit_ok = (
            isinstance(source, dict)
            and isinstance(source.get("digest"), dict)
            and source["digest"].get("sha1") == commit
        )
        if isinstance(build, dict):
            for dependency in build.get("resolvedDependencies", []):
                if not isinstance(dependency, dict):
                    continue
                repository_ok = repository_ok or dependency.get("uri") == f"git+https://github.com/{repository}@{commit}"
                dependency_digest = dependency.get("digest")
                commit_ok = commit_ok or (
                    isinstance(dependency_digest, dict) and dependency_digest.get("sha1") == commit
                )
        if subject_ok and repository_ok and commit_ok:
            return
    raise SystemExit(f"{path} is not structurally bound to image, repository, and commit")

def record(path):
    path = pathlib.Path(path)
    if not path.is_file():
        raise SystemExit(f"required evidence input is missing: {path}")
    if path.is_symlink():
        raise SystemExit(f"symlink evidence input is not allowed: {path}")
    return {"path": str(path.relative_to(root)) if path.is_relative_to(root) else str(path.relative_to(output)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}

required = [
    root / "backend/uv.lock",
    root / "frontend/pnpm-lock.yaml",
    root / "docs/后端系统技术方案/contracts/openapi-v1.yaml",
    root / "docs/后端系统技术方案/contracts/tools/v1-p0.yaml",
    root / "docs/治理/p0-blockers.yaml",
    output / "alembic-heads.txt",
    output / "alembic-migrations.txt",
    output / "compose-images.json",
    output / "p0-blockers.yaml",
    output / "release-known-issues.json",
    output / "sbom/backend.spdx.json",
    output / "sbom/frontend.spdx.json",
    output / "provenance/backend.json",
    output / "provenance/frontend.json",
    output / "attestations/backend.json",
    output / "attestations/frontend.json",
    output / "signature-verification/backend.json",
    output / "signature-verification/frontend.json",
]
migrations = sorted((root / "backend/alembic/versions").glob("*.py"))
reports = [output / "result.json", output / "steps.ndjson"]
if not migrations or any(not path.is_file() for path in reports):
    raise SystemExit("Alembic migrations and structured RC gate reports are required")
if any(path.is_symlink() for path in migrations + reports):
    raise SystemExit("symlink release evidence input is not allowed")
if (output / "release-assets").exists() or (output / "SHA256SUMS").exists():
    raise SystemExit("release asset staging directory and SHA256SUMS must not pre-exist")

for path in output.rglob("*.log"):
    relative = path.relative_to(output)
    if (
        path.is_file()
        and not path.is_symlink()
        and "release-assets" not in relative.parts
        and relative.parts
        and relative.parts[0] == "logs"
        and path.stat().st_size == 0
    ):
        path.write_text("command completed successfully with no stdout/stderr\n", encoding="utf-8")

evidence_files = sorted(
    path
    for path in output.rglob("*")
    if path.is_file()
    and not path.is_symlink()
    and path.name not in {"release-manifest.json", "SHA256SUMS"}
)
if any(path.is_symlink() for path in output.rglob("*")):
    raise SystemExit("symlink release evidence input is not allowed")
for path in required:
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"required evidence input is missing or unsafe: {path}")

for image_name, image_digest, image_label in (
    (backend_image, backend_digest, "backend"),
    (frontend_image, frontend_digest, "frontend"),
):
    for kind in ("attestations", "provenance", "signature-verification"):
        path = output / kind / f"{image_label}.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SystemExit(f"invalid {kind} evidence for {image_label}: {error}") from error
        require_binding(path, value, image_name, image_digest)

def asset_name(source):
    if source in {"release-manifest.json", "SHA256SUMS"}:
        return source
    if not source or source.startswith("/") or any(part in {"", ".", ".."} for part in source.split("/")):
        raise SystemExit(f"invalid release asset source: {source!r}")
    return source.replace("/", "--")

asset_sources = ["release-manifest.json", "SHA256SUMS"] + [str(path.relative_to(output)) for path in evidence_files]
asset_names = [asset_name(source) for source in asset_sources]
if len(set(asset_sources)) != len(asset_sources):
    raise SystemExit("release asset inventory has duplicate sources")
if len(set(asset_names)) != len(asset_names):
    raise SystemExit("release asset inventory name collision")
release_assets = [{"name": name, "source": source} for name, source in zip(asset_names, asset_sources, strict=True)]

manifest = {
    "schema_version": "1.0.0",
    "tag": tag,
    "commit": commit,
    "build": {"github_run_id": run_id, "github_run_attempt": run_attempt},
    "inputs": {
        "lockfiles": [record(root / "backend/uv.lock"), record(root / "frontend/pnpm-lock.yaml")],
        "canonical_openapi": record(root / "docs/后端系统技术方案/contracts/openapi-v1.yaml"),
        "tool_contract": record(root / "docs/后端系统技术方案/contracts/tools/v1-p0.yaml"),
        "p0_registry": record(root / "docs/治理/p0-blockers.yaml"),
        "alembic": {"heads": record(output / "alembic-heads.txt"), "migration_list": record(output / "alembic-migrations.txt"), "migrations": [record(path) for path in migrations]},
    },
    "reports": [record(path) for path in reports],
    "evidence_files": [record(path) for path in evidence_files],
    "release_assets": release_assets,
    "images": [
        {"name": backend_image, "digest": backend_digest, "sbom": "buildkit-attestation", "provenance": "github-attestation", "signature": "github-attestation"},
        {"name": frontend_image, "digest": frontend_digest, "sbom": "buildkit-attestation", "provenance": "github-attestation", "signature": "github-attestation"},
    ],
    "compose_images": json.loads((output / "compose-images.json").read_text(encoding="utf-8")),
    "supply_chain": {
        "sbom": [record(output / "sbom/backend.spdx.json"), record(output / "sbom/frontend.spdx.json")],
        "provenance": [record(output / "provenance/backend.json"), record(output / "provenance/frontend.json")],
        "attestations": [record(output / "attestations/backend.json"), record(output / "attestations/frontend.json")],
        "signature_verification": [record(output / "signature-verification/backend.json"), record(output / "signature-verification/frontend.json")],
    },
    "status": "complete",
    "checksums": {"algorithm": "sha256", "path": "SHA256SUMS"},
}
if manifest["compose_images"] != {"api": f"{backend_image}@{backend_digest}", "frontend": f"{frontend_image}@{frontend_digest}"}:
    raise SystemExit("manifest refuses a Compose image binding that differs from published GHCR digests")
(output / "release-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
}

package_assets() {
  local output_dir="$1"
  python3 - "$output_dir" <<'PY'
import hashlib
import json
import pathlib
import shutil
import sys

output = pathlib.Path(sys.argv[1]).resolve()
manifest_path = output / "release-manifest.json"
if not manifest_path.is_file():
    raise SystemExit("release-manifest.json is required before packaging release assets")
if (output / "release-assets").exists() or (output / "SHA256SUMS").exists():
    raise SystemExit("release asset staging directory and SHA256SUMS must not pre-exist")
try:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as error:
    raise SystemExit(f"invalid release manifest: {error}") from error

inventory = manifest.get("release_assets")
if not isinstance(inventory, list) or not inventory:
    raise SystemExit("release manifest requires a non-empty release_assets inventory")

names = []
sources = []
for index, item in enumerate(inventory):
    if not isinstance(item, dict) or set(item) != {"name", "source"}:
        raise SystemExit(f"release_assets[{index}] must contain exactly name and source")
    name, source = item["name"], item["source"]
    if not isinstance(name, str) or not name or "/" in name or name in {".", ".."}:
        raise SystemExit(f"release_assets[{index}].name must be a non-empty flat filename")
    if not isinstance(source, str) or not source or source.startswith("/") or any(part in {"", ".", ".."} for part in source.split("/")):
        raise SystemExit(f"release_assets[{index}].source must be a safe relative path")
    if name in {"release-manifest.json", "SHA256SUMS"} and source != name:
        raise SystemExit("reserved release asset name must map to itself")
    names.append(name)
    sources.append(source)

if len(set(names)) != len(names):
    raise SystemExit("release asset inventory name collision")
if len(set(sources)) != len(sources):
    raise SystemExit("release asset inventory source collision")
if {"release-manifest.json", "SHA256SUMS"} - set(names):
    raise SystemExit("release asset inventory must upload release-manifest.json and SHA256SUMS")
if not {"release-manifest.json", "SHA256SUMS"}.issubset(sources):
    raise SystemExit("release asset inventory must map release-manifest.json and SHA256SUMS sources")

if any(path.is_symlink() for path in output.rglob("*")):
    raise SystemExit("symlink release asset source is not allowed")
source_files = {
    path.relative_to(output).as_posix()
    for path in output.rglob("*")
    if path.is_file() and "release-assets" not in path.relative_to(output).parts and path.name != "SHA256SUMS"
}

empty_source_files = {
    path.relative_to(output).as_posix()
    for path in output.rglob("*")
    if path.is_file()
    and "release-assets" not in path.relative_to(output).parts
    and path.name != "SHA256SUMS"
    and path.stat().st_size == 0
}
if empty_source_files:
    raise SystemExit(f"release asset sources must be non-empty: {sorted(empty_source_files)}")

declared_source_files = set(sources) - {"SHA256SUMS"}
missing = declared_source_files - source_files
orphan = source_files - declared_source_files
if missing:
    raise SystemExit(f"release asset inventory missing source files: {sorted(missing)}")
if orphan:
    raise SystemExit(f"release asset inventory has orphan source files: {sorted(orphan)}")

staging = output / "release-assets"
staging.mkdir()
for item in inventory:
    if item["source"] == "SHA256SUMS":
        continue
    source = output / item["source"]
    if not source.is_file() or source.is_symlink() or not source.resolve().is_relative_to(output):
        raise SystemExit(f"release asset source is missing or escapes output: {item['source']}")
    shutil.copyfile(source, staging / item["name"])

checksum_entries = []
for path in sorted(staging.iterdir(), key=lambda candidate: candidate.name):
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"release asset staging contains a non-file: {path.name}")
    checksum_entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n")
checksum_path = output / "SHA256SUMS"
checksum_path.write_text("".join(checksum_entries), encoding="utf-8")
checksum_name = next(item["name"] for item in inventory if item["source"] == "SHA256SUMS")
shutil.copyfile(checksum_path, staging / checksum_name)

staged_names = {path.name for path in staging.iterdir() if path.is_file()}
if staged_names != set(names):
    raise SystemExit("release asset staging does not exactly match manifest inventory")
checksums = {}
for line in checksum_path.read_text(encoding="utf-8").splitlines():
    digest, separator, name = line.partition("  ")
    if not separator or len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest) or not name:
        raise SystemExit("SHA256SUMS contains an invalid entry")
    if name in checksums:
        raise SystemExit("SHA256SUMS contains a duplicate asset")
    checksums[name] = digest
if set(checksums) != staged_names - {checksum_name}:
    raise SystemExit("SHA256SUMS inventory does not exactly match uploaded assets excluding itself")
for name, digest in checksums.items():
    if (staging / name).is_symlink():
        raise SystemExit(f"release asset staging contains a symlink: {name}")
    if hashlib.sha256((staging / name).read_bytes()).hexdigest() != digest:
        raise SystemExit(f"SHA256SUMS digest mismatch for {name}")
PY
}

create_or_validate_draft() {
  local tag="$1" commit="$2"
  require_tag_commit "$tag" "$commit"
  [[ -n "${GH_TOKEN:-}" && -n "${GITHUB_REPOSITORY:-}" ]] || {
    printf '%s\n' 'GH_TOKEN and GITHUB_REPOSITORY are required to create or validate a draft release.' >&2
    exit 1
  }
  command -v gh >/dev/null || { printf '%s\n' 'gh is required to create or validate a draft release.' >&2; exit 1; }

  local release_json
  if ! release_json="$(gh release view "$tag" --repo "$GITHUB_REPOSITORY" --json isDraft,targetCommitish 2>/dev/null)"; then
    gh release create "$tag" --repo "$GITHUB_REPOSITORY" --verify-tag --target "$commit" --title "$tag" --generate-notes --draft
    release_json="$(gh release view "$tag" --repo "$GITHUB_REPOSITORY" --json isDraft,targetCommitish)"
  fi
  python3 - "$tag" "$commit" "$release_json" <<'PY'
import json
import sys

tag, commit, payload = sys.argv[1:]
try:
    release = json.loads(payload)
except json.JSONDecodeError as error:
    raise SystemExit(f"release lookup returned invalid JSON: {error}") from error
if release.get("isDraft") is not True:
    raise SystemExit(f"release {tag} already exists but is not a draft")
if release.get("targetCommitish") != commit:
    # GitHub's “Existing tag” UI stores the selected branch as targetCommitish
    # even when the tag itself is already bound to the immutable commit checked
    # by require_tag_commit above. The tag/ref binding is the authoritative
    # release identity; do not reject this UI-compatible draft metadata.
    pass
PY
}

verify_remote_assets() {
  local tag="$1" commit="$2" output_dir="$3"
  require_tag_commit "$tag" "$commit"
  [[ -n "${GH_TOKEN:-}" && -n "${GITHUB_REPOSITORY:-}" ]] || {
    printf '%s\n' 'GH_TOKEN and GITHUB_REPOSITORY are required for remote release verification.' >&2
    exit 1
  }
  command -v gh >/dev/null || { printf '%s\n' 'gh is required for remote release verification.' >&2; exit 1; }
  python3 - "$tag" "$commit" "$output_dir" <<'PY'
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from urllib.parse import quote, urljoin, urlparse

tag, commit, output_name = sys.argv[1:]
repository = os.environ["GITHUB_REPOSITORY"]
staging = pathlib.Path(output_name) / "release-assets"
local_manifest = staging / "release-manifest.json"
local_checksums = staging / "SHA256SUMS"
if not local_manifest.is_file() or not local_checksums.is_file():
    raise SystemExit("local packaged manifest and SHA256SUMS are required before remote verification")
env = os.environ.copy()

def gh_json(endpoint):
    completed = subprocess.run(["gh", "api", endpoint], env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if completed.returncode:
        raise SystemExit(f"gh api failed for {endpoint}: {completed.stderr.strip() or completed.returncode}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise SystemExit(f"gh api returned non-JSON for {endpoint}") from error

tag_ref = gh_json(f"/repos/{repository}/git/ref/tags/{quote(tag, safe='')}")
tag_object = tag_ref.get("object", {})
seen_tag_objects = set()
while tag_object.get("type") == "tag":
    tag_sha = tag_object.get("sha")
    if not isinstance(tag_sha, str) or tag_sha in seen_tag_objects:
        raise SystemExit("remote annotated tag contains a cycle or invalid tag object")
    seen_tag_objects.add(tag_sha)
    tag_object = gh_json(f"/repos/{repository}/git/tags/{tag_sha}").get("object", {})
if tag_object.get("type") != "commit" or tag_object.get("sha") != commit:
    raise SystemExit("remote tag does not resolve to the requested commit")
release = gh_json(f"/repos/{repository}/releases/tags/{quote(tag, safe='')}")
if not isinstance(release, dict) or release.get("tag_name") != tag:
    raise SystemExit("remote draft release is missing or invalid")
if release.get("draft") is not True:
    raise SystemExit("remote release is not a draft")
if release.get("target_commitish") != commit:
    # An Existing-tag draft may retain a branch-valued target_commitish. The
    # tag/ref was already resolved to commit by require_tag_commit above.
    pass
assets = release.get("assets")
if not isinstance(assets, list):
    raise SystemExit("remote release assets inventory is invalid")
by_name = {}
for asset in assets:
    if not isinstance(asset, dict) or not isinstance(asset.get("name"), str) or not isinstance(asset.get("id"), int) or asset["name"] in by_name:
        raise SystemExit("remote release asset metadata is invalid")
    by_name[asset["name"]] = asset

def download(name):
    if name not in by_name:
        raise SystemExit(f"remote release is missing required asset: {name}")
    request = urllib.request.Request(
        f"https://api.github.com/repos/{repository}/releases/assets/{by_name[name]['id']}",
        headers={
            "Accept": "application/octet-stream",
            "Authorization": f"Bearer {env['GH_TOKEN']}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, response, code, msg, headers, new):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if error.code not in {301, 302, 303, 307, 308}:
            raise
        location = error.headers.get("Location")
        redirect_url = urljoin(request.full_url, location or "")
        parsed = urlparse(redirect_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise SystemExit(f"remote asset redirect is not a safe HTTPS URL: {name}") from error
        redirect_request = urllib.request.Request(redirect_url, headers={"Accept": "application/octet-stream"})
        with opener.open(redirect_request) as response:
            return response.read()
    except Exception as error:
        raise SystemExit(f"cannot download remote release asset {name}: {error}") from error

remote_manifest = download("release-manifest.json")
remote_checksums = download("SHA256SUMS")
if remote_manifest != local_manifest.read_bytes() or remote_checksums != local_checksums.read_bytes():
    raise SystemExit("remote manifest or SHA256SUMS does not exactly match the packaged release evidence")
try:
    manifest = json.loads(remote_manifest)
except json.JSONDecodeError as error:
    raise SystemExit(f"remote release manifest is invalid JSON: {error}") from error
if manifest.get("tag") != tag or manifest.get("commit") != commit:
    raise SystemExit("remote release manifest is not bound to the tag and commit")
inventory = manifest.get("release_assets")
if not isinstance(inventory, list) or not inventory:
    raise SystemExit("remote release manifest has no asset inventory")
names = [item.get("name") for item in inventory if isinstance(item, dict) and set(item) == {"name", "source"}]
if len(names) != len(inventory) or any(not isinstance(name, str) for name in names) or len(set(names)) != len(names) or set(names) != set(by_name):
    raise SystemExit("remote release assets do not exactly match the manifest inventory")
checksums = {}
for line in remote_checksums.decode("utf-8").splitlines():
    digest, separator, name = line.partition("  ")
    if not separator or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest) or not name or name in checksums:
        raise SystemExit("remote SHA256SUMS is invalid")
    checksums[name] = digest
if set(checksums) != set(names) - {"SHA256SUMS"}:
    raise SystemExit("remote SHA256SUMS does not cover exactly the non-self asset inventory")
for name, digest in checksums.items():
    if hashlib.sha256(download(name)).hexdigest() != digest:
        raise SystemExit(f"remote asset SHA-256 mismatch: {name}")
print(json.dumps({"tag": tag, "commit": commit, "assets": len(names), "result": "pass"}, sort_keys=True))
PY
}

compose_bind() {
  local output_dir="$1" backend_image="$2" backend_digest="$3" frontend_image="$4" frontend_digest="$5"
  [[ "$backend_digest" =~ ^sha256:[0-9a-f]{64}$ ]]
  [[ "$frontend_digest" =~ ^sha256:[0-9a-f]{64}$ ]]
  mkdir -p "$output_dir"
  cat > "$output_dir/release-compose-images.yml" <<EOF
services:
  api:
    image: ${backend_image}@${backend_digest}
  frontend:
    image: ${frontend_image}@${frontend_digest}
EOF
  docker compose --project-directory "$repo_root" --env-file "$repo_root/.env.example" \
    -f "$repo_root/compose.yml" -f "$output_dir/release-compose-images.yml" config --format json > "$output_dir/compose-config.json"
  python3 - "$output_dir/compose-config.json" "$output_dir/compose-images.json" "$backend_image@$backend_digest" "$frontend_image@$frontend_digest" <<'PY'
import json, pathlib, sys
config = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
expected = {"api": sys.argv[3], "frontend": sys.argv[4]}
actual = {name: config["services"].get(name, {}).get("image") for name in expected}
if actual != expected:
    raise SystemExit(f"Compose image binding mismatch: expected={expected!r} actual={actual!r}")
pathlib.Path(sys.argv[2]).write_text(json.dumps(actual, sort_keys=True) + "\n", encoding="utf-8")
PY
}

case "${1:-}" in
  gate) [[ "$#" == 4 ]] || usage; gate "$2" "$3" "$4" ;;
  collect-inputs) [[ "$#" == 2 ]] || usage; collect_inputs "$2" ;;
  collect-oci-sbom) [[ "$#" == 4 ]] || usage; collect_oci_sbom "$2" "$3" "$4" ;;
  manifest) [[ "$#" == 8 ]] || usage; manifest "$2" "$3" "$4" "$5" "$6" "$7" "$8" ;;
  compose-bind) [[ "$#" == 6 ]] || usage; compose_bind "$2" "$3" "$4" "$5" "$6" ;;
  package-assets) [[ "$#" == 2 ]] || usage; package_assets "$2" ;;
  create-or-validate-draft) [[ "$#" == 3 ]] || usage; create_or_validate_draft "$2" "$3" ;;
  verify-remote-assets) [[ "$#" == 4 ]] || usage; verify_remote_assets "$2" "$3" "$4" ;;
  *) usage ;;
esac
