"""Test-only child used to verify pg18_ci process and cleanup semantics."""

from __future__ import annotations

import json
import os
import runpy
import signal
import subprocess
import sys
import time
from pathlib import Path


def _write_ready(mode: str, child_pid: int | None) -> None:
    ready_path = Path(os.environ["QF_PG18_CI_PROBE_READY"])
    payload = {
        "mode": mode,
        "database_name": os.environ["QF_PG18_CI_DATABASE_NAME"],
        "runtime_root": os.environ["QF_PG18_CI_RUNTIME_ROOT"],
        "pytest_runtime_root": os.environ["QF_TEST_RUNTIME_ROOT"],
        "pid": os.getpid(),
        "process_group_id": os.getpgrp(),
        "child_pid": child_pid,
    }
    temporary = ready_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    os.replace(temporary, ready_path)


def _exit_without_atexit(signum: int, _frame: object) -> None:
    os._exit(128 + signum)


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"normal", "rc4", "wait"}:
        raise SystemExit("usage: pg18_ci_process_probe.py normal|rc4|wait")
    mode = sys.argv[1]
    # Execute the real pytest environment bootstrap.  HUP/TERM intentionally use
    # os._exit below, proving the parent harness removes roots when Python cannot.
    runpy.run_path(str(Path("tests/conftest.py").resolve()))
    if mode == "normal":
        _write_ready(mode, None)
        return 0
    if mode == "rc4":
        _write_ready(mode, None)
        return 4

    resist_signals = os.getenv("QF_PG18_CI_PROBE_RESIST_SIGNALS") == "1"
    for forwarded_signal in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        signal.signal(
            forwarded_signal,
            signal.SIG_IGN if resist_signals else _exit_without_atexit,
        )
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(3600)"],
        start_new_session=False,
    )
    _write_ready(mode, child.pid)
    while True:
        time.sleep(0.1)


if __name__ == "__main__":
    raise SystemExit(main())
