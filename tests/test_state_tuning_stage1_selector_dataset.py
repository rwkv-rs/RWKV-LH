import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.model_io import parse_tool_selection


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/datasets/rwkv_lh_state_tuning_stage1_selector_v1"


def rows(name: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (DATA / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_stage1_selector_dataset_is_exact_residual_slice() -> None:
    train = rows("stage_sft.train.jsonl")
    dev = rows("stage_sft.dev.jsonl")
    assert len(train) == 500
    assert len(dev) == 79
    assert len({row["semantic_family_id"] for row in train}) == 100
    assert len({row["semantic_family_id"] for row in dev}) == 17
    assert not (
        {row["semantic_family_id"] for row in train}
        & {row["semantic_family_id"] for row in dev}
    )
    assert Counter(row["failure_cluster"] for row in train) == {
        "no_progress_recovery": 140,
        "observation_binding": 125,
        "coverage_focus": 110,
        "completion_evidence": 95,
        "privacy_gate": 30,
    }
    assert all(row["stage"] == "selector" for row in train + dev)
    assert all(
        parse_tool_selection(row["target"]) == row["target_operation"]
        for row in train + dev
    )
    assert len({row["prompt_sha256"] for row in train + dev}) == 579


def test_stage1_target_suffix_exports_are_exact() -> None:
    for split, count in (("train", 500), ("dev", 79)):
        stages = rows(f"stage_sft.{split}.jsonl")
        exported = rows(f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl")
        assert len(stages) == len(exported) == count
        for stage, row in zip(stages, exported, strict=True):
            assert row == {
                "prompt": stage["prompt"],
                "target": stage["target"],
                "text": stage["prompt"] + stage["target"],
            }


def test_stage1_manifest_pins_every_artifact_and_parent() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["training_ready"] is True
    assert manifest["remote_tokenizer_validated"] is True
    assert manifest["loss_mask"] == "target_suffix"
    assert manifest["counts"]["observed_wrong_outer_calls"] == 77
    assert manifest["validation"]["remote_training_contract"]["failure_count"] == 0
    assert (
        manifest["validation"]["remote_training_contract"]
        ["target_suffix_exact_label_match_rate"]
        == 1.0
    )
    assert manifest["validation"]["remote_training_contract"]["jsonl_bos_token_id"] == 0
    assert (
        manifest["validation"]["remote_training_contract"]
        ["first_target_predicted_from_last_prompt_token"]
        is True
    )
    for name, record in manifest["files"].items():
        path = DATA / name
        assert digest(path) == record["sha256"]
        assert path.stat().st_size == record["bytes"]
    parent = ROOT / manifest["parent"]["dataset_manifest"]
    residual = ROOT / manifest["parent"]["residual_eval"]
    prereg = ROOT / manifest["preregistration"]["path"]
    amendment = ROOT / manifest["preregistration"]["amendment_path"]
    assert digest(parent) == manifest["parent"]["dataset_manifest_sha256"]
    assert digest(residual) == manifest["parent"]["residual_eval_sha256"]
    assert digest(prereg) == manifest["preregistration"]["sha256"]
    assert amendment.is_file()
    assert digest(amendment) == manifest["preregistration"]["amendment_sha256"]


def test_stage1_hard_negatives_are_the_observed_parent_outer_calls() -> None:
    registry = json.loads(
        (DATA / "hard_negative_registry.json").read_text(encoding="utf-8")
    )
    assert registry["wrong_outer_function_counts"] == {
        "list_directory": 41,
        "read_file": 18,
        "read_json": 15,
        "connector_lookup": 3,
    }
    residuals = rows("observed_parent_selector_residuals.jsonl")
    actual = Counter(
        row["actual_outer_function"]
        for row in residuals
        if row["actual_outer_function"] != "select_tool"
    )
    assert dict(actual) == registry["wrong_outer_function_counts"]
