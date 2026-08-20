"""Live supervisor process skeleton.

The supervisor is deliberately fail-closed. Until the P4 runner is implemented it
observes the database only and never marks a Deployment as trading.
"""

from __future__ import annotations

import argparse
import logging
import signal
import time
from collections.abc import Sequence

from sqlalchemy import func, select

from quantfoundry.db.models import Deployment
from quantfoundry.db.session import (
    create_database_engine,
    create_session_factory,
    ping_database,
)
from quantfoundry.logging_utils import configure_logging
from quantfoundry.settings import Settings

LOGGER = logging.getLogger("quantfoundry.live_supervisor")


class StopFlag:
    requested = False

    def request(self, *_: object) -> None:
        self.requested = True


def observe_once(settings: Settings) -> int:
    engine = create_database_engine(settings)
    factory = create_session_factory(engine)
    with factory() as session:
        count = session.scalar(
            select(func.count()).select_from(Deployment).where(
                Deployment.desired_state == "RUNNING"
            )
        )
    return int(count or 0)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="QuantFoundry live supervisor")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--once", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging()
    settings = Settings.from_env()
    engine = create_database_engine(settings)
    if args.check:
        ping_database(engine)
        return 0
    if args.once:
        observe_once(settings)
        return 0

    stop = StopFlag()
    signal.signal(signal.SIGTERM, stop.request)
    signal.signal(signal.SIGINT, stop.request)
    LOGGER.info("live supervisor started in observation-only P0 mode")
    while not stop.requested:
        pending = observe_once(settings)
        if pending:
            LOGGER.warning(
                "deployments request RUNNING but the P4 live runner is not implemented",
                extra={"error_code": "LIVE_RUNNER_NOT_IMPLEMENTED"},
            )
        time.sleep(settings.supervisor_poll_seconds)
    LOGGER.info("live supervisor stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
