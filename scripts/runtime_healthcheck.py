#!/usr/bin/env python3
"""Read-only worker/scheduler liveness check backed by durable heartbeats."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--component", required=True, choices=("worker", "scheduler"))
    parser.add_argument("--queue", choices=("core", "agent"))
    parser.add_argument("--max-age-seconds", type=int, default=120)
    args = parser.parse_args()
    if args.component == "worker" and args.queue is None:
        parser.error("--queue is required for worker health checks")
    if args.component == "scheduler" and args.queue is not None:
        parser.error("--queue is invalid for scheduler health checks")
    if args.max_age_seconds < 1:
        parser.error("--max-age-seconds must be positive")
    return args


def main() -> int:
    args = parse_args()
    database_url = os.environ.get("QF_DATABASE_URL")
    if database_url is None:
        print(
            "QF_DATABASE_URL is required for heartbeat health checks", file=sys.stderr
        )
        return 1

    threshold = datetime.now(UTC) - timedelta(seconds=args.max_age_seconds)
    query = (
        "SELECT 1 FROM runtime_heartbeats "
        "WHERE component = :component AND occurred_at >= :threshold"
    )
    parameters: dict[str, object] = {
        "component": args.component,
        "threshold": threshold,
    }
    if args.queue is not None:
        query += " AND queue_name = :queue"
        parameters["queue"] = args.queue

    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            heartbeat = connection.execute(
                text(f"{query} LIMIT 1"), parameters
            ).scalar_one_or_none()
        if heartbeat is not None:
            return 0
        print(
            f"no recent {args.component} heartbeat"
            + (f" for queue {args.queue}" if args.queue is not None else ""),
            file=sys.stderr,
        )
        return 1
    except SQLAlchemyError as error:
        print(f"heartbeat query failed: {error}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
