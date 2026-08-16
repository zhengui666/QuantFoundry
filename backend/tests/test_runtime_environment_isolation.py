"""Regression coverage for test-owned runtime storage isolation."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

PROBE_MODE = os.getenv("QF_RUNTIME_ISOLATION_PROBE_MODE")


def test_runtime_environment_subprocess_probe() -> None:
    runtime_root = Path(os.environ["QF_TEST_RUNTIME_ROOT"])
    report_path = Path(os.environ["QF_RUNTIME_ISOLATION_REPORT"])
    ambient_root = Path(os.environ["QF_RUNTIME_ISOLATION_AMBIENT_ROOT"])
    runtime_directories = {
        Path(os.environ["QF_ARTIFACT_DIR"]),
        Path(os.environ["QF_DATASET_DIR"]),
        Path(os.environ["QF_COST_MODEL_DIR"]),
        Path(os.environ["QF_POLICY_DIR"]),
    }

    assert len(runtime_directories) == 4
    assert all(path.parent == runtime_root for path in runtime_directories)
    assert all(path.is_dir() for path in runtime_directories)
    assert all(not path.is_relative_to(ambient_root) for path in runtime_directories)

    cost_root = Path(os.environ["QF_COST_MODEL_DIR"])
    policy_root = Path(os.environ["QF_POLICY_DIR"])
    cost_payloads = [json.loads(path.read_text()) for path in cost_root.glob("*.json")]
    policy_payloads = [
        json.loads(path.read_text()) for path in policy_root.glob("*.json")
    ]
    assert {payload["cost_model_id"] for payload in cost_payloads} == {
        "COST-00000000-0000-4000-8000-000000000003",
        "COST-00000000-0000-4000-8000-000000000103",
    }
    assert {payload["policy_id"] for payload in policy_payloads} == {
        "RP-00000000-0000-4000-8000-000000000004",
        "RP-00000000-0000-4000-8000-000000000104",
    }
    report_path.write_text(str(runtime_root), encoding="utf-8")

    if PROBE_MODE == "failure":
        pytest.fail("intentional runtime cleanup probe failure")
    if PROBE_MODE == "interrupt":
        while True:
            time.sleep(0.05)


test_runtime_environment_subprocess_probe.__test__ = PROBE_MODE is not None


@pytest.mark.parametrize(
    ("mode", "expected_return_code"),
    [("normal", 0), ("failure", 1), ("interrupt", 2)],
)
def test_ambient_runtime_directories_are_ignored_and_cleaned(
    tmp_path: Path,
    mode: str,
    expected_return_code: int,
) -> None:
    ambient_root = tmp_path / "ambient"
    runtime_parent = tmp_path / "runtime-parent"
    runtime_parent.mkdir()
    environment = os.environ.copy()
    ambient_sentinels: dict[Path, set[str]] = {}
    for environment_name, directory_name in (
        ("QF_ARTIFACT_DIR", "artifacts"),
        ("QF_DATASET_DIR", "datasets"),
        ("QF_COST_MODEL_DIR", "cost-models"),
        ("QF_POLICY_DIR", "policies"),
    ):
        directory = ambient_root / ("shared" if mode == "normal" else directory_name)
        directory.mkdir(parents=True, exist_ok=True)
        sentinel_name = f"ambient-{environment_name.lower()}.txt"
        (directory / sentinel_name).write_text(
            f"do-not-touch:{environment_name}", encoding="utf-8"
        )
        ambient_sentinels.setdefault(directory, set()).add(sentinel_name)
        environment[environment_name] = str(directory)

    report_path = tmp_path / f"runtime-{mode}.txt"
    environment.update(
        {
            "PYTEST_ADDOPTS": "",
            "QF_ALLOW_TEST_SCHEMA_BOOTSTRAP": "1",
                "QF_DATABASE_URL": f"sqlite:///{tmp_path / f'{mode}.db'}",
                "QF_ALLOW_EXTERNAL_TEST_DATABASE": "1",
                "QF_RUNTIME_ISOLATION_AMBIENT_ROOT": str(ambient_root),
            "QF_RUNTIME_ISOLATION_PROBE_MODE": mode,
            "QF_RUNTIME_ISOLATION_REPORT": str(report_path),
            "QF_TEST_RUNTIME_PARENT": str(runtime_parent),
        }
    )
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        str(Path(__file__).resolve()),
        "-k",
        "runtime_environment_subprocess_probe",
    ]

    process: subprocess.Popen[str] | None = None
    try:
        if mode == "interrupt":
            process = subprocess.Popen(
                command,
                cwd=Path(__file__).resolve().parents[1],
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            deadline = time.monotonic() + 60
            while not report_path.exists() and process.poll() is None:
                if time.monotonic() >= deadline:
                    pytest.fail("runtime interrupt probe did not start")
                time.sleep(0.05)
            process.send_signal(signal.SIGINT)
            try:
                output, _ = process.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                pytest.fail("runtime interrupt probe did not stop")
            return_code = process.returncode
        else:
            completed = subprocess.run(
                command,
                cwd=Path(__file__).resolve().parents[1],
                env=environment,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            output = completed.stdout + completed.stderr
            return_code = completed.returncode

        assert return_code == expected_return_code, output
        assert report_path.is_file(), output
        runtime_root = Path(report_path.read_text(encoding="utf-8"))
        assert not runtime_root.exists()
        assert list(runtime_parent.iterdir()) == []
        for directory, sentinel_names in ambient_sentinels.items():
            assert {path.name for path in directory.iterdir()} == sentinel_names
    finally:
        if process is not None and process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
        shutil.rmtree(runtime_parent, ignore_errors=True)


test_ambient_runtime_directories_are_ignored_and_cleaned.__test__ = PROBE_MODE is None
