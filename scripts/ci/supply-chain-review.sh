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
import urllib.error
import urllib.parse
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
MAX_ASSET_BYTES = 64 * 1024 * 1024
MAX_TOTAL_ASSET_BYTES = 512 * 1024 * 1024
downloaded_total = [0]

def save_response(response, output, name):
    content_length = response.headers.get("Content-Length")
    if content_length is not None and int(content_length) > MAX_ASSET_BYTES:
        raise SystemExit(f"release asset {name} exceeds the size limit")
    copied = 0
    with output.open("wb") as destination:
        while chunk := response.read(1024 * 1024):
            copied += len(chunk)
            downloaded_total[0] += len(chunk)
            if copied > MAX_ASSET_BYTES or downloaded_total[0] > MAX_TOTAL_ASSET_BYTES:
                raise SystemExit(f"release asset {name} exceeds the size limit")
            destination.write(chunk)

for asset in assets:
    name = asset.get("name") if isinstance(asset, dict) else None
    asset_id = asset.get("id") if isinstance(asset, dict) else None
    if (
        not isinstance(name, str)
        or not name
        or "/" in name
        or "\\" in name
        or name in {".", ".."}
        or any(ord(char) < 32 or ord(char) == 127 for char in name)
        or name in {"release.json", "tag.json"}
        or not isinstance(asset_id, int)
    ):
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
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, request, response, code, msg, headers, new):
            return None

    opener = urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request) as response:
            save_response(response, output, name)
    except urllib.error.HTTPError as error:
        if error.code not in {301, 302, 303, 307, 308}:
            raise
        location = error.headers.get("Location")
        redirect_url = urllib.parse.urljoin(request.full_url, location or "")
        parsed = urllib.parse.urlparse(redirect_url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.hostname
            not in {
                "api.github.com",
                "github.com",
                "objects.githubusercontent.com",
            }
            or parsed.username
            or parsed.password
        ):
            raise SystemExit(f"unsafe release asset redirect for {name}") from error
        redirect_request = urllib.request.Request(
            redirect_url, headers={"Accept": "application/octet-stream"}
        )
        with opener.open(redirect_request) as response:
            save_response(response, output, name)
    except Exception as error:
        raise SystemExit(f"cannot download release asset {name}: {error}") from error
if len(names) != len(set(names)):
    raise SystemExit("release asset names are not unique")
required = {"release-manifest.json", "SHA256SUMS"}
if not required.issubset(names):
    raise SystemExit("release manifest and SHA256SUMS are required assets")
PY

python3 - "$work_dir" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
release = json.loads((root / "release.json").read_text(encoding="utf-8"))
expected = {
    asset["name"]
    for asset in release.get("assets", [])
    if isinstance(asset, dict) and isinstance(asset.get("name"), str)
}
listed = set()
for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
    digest, separator, name = line.partition("  ")
    if len(digest) != 64 or not separator or not name:
        raise SystemExit("SHA256SUMS contains an invalid entry")
    listed.add(name.removeprefix("*"))
if listed != expected - {"SHA256SUMS"}:
    raise SystemExit("SHA256SUMS must cover every release asset except itself")
PY
(cd "$work_dir" && sha256sum --check --strict SHA256SUMS)

python3 - "$work_dir" "$tag" "$commit" "$repository" <<'PY'
import base64
import json
import pathlib
import sys

work_dir, expected_tag, expected_commit, expected_repository = sys.argv[1:]
root = pathlib.Path(work_dir)

def statements(value):
    entries = value if isinstance(value, list) else [value]
    found = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        verification = entry.get("verificationResult")
        if (
            isinstance(verification, dict)
            and verification.get("verified") is True
            and isinstance(
            verification.get("statement"), dict
            )
        ):
            found.append(verification["statement"])
    return found


