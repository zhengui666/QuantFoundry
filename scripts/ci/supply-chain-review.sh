#!/usr/bin/env bash
set -euo pipefail

tag="${1:?release tag is required}"
commit="${2:?release commit is required}"
repository="${GITHUB_REPOSITORY:?GITHUB_REPOSITORY is required}"
command -v gh >/dev/null || { printf '%s\n' 'gh is required' >&2; exit 127; }
command -v docker >/dev/null || { printf '%s\n' 'docker is required' >&2; exit 127; }
command -v python3 >/dev/null || { printf '%s\n' 'python3 is required' >&2; exit 127; }

work_dir="$(mktemp -d "${RUNNER_TEMP:-/tmp}/qf-supply-review.XXXXXX")"
trap 'rm -rf "$work_dir"' EXIT

release_json="$work_dir/release.json"
gh api "repos/$repository/releases/tags/$tag" >"$release_json"
tag_json="$work_dir/tag.json"
gh api "repos/$repository/git/ref/tags/$tag" >"$tag_json"

python3 - "$release_json" "$tag_json" "$work_dir" "$tag" "$commit" "$repository" <<'PY'
import json
import os
import pathlib
import subprocess
import sys
import urllib.request

release_path, tag_path, work_dir, expected_tag, expected_commit, expected_repository = sys.argv[1:]
release = json.loads(pathlib.Path(release_path).read_text(encoding="utf-8"))
tag = json.loads(pathlib.Path(tag_path).read_text(encoding="utf-8"))
if release.get("draft") is not False or release.get("prerelease") is not True:
    raise SystemExit("release must be a published prerelease")
if release.get("tag_name") != expected_tag or release.get("target_commitish") != expected_commit:
    raise SystemExit("release tag or target commit is not bound to the reviewed commit")
if tag.get("object", {}).get("type") != "commit" or tag.get("object", {}).get("sha") != expected_commit:
    raise SystemExit("tag ref is not a lightweight ref bound to the reviewed commit")

assets = release.get("assets")
if not isinstance(assets, list) or not assets:
    raise SystemExit("release has no evidence assets")
names = []
for asset in assets:
    name = asset.get("name") if isinstance(asset, dict) else None
    asset_id = asset.get("id") if isinstance(asset, dict) else None
    if not isinstance(name, str) or not name or "/" in name or not isinstance(asset_id, int):
        raise SystemExit("release contains an invalid asset")
    names.append(name)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN or GH_TOKEN is required to download release assets")
    output = pathlib.Path(work_dir) / name
    request = urllib.request.Request(
        f"https://api.github.com/repos/{expected_repository}/releases/assets/{asset_id}",
        headers={
            "Accept": "application/octet-stream",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request) as response:
            output.write_bytes(response.read())
    except Exception as error:
        raise SystemExit(f"cannot download release asset {name}: {error}") from error
if len(names) != len(set(names)):
    raise SystemExit("release asset names are not unique")
required = {"release-manifest.json", "SHA256SUMS"}
if not required.issubset(names):
    raise SystemExit("release manifest and SHA256SUMS are required assets")
PY

(cd "$work_dir" && sha256sum --check --strict SHA256SUMS)

python3 - "$work_dir" "$tag" "$commit" <<'PY'
import json
import pathlib
import sys

work_dir, expected_tag, expected_commit = sys.argv[1:]
root = pathlib.Path(work_dir)
manifest = json.loads((root / "release-manifest.json").read_text(encoding="utf-8"))
if manifest.get("tag") != expected_tag or manifest.get("commit") != expected_commit:
    raise SystemExit("release manifest tag or commit is not bound")
if manifest.get("status") != "complete":
    raise SystemExit("release manifest is not complete")
inventory = manifest.get("release_assets")
metadata_files = {"release.json", "tag.json"}
actual = sorted(path.name for path in root.iterdir() if path.is_file() and path.name not in metadata_files)
if not isinstance(inventory, list) or sorted(item.get("name") for item in inventory) != actual:
    raise SystemExit("release assets do not match the manifest inventory")
required_sources = {
    "evidence/p0-blockers.yaml",
    "evidence/release-known-issues.json",
    "evidence/attestations/backend.json",
    "evidence/attestations/frontend.json",
    "evidence/provenance/backend.json",
    "evidence/provenance/frontend.json",
    "evidence/signature-verification/backend.json",
    "evidence/signature-verification/frontend.json",
    "evidence/sbom/backend.spdx.json",
    "evidence/sbom/frontend.spdx.json",
}
sources = {item.get("source") for item in inventory if isinstance(item, dict)}
if not required_sources.issubset(sources):
    raise SystemExit("release inventory is missing supply-chain or P0 snapshots")
images = manifest.get("images")
compose = manifest.get("compose_images")
if not isinstance(images, list) or len(images) != 2 or not isinstance(compose, dict):
    raise SystemExit("release manifest image bindings are incomplete")
for image in images:
    name, digest = image.get("name"), image.get("digest")
    if not isinstance(name, str) or not isinstance(digest, str) or not digest.startswith("sha256:"):
        raise SystemExit("invalid image digest in release manifest")
    subprocess = __import__("subprocess")
    subprocess.run(["docker", "buildx", "imagetools", "inspect", f"{name}@{digest}"], check=True)
    if image is images[0] and compose.get("api") != f"{name}@{digest}":
        raise SystemExit("Compose backend binding does not match image digest")
    if image is images[1] and compose.get("frontend") != f"{name}@{digest}":
        raise SystemExit("Compose frontend binding does not match image digest")
print(json.dumps({"result": "pass", "tag": expected_tag, "commit": expected_commit, "images": images}, sort_keys=True))
PY
