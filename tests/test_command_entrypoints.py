from pathlib import Path
import shutil
import sys

import pytest

from rwkv_lh.harness import ActionHarness
from rwkv_lh.schema import GoalState, TaskAction


def _goal(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return GoalState.create(request="Check the runtime tools.", constraints=(), workspace_root=workspace)


@pytest.mark.parametrize("sandboxed", [False, True])
@pytest.mark.parametrize("operation", ["check_command", "run_command"])
@pytest.mark.parametrize("executable", ["python3", sys.executable])
def test_project_python_executable_runs_code_and_imports_project_packages(tmp_path, sandboxed, operation, executable):
    harness = ActionHarness(sandbox_commands=sandboxed)
    result = harness.execute(TaskAction(operation, {
        "argv": [executable, "-c", "import requests; print('runtime-ready')"],
    }), _goal(tmp_path))
    assert result.success, result.output
    assert result.output.strip() == "runtime-ready"
    assert result.metadata["sandboxed"] is sandboxed


@pytest.mark.parametrize("sandboxed", [False, True])
@pytest.mark.parametrize("kind", ["native", "shell", "python_console", "python_env", "interpreter_alias"])
def test_project_entrypoint_preserves_its_actual_interpreter(tmp_path, monkeypatch, sandboxed, kind):
    runtime = Path(sys.executable).resolve(strict=True)
    prefix = tmp_path / "project-runtime"
    binary_dir = prefix / "bin"
    binary_dir.mkdir(parents=True)
    entrypoint = binary_dir / "opaque-entrypoint"
    arguments = []
    if kind == "native":
        shutil.copy2(shutil.which("printf"), entrypoint)
        arguments = ["entrypoint-ready\\n"]
    elif kind == "shell":
        entrypoint.write_text("#!/bin/sh\nprintf 'entrypoint-ready\\n'\n")
    elif kind == "python_console":
        entrypoint.write_text(f"#!{runtime} -I\nimport sys\nassert sys.flags.isolated == 1\nprint('entrypoint-ready')\n")
    elif kind == "python_env":
        entrypoint.write_text(f"#!/usr/bin/env python3\nimport sys\nassert sys.version_info[:2] == {sys.version_info[:2]!r}\nprint('entrypoint-ready')\n")
    else:
        entrypoint.symlink_to(runtime)
        arguments = ["-c", "print('entrypoint-ready')"]
    if not entrypoint.is_symlink():
        entrypoint.chmod(0o755)
    monkeypatch.setattr(sys, "prefix", str(prefix))
    monkeypatch.setenv("PATH", f"{binary_dir}:/usr/bin:/bin")
    result = ActionHarness(sandbox_commands=sandboxed).execute(TaskAction("check_command", {
        "argv": [entrypoint.name, *arguments],
    }), _goal(tmp_path))
    assert result.success, result.output
    assert result.output.strip() == "entrypoint-ready"
    assert result.metadata["sandboxed"] is sandboxed
