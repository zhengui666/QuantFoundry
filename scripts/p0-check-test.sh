#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixture_dir="$(mktemp -d)"
mock_dir="$fixture_dir/mock-bin"
trap 'rm -rf "$fixture_dir"' EXIT
mkdir -p "$mock_dir"

commit_sha="$(git -C "$repo_root" rev-parse HEAD)"
criterion='Independent criterion is satisfied.'
export QF_MOCK_COMMIT="$commit_sha"
export QF_MOCK_ARTIFACT_DIR="$fixture_dir"

python3 - "$fixture_dir" "$commit_sha" "$criterion" <<'PY'
import hashlib
import json
import pathlib
import sys
import zipfile

directory = pathlib.Path(sys.argv[1])
commit, criterion = sys.argv[2:]
content_types = {
    "Independent Test Agent": "application/vnd.quantfoundry.p0-test-evidence+json;version=1",
    "Independent Review Agent": "application/vnd.quantfoundry.p0-review-evidence+json;version=1",
}

def create(role, run_id, artifact_id, report_commit=commit, release_asset=False):
    uri = (
        "https://github.com/acme/quantfoundry/releases/download/v0.1.0-alpha/review-evidence.zip"
        if release_asset
        else f"https://github.com/acme/quantfoundry/actions/runs/{run_id}/artifacts/{artifact_id}"
    )
    run_uri = f"https://github.com/acme/quantfoundry/actions/runs/{run_id}"
    commands = [{"command": "make test" if role.endswith("Test Agent") else "make review", "result": "pass", "exit_code": 0}]
    attestation = {
        "provider": "github-actions",
        "issuer": "https://token.actions.githubusercontent.com",
        "repository": "acme/quantfoundry",
        "run_id": run_id,
        "subject_uri": run_uri,
    }
    report = {
        "schema_version": "1.0.0",
        "content_type": content_types[role],
        "commit_sha": report_commit,
        "github_run_id": run_id,
        "verifier_role": role,
        "verified_at_utc": "2026-08-11T00:00:00Z",
        "closure_criteria": [criterion],
        "commands": commands,
        "artifact": {"run_uri": run_uri},
        "attestation": attestation,
    }
    payload = json.dumps(report, sort_keys=True, separators=(",", ":")).encode()
    archive = directory / f"artifact-{artifact_id}.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        bundle.writestr("p0-evidence.json", payload)
    return {
        "role": role,
        "run_id": run_id,
        "artifact_id": artifact_id,
        "uri": uri,
        "run_uri": run_uri,
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "report_sha256": hashlib.sha256(payload).hexdigest(),
        "content_type": content_types[role],
        "commands": commands,
    }

metadata = {
    "test": create("Independent Test Agent", 100, 200),
    "review": create("Independent Review Agent", 101, 201),
    "review_bad_commit": create("Independent Review Agent", 101, 202, "ffffffffffffffffffffffffffffffffffffffff"),
    "review_same_run": create("Independent Review Agent", 100, 203),
    "review_release_asset": create("Independent Review Agent", 101, 204, release_asset=True),
}
(directory / "metadata.json").write_text(json.dumps(metadata, sort_keys=True), encoding="utf-8")
PY

mock_gh="$mock_dir/gh"
# shellcheck disable=SC2016 # The quoted arguments are literal source for the mock gh executable.
printf '%s\n' \
  '#!/usr/bin/env bash' \
  'set -euo pipefail' \
  '[[ "${1:-}" == api ]] || exit 2' \
  'endpoint="${2:-}"' \
  'if [[ "${QF_MOCK_FAIL:-}" == 1 ]]; then exit 1; fi' \
  'output=""' \
  'for ((index = 1; index <= $#; index++)); do' \
  '  if [[ "${!index}" == --output ]]; then next=$((index + 1)); output="${!next}"; fi' \
  'done' \
  'if [[ "$endpoint" =~ /actions/artifacts/([0-9]+)/zip$ ]]; then' \
  '  cp "$QF_MOCK_ARTIFACT_DIR/artifact-${BASH_REMATCH[1]}.zip" "$output"' \
  '  exit 0' \
  'fi' \
  'if [[ "$endpoint" =~ /releases/assets/204$ ]]; then if [[ -n "$output" ]]; then cp "$QF_MOCK_ARTIFACT_DIR/artifact-204.zip" "$output"; else cat "$QF_MOCK_ARTIFACT_DIR/artifact-204.zip"; fi; exit 0; fi' \
  'if [[ "$endpoint" =~ /actions/runs/[0-9]+$ ]]; then run_path="${QF_MOCK_RUN_PATH:-}"; if [[ -z "$run_path" ]]; then if [[ "$endpoint" == */actions/runs/100 ]]; then run_path=".github/workflows/independent-agent-test.yml@refs/heads/main"; else run_path=".github/workflows/independent-agent-review.yml@refs/heads/main"; fi; fi; printf "{\\\"head_sha\\\":\\\"%s\\\",\\\"status\\\":\\\"%s\\\",\\\"conclusion\\\":\\\"%s\\\",\\\"path\\\":\\\"%s\\\"}\\n" "${QF_MOCK_RUN_HEAD:-$QF_MOCK_COMMIT}" "${QF_MOCK_RUN_STATUS:-completed}" "${QF_MOCK_RUN_CONCLUSION:-success}" "$run_path"; exit 0; fi' \
  'if [[ "$endpoint" =~ /actions/artifacts/([0-9]+)$ ]]; then' \
  '  case "${BASH_REMATCH[1]}" in 200) run=100 ;; 201|202) run=101 ;; 203) run=100 ;; *) exit 1 ;; esac' \
  '  printf "{\\\"expired\\\":false,\\\"workflow_run\\\":{\\\"id\\\":%s}}\\n" "$run"' \
  '  exit 0' \
  'fi' \
  'if [[ "$endpoint" == */git/ref/tags/v0.1.0-alpha ]]; then printf "{\\\"object\\\":{\\\"type\\\":\\\"commit\\\",\\\"sha\\\":\\\"%s\\\"}}\\n" "$QF_MOCK_COMMIT"; exit 0; fi' \
  'if [[ "$endpoint" == */releases/tags/v0.1.0-alpha ]]; then printf "{\\\"assets\\\":[{\\\"name\\\":\\\"review-evidence.zip\\\",\\\"id\\\":204}]}\\n"; exit 0; fi' \
  'exit 1' > "$mock_gh"
