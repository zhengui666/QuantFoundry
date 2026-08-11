#!/usr/bin/env python3
"""Verify repeat local bootstrap output without exposing one-time tokens."""

from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

STABLE_FIELDS = (
    "owner_id",
    "workspace_id",
    "settings_id",
    "ai_connection_id",
    "data_connection_id",
    "research_policy_id",
    "validation_policy_id",
    "risk_policy_id",
    "cost_model_id",
    "dataset_id",
)


def load_result(path: Path) -> dict[str, object]:
    if path.is_symlink():
        raise ValueError(f"refusing symlink bootstrap result: {path}")
    if stat.S_IMODE(path.stat().st_mode) != 0o600:
        raise ValueError(f"bootstrap result must have mode 0600: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"bootstrap result must be an object: {path}")
    return value


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: bootstrap_result_check.py FIRST SECOND", file=sys.stderr)
        return 2
    first = load_result(Path(sys.argv[1]))
    second = load_result(Path(sys.argv[2]))
    if any(first.get(field) != second.get(field) for field in STABLE_FIELDS):
        raise ValueError("repeat bootstrap changed a stable canonical reference")
    first_token = first.get("owner_session_token")
    second_token = second.get("owner_session_token")
    if not isinstance(first_token, str) or not isinstance(second_token, str):
        raise TypeError("repeat bootstrap did not return one-time session tokens")
    if not first_token or not second_token or first_token == second_token:
        raise ValueError("repeat bootstrap must rotate the one-time session token")
    print(
        "Bootstrap repeat preserved 10 canonical refs and rotated the one-time token."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
