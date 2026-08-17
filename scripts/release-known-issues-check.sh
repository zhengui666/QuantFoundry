#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
registry="${1:-$repo_root/docs/治理/release-known-issues.json}"

python3 - "$registry" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])

def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate key: {key}")
        result[key] = value
    return result

try:
    data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=reject_duplicate_keys)
except (OSError, ValueError, json.JSONDecodeError) as error:
    raise SystemExit(f"invalid known-issue registry: {error}")

if not isinstance(data, dict) or data.get("version") != "1.0.0" or not isinstance(data.get("issues"), list):
    raise SystemExit("known-issue registry must contain version 1.0.0 and an issues array")

blocking = []
ids = set()
allowed_severity = {"S0", "S1", "S2", "S3"}
allowed_status = {"open", "closed"}
allowed_scope = {"V1_P0_PATH", "OTHER"}
for index, issue in enumerate(data["issues"]):
    if not isinstance(issue, dict):
        raise SystemExit(f"issues[{index}] must be an object")
    required = ("id", "severity", "status", "scope")
    if any(not isinstance(issue.get(key), str) or not issue[key].strip() for key in required):
        raise SystemExit(f"issues[{index}] requires non-empty id, severity, status, and scope")
    if issue["id"] in ids:
        raise SystemExit(f"issues[{index}].id is duplicated")
    ids.add(issue["id"])
    if issue["severity"] not in allowed_severity:
        raise SystemExit(f"issues[{index}].severity is unsupported")
    if issue["status"] not in allowed_status:
        raise SystemExit(f"issues[{index}].status is unsupported")
    if issue["scope"] not in allowed_scope:
        raise SystemExit(f"issues[{index}].scope is unsupported")
    if issue["severity"] == "S0" and issue["status"] != "closed":
        blocking.append(issue["id"])
    elif issue["severity"] == "S1" and issue["status"] != "closed" and issue["scope"] == "V1_P0_PATH":
        blocking.append(issue["id"])

if blocking:
    raise SystemExit("unresolved blocking known issue(s): " + ", ".join(blocking))
print(json.dumps({"result": "pass", "gate": "known-issue-review", "issues": len(data["issues"]), "blocking": []}, sort_keys=True))
PY
