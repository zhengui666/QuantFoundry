#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
fixture_root="$(mktemp -d)"
trap 'rm -rf "$fixture_root"' EXIT

write_fixture() {
  local name="$1"
  local directory="$fixture_root/$name"
  mkdir -p "$directory/attestations"
  printf '%s\n' '{"evidence":"backend"}' > "$directory/attestations/backend.json"
  case "$name" in
    positive)
      printf '%s\n' '{"release_assets":[{"name":"release-manifest.json","source":"release-manifest.json"},{"name":"SHA256SUMS","source":"SHA256SUMS"},{"name":"attestations--backend.json","source":"attestations/backend.json"}]}' > "$directory/release-manifest.json"
      ;;
    collision)
      mkdir -p "$directory/provenance"
      printf '%s\n' '{"evidence":"provenance"}' > "$directory/provenance/backend.json"
      printf '%s\n' '{"release_assets":[{"name":"release-manifest.json","source":"release-manifest.json"},{"name":"SHA256SUMS","source":"SHA256SUMS"},{"name":"backend.json","source":"attestations/backend.json"},{"name":"backend.json","source":"provenance/backend.json"}]}' > "$directory/release-manifest.json"
      ;;
    orphan)
      printf '%s\n' '{"orphan":true}' > "$directory/unlisted.json"
      printf '%s\n' '{"release_assets":[{"name":"release-manifest.json","source":"release-manifest.json"},{"name":"SHA256SUMS","source":"SHA256SUMS"},{"name":"attestations--backend.json","source":"attestations/backend.json"}]}' > "$directory/release-manifest.json"
      ;;
    missing)
      printf '%s\n' '{"release_assets":[{"name":"release-manifest.json","source":"release-manifest.json"},{"name":"SHA256SUMS","source":"SHA256SUMS"},{"name":"missing--backend.json","source":"missing/backend.json"},{"name":"attestations--backend.json","source":"attestations/backend.json"}]}' > "$directory/release-manifest.json"
      ;;
    symlink)
      printf '%s\n' '{"evidence":"outside"}' > "$fixture_root/outside.json"
      ln -s "$fixture_root/outside.json" "$directory/escape.json"
      printf '%s\n' '{"release_assets":[{"name":"release-manifest.json","source":"release-manifest.json"},{"name":"SHA256SUMS","source":"SHA256SUMS"},{"name":"escape.json","source":"escape.json"},{"name":"attestations--backend.json","source":"attestations/backend.json"}]}' > "$directory/release-manifest.json"
      ;;
    unsafe-source)
      printf '%s\n' '{"release_assets":[{"name":"release-manifest.json","source":"release-manifest.json"},{"name":"SHA256SUMS","source":"SHA256SUMS"},{"name":"escape.json","source":"../outside.json"},{"name":"attestations--backend.json","source":"attestations/backend.json"}]}' > "$directory/release-manifest.json"
      ;;
    unsafe-name)
      printf '%s\n' '{"release_assets":[{"name":"release-manifest.json","source":"release-manifest.json"},{"name":"SHA256SUMS","source":"SHA256SUMS"},{"name":"nested/backend.json","source":"attestations/backend.json"}]}' > "$directory/release-manifest.json"
      ;;
    reserved-mismatch)
      printf '%s\n' '{"release_assets":[{"name":"release-manifest.json","source":"attestations/backend.json"},{"name":"SHA256SUMS","source":"SHA256SUMS"}]}' > "$directory/release-manifest.json"
      ;;
    reserved-swap)
      printf '%s\n' '{"release_assets":[{"name":"release-manifest.json","source":"SHA256SUMS"},{"name":"SHA256SUMS","source":"release-manifest.json"}]}' > "$directory/release-manifest.json"
      ;;
    *)
      printf 'Unknown fixture: %s\n' "$name" >&2
      exit 2
      ;;
  esac
}

write_fixture positive
"$repo_root/scripts/release-evidence.sh" package-assets "$fixture_root/positive"
test -f "$fixture_root/positive/SHA256SUMS"
test -f "$fixture_root/positive/release-assets/release-manifest.json"
test -f "$fixture_root/positive/release-assets/SHA256SUMS"
test -f "$fixture_root/positive/release-assets/attestations--backend.json"
python3 - "$fixture_root/positive" <<'PY'
import hashlib
import pathlib
import subprocess
import sys

root = pathlib.Path(sys.argv[1])
staging = root / "release-assets"
assert sorted(path.name for path in staging.iterdir()) == [
    "SHA256SUMS", "attestations--backend.json", "release-manifest.json"
]
assert (staging / "release-manifest.json").read_bytes() == (root / "release-manifest.json").read_bytes()
assert (staging / "attestations--backend.json").read_bytes() == (root / "attestations/backend.json").read_bytes()
assert (staging / "SHA256SUMS").read_bytes() == (root / "SHA256SUMS").read_bytes()
checksums = {}
for line in (root / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
    digest, name = line.split("  ", 1)
    assert name not in checksums
    checksums[name] = digest
assert set(checksums) == {"attestations--backend.json", "release-manifest.json"}
for name, digest in checksums.items():
    assert hashlib.sha256((staging / name).read_bytes()).hexdigest() == digest
subprocess.run(["sha256sum", "--check", "--strict", str(root / "SHA256SUMS")], cwd=staging, check=True, stdout=subprocess.DEVNULL)
PY

for case_name in collision orphan missing symlink unsafe-source unsafe-name reserved-mismatch reserved-swap; do
  write_fixture "$case_name"
  diagnostic="$fixture_root/$case_name.err"
  if "$repo_root/scripts/release-evidence.sh" package-assets "$fixture_root/$case_name" > /dev/null 2>"$diagnostic"; then
    printf 'Expected fixture to fail: %s\n' "$case_name" >&2
    exit 1
  fi
  case "$case_name" in
    collision) expected='name collision' ;;
    orphan) expected='orphan source files' ;;
    missing) expected='missing source files' ;;
    symlink) expected='symlink release asset source' ;;
    unsafe-source) expected='source must be a safe relative path' ;;
    unsafe-name) expected='name must be a non-empty flat filename' ;;
    reserved-mismatch|reserved-swap) expected='reserved release asset name must map to itself' ;;
  esac
  grep -Fq "$expected" "$diagnostic" || {
    cat "$diagnostic" >&2
    exit 1
  }
done

printf '%s\n' '{"result":"pass","gate":"release-evidence-assets-fixtures"}'
