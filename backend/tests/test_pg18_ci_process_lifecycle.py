"""PostgreSQL 18 lifecycle tests for the real release harness process tree."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest


def _postgres_server_version() -> int:
    completed = subprocess.run(
        ["psql", "-Atqc", "SHOW server_version_num", "postgres"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0:
        return 0
    try:
        return int(completed.stdout.strip())
    except ValueError:
        return 0


PG18_AVAILABLE = _postgres_server_version() >= 180000


def test_process_group_launcher_restores_ignored_async_signals(tmp_path: Path) -> None:
    ready_path = tmp_path / "launcher-ready.json"
    launcher = Path(__file__).resolve().parents[1] / "scripts/process_group_launcher.py"
    ignore_then_exec = """
import os, signal, sys
for item in (signal.SIGHUP, signal.SIGINT, signal.SIGQUIT, signal.SIGTERM):
    signal.signal(item, signal.SIG_IGN)
os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
"""
    probe = """
import json, os, signal, time
payload = {
    'pid': os.getpid(),
    'pgid': os.getpgrp(),
    'hup_default': signal.getsignal(signal.SIGHUP) == signal.SIG_DFL,
    'int_not_ignored': signal.getsignal(signal.SIGINT) != signal.SIG_IGN,
    'quit_default': signal.getsignal(signal.SIGQUIT) == signal.SIG_DFL,
    'term_default': signal.getsignal(signal.SIGTERM) == signal.SIG_DFL,
}
open(os.environ['QF_LAUNCHER_READY'], 'w', encoding='utf-8').write(json.dumps(payload))
while True:
    time.sleep(0.1)
"""
    environment = os.environ.copy()
    environment["QF_LAUNCHER_READY"] = str(ready_path)
    process = subprocess.Popen(
        [
            sys.executable,
            "-c",
            ignore_then_exec,
            str(launcher),
            sys.executable,
            "-c",
            probe,
        ],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        deadline = time.monotonic() + 20
        while not ready_path.exists() and process.poll() is None:
            if time.monotonic() >= deadline:
                pytest.fail("managed launcher probe did not become ready")
            time.sleep(0.05)
        assert ready_path.is_file()
        ready = json.loads(ready_path.read_text(encoding="utf-8"))
        assert ready["pid"] != process.pid
        assert ready["pgid"] == process.pid
        assert ready["hup_default"] is True
        assert ready["int_not_ignored"] is True
        assert ready["quit_default"] is True
        assert ready["term_default"] is True
        os.killpg(process.pid, signal.SIGINT)
        process.communicate(timeout=5)
        assert process.returncode in {-signal.SIGINT, 130}
    finally:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate(timeout=5)


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(str(path.relative_to(root)).encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _pid_exists(pid: int | None) -> bool:
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _database_exists(name: str) -> bool:
    completed = subprocess.run(
        [
            "psql",
            "-Atqc",
            f"SELECT count(*) FROM pg_database WHERE datname = '{name}'",
            "postgres",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return completed.returncode != 0 or completed.stdout.strip() != "0"


def _safety_cleanup(process: subprocess.Popen[str], ready: dict[str, Any]) -> None:
    process_group_id = ready.get("process_group_id")
    if isinstance(process_group_id, int):
        try:
            os.killpg(process_group_id, signal.SIGTERM)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.send_signal(signal.SIGTERM)
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            if isinstance(process_group_id, int):
                try:
                    os.killpg(process_group_id, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            process.kill()
            process.communicate(timeout=5)
    database_name = ready.get("database_name")
    if isinstance(database_name, str):
        subprocess.run(
            ["dropdb", "--if-exists", "--force", database_name],
            capture_output=True,
            timeout=10,
            check=False,
        )
    runtime_root = ready.get("runtime_root")
    if isinstance(runtime_root, str):
        shutil.rmtree(runtime_root, ignore_errors=True)


@pytest.mark.skipif(not PG18_AVAILABLE, reason="requires PostgreSQL 18 release gate")
@pytest.mark.parametrize(
    ("mode", "forwarded_signal", "expected_status"),
    [
        ("normal", None, 0),
        ("rc4", None, 4),
        ("wait", signal.SIGHUP, 129),
        ("wait", signal.SIGINT, 130),
        ("wait", signal.SIGTERM, 143),
    ],
)
def test_pg18_ci_cleans_process_group_database_and_runtime(
    tmp_path: Path,
    mode: str,
    forwarded_signal: signal.Signals | None,
    expected_status: int,
) -> None:
    ambient_root = tmp_path / "ambient"
    environment = os.environ.copy()
    for environment_name, directory_name in (
        ("QF_ARTIFACT_DIR", "artifacts"),
        ("QF_DATASET_DIR", "datasets"),
        ("QF_COST_MODEL_DIR", "cost-models"),
        ("QF_POLICY_DIR", "policies"),
    ):
        directory = ambient_root / directory_name
        directory.mkdir(parents=True)
        (directory / "sentinel.txt").write_text(
            f"ambient:{environment_name}", encoding="utf-8"
        )
        environment[environment_name] = str(directory)
    ambient_hash = _tree_hash(ambient_root)
    ready_path = tmp_path / "ready.json"
    environment.update(
        {
            "QF_ENVIRONMENT": "test",
            "QF_PG18_CI_CHILD_STOP_TIMEOUT_SECONDS": "5",
            "QF_PG18_CI_ENABLE_PROCESS_PROBE": "1",
            "QF_PG18_CI_PROBE_READY": str(ready_path),
        }
    )
    if forwarded_signal == signal.SIGTERM:
        environment["QF_PG18_CI_PROBE_RESIST_SIGNALS"] = "1"
    backend_root = Path(__file__).resolve().parents[1]
    process = subprocess.Popen(
        [str(backend_root / "scripts/pg18_ci.sh"), "--process-probe", mode],
        cwd=backend_root,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    ready: dict[str, Any] = {}
    try:
        deadline = time.monotonic() + 60
        while not ready_path.exists() and process.poll() is None:
            if time.monotonic() >= deadline:
                pytest.fail("pg18_ci process probe did not become ready")
            time.sleep(0.05)
        if ready_path.exists():
            ready = json.loads(ready_path.read_text(encoding="utf-8"))
        if forwarded_signal is not None:
            assert process.poll() is None, "signal probe exited before synchronization"
            process.send_signal(forwarded_signal)
        output, _ = process.communicate(timeout=30)

        assert process.returncode == expected_status, output
        assert ready, output
        assert not Path(str(ready["runtime_root"])).exists()
        assert not Path(str(ready["pytest_runtime_root"])).exists()
        assert not _database_exists(str(ready["database_name"]))
        deadline = time.monotonic() + 5
        probe_pids = [ready.get("pid"), ready.get("child_pid")]
        while (
            any(_pid_exists(pid) for pid in probe_pids) and time.monotonic() < deadline
        ):
            time.sleep(0.05)
        assert not any(_pid_exists(pid) for pid in probe_pids)
        assert _tree_hash(ambient_root) == ambient_hash
    except subprocess.TimeoutExpired as error:
        pytest.fail(f"pg18_ci process probe did not stop: {error}")
    finally:
        _safety_cleanup(process, ready)
