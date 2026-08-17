"""Launch one release-gate command in an isolated, signal-correct process group."""

from __future__ import annotations

import os
import signal
import sys


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: process_group_launcher.py COMMAND [ARG ...]")
    # POSIX shells start asynchronous commands with SIGINT/SIGQUIT ignored.
    # Those dispositions survive exec unless explicitly restored.
    managed_signals = (
        signal.SIGHUP,
        signal.SIGINT,
        signal.SIGQUIT,
        signal.SIGTERM,
    )
    os.setsid()
    for managed_signal in managed_signals:
        signal.signal(managed_signal, signal.SIG_DFL)
    ready_path = os.environ.get("QF_PROCESS_GROUP_READY")
    if ready_path:
        try:
            with open(ready_path, "x", encoding="utf-8"):
                pass
        except OSError:
            raise
    try:
        os.execvp(sys.argv[1], sys.argv[1:])
    except OSError:
        if ready_path:
            try:
                os.unlink(ready_path)
            except FileNotFoundError:
                pass
        raise


if __name__ == "__main__":
    main()
