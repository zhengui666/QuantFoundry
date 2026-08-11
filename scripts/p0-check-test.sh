#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixture_dir="$(mktemp -d)"
trap 'rm -rf "$fixture_dir"' EXIT

commit_sha='0123456789abcdef0123456789abcdef01234567'
artifact_sha256='0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef'
criterion='Independent criterion is satisfied.'

write_fixture() {
  local name="$1"
  local evidence="$2"
  local status="${3:-closed}"
  printf '%s\n' \
    'version: "1.0.0"' \
    'blockers:' \
    '  - id: P0-FIXTURE' \
    '    owner_role: Release Agent' \
    "    closure_criteria: [\"$criterion\"]" \
    "    status: $status" \
    '    release_blocking: true' \
    "$evidence" > "$fixture_dir/$name.yaml"
}

valid_evidence="    evidence:\n      - verifier_role: Independent Test Agent\n        verified_at_utc: '2026-08-11T00:00:00Z'\n        commit_sha: $commit_sha\n        build_id: github-actions/100\n        artifact_uri: https://github.com/acme/quantfoundry/actions/runs/100/artifacts/200\n        artifact_sha256: $artifact_sha256\n        closure_criteria: [\"$criterion\"]\n        commands: [{command: 'make test', result: pass, exit_code: 0}]\n      - verifier_role: Independent Review Agent\n        verified_at_utc: '2026-08-11T00:01:00Z'\n        commit_sha: $commit_sha\n        build_id: github-actions/101\n        artifact_uri: https://github.com/acme/quantfoundry/actions/runs/101/artifacts/201\n        artifact_sha256: $artifact_sha256\n        closure_criteria: [\"$criterion\"]\n        commands: [{command: 'make review', result: pass, exit_code: 0}]"
write_fixture positive "$(printf '%b' "$valid_evidence")"
QF_RELEASE_COMMIT="$commit_sha" "$repo_root/scripts/p0-check.sh" "$fixture_dir/positive.yaml" --require-closed >/dev/null

for case_name in empty-evidence missing-reviewer wrong-commit missing-artifact status-bypass; do
  evidence="$valid_evidence"
  fixture_status='closed'
  case "$case_name" in
    empty-evidence) evidence='    evidence: []' ;;
    missing-reviewer) evidence="${valid_evidence/Independent Review Agent/Release Agent}" ;;
    wrong-commit) evidence="${valid_evidence/$commit_sha/ffffffffffffffffffffffffffffffffffffffff}" ;;
    missing-artifact) evidence="${valid_evidence/artifact_uri: https:\/\/github.com\/acme\/quantfoundry\/actions\/runs\/100\/artifacts\/200/artifact_uri: ''}" ;;
    status-bypass) fixture_status='waived' ;;
  esac
  write_fixture "$case_name" "$(printf '%b' "$evidence")" "$fixture_status"
  if QF_RELEASE_COMMIT="$commit_sha" "$repo_root/scripts/p0-check.sh" "$fixture_dir/$case_name.yaml" --require-closed >/dev/null 2>&1; then
    printf 'Expected fixture to fail: %s\n' "$case_name" >&2
    exit 1
  fi
done

printf '%s\n' '{"result":"pass","gate":"p0-check-fixtures"}'
