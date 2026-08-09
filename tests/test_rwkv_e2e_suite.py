import json
import tempfile
from pathlib import Path

from rwkv_lh.store import LongHorizonStore
from scripts.run_rwkv_e2e_benchmark import (
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
