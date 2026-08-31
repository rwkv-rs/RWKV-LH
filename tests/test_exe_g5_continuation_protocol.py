from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREREGISTRATION = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/EXE_G5_G3_CONTINUED_TRUE_WORKFLOW_PREREGISTRATION.md"
RUNNER = ROOT / "scripts/run_remote_exe_g5_g3_continued_true_workflow_state_tuning.sh"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_g5_is_one_g3_initialized_state_on_physical_gpu0() -> None:
    assert sha256_file(PREREGISTRATION) == "0d1cc89db61480cb5350c21f973898adcdd2cd62031e01ccc9166cbe236ff6ac"
    assert sha256_file(RUNNER) == "3bdc74b52159252c22c0c8985e34bb3a37082b17439390946c6ffbdafd086e30"
    text = RUNNER.read_text(encoding="utf-8")
    assert "export CUDA_VISIBLE_DEVICES=0" in text
    assert text.count("--state_init ") == 1
    assert "--state_init_sha256 9f22ce1ef1b71a157f966e4abeb1ef0ef67014bc9fd26f86106857f23b01e016" in text
    assert "--require_state_init 1" in text
    assert "--state_init_expected_tensors 61" in text
    assert "--epoch_steps 2000" in text
    assert "--step_save 250" in text
    assert "--lr_init 5e-6" in text
    assert "--lr_final 5e-7" in text
    assert "--warmup_steps 40" in text
    assert "--random_seed 1063" in text
    assert "--loss_mask target_suffix" in text
    assert "--jsonl_bos_token_id 0" in text
