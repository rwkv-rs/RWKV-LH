import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from rwkv_lh.benchmark_verifier import check_spec, run_isolated_verifier
from rwkv_lh.store import LongHorizonStore
from scripts.run_rwkv_e2e_benchmark import (
    FaultInjectingHarness,
    FORBIDDEN_VISIBLE_KEYS,
    VISIBLE_TASK_KEYS,
    _check,
    load_suite,
    materialize_workspace,
)


def test_rwkv_e2e_catalog_has_30_balanced_model_visible_tasks():
    tasks, acceptance = load_suite()
    assert len(tasks) == 30
    assert len(acceptance) == 30
    assert {task["level"] for task in tasks} == {"basic", "medium", "hard"}
    assert {
        level: sum(task["level"] == level for task in tasks)
        for level in ("basic", "medium", "hard")
    } == {"basic": 10, "medium": 10, "hard": 10}
    for task in tasks:
        assert set(task) <= VISIBLE_TASK_KEYS
        assert not (set(task) & FORBIDDEN_VISIBLE_KEYS)


def test_rwkv_e2e_workspace_never_contains_hidden_acceptance():
    tasks, _ = load_suite()
    task = next(item for item in tasks if item["task_id"] == "E2E-B02")
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory) / "workspace"
        materialize_workspace(task, workspace)
        assert (workspace / "input.txt").read_text(encoding="utf-8") == "project=Orion\ncount=7\n"
        assert not (workspace / "acceptance.json").exists()
        assert not any("acceptance" in path.name for path in workspace.rglob("*"))


def test_external_acceptance_is_independent_of_agent_completion_state():
    tasks, acceptance = load_suite()
    task = next(item for item in tasks if item["task_id"] == "E2E-B02")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = root / "workspace"
        materialize_workspace(task, workspace)
        (workspace / "report.json").write_text(
            json.dumps({"project": "Orion", "doubled_count": 14}) + "\n",
            encoding="utf-8",
        )
        store = LongHorizonStore(root / "state")
        results = [
            _check(item, workspace, store, "NOT-A-RUN", {})
            for item in acceptance["E2E-B02"]["checks"]
        ]
        assert all(item.passed for item in results)


def test_long_horizon_catalog_has_12_hidden_acceptance_cases():
    tasks, acceptance = load_suite("lh12")
    assert len(tasks) == 12
    assert len(acceptance) == 12
    assert {task["task_id"] for task in tasks} == {
        f"E2E-LH{index:02d}" for index in range(1, 13)
    }
    assert all(task["level"] == "long_horizon" for task in tasks)
    for task in tasks:
        assert set(task) <= VISIBLE_TASK_KEYS
        assert not (set(task) & FORBIDDEN_VISIBLE_KEYS)


def test_long_horizon_generators_materialize_dynamic_pressure_fixtures():
    tasks, _ = load_suite("lh12")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        manifest_task = next(item for item in tasks if item["task_id"] == "E2E-LH03")
        manifest_workspace = root / "manifest"
        materialize_workspace(manifest_task, manifest_workspace)
        assert len(list((manifest_workspace / "catalog").rglob("manifest.json"))) == 3
        assert (manifest_workspace / "catalog/root_manifest.json").is_file()

        shard_task = next(item for item in tasks if item["task_id"] == "E2E-LH05")
        shard_workspace = root / "shards"
        materialize_workspace(shard_task, shard_workspace)
        assert len(list((shard_workspace / "shards").glob("*.json"))) == 18
        assert len(list((shard_workspace / "fallback").glob("*.json"))) == 4

        memory_task = next(item for item in tasks if item["task_id"] == "E2E-LH11")
        memory_workspace = root / "memory"
        materialize_workspace(memory_task, memory_workspace)
        assert len(list((memory_workspace / "artifacts").glob("*.txt"))) == 40


def test_all_seeded_python_files_compile():
    tasks, _ = load_suite("lh12")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for task in tasks:
            workspace = root / task["task_id"]
            materialize_workspace(task, workspace)
            for path in workspace.rglob("*.py"):
                compile(path.read_text(encoding="utf-8"), str(path), "exec")


