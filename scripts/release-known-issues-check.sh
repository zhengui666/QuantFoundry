#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
registry="${1:-$repo_root/docs/治理/release-known-issues.json}"

python3 - "$registry" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError) as error:
    raise SystemExit(f"invalid known-issue registry: {error}")

if not isinstance(data, dict) or data.get("version") != "1.0.0" or not isinstance(data.get("issues"), list):
    raise SystemExit("known-issue registry must contain version 1.0.0 and an issues array")

blocking = []
for index, issue in enumerate(data["issues"]):
    if not isinstance(issue, dict):
        raise SystemExit(f"issues[{index}] must be an object")
    required = ("id", "severity", "status", "scope")
    if any(not isinstance(issue.get(key), str) or not issue[key].strip() for key in required):
        raise SystemExit(f"issues[{index}] requires non-empty id, severity, status, and scope")
    if issue["severity"] == "S0" and issue["status"] != "closed":
        blocking.append(issue["id"])
    elif issue["severity"] == "S1" and issue["status"] != "closed" and issue["scope"] == "V1_P0_PATH":
        blocking.append(issue["id"])

if blocking:
    raise SystemExit("unresolved blocking known issue(s): " + ", ".join(blocking))
print(json.dumps({"result": "pass", "gate": "known-issue-review", "issues": len(data["issues"]), "blocking": []}, sort_keys=True))
PY