def bound_statement(value, subject_name, digest, repository, commit):
    expected_digest = digest.removeprefix("sha256:")
    for statement in statements(value):
        if statement.get("predicateType") != "https://slsa.dev/provenance/v1":
            continue
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
        workflow_path = workflow.get("path") if isinstance(workflow, dict) else None
        workflow_ref = workflow.get("ref") if isinstance(workflow, dict) else None
        workflow_repo_ok = workflow_repo in {
            expected_repository,
            f"https://github.com/{expected_repository}",
        }
        workflow_ok = workflow_repo_ok and workflow_path == ".github/workflows/rc-release.yml" and workflow_ref in {
            f"refs/tags/{expected_tag}",
            "refs/heads/main",
        }
        source_commit_ok = (
            isinstance(source, dict)
            and isinstance(source.get("digest"), dict)
            and source["digest"].get("sha1") == commit
        )
        source_pair_ok = workflow_ok and source_commit_ok and (
            source_repo == repository
            or source_uri == f"git+https://github.com/{repository}@{commit}"
        )
        dependency_pair_ok = False
        if isinstance(build, dict):
            for dependency in build.get("resolvedDependencies", []):
                if not isinstance(dependency, dict):
                    continue
                uri = dependency.get("uri")
                dependency_digest = dependency.get("digest")
                dependency_pair_ok = dependency_pair_ok or (
                    uri == f"git+https://github.com/{repository}@{commit}"
                    and isinstance(dependency_digest, dict)
                    and dependency_digest.get("sha1") == commit
                )
        if subject_ok and workflow_ok and (source_pair_ok or dependency_pair_ok):
            return
    raise SystemExit(f"attestation is not structurally bound to {subject_name}, {repository}, and {commit}")


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
    "p0-blockers.yaml",
    "release-known-issues.json",
    "attestations/backend.json",
    "attestations/frontend.json",
    "provenance/backend.json",
    "provenance/frontend.json",
    "signature-verification/backend.json",
    "signature-verification/frontend.json",
    "sbom/backend.spdx.json",
    "sbom/frontend.spdx.json",
}
sources = {item.get("source") for item in inventory if isinstance(item, dict)}
if not required_sources.issubset(sources):
    raise SystemExit("release inventory is missing supply-chain or P0 snapshots")
