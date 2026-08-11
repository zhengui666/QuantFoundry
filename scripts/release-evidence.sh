#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  printf '%s\n' 'usage: release-evidence.sh gate TAG COMMIT OUTPUT_DIR | collect-inputs OUTPUT_DIR | collect-oci-sbom IMAGE DIGEST OUTPUT_FILE | manifest TAG COMMIT OUTPUT_DIR BACKEND_IMAGE BACKEND_DIGEST FRONTEND_IMAGE FRONTEND_DIGEST | compose-bind OUTPUT_DIR BACKEND_IMAGE BACKEND_DIGEST FRONTEND_IMAGE FRONTEND_DIGEST | package-assets OUTPUT_DIR' >&2
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
  (cd "$repo_root/backend" && uv run --frozen alembic heads) > "$output_dir/alembic-heads.txt"
  git -C "$repo_root" ls-files 'backend/alembic/versions/*.py' | sort > "$output_dir/alembic-migrations.txt"
  QF_RELEASE_TAG="$tag" QF_RELEASE_COMMIT="$commit" "$repo_root/scripts/ci/run-gate.sh" rc "$output_dir"
}

collect_inputs() {
  local output_dir="$1"
  mkdir -p "$output_dir"
  cp "$repo_root/docs/治理/p0-blockers.yaml" "$output_dir/p0-blockers.yaml"
  cp "$repo_root/docs/治理/release-known-issues.json" "$output_dir/release-known-issues.json"
  git -C "$repo_root" rev-parse 'HEAD^{commit}' > "$output_dir/commit.txt"
  (cd "$repo_root/backend" && uv run --frozen alembic heads) > "$output_dir/alembic-heads.txt"
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
import json
import os
import pathlib
import sys
import urllib.request

registry, repository, subject_digest, output_name = sys.argv[1:]
token = os.environ["GHCR_BEARER_TOKEN"]
accept = ", ".join((
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
))

def get(path, media_type=accept):
    request = urllib.request.Request(
        f"{registry}/v2/{repository}/{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": media_type},
    )
    with urllib.request.urlopen(request) as response:
        return response.read()

index = json.loads(get(f"manifests/{subject_digest}").decode("utf-8"))
descriptors = index.get("manifests", [])
attestations = [
    item for item in descriptors
    if item.get("annotations", {}).get("vnd.docker.reference.type") == "attestation-manifest"
    and item.get("annotations", {}).get("vnd.docker.reference.digest") == subject_digest
]
if not attestations:
    raise SystemExit("published image has no BuildKit attestation manifest bound to its digest")

for descriptor in attestations:
    manifest = json.loads(get(f"manifests/{descriptor['digest']}").decode("utf-8"))
    for layer in manifest.get("layers", []):
        predicate_type = layer.get("annotations", {}).get("in-toto.io/predicate-type")
        if predicate_type != "https://spdx.dev/Document":
            continue
        payload = get(f"blobs/{layer['digest']}", "application/vnd.in-toto+json")
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
import hashlib
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])
tag, commit, backend_image, backend_digest, frontend_image, frontend_digest, run_id, run_attempt = sys.argv[3:]

def record(path):
    path = pathlib.Path(path)
    if not path.is_file():
        raise SystemExit(f"required evidence input is missing: {path}")
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
if (output / "release-assets").exists() or (output / "SHA256SUMS").exists():
    raise SystemExit("release asset staging directory and SHA256SUMS must not pre-exist")

evidence_files = sorted(path for path in output.rglob("*") if path.is_file() and path.name not in {"release-manifest.json", "SHA256SUMS"})

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

source_files = {
    path.relative_to(output).as_posix()
    for path in output.rglob("*")
    if path.is_file() and "release-assets" not in path.relative_to(output).parts and path.name != "SHA256SUMS"
}
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
    shutil.copyfile(output / item["source"], staging / item["name"])

checksum_entries = []
for path in sorted(staging.iterdir(), key=lambda candidate: candidate.name):
    if not path.is_file():
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
    if hashlib.sha256((staging / name).read_bytes()).hexdigest() != digest:
        raise SystemExit(f"SHA256SUMS digest mismatch for {name}")
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
  *) usage ;;
esac
