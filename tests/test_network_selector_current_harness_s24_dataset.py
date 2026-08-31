from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
    NetworkSelectorProgress,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest
from rwkv_lh.exact_tool_selector.runtime_projection import (
    SELECTOR_STAGE_PROJECTION_VERSION,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_current_harness_training_s24_v1"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_s24_matches_current_harness_input_and_preserves_frozen_splits() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (DATASET / "cases.jsonl").read_text(encoding="utf-8").splitlines()]

    assert Counter(row["split"] for row in rows) == {"train": 2000, "dev": 276, "test": 250}
    assert manifest["counts"] == {"dev": 276, "test": 250, "train": 2000}
    assert sha256_file(DATASET / "cases.jsonl") == manifest["files"]["cases.jsonl"]["sha256"]
    assert sha256_file(ROOT / manifest["generator"]["path"]) == manifest["generator"]["sha256"]
    assert set(row["label"] for row in rows if row["split"] == "test") == set(NETWORK_EXACT_TOOL_LABELS)
    assert len({row["rendered_input"] for row in rows}) == len(rows)
    assert manifest["validation"]["holdout_similarity"]["maximum"]["score"] < 0.75

    for row in rows:
        value = row["selector_input"]
        progress = value["progress"]
        assert row["selector_input_sha256"] == canonical_digest(value)
        assert progress["completed_stage_count"] == progress["action_index"]
        assert len(progress["succeeded_operations"]) + len(progress["failed_operations"]) <= 1
        assert all(set(tool) == {"name", "description"} for tool in value["tools"])
        recreated = NetworkSelectorInput.create(
            task_request=value["task_request"],
            stage_objective=value["stage_objective"],
            stage_role="work",
            progress=NetworkSelectorProgress(
                completed_stage_count=progress["completed_stage_count"],
                action_index=progress["action_index"],
                succeeded_operations=tuple(progress["succeeded_operations"]),
                failed_operations=tuple(progress["failed_operations"]),
                protocol_rejection_count=progress["protocol_rejection_count"],
            ),
        )
        assert recreated.render_bootstrap() == row["bootstrap"]
        assert recreated.render_step() == row["step"]
        assert recreated.render() == row["rendered_input"]
        step = json.loads(row["step"].removeprefix("SelectorStepV2: "))
        stage = json.loads(step["stage_objective"].removeprefix("CurrentDirectStageV1: "))
        assert stage["schema_version"] == SELECTOR_STAGE_PROJECTION_VERSION
        latest = stage["latest_action"]
        operations = progress["failed_operations"] or progress["succeeded_operations"]
        if not operations:
            assert progress["action_index"] == 0
            assert latest is None
        else:
            assert latest["sequence"] == progress["action_index"]
            assert latest["operation"] == operations[0]
            assert latest["success"] == bool(progress["succeeded_operations"])
        assert row["generated_rwkv_text"] is False
        assert row["contains_full_tool_results"] is False
        assert row["contains_tool_schemas"] is False
        assert row["contains_executor_text"] is False
