from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREREGISTRATION = ROOT / (
    "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/"
    "SEL_2P9_S60_EXE_G3_G5_FACTORIAL_PREREGISTRATION.md"
)
RUNNER = ROOT / "temp/run_s60_g3_g5_real_factorial_ablation_20260829.py"
VALIDATOR = ROOT / "temp/validate_current_architecture_e2e_v7_requirement_tail_20260829.py"
RELEASE_RUNNER = ROOT / "temp/run_s60_selected_architecture_release_gates_20260829.py"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_runner():
    spec = importlib.util.spec_from_file_location("rwkv_lh_s60_factorial_test", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_release_runner():
    spec = importlib.util.spec_from_file_location(
        "rwkv_lh_s60_release_test", RELEASE_RUNNER
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def valid_row(arm: str) -> dict[str, object]:
    return {
        "arm": arm,
        "case_count": 6,
        "strict_passed": 6,
        "integrity_status": "valid",
        "raw_outputs_modified_or_deleted": False,
        "generation_inputs": 7,
        "raw_generations": 7,
        "request_last_inputs": 6,
        "protocol_rejection_last_inputs": 1,
        "committed_selector_outputs": 5,
        "selector_question_last_inputs": 5,
        "selector_requirement_byte_tail_inputs": 5,
    }


def test_factorial_is_frozen_to_s60_requirement_tail_and_g3_initialized_g5() -> None:
    assert sha256_file(PREREGISTRATION) == (
        "6cdf850d79f5a44feb92b8efb342c77238c31ed297117f7aaad6c0ab293258d5"
    )
    assert sha256_file(VALIDATOR) == (
        "da6799bb85b89995aef91a06c16a0806262f6ba630fc4de81d784d57c8218ce3"
    )
    text = RUNNER.read_text(encoding="utf-8")
    assert 'for selector_kind in ("S53", "S60")' in text
    assert '"S60_G3"' in text and '"S60_G5"' in text
    assert "never deploy S53" in text
    assert "run_remote_exe_g5_g3_continued_candidate_vllm.sh" in text
    assert "validate_current_architecture_e2e_v7_requirement_tail_20260829.py" in text


def test_s60_arm_gate_requires_literal_requirement_byte_tail_for_every_output() -> None:
    runner = load_runner()
    row = valid_row("S60_G3")
    assert runner.arm_gate(row) is True
    row["selector_requirement_byte_tail_inputs"] = 4
    assert runner.arm_gate(row) is False
    row["selector_requirement_byte_tail_inputs"] = 5
    row["selector_question_last_inputs"] = 4
    assert runner.arm_gate(row) is False


def test_retained_s53_baseline_does_not_claim_v7_tail_evidence() -> None:
    runner = load_runner()
    row = valid_row("S53_G3")
    row["selector_requirement_byte_tail_inputs"] = 0
    row["selector_question_last_inputs"] = 0
    assert runner.arm_gate(row) is True


def test_full90_release_gate_requires_v7_tail_and_only_registered_unsupported() -> None:
    release = load_release_runner()
    value = {
        "case_count": 90,
        "integrity_exit_code": 0,
        "integrity_status": "valid",
        "raw_outputs_modified_or_deleted": False,
        "generation_inputs": 120,
        "raw_generations": 120,
        "request_last_inputs": 116,
        "protocol_rejection_last_inputs": 4,
        "committed_selector_outputs": 112,
        "selector_requirement_byte_tail_inputs": 112,
        "unsupported": [{"task_id": "E2E-LH09", "operation": "mock_api"}],
        "runner_errors": [],
    }
    assert release.full90_integrity_gate(value) is True
    value["selector_requirement_byte_tail_inputs"] = 111
    assert release.full90_integrity_gate(value) is False
    value["selector_requirement_byte_tail_inputs"] = 112
    value["unsupported"] = []
    assert release.full90_integrity_gate(value) is False
