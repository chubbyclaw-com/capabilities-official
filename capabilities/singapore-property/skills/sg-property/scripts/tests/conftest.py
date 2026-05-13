"""Shared fixtures: every test gets a clean SGPROP_HOME pointing at a tmp dir."""
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).resolve().parent.parent


@pytest.fixture
def sgprop_home(tmp_path, monkeypatch):
    home = tmp_path / "sgprop"
    monkeypatch.setenv("SGPROP_HOME", str(home))
    return home


@pytest.fixture
def run_script(sgprop_home):
    """Invoke a script with stdin/argv. Returns (returncode, stdout, stderr)."""

    def _run(script_name, *args, stdin=""):
        script = SCRIPT_DIR / script_name
        result = subprocess.run(
            [sys.executable, str(script), *args],
            input=stdin,
            capture_output=True,
            text=True,
            env={**os.environ, "SGPROP_HOME": str(sgprop_home)},
        )
        return result.returncode, result.stdout, result.stderr

    return _run
