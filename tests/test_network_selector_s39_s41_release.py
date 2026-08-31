from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = (
    ROOT
    / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828"
)
SELECTION = (
    EXPERIMENT
    / "run_s39_full_variant_matched_prefix_head_dev_selection/DEV_SELECTION.json"
)
HEAD = (
    EXPERIMENT
    / "run_s39_full_variant_matched_prefix_head_dev_selection/candidates/concat-h64/selector_head.json"
)
S40_REPORT = (
    EXPERIMENT
    / "run_s40_full_variant_matched_prefix_locked_test/TEST_REPORT.json"
)
S41_REPORT = EXPERIMENT / "run_s41_v3_product_shadow_canary/CANARY_REPORT.json"
CURRENT_LAUNCH = (
    ROOT / "scripts/run_network_selector_s60_requirement_byte_tail_zero_service.sh"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_s39_s41_release_is_content_addressed_and_all_gates_pass() -> None:
    assert sha256_file(SELECTION) == (
        "d1261c8c19b2b16644c52c58e0124a9860d0bc86f554c60afa5b602f97022571"
    )
    assert sha256_file(HEAD) == (
        "e2c4ffa85bb98637f8ba3dd2caf5789b732f2bb43ebc9b19bc4242e0ff3063dd"
    )
    assert sha256_file(S40_REPORT) == (
        "aa8fe7d3973310d00b34294f8d3d043935fafc2fd0f20d51b15afee9ffcb12a8"
    )
    assert sha256_file(S41_REPORT) == (
        "75ad2c9fa2d31ed57c69b4f53a3624985900e187604b354a64b335e1dbf647c5"
    )

    selection = json.loads(SELECTION.read_text(encoding="utf-8"))
    assert selection["selected_candidate_id"] == "concat-h64"
    assert selection["trained_candidate_ids"] == ["concat-h64"]
    assert selection["locked_regression_unlocked"] is True
    assert selection["locked_head_file_sha256"] == sha256_file(HEAD)
    assert selection["locked_head_hash"] == (
        "73ecba1dcd84a2b8005d486b71fad210b1aab2f9981e8e04b2b7c90846ade7a7"
    )
    assert selection["state_profile"] == {"id": "zero", "sha256": "0" * 64}
    assert selection["test_labels_accessed"] == 0
    assert selection["test_metrics_computed"] is False

    s40 = json.loads(S40_REPORT.read_text(encoding="utf-8"))
    assert s40["accepted"] is True
    assert s40["product_gpu0_canary_unlocked"] is True
    assert all(s40["gates"].values())
    assert s40["s39_metrics"]["accuracy"] >= 0.96
    assert s40["s39_metrics"]["macro_f1"] >= 0.96
    assert s40["s28_metrics"]["accuracy"] >= 0.99
    assert s40["additional_rwkv_forward_count"] == 0
    assert s40["generated_rwkv_text_count"] == 0
    assert s40["logit_postprocessing_count"] == 0
    assert s40["executor_model_call_count"] == 0

    s41 = json.loads(S41_REPORT.read_text(encoding="utf-8"))
    assert s41["accepted"] is True
    assert s41["env_local_activation_unlocked"] is True
    assert all(s41["gates"].values())
    assert s41["physical_gpu"] == 0
    assert s41["selected_current_rows"] == 25
    assert s41["total_selector_calls"] == 37
    assert s41["exact_prefix_rows"] == 37
    assert s41["maximum_abs_logit_difference"] <= 0.005
    assert s41["generated_rwkv_text_count"] == 0
    assert s41["sampling_invocation_count"] == 0
    assert s41["logit_postprocessing_count"] == 0
    assert s41["retry_count"] == 0
    assert s41["fallback_count"] == 0
    assert s41["harness_tool_execution_count"] == 0
    assert s41["executor_model_call_count"] == 0


def test_current_release_launch_and_example_pin_s60_zero_state_identity() -> None:
    assert os.access(CURRENT_LAUNCH, os.X_OK)
    launch = CURRENT_LAUNCH.read_text(encoding="utf-8")
    for required in (
        "CUDA_VISIBLE_DEVICES=0",
        "--port \"$SERVICE_PORT\"",
        "--profile-id zero",
        "--profile-sha256 \"$ZERO_SHA256\"",
        "721669ce8733b590b3aa6c910d8bc13d744612f1fee884d5276a3f0d96d0d441",
        "205f995690232aef9c442b19a009fb2eda4c6be4e524e3fc903bb2dd17d72f9e",
    ):
        assert required in launch

    selector_values: dict[str, str] = {}
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        if line.startswith("RWKV_SELECTOR_"):
            key, value = line.split("=", 1)
            selector_values[key] = value
    assert selector_values == {
        "RWKV_SELECTOR_BASE_URL": "http://127.0.0.1:29621",
        "RWKV_SELECTOR_MODEL": "rwkv7-g1i-2.9b-vllm-v1",
        "RWKV_SELECTOR_MODEL_SHA256": (
            "01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044"
        ),
        "RWKV_SELECTOR_HEAD_SHA256": (
            "721669ce8733b590b3aa6c910d8bc13d744612f1fee884d5276a3f0d96d0d441"
        ),
        "RWKV_SELECTOR_HEAD_HASH": (
            "205f995690232aef9c442b19a009fb2eda4c6be4e524e3fc903bb2dd17d72f9e"
        ),
        "RWKV_SELECTOR_FEATURE_PROTOCOL": (
            "rwkv-lh.vllm-rwkv-final-hidden-mean-last-concat.v1"
        ),
        "RWKV_SELECTOR_INPUT_PROTOCOL": (
            "rwkv-lh.exact-tool-selector-input.v7-requirement-byte-tail"
        ),
        "RWKV_SELECTOR_STATE_PROFILE_ID": "zero",
        "RWKV_SELECTOR_STATE_PROFILE_SHA256": "0" * 64,
        "RWKV_SELECTOR_STATE_PROFILE_MANIFEST_SHA256": (
            "706ff62cc8ae5851f9c918509911d4ee701f9db5d00bef16f24d2a568e3a0b47"
        ),
            "RWKV_SELECTOR_CONNECT_TIMEOUT": "10",
            "RWKV_SELECTOR_READ_TIMEOUT": "120",
            "RWKV_SELECTOR_LAUNCHER": (
                "/home/chase/GitHub/RWKV-LH/scripts/"
                "run_network_selector_s60_requirement_byte_tail_zero_service.sh"
            ),
        }
