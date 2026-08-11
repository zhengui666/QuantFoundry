#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  printf '%s\n' 'usage: release-evidence.sh gate TAG COMMIT OUTPUT_DIR | manifest TAG COMMIT OUTPUT_DIR BACKEND_IMAGE BACKEND_DIGEST FRONTEND_IMAGE FRONTEND_DIGEST | compose-bind OUTPUT_DIR BACKEND_IMAGE BACKEND_DIGEST FRONTEND_IMAGE FRONTEND_DIGEST' >&2
  exit 2
}

require_tag_commit() {
  local tag="$1" commit="$2"
  [[ "$tag" =~ ^v[0-9]+\.[0-9]+\.[0-9]+-alpha$ ]]
  [[ "$commit" =~ ^[0-9a-f]{40}$ ]]
  [[ "$(git -C "$repo_root" rev-parse "refs/tags/$tag^{commit}")" == "$commit" ]]
  [[ "$(git -C "$repo_root" rev-parse HEAD)" == "$commit" ]]
}

run_gate() {
  local output_dir="$1" name="$2"
  shift 2
  local status=0
  set +e
  "$@" >"$output_dir/reports/$name.log" 2>&1
  status=$?
  set -e
  python3 - "$output_dir/reports/$name.json" "$name" "$status" <<'PY'
import json, pathlib, sys
pathlib.Path(sys.argv[1]).write_text(json.dumps({"gate": sys.argv[2], "exit_code": int(sys.argv[3])}, sort_keys=True) + "\n", encoding="utf-8")
PY
  [[ "$status" == 0 ]] || exit "$status"
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
  run_gate "$output_dir" p0-evidence make -C "$repo_root" p0-check
  run_gate "$output_dir" known-issues "$repo_root/scripts/release-known-issues-check.sh"
  run_gate "$output_dir" platform-static make -C "$repo_root" platform
  run_gate "$output_dir" makefile-parse make -C "$repo_root" -n p0-check platform hygiene ci
  run_gate "$output_dir" security-license-secret make -C "$repo_root" hygiene
  run_gate "$output_dir" full-ci make -C "$repo_root" ci
  run_gate "$output_dir" offline-fixture-unit bash -c "cd '$repo_root/backend' && uv run --frozen pytest -q tests/test_p0.py tests/test_quant_engines.py tests/test_event_migration_and_bootstrap.py -k 'not sqlite_foreign_keys'"
  run_gate "$output_dir" full-restore bash -c "cd '$repo_root/backend' && uv run --frozen pytest -q tests/test_event_migration_and_bootstrap.py -k 'restore or roundtrip'"
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
]
migrations = sorted((root / "backend/alembic/versions").glob("*.py"))
reports = sorted((output / "reports").glob("*"))
if not migrations or not reports:
    raise SystemExit("Alembic migrations and RC gate reports are required")
evidence_files = sorted(path for path in output.rglob("*") if path.is_file() and path.name not in {"release-manifest.json", "SHA256SUMS"})

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
    "images": [
        {"name": backend_image, "digest": backend_digest, "sbom": "buildkit-attestation", "provenance": "github-attestation", "signature": "github-attestation"},
        {"name": frontend_image, "digest": frontend_digest, "sbom": "buildkit-attestation", "provenance": "github-attestation", "signature": "github-attestation"},
    ],
    "compose_images": json.loads((output / "compose-images.json").read_text(encoding="utf-8")),
}
if manifest["compose_images"] != {"api": f"{backend_image}@{backend_digest}", "frontend": f"{frontend_image}@{frontend_digest}"}:
    raise SystemExit("manifest refuses a Compose image binding that differs from published GHCR digests")
(output / "release-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
  manifest) [[ "$#" == 8 ]] || usage; manifest "$2" "$3" "$4" "$5" "$6" "$7" "$8" ;;
  compose-bind) [[ "$#" == 6 ]] || usage; compose_bind "$2" "$3" "$4" "$5" "$6" ;;
  *) usage ;;
esac
