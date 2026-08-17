#!/usr/bin/env python3
"""Create the first owner access key in the embedded Control DB.

This is the trusted local recovery ceremony: the secret is printed once and
never written to a file, environment variable, database column, or log.
"""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import select

from app.control_plane import (
    ControlSessionLocal,
    GeneralAccessKey,
    init_control_db,
    issue_access_key,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create the first QuantFoundry access key"
    )
    parser.add_argument("--label", default="primary", help="human label for the key")
    parser.add_argument("--check", action="store_true", help="check whether the first-key ceremony is still required")
    args = parser.parse_args()
    try:
        init_control_db()
        if args.check:
            with ControlSessionLocal() as session:
                has_active = session.scalar(
                    select(GeneralAccessKey.key_id).where(
                        GeneralAccessKey.status == "ACTIVE"
                    ).limit(1)
                ) is not None
            return 3 if has_active else 0
        print(issue_access_key(args.label.strip()))
    except (RuntimeError, ValueError) as error:
        print(f"access-key bootstrap failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
