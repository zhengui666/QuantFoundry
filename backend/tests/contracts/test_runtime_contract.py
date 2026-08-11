import subprocess
import sys
from pathlib import Path


def test_runtime_contract_diff():
    result = subprocess.run(
        [sys.executable, "scripts/runtime_contract_diff.py"],
        cwd=Path(__file__).parents[2],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