chmod +x "$mock_gh"

write_fixture() {
  local name="$1"
  QF_FIXTURE_CASE="$name" python3 - "$fixture_dir" "$commit_sha" "$criterion" <<'PY'
import json
import os
import pathlib
import sys

directory = pathlib.Path(sys.argv[1])
commit, criterion = sys.argv[2:]
case = os.environ["QF_FIXTURE_CASE"]
metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))

def record(item):
    attestation = {
        "provider": "github-actions",
        "issuer": "https://token.actions.githubusercontent.com",
        "repository": "acme/quantfoundry",
        "run_id": item["run_id"],
        "subject_uri": item["run_uri"],
        "subject_sha256": item["report_sha256"],
    }
    return {
        "verifier_role": item["role"],
        "verified_at_utc": "2026-08-11T00:00:00Z",
        "commit_sha": commit,
        "build_id": f"github-actions/{item['run_id']}",
        "artifact_uri": item["uri"],
        "artifact_sha256": item["archive_sha256"],
        "report": {"path": "p0-evidence.json", "sha256": item["report_sha256"], "content_type": item["content_type"]},
        "attestation": attestation,
        "closure_criteria": [criterion],
        "commands": item["commands"],
    }

expected_ids = [
    "P0-PRODUCT-PAPER-DAILY-SCHEDULER",
    "P0-CONTRACT-OPENAPI-45",
    "P0-CONTRACT-TOOLS-13",
    "P0-SCHEMA-ALEMBIC-AUTHORITY",
    "P0-ARCHITECTURE-TARGET-LAYERS",
    "P0-SECURITY-RESEARCH-INTEGRITY",
    "P0-CI-REPRODUCIBILITY",
    "P0-SUPPLY-CHAIN-RELEASE-EVIDENCE",
]
test = record(metadata["test"])
review = record(metadata["review"])
status = "closed"
evidence = [test, review]
if case == "empty-evidence":
    evidence = []
elif case == "missing-reviewer":
    evidence = [test]
elif case == "wrong-commit":
    test["commit_sha"] = "ffffffffffffffffffffffffffffffffffffffff"
elif case == "missing-artifact":
    test["artifact_uri"] = ""
elif case == "status-bypass":
    status = "waived"
elif case == "hash-mismatch":
    test["artifact_sha256"] = "f" * 64
elif case == "report-identity":
    evidence = [test, record(metadata["review_bad_commit"])]
elif case == "run-collision":
    evidence = [test, record(metadata["review_same_run"])]
elif case == "release-asset-positive":
    evidence = [test, record(metadata["review_release_asset"])]

def blocker(blocker_id):
    return {
        "id": blocker_id,
        "owner_role": "Release Agent",
        "closure_criteria": [criterion],
        "status": status,
        "release_blocking": True,
        "evidence": evidence,
    }

fixture = {
    "version": "1.0.0",
    "blockers": [blocker(blocker_id) for blocker_id in expected_ids],
}
if case == "missing-id":
    fixture["blockers"] = fixture["blockers"][:-1]
elif case == "duplicate-id":
    fixture["blockers"][-1]["id"] = fixture["blockers"][0]["id"]
elif case == "release-flag":
    fixture["blockers"][0]["release_blocking"] = False
elif case == "empty-registry":
    fixture["blockers"] = []
elif case == "unknown-id":
    fixture["blockers"][-1]["id"] = "P0-UNKNOWN"
(directory / f"{case}.yaml").write_text(json.dumps(fixture), encoding="utf-8")
PY
}

