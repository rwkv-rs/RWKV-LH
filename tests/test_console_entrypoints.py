"""Installed commands must resolve to live entrypoints before accessing a model."""

import importlib
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest


ROOT = Path(__file__).resolve().parents[1]
ENTRIES = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["scripts"]


@pytest.mark.parametrize("command,entry", ENTRIES.items())
def test_declared_console_entrypoint_help(command, entry):
    module_name, function_name = entry.split(":")
    module = importlib.import_module(module_name)
    assert callable(getattr(module, function_name))
    # --help must exit before loading service credentials or making model calls.
    result = subprocess.run(
        [sys.executable, "-c",
         f"from {module_name} import {function_name}; "
         f"raise SystemExit({function_name}())", "--help"],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, (command, result.stderr)
    assert "usage:" in result.stdout.lower()


def test_default_console_command_accepts_coding_job_arguments():
    module_name, function_name = ENTRIES["rwkv-lh"].split(":")
    result = subprocess.run(
        [sys.executable, "-c",
         f"from {module_name} import {function_name}; "
         f"raise SystemExit({function_name}())", "--help"],
        cwd=ROOT, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stderr
    for option in ("--request", "--source-workspace", "--output-dir",
                   "--max-calls", "--max-seconds"):
        assert option in result.stdout