def test_dynamic_discovery_manifest_exposes_only_root_entrypoint():
    tasks, _ = load_suite("lh12")
    task = next(item for item in tasks if item["task_id"] == "E2E-LH03")
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory) / "workspace"
        materialize_workspace(task, workspace)
        goal = type("Goal", (), {"workspace_root": str(workspace)})()
        harness = FaultInjectingHarness(
            manifest_entrypoints=("catalog/root_manifest.json",)
        )
        manifest = harness.workspace_manifest(goal)
        assert manifest["discovery_policy"] == "entrypoints_only"
        assert [entry["path"] for entry in manifest["entries"]] == [
            "catalog/root_manifest.json"
        ]


@pytest.mark.skipif(
    os.name != "posix" or shutil.which("bwrap") is None,
    reason="bubblewrap verifier requires Linux and bwrap",
)
def test_benchmark_agent_command_sandbox_does_not_share_network():
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory) / "workspace"
        workspace.mkdir()
        goal = type("Goal", (), {"workspace_root": str(workspace)})()
        harness = FaultInjectingHarness()
        command, _ = harness._bubblewrap_command(
            goal,
            workspace,
            ["python", "probe.py"],
        )
        assert "--unshare-all" in command
        assert "--share-net" not in command


def test_cascading_command_stage_checker_requires_ordered_failures_then_success():
    events = []
    for index, (exit_code, output) in enumerate(
        [(1, "layer A"), (1, "layer B"), (1, "layer C"), (0, "ok")],
        start=1,
    ):
        attempt_id = f"A{index}"
        events.extend(
            [
                {
                    "type": "attempt_started",
                    "data": {
                        "attempt_id": attempt_id,
                        "arguments": {"argv": ["python", "verify.py"]},
                    },
                },
                {
                    "type": "action_returned",
                    "data": {
                        "attempt_id": attempt_id,
                        "exit_code": exit_code,
                        "output": output,
                    },
                },
            ]
        )
    result = check_spec(
        {
            "kind": "command_exit_stages",
            "argv": ["python", "verify.py"],
            "stages": ["layer A", "layer B", "layer C"],
        },
        Path("."),
        events,
        {},
    )
    assert result.passed


@pytest.mark.skipif(
    os.name != "posix" or shutil.which("bwrap") is None,
    reason="bubblewrap verifier requires Linux and bwrap",
)
def test_isolated_verifier_hides_catalog_logs_tests_and_parent_memory():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = root / "workspace"
        workspace.mkdir()
        (workspace / "probe.py").write_text(
            """import os
from pathlib import Path

assert not Path('/tests').exists()
assert not Path('/logs/verifier').exists()
assert not Path('/opt/rwkv-lh-src').exists()
try:
    os.open(f'/proc/{os.getppid()}/mem', os.O_RDONLY)
except OSError:
    pass
else:
    raise AssertionError('verifier parent memory is readable')
try:
    Path('leak.txt').write_text('leaked')
except OSError:
    pass
else:
    raise AssertionError('verifier workspace is writable')
""",
            encoding="utf-8",
        )
        result = run_isolated_verifier(
            {"checks": [{"kind": "command_exit", "argv": ["python", "probe.py"]}]},
            workspace,
            [],
            {},
            private_root=root / "private",
        )
        assert result.passed
        assert result.metadata["acceptance_transport"] == "stdin"
        assert result.metadata["workspace_mount"] == "read_only_snapshot"
        assert result.metadata["network"] == "unshared"
        assert not (workspace / "leak.txt").exists()


@pytest.mark.skipif(
    os.name != "posix" or shutil.which("bwrap") is None,
    reason="bubblewrap verifier requires Linux and bwrap",
)
def test_isolated_verifier_rejects_workspace_symlinks_fail_closed():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = root / "workspace"
        workspace.mkdir()
        outside = root / "hidden_acceptance.json"
        outside.write_text('{"secret": true}', encoding="utf-8")
        (workspace / "escape.json").symlink_to(outside)
        with pytest.raises(ValueError, match="rejects non-regular file"):
            run_isolated_verifier(
                {"checks": [{"kind": "path_absent", "path": "nothing"}]},
                workspace,
                [],
                {},
                private_root=root / "private",
            )
