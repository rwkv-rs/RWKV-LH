"""Regression cases for process isolation and persisted worker ownership."""

from pathlib import Path
import fcntl
import subprocess
import sys
import tomllib

import pytest

from rwkv_lh.harness import ActionHarness
from rwkv_lh.schema import TaskAction
from rwkv_lh.web_ui import ManualRunManager, update_metadata
from test_retrieval_harness import _goal
from test_web_ui import create_repository_run


def test_requested_command_sandbox_never_falls_back_to_host(tmp_path, monkeypatch):
    goal = _goal(tmp_path)
    harness = ActionHarness(sandbox_commands=True)
    harness._bubblewrap = None
    calls = []
    monkeypatch.setattr("rwkv_lh.harness.subprocess.run", lambda *args, **kwargs: calls.append(args))
    result = harness.execute(TaskAction("run_command", {"argv": [sys.executable, "-c", "print('safe')"]}), goal)
    assert not calls
    assert not result.success and "sandbox" in result.error["message"]


def test_command_sandbox_does_not_share_host_network(tmp_path):
    goal = _goal(tmp_path)
    harness = ActionHarness(sandbox_commands=True)
    harness._bubblewrap = "/usr/bin/bwrap"
    command, _ = harness._bubblewrap_command(goal, Path(goal.workspace_root), ["/usr/bin/true"])
    assert "--unshare-all" in command
    assert "--share-net" not in command


def test_check_command_writes_are_never_retained_in_the_workspace(tmp_path):
    goal = _goal(tmp_path)
    harness = ActionHarness(sandbox_commands=False)
    marker = Path(goal.workspace_root) / "outside.txt"
    result = harness.execute(TaskAction("check_command", {
        "argv": [sys.executable, "-c",
                 "from pathlib import Path; Path('outside.txt').write_text('leak'); print('wrote')"],
    }), goal)
    assert result.success and result.action_type == "check_command"
    assert "wrote" in result.output  # the command itself ran and could write...
    assert not marker.exists()  # ...but nothing it wrote reaches the workspace
    assert result.metadata["workspace_ephemeral"] is True
    assert result.metadata["writes_discarded"] is True


def test_check_command_ephemeral_sandbox_uses_overlay_when_supported(tmp_path):
    goal = _goal(tmp_path)
    harness = ActionHarness(sandbox_commands=True)
    harness._bubblewrap = "/usr/bin/bwrap"
    harness._overlay_support = True
    command, _ = harness._bubblewrap_command(
        goal, Path(goal.workspace_root), ["/usr/bin/true"], ephemeral_overlay=True)
    assert "--tmp-overlay" in command and "--overlay-src" in command
    assert "--bind" not in command[command.index("--tmpfs"):]


def test_command_timeout_preserves_partial_output(tmp_path):
    goal = _goal(tmp_path)
    harness = ActionHarness(sandbox_commands=False)
    result = harness.execute(TaskAction("run_command", {
        "argv": [sys.executable, "-u", "-c",
                 "import time; print('PARTIAL_DIAGNOSTIC_READY', flush=True); time.sleep(30)"],
        "timeout": 2.0,
    }), goal)
    assert not result.success
    assert result.exit_code is None
    assert "PARTIAL_DIAGNOSTIC_READY" in result.output
    assert result.metadata["timed_out"] is True
    assert result.error["type"] == "TimeoutExpired"
    assert result.outcome_type == "timeout"


def test_restarted_web_manager_does_not_spawn_over_persisted_live_worker(tmp_path, monkeypatch):
    repository, metadata = create_repository_run(tmp_path)
    run_id = metadata["run_id"]
    update_metadata(repository.run_root(run_id), active=True, pid=8123)
    manager = ManualRunManager(repository)
    monkeypatch.setattr(manager, "_managed_pid_alive", lambda run, pid: run == run_id and pid == 8123)
    calls = []
    monkeypatch.setattr("rwkv_lh.web_ui.subprocess.Popen", lambda *args, **kwargs: calls.append(args))
    with pytest.raises(RuntimeError, match="already active"):
        manager.launch(run_id, resume=True)
    assert not calls
    assert repository.metadata(run_id)["pid"] == 8123


@pytest.mark.parametrize("publication_fails", [False, True])
def test_child_holds_worker_claim_until_exit_even_without_published_pid(tmp_path, monkeypatch, publication_fails):
    repository, metadata = create_repository_run(tmp_path)
    run_id = metadata["run_id"]
    real_popen = subprocess.Popen
    children = []

    def spawn_waiting_child(command, **kwargs):
        child = real_popen(
            [sys.executable, "-c", "import sys; sys.stdin.buffer.read(1)"],
            stdin=subprocess.PIPE, **kwargs,
        )
        children.append(child)
        return child

    def publish(run_root, **values):
        if publication_fails and values.get("pid") is not None:
            raise RuntimeError("simulated PID publication failure")
        return update_metadata(run_root, **values)

    monkeypatch.setattr("rwkv_lh.web_ui.subprocess.Popen", spawn_waiting_child)
    monkeypatch.setattr("rwkv_lh.web_ui.update_metadata", publish)
    # Exercise the inherited OS claim independently of PID discovery.
    monkeypatch.setattr(ManualRunManager, "_managed_pid_alive", lambda *args: False)
    try:
        manager = ManualRunManager(repository)
        if publication_fails:
            with pytest.raises(RuntimeError, match="publication failure"):
                manager.launch(run_id)
            assert repository.metadata(run_id)["pid"] is None
        else:
            manager.launch(run_id)
        with pytest.raises(RuntimeError, match="already active"):
            ManualRunManager(repository).launch(run_id, resume=True)
        assert len(children) == 1
    finally:
        for child in children:
            child.communicate(input=b"x", timeout=5)
    with (repository.run_root(run_id) / "worker.lock").open("a+b") as claim:
        fcntl.flock(claim.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


@pytest.mark.parametrize("package", ["rwkv_agent_v1", "rwkv_agent_capability_ladder_v1"])
def test_development_benchmarks_keep_runtime_data_in_package(package):
    # Inspect only these two public package paths. Do not build a wheel or scan
    # other benchmark packages, which include owner-protected holdout material.
    root = Path(__file__).resolve().parents[1]
    config = tomllib.loads((root / "pyproject.toml").read_text())
    name = f"benchmarks.rwkv_e2e.{package}"
    package_root = root / "benchmarks" / "rwkv_e2e" / package
    files = {path.name for pattern in config["tool"]["setuptools"]["package-data"].get(name, [])
             for path in package_root.glob(pattern) if path.is_file()}
    assert {"tasks.json", "acceptance.json"} <= files