asset_path = {
    item["source"]: root / item["name"]
    for item in inventory
    if isinstance(item, dict) and isinstance(item.get("source"), str) and isinstance(item.get("name"), str)
}
trusted_verifier_root = pathlib.Path(os.environ.get("QF_RELEASE_TRUSTED_VERIFIER_ROOT", ""))
trusted_verifier_commit = os.environ.get("QF_RELEASE_TRUSTED_VERIFIER_COMMIT", "")
if (
    not trusted_verifier_root.is_dir()
    or not re.fullmatch(r"[0-9a-f]{40}", trusted_verifier_commit)
    or subprocess.run(
        ["git", "-C", str(trusted_verifier_root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    != trusted_verifier_commit
):
    raise SystemExit("trusted verifier checkout is required for release snapshot validation")
trusted_env = os.environ.copy()
trusted_env.update(
    {
        "QF_RELEASE_REPO_ROOT": os.environ.get("QF_RELEASE_REPO_ROOT", str(trusted_verifier_root)),
        "QF_RELEASE_COMMIT": commit,
        "QF_RELEASE_TRUSTED_VERIFIER_ROOT": str(trusted_verifier_root),
        "QF_RELEASE_TRUSTED_VERIFIER_COMMIT": trusted_verifier_commit,
    }
)
subprocess.run(
    [
        str(trusted_verifier_root / "scripts/p0-check.sh"),
        str(asset_path["p0-blockers.yaml"]),
        "--require-closed",
    ],
    check=True,
    env=trusted_env,
)
subprocess.run(
    [str(trusted_verifier_root / "scripts/release-known-issues-check.sh"), str(asset_path["release-known-issues.json"])],
    check=True,
    env=trusted_env,
)
images = manifest.get("images")
compose = manifest.get("compose_images")
if not isinstance(images, list) or len(images) != 2 or not isinstance(compose, dict):
    raise SystemExit("release manifest image bindings are incomplete")
expected_images = [
    f"ghcr.io/{expected_repository.lower()}/backend",
    f"ghcr.io/{expected_repository.lower()}/frontend",
]
for image, expected_name in zip(images, expected_images, strict=True):
    name, digest = image.get("name"), image.get("digest")
    if name != expected_name or not isinstance(digest, str) or not digest.startswith("sha256:"):
        raise SystemExit("invalid image digest in release manifest")
    subprocess = __import__("subprocess")
    subject = f"{name}@{digest}"
    subprocess.run(["docker", "buildx", "imagetools", "inspect", subject], check=True)
    verified = subprocess.run(
        [
            "gh",
            "attestation",
            "verify",
            f"oci://{subject}",
            "--repo",
            expected_repository,
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        verification = json.loads(verified.stdout)
    except json.JSONDecodeError as error:
        raise SystemExit(f"GitHub attestation verification returned invalid JSON for {name}") from error
    bound_statement(verification, subject, digest, expected_repository, expected_commit)
    for kind, relative in (
        ("attestation", f"attestations/{'backend' if image is images[0] else 'frontend'}.json"),
        ("provenance", f"provenance/{'backend' if image is images[0] else 'frontend'}.json"),
        ("signature", f"signature-verification/{'backend' if image is images[0] else 'frontend'}.json"),
    ):
        try:
            evidence = json.loads(asset_path[relative].read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SystemExit(f"invalid {kind} evidence for {name}: {error}") from error
        bound_statement(evidence, subject, digest, expected_repository, expected_commit)
        if evidence != verification:
            raise SystemExit(f"archived {kind} evidence differs from live cryptographic verification for {name}")
    sbom_name = 'backend' if image is images[0] else 'frontend'
    sbom = json.loads(asset_path[f"sbom/{sbom_name}.spdx.json"].read_text(encoding="utf-8"))
    if (
        not isinstance(sbom.get("spdxVersion"), str)
        or not sbom["spdxVersion"].startswith("SPDX-")
        or sbom.get("SPDXID") != "SPDXRef-DOCUMENT"
        or not isinstance(sbom.get("documentNamespace"), str)
        or not sbom["documentNamespace"].startswith("https://")
        or not isinstance(sbom.get("creationInfo"), dict)
        or not isinstance(sbom["creationInfo"].get("created"), str)
        or not isinstance(sbom["creationInfo"].get("creators"), list)
        or not sbom["creationInfo"]["creators"]
        or not isinstance(sbom.get("packages"), list)
        or not sbom["packages"]
    ):
        raise SystemExit(f"{sbom_name} SBOM is not a valid SPDX document")
    package_ids = set()
    for package in sbom["packages"]:
        if (
            not isinstance(package, dict)
            or not isinstance(package.get("SPDXID"), str)
            or not isinstance(package.get("name"), str)
            or not package["name"]
            or not isinstance(package.get("downloadLocation"), str)
        ):
            raise SystemExit(f"{sbom_name} SBOM contains an incomplete package")
        package_ids.add(package["SPDXID"])
    relationships = sbom.get("relationships")
    if not isinstance(relationships, list) or not any(
        isinstance(relationship, dict)
        and relationship.get("spdxElementId") == "SPDXRef-DOCUMENT"
        and relationship.get("relationshipType") == "DESCRIBES"
        and relationship.get("relatedSpdxElement") in package_ids
        for relationship in relationships
    ):
        raise SystemExit(f"{sbom_name} SBOM has no standard document-to-package relationship")
    if sbom.get("x-quantfoundry-subject") != {"name": name, "digest": digest}:
        raise SystemExit(f"{sbom_name} SBOM is not bound to the image digest")
    if image is images[0] and compose.get("api") != f"{name}@{digest}":
        raise SystemExit("Compose backend binding does not match image digest")
    if image is images[1] and compose.get("frontend") != f"{name}@{digest}":
        raise SystemExit("Compose frontend binding does not match image digest")
print(json.dumps({"result": "pass", "tag": expected_tag, "commit": expected_commit, "images": images}, sort_keys=True))
PY
