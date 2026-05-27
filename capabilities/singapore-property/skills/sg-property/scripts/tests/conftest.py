"""Shared fixtures for calc_*.py script tests."""
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def run_script():
    """Invoke a script with stdin/argv. Returns (returncode, stdout, stderr)."""

    def _run(script_name, *args, stdin=""):
        script = SCRIPT_DIR / script_name
        result = subprocess.run(
            [sys.executable, str(script), *args],
            input=stdin,
            capture_output=True,
            text=True,
        )
        return result.returncode, result.stdout, result.stderr

    return _run
