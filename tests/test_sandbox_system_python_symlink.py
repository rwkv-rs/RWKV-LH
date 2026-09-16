from pathlib import Path
import shutil
import sys

from rwkv_lh.harness import ActionHarness
from rwkv_lh.schema import GoalState


def test_system_python_symlink_in_venv_is_rebased_into_sandbox(tmp_path, monkeypatch):
    system_python = Path('/usr/bin/python3').resolve(strict=True)
    venv = tmp_path / 'venv'
    (venv / 'bin').mkdir(parents=True)
    executable = venv / 'bin/python'
    executable.symlink_to(system_python)
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    monkeypatch.setattr(sys, 'prefix', str(venv))
    monkeypatch.setattr(sys, 'executable', str(executable))
    goal = GoalState.create(request='sandbox regression', workspace_root=str(workspace), constraints=[])
    command, _ = ActionHarness()._bubblewrap_command(goal, workspace, [str(executable), '-B', 'solution.py'])
    assert command[-3] == '/opt/rwkv-lh-venv/bin/python'
    assert ['--ro-bind', str(venv), '/opt/rwkv-lh-venv'] == command[command.index(str(venv))-1:command.index(str(venv))+2]
