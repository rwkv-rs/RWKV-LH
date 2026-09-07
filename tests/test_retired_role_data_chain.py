"""Prevent the retired synthetic role-data toolchain from becoming executable again."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
RETIRED_SCRIPT_STEMS = (
    "assemble_g1j_auditor_final_round2_mix_v1",
    "generate_g1j_auditor_final_state_tuning_v2",
    "generate_g1j_auditor_final_state_tuning_v3",
    "generate_g1j_auditor_step_state_tuning_v3",
    "generate_g1j_auditor_step_state_tuning_v4",
    "generate_g1j_executor_observation_state_tuning_v4",
    "generate_g1j_executor_quantifier_state_tuning_v5",
    "generate_g1j_executor_structured_state_tuning_v6",
    "validate_g1j_executor_observation_provenance_public_v4",
    "validate_g1j_executor_observation_public_v4",
)


def test_retired_synthetic_role_entrypoints_cannot_be_run_or_imported() -> None:
    executable = []
    for stem in RETIRED_SCRIPT_STEMS:
        if (ROOT / "scripts" / f"{stem}.py").exists():
            executable.append(f"scripts/{stem}.py")
        elif importlib.util.find_spec(f"scripts.{stem}") is not None:
            executable.append(f"import scripts.{stem}")
    assert not executable, f"Retired role-data entrypoints remain executable: {executable}"


def test_retired_role_bytecode_cannot_be_executed_directly() -> None:
    cached = []
    for directory in ("scripts", "tests"):
        for path in (ROOT / directory).rglob("*.pyc"):
            name = path.name.lower()
            if "holdout" in name:
                continue
            is_retired = "g1j" in name or name.startswith(
                (
                    "test_executor_observation_confirmation_v4.",
                    "test_executor_observation_dataset_v4.",
                    "test_executor_observation_evaluator_v4.",
                    "test_executor_observation_selection_v4.",
                )
            )
            source_stem = path.name.split(".", 1)[0]
            if is_retired and not (ROOT / directory / f"{source_stem}.py").exists():
                cached.append(str(path.relative_to(ROOT)))
    assert not cached, f"Retired role bytecode remains directly executable: {cached}"


def test_repository_tests_do_not_load_python_modules_from_temp() -> None:
    dependencies = []
    for path in sorted((ROOT / "tests").rglob("*.py")):
        if path == Path(__file__).resolve():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                names = []
            if any(name == "temp" or name.startswith("temp.") for name in names):
                dependencies.append(f"{path.relative_to(ROOT)}:{node.lineno}")
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                module_path = PurePosixPath(node.value.replace("\\", "/"))
                if module_path.suffix in {".py", ".pyc"} and "temp" in module_path.parts:
                    dependencies.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not dependencies, f"Tests depend on temporary Python modules: {dependencies}"
