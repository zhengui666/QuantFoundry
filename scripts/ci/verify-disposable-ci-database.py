#!/usr/bin/env python3
"""Reject CI database URLs that are not bound to this GitHub run."""

from __future__ import annotations

import os
import re
import sys
from urllib.parse import parse_qs, urlsplit

from sqlalchemy import create_engine, text


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify-disposable-ci-database.py DATABASE_URL")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    if not run_id.isdigit() or int(run_id) < 1:
        raise SystemExit("GITHUB_RUN_ID is required for disposable CI database proof")
    run_attempt = os.getenv("GITHUB_RUN_ATTEMPT", "")
    if not run_attempt.isdigit() or int(run_attempt) < 1:
        raise SystemExit(
            "GITHUB_RUN_ATTEMPT is required for disposable CI database proof"
        )
    expected = f"qf_ci_{run_id}_{run_attempt}"
    database_url = sys.argv[1]
    parsed = urlsplit(database_url)
    routing_overrides = {
        key.lower()
        for key in parse_qs(parsed.query, keep_blank_values=True)
        if key.lower() in {"host", "hostaddr", "port", "service", "dbname", "user"}
    }
    if (
        parsed.hostname != "localhost"
        or parsed.port != 5432
        or parsed.username != "quantfoundry"
        or routing_overrides
    ):
        raise SystemExit(
            "CI database must use the fixed localhost:5432 quantfoundry endpoint"
        )
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            actual, user, port = connection.execute(
                text(
                    "SELECT current_database(), current_user, "
                    "inet_server_port()"
                )
            ).one()
    finally:
        engine.dispose()
    if (
        actual != expected
        or user != "quantfoundry"
        or port != 5432
        or not re.fullmatch(r"qf_ci_[0-9]+_[0-9]+", str(actual))
    ):
        raise SystemExit(
            f"database name {actual!r} is not the current run's disposable database"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