run_fixture() {
  local name="$1"
  env \
    PATH="$mock_dir:$PATH" \
    GITHUB_REPOSITORY='acme/quantfoundry' \
    GITHUB_TOKEN='fixture-token' \
    QF_RELEASE_COMMIT="$commit_sha" \
    "$repo_root/scripts/p0-check.sh" "$fixture_dir/$name.yaml" --require-closed
}

write_fixture positive
run_fixture positive >/dev/null
write_fixture release-asset-positive
run_fixture release-asset-positive >/dev/null

# Offline reporting validates only local registry schema and must not require
# remote credentials or closure evidence, including when a blocker is unclosed.
write_fixture positive
env PATH="$mock_dir:$PATH" QF_RELEASE_COMMIT="$commit_sha" \
  "$repo_root/scripts/p0-check.sh" "$fixture_dir/positive.yaml" --offline-report >/dev/null
write_fixture empty-evidence
env PATH="$mock_dir:$PATH" QF_RELEASE_COMMIT="$commit_sha" \
  "$repo_root/scripts/p0-check.sh" "$fixture_dir/empty-evidence.yaml" --offline-report >/dev/null
write_fixture status-bypass
if env PATH="$mock_dir:$PATH" QF_RELEASE_COMMIT="$commit_sha" \
  "$repo_root/scripts/p0-check.sh" "$fixture_dir/status-bypass.yaml" --offline-report >/dev/null 2>&1; then
  printf '%s\n' 'Expected schema-invalid offline fixture to fail.' >&2
  exit 1
fi

for case_name in empty-evidence missing-reviewer wrong-commit missing-artifact status-bypass hash-mismatch report-identity run-collision missing-id duplicate-id release-flag empty-registry unknown-id; do
  write_fixture "$case_name"
  if run_fixture "$case_name" >/dev/null 2>&1; then
    printf 'Expected fixture to fail: %s\n' "$case_name" >&2
    exit 1
  fi
done

if env -u GITHUB_TOKEN PATH="$mock_dir:$PATH" GITHUB_REPOSITORY='acme/quantfoundry' QF_RELEASE_COMMIT="$commit_sha" "$repo_root/scripts/p0-check.sh" "$fixture_dir/positive.yaml" --require-closed >/dev/null 2>&1; then
  printf '%s\n' 'Expected fixture to fail without GITHUB_TOKEN.' >&2
  exit 1
fi
if env PATH="$mock_dir:$PATH" GITHUB_REPOSITORY='acme/quantfoundry' GITHUB_TOKEN='fixture-token' QF_RELEASE_COMMIT="$commit_sha" QF_MOCK_FAIL=1 "$repo_root/scripts/p0-check.sh" "$fixture_dir/positive.yaml" --require-closed >/dev/null 2>&1; then
  printf '%s\n' 'Expected fixture to fail when remote evidence is unavailable.' >&2
  exit 1
fi
if env PATH="$mock_dir:$PATH" GITHUB_REPOSITORY='acme/quantfoundry' GITHUB_TOKEN='fixture-token' QF_RELEASE_COMMIT="$commit_sha" QF_MOCK_RUN_HEAD='ffffffffffffffffffffffffffffffffffffffff' "$repo_root/scripts/p0-check.sh" "$fixture_dir/positive.yaml" --require-closed >/dev/null 2>&1; then
  printf '%s\n' 'Expected fixture to fail when run identity is not bound to the commit.' >&2
  exit 1
fi
if env PATH="$mock_dir:$PATH" GITHUB_REPOSITORY='acme/quantfoundry' GITHUB_TOKEN='fixture-token' QF_RELEASE_COMMIT="$commit_sha" QF_MOCK_RUN_CONCLUSION='failure' "$repo_root/scripts/p0-check.sh" "$fixture_dir/positive.yaml" --require-closed >/dev/null 2>&1; then
  printf '%s\n' 'Expected fixture to fail when a verification run fails.' >&2
  exit 1
fi
if env PATH="$mock_dir:$PATH" GITHUB_REPOSITORY='acme/quantfoundry' GITHUB_TOKEN='fixture-token' QF_RELEASE_COMMIT="$commit_sha" QF_MOCK_RUN_STATUS='completed' QF_MOCK_RUN_CONCLUSION='cancelled' "$repo_root/scripts/p0-check.sh" "$fixture_dir/positive.yaml" --require-closed >/dev/null 2>&1; then
  printf '%s\n' 'Expected fixture to fail when a verification run is cancelled.' >&2
  exit 1
fi
if env PATH="$mock_dir:$PATH" GITHUB_REPOSITORY='acme/quantfoundry' GITHUB_TOKEN='fixture-token' QF_RELEASE_COMMIT="$commit_sha" QF_MOCK_RUN_PATH='.github/workflows/untrusted.yml@refs/heads/main' "$repo_root/scripts/p0-check.sh" "$fixture_dir/positive.yaml" --require-closed >/dev/null 2>&1; then
  printf '%s\n' 'Expected fixture to fail for an unauthorized verification workflow.' >&2
  exit 1
fi

printf '%s\n' '{"result":"pass","gate":"p0-check-fixtures"}'
