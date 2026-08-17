#!/usr/bin/env python3
"""Read-only worker/scheduler liveness check backed by durable heartbeats."""

from __future__ import annotations

import argparse
import os
import socket
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app import main as domain_main
from app.main import RuntimeHeartbeat, SessionLocal


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--component", required=True, choices=("worker", "scheduler"))
    parser.add_argument("--queue", choices=("core", "agent"))
    parser.add_argument("--max-age-seconds", type=int, default=120)
    parser.add_argument(
        "--instance-id",
        default=None,
    )
    args = parser.parse_args()
    if args.component == "worker" and args.queue is None:
        parser.error("--queue is required for worker health checks")
    if args.component == "scheduler" and args.queue is not None:
        parser.error("--queue is invalid for scheduler health checks")
    if args.max_age_seconds < 1:
        parser.error("--max-age-seconds must be positive")
    if args.instance_id is None:
        if args.component == "worker":
            args.instance_id = os.getenv("QF_WORKER_ID") or socket.gethostname()
        else:
            args.instance_id = os.getenv("QF_SCHEDULER_ID") or (
                f"{socket.gethostname()}:{os.getppid()}:scheduler"
            )
    if args.component == "worker" and not args.instance_id.endswith(f":{args.queue}"):
        args.instance_id = f"{args.instance_id}:{args.queue}"
    return args


def main() -> int:
    args = parse_args()
    if not domain_main.app.state.domain_database_available:
        environment = os.getenv("QF_ENVIRONMENT") or os.getenv("QF_ENV", "production")
        if environment in {"local", "development"}:
            return 0
        print("domain_database_unavailable", file=sys.stderr)
        return 1
    now = datetime.now(UTC)
    threshold = now - timedelta(seconds=args.max_age_seconds)
    statement = select(RuntimeHeartbeat).where(
        RuntimeHeartbeat.component == args.component,
        RuntimeHeartbeat.occurred_at >= threshold,
        RuntimeHeartbeat.occurred_at <= now,
        RuntimeHeartbeat.instance_id == args.instance_id,
    )
    if args.queue is not None:
        statement = statement.where(RuntimeHeartbeat.queue_name == args.queue)
    session = SessionLocal()
    try:
        if session.execute(statement.limit(1)).scalar_one_or_none():
            return 0
        print(
            f"heartbeat_missing component={args.component} queue={args.queue}",
            file=sys.stderr,
        )
        return 1
    except SQLAlchemyError as error:
        print(f"heartbeat_query_failed error={type(error).__name__}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
