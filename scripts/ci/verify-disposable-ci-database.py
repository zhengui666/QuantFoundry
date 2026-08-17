#!/usr/bin/env python3
"""Reject CI database URLs that are not bound to this GitHub run."""

from __future__ import annotations

import os
import re
import sys

from sqlalchemy import create_engine, text


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify-disposable-ci-database.py DATABASE_URL")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    if not run_id.isdigit() or int(run_id) < 1:
        raise SystemExit("GITHUB_RUN_ID is required for disposable CI database proof")
    expected = f"qf_ci_{run_id}"
    engine = create_engine(sys.argv[1])
    try:
        with engine.connect() as connection:
            actual = connection.execute(text("SELECT current_database()" )).scalar_one()
    finally:
        engine.dispose()
    if actual != expected or not re.fullmatch(r"qf_ci_[0-9]+", str(actual)):
        raise SystemExit(
            f"database name {actual!r} is not the current run's disposable database"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
