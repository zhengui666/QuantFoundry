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

for case_name in collision orphan missing; do
  write_fixture "$case_name"
  if "$repo_root/scripts/release-evidence.sh" package-assets "$fixture_root/$case_name" >/dev/null 2>&1; then
    printf 'Expected fixture to fail: %s\n' "$case_name" >&2
    exit 1
  fi
done

printf '%s\n' '{"result":"pass","gate":"release-evidence-assets-fixtures"}'
