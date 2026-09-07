from __future__ import annotations

import hashlib
import importlib.resources
import json
from pathlib import Path

from scripts.run_rwkv_e2e_benchmark import load_suite


def test_real_project_development_suite_has_twelve_private_behavior_contracts() -> None:
    tasks, cases = load_suite("realprojectdevv1")
    assert {task["task_id"] for task in tasks} == {
        f"RP-{family}-{number:02d}"
        for family in ("CLI", "DATA", "API", "MAINT", "WEB", "FULL")
        for number in (1, 2)
    }
    for task in tasks:
        checks = cases[task["task_id"]]["checks"]
        assert len(checks) == 1
        check = checks[0]
        assert check["kind"] == "project_behavior"
        assert hashlib.sha256(check["program"].encode()).hexdigest() == check["program_sha256"]
        assert check["browser"] == task["task_id"].startswith(("RP-WEB-", "RP-FULL-"))
        assert all("private_verify" not in item["path"] and not item["path"].startswith("reference/")
                   for item in task["workspace_files"])
        assert cases[task["task_id"]]["runner_control"]["network_policy"] == "offline"


def test_project_suite_compiled_resources_match_frozen_authored_contracts() -> None:
    dataset = Path(__file__).resolve().parents[1] / "data/datasets/rwkv_lh_real_project_dev_v1"
    package = importlib.resources.files("benchmarks.rwkv_e2e.rwkv_real_project_dev_v1")
    manifest = json.loads((dataset / "MANIFEST.json").read_text())
    for record in manifest["compiled_resources"]:
        assert hashlib.sha256(package.joinpath(record["path"]).read_bytes()).hexdigest() == record["sha256"]
    tasks, cases = load_suite("realprojectdevv1")
    authored = {json.loads(path.read_text())["task_id"]: path for path in dataset.glob("*/RP-*/task.json")}
    for task in tasks:
        source = authored[task["task_id"]]
        assert task == json.loads(source.read_text())
        assert cases[task["task_id"]]["checks"][0]["program"] == source.with_name("private_verify.py").read_text()
