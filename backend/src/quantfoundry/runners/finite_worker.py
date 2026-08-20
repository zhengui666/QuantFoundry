"""Durable finite-job worker.

P0/P1 implements queue ownership and process health. Concrete plugin, import, and
backtest handlers are added by later milestones and remain isolated child processes.
"""

from __future__ import annotations

import argparse
import logging
import os
import signal
import socket
import time
from collections.abc import Callable, Sequence

from sqlalchemy.orm import Session

from quantfoundry.db.models import Job
from quantfoundry.db.session import (
    create_database_engine,
    create_session_factory,
    ping_database,
)
from quantfoundry.events import append_event
from quantfoundry.jobs import claim_next_job, complete_job, fail_job, release_expired_leases
from quantfoundry.logging_utils import configure_logging
from quantfoundry.settings import Settings

LOGGER = logging.getLogger("quantfoundry.finite_worker")
Handler = Callable[[Session, Job], None]


def _noop_handler(_: Session, __: Job) -> None:
    return


HANDLERS: dict[str, Handler] = {"SYSTEM_NOOP": _noop_handler}


class StopFlag:
    requested = False

    def request(self, *_: object) -> None:
        self.requested = True


def run_once(settings: Settings, *, owner: str) -> bool:
    engine = create_database_engine(settings)
    factory = create_session_factory(engine)
    with factory.begin() as session:
        release_expired_leases(session)
        job = claim_next_job(
            session,
            owner=owner,
            lease_seconds=settings.job_lease_seconds,
        )
        if job is None:
            return False
        append_event(
            session,
            kind="JOB_LEASED",
            aggregate_type="job",
            aggregate_id=job.id,
            payload={"kind": job.kind, "attempt": job.attempt},
        )

    handler = HANDLERS.get(job.kind)
    with factory.begin() as session:
        current = session.get(Job, job.id)
        if current is None:
            return True
        if handler is None:
            message = f"Unsupported job kind: {current.kind}"
            fail_job(session, current, message)
            append_event(
                session,
                kind="JOB_FAILED",
                aggregate_type="job",
                aggregate_id=current.id,
                payload={"error_code": "JOB_KIND_UNSUPPORTED", "message": message},
            )
            return True
        try:
            handler(session, current)
            complete_job(session, current)
            append_event(
                session,
                kind="JOB_SUCCEEDED",
                aggregate_type="job",
                aggregate_id=current.id,
                payload={"kind": current.kind},
            )
        except Exception as exc:  # noqa: BLE001 - a job failure must reach durable state
            fail_job(session, current, str(exc))
            append_event(
                session,
                kind="JOB_FAILED",
                aggregate_type="job",
                aggregate_id=current.id,
                payload={"error_code": type(exc).__name__},
            )
            LOGGER.exception("job failed", extra={"job_id": str(current.id)})
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QuantFoundry finite worker")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--once", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging()
    settings = Settings.from_env()
    settings.ensure_worker_directories()
    engine = create_database_engine(settings)
    if args.check:
        ping_database(engine)
        return 0

    owner = f"{socket.gethostname()}:{os.getpid()}"
    if args.once:
        run_once(settings, owner=owner)
        return 0

    stop = StopFlag()
    signal.signal(signal.SIGTERM, stop.request)
    signal.signal(signal.SIGINT, stop.request)
    LOGGER.info("finite worker started")
    while not stop.requested:
        worked = run_once(settings, owner=owner)
        if not worked:
            time.sleep(settings.job_poll_seconds)
    LOGGER.info("finite worker stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
