#!/usr/bin/env python3
"""Read-only worker/scheduler liveness check backed by durable heartbeats."""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime, timedelta

from app.main import RuntimeHeartbeat, SessionLocal
from sqlalchemy import select
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
    threshold = datetime.now(UTC) - timedelta(seconds=args.max_age_seconds)
    statement = select(RuntimeHeartbeat).where(
        RuntimeHeartbeat.component == args.component,
        RuntimeHeartbeat.occurred_at >= threshold,
    )
    if args.queue is not None:
        statement = statement.where(RuntimeHeartbeat.queue_name == args.queue)
    session = SessionLocal()
    try:
        return 0 if session.execute(statement.limit(1)).scalar_one_or_none() else 1
    except SQLAlchemyError:
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
