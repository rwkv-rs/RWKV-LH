"""Repository boundaries that prevent retired role data paths from returning."""

from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTECTED_INPUT_FIELDS = frozenset(("current_progress", "execution_state", "gap_catalog"))


def _protocol_literals(path: Path) -> list[int]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys = {
                key.value for key in node.keys
                if isinstance(key, ast.Constant) and isinstance(key.value, str)
            }
            if {"assigned_action_count", "successful_action_count", "failed_action_count"} <= keys:
                violations.add(node.lineno)
            for key, value in zip(node.keys, node.values):
                if isinstance(key, ast.Constant) and key.value in PROTECTED_INPUT_FIELDS and isinstance(value, ast.Dict):
                    violations.add(value.lineno)
        elif isinstance(node, ast.keyword):
            if node.arg in PROTECTED_INPUT_FIELDS and isinstance(node.value, ast.Dict):
                violations.add(node.value.lineno)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if isinstance(node.value, ast.Dict) and any(
                isinstance(target, ast.Name) and target.id in PROTECTED_INPUT_FIELDS
                for target in targets
            ):
                violations.add(node.lineno)
    return sorted(violations)


def test_scripts_tests_and_temp_use_shared_role_input_builders() -> None:
    paths = [*ROOT.joinpath("scripts").rglob("*.py"), *ROOT.joinpath("tests").rglob("*.py")]
    paths.extend(ROOT.joinpath("temp").glob("*.py"))
    violations = [
        f"{path.relative_to(ROOT)}:{line}"
        for path in sorted(paths)
        for line in _protocol_literals(path)
    ]
    assert not violations, "Role protocol dictionaries must come from shared builders: " + ", ".join(violations)


def test_active_datasets_do_not_expose_retired_synthetic_role_data() -> None:
    manifest = json.loads(ROOT.joinpath(
        "data/experiments/PROTOCOL_DATA_CHAIN_UNIFICATION_R1_20260907/DELETION_MANIFEST.json"
    ).read_text(encoding="utf-8"))
    retired = [path for path in manifest["deleted_roots"]
               if path.startswith("data/datasets/") and ROOT.joinpath(path).exists()]
    assert not retired, "Historical synthetic role datasets remain active: " + ", ".join(retired)


def test_sealed_acceptance_is_outside_the_ordinary_test_suite() -> None:
    assert not ROOT.joinpath("tests/test_real_agent_holdout_v2.py").exists(), (
        "Ordinary pytest must not load the sealed acceptance dataset"
    )
    assert ROOT.joinpath("acceptance_tests/test_real_agent_holdout_v2.py").is_file()


def test_native_runtime_cache_does_not_depend_on_analysis_temp_directory() -> None:
    from rwkv_lh.state_router.local_backend import LocalVLLMRWKVSettings

    assert LocalVLLMRWKVSettings().runtime_temp.is_relative_to(ROOT / "data/runtime")


def test_deleted_protocol_modules_leave_no_executable_bytecode() -> None:
    orphaned = []
    for path in ROOT.joinpath("rwkv_lh/goal_state_protocols").rglob("*.pyc"):
        source_directory = path.parent.parent if path.parent.name == "__pycache__" else path.parent
        if not source_directory.joinpath(path.name.split(".", 1)[0] + ".py").exists():
            orphaned.append(str(path.relative_to(ROOT)))
    assert not orphaned, "Deleted protocol bytecode remains: " + ", ".join(orphaned)
