#!/usr/bin/env python3
"""Create the first owner access key in the embedded Control DB.

This is the trusted local recovery ceremony: the secret is printed once and
never written to a file, environment variable, database column, or log.
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime

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
    parser.add_argument(
        "--check",
        action="store_true",
        help="check whether the first-key ceremony is still required",
    )
    args = parser.parse_args()
    try:
        init_control_db()
        if args.check:
            with ControlSessionLocal() as session:
                has_active = (
                    session.scalar(
                        select(GeneralAccessKey.key_id)
                        .where(GeneralAccessKey.status == "ACTIVE")
                        .limit(1)
                    )
                    is not None
                )
            return 3 if has_active else 0
        issued_key = issue_access_key(args.label.strip())
        try:
            print(issued_key, flush=True)
        except BaseException as error:
            key_id = issued_key.split(".", 1)[0][4:]
            try:
                with ControlSessionLocal.begin() as session:
                    row = session.get(GeneralAccessKey, key_id)
                    if row is not None and row.status == "ACTIVE":
                        row.status = "REVOKED"
                        row.revoked_at = datetime.now(UTC)
                        row.revision += 1
            except BaseException as revoke_error:
                print(
                    f"access-key bootstrap delivery failed; revocation also failed for {key_id}; key may remain active: {revoke_error}",
                    file=sys.stderr,
                )
                if isinstance(revoke_error, (KeyboardInterrupt, SystemExit)):
                    raise
                return 2
            print(
                f"access-key bootstrap delivery failed; issued key {key_id} was revoked: {error}",
                file=sys.stderr,
            )
            if isinstance(error, KeyboardInterrupt):
                raise
            return 1
    except (RuntimeError, ValueError) as error:
        print(f"access-key bootstrap failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
