from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.run_rwkv_e2e_benchmark import (
    FORBIDDEN_VISIBLE_KEYS,
    VISIBLE_TASK_KEYS,
    load_suite,
    materialize_workspace,
)


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "benchmarks/rwkv_e2e/rwkv_real_agent_holdout_v2"
DATASET = ROOT / "data/datasets/rwkv_lh_real_agent_holdout_v2"
EXPERIMENT = (
    ROOT
    / "data/acceptance/real_agent_holdout_v2"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def test_real_agent_holdout_v2_is_frozen_model_clean_and_not_training_data(
    tmp_path: Path,
) -> None:
    tasks, acceptance = load_suite("realagentholdoutv2")
    expected_ids = {
        "REAL-HOLDOUT-V2-DIAG-01",
        "REAL-HOLDOUT-V2-FIX-01",
        "REAL-HOLDOUT-V2-FIX-02",
        "REAL-HOLDOUT-V2-FEAT-01",
        "REAL-HOLDOUT-V2-MIGRATE-01",
        "REAL-HOLDOUT-V2-DATA-01",
        "REAL-HOLDOUT-V2-WEB-01",
        "REAL-HOLDOUT-V2-PERF-01",
        "REAL-HOLDOUT-V2-RESUME-01",
        "REAL-HOLDOUT-V2-NET-01",
        "REAL-HOLDOUT-V2-SAFE-01",
        "REAL-HOLDOUT-V2-AUTH-01",
    }
    assert len(tasks) == len(acceptance) == 12
    assert {task["task_id"] for task in tasks} == expected_ids
    assert all(set(task) <= VISIBLE_TASK_KEYS for task in tasks)
    assert all(not (set(task) & FORBIDDEN_VISIBLE_KEYS) for task in tasks)

    for index, task in enumerate(tasks):
        workspace = tmp_path / f"case-{index:02d}"
        materialize_workspace(task, workspace)
        assert not (workspace / "acceptance.json").exists()
        assert not any("acceptance" in path.name for path in workspace.rglob("*"))
        for path in workspace.rglob("*.py"):
            compile(path.read_text(encoding="utf-8"), str(path), "exec")


def test_real_agent_holdout_v2_manifest_binds_every_input_and_budget() -> None:
    package_manifest = json.loads((PACKAGE / "manifest.json").read_text())
    assert package_manifest == json.loads((DATASET / "manifest.json").read_text())
    assert package_manifest == json.loads(
        (EXPERIMENT / "FREEZE_MANIFEST.json").read_text()
    )
    tasks_payload = json.loads((PACKAGE / "tasks.json").read_text())
    acceptance_payload = json.loads((PACKAGE / "acceptance.json").read_text())
    assert package_manifest["state_tuning_eligible"] is False
    assert package_manifest["frozen_before_model_evaluation"] is True
    assert package_manifest["model_outputs_inspected"] is False
    assert package_manifest["task_count"] == 12
    assert package_manifest["source_count"] == 4
    assert package_manifest["tasks_sha256"] == _sha(PACKAGE / "tasks.json")
    assert package_manifest["acceptance_sha256"] == _sha(
        PACKAGE / "acceptance.json"
    )

    tasks = {task["task_id"]: task for task in tasks_payload["tasks"]}
    records = {item["task_id"]: item for item in package_manifest["task_records"]}
    assert set(tasks) == set(records) == set(acceptance_payload["cases"])
    for task_id, record in records.items():
        task = tasks[task_id]
        assert record["state_tuning_eligible"] is False
        assert record["budget"] == {
            "max_transitions": 96,
            "wall_clock_seconds": 900,
        }
        assert record["user_prompt_sha256"] == hashlib.sha256(
            task["user_request"].encode("utf-8")
        ).hexdigest()
        assert record["fixture_sha256"] == hashlib.sha256(
            _canonical(
                {
                    "workspace_files": task["workspace_files"],
                    "workspace_generators": task["workspace_generators"],
                }
            )
        ).hexdigest()
        assert record["hidden_acceptance_sha256"] == hashlib.sha256(
            _canonical(acceptance_payload["cases"][task_id])
        ).hexdigest()


def test_real_agent_holdout_v2_network_authority_is_case_local() -> None:
    tasks, acceptance = load_suite("realagentholdoutv2")
    levels = {task["task_id"]: task["level"] for task in tasks}
    for task_id, case in acceptance.items():
        expected = "auto_public" if levels[task_id] == "network" else "offline"
        assert case["runner_control"]["network_policy"] == expected
        grounding = [
            check
            for check in case["checks"]
            if check["kind"] == "network_evidence_grounding"
        ]
        assert bool(grounding) == (levels[task_id] == "network")


def test_real_agent_holdout_v2_similarity_audit_is_fixed_and_passes() -> None:
    audit = json.loads((EXPERIMENT / "SIMILARITY_AUDIT.json").read_text())
    assert audit["algorithm"] == "utf8-byte-5gram-cosine.v1"
    assert audit["threshold_exclusive"] == 0.75
    assert audit["maximum_similarity"] < audit["threshold_exclusive"]
    assert audit["passed"] is True
    assert audit["state_tuning_eligible"] is False
    assert audit["holdout_prompt_count"] == 12
    assert audit["holdout_tasks_sha256"] == _sha(PACKAGE / "tasks.json")
    removal = json.loads((ROOT / (
        "data/experiments/PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907/"
        "DELETION_MANIFEST.json"
    )).read_text(encoding="utf-8"))
    original_registry = next(record for record in removal["files"] if record["path"] == (
        "data/datasets/rwkv_lh_g1j_selector_intent_state_tuning_v2/source_registry.jsonl"
    ))
    assert audit["training_source_registry_sha256"] == original_registry["sha256"]


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is unavailable")
def test_real_agent_holdout_v2_seeded_javascript_parses(tmp_path: Path) -> None:
    tasks, _ = load_suite("realagentholdoutv2")
    for index, task in enumerate(tasks):
        workspace = tmp_path / f"js-{index:02d}"
        materialize_workspace(task, workspace)
        for path in workspace.rglob("*.js"):
            completed = subprocess.run(
                ["node", "--check", str(path)],
                text=True,
                capture_output=True,
                check=False,
            )
            assert completed.returncode == 0, completed.stdout + completed.stderr
