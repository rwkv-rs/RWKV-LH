from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
    NetworkSelectorProgress,
    network_selector_menu_digest,
)

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data" / "datasets" / "rwkv_lh_network_exact_tool_selector_v2_4"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_network_selector_v2_dataset_is_frozen_balanced_and_replayable() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in (DATASET / "cases.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]

    assert manifest["dataset_version"] == "rwkv-lh.network-exact-tool-selector.v2.4"
    assert manifest["class_order"] == list(NETWORK_EXACT_TOOL_LABELS)
    assert manifest["menu_digest"] == network_selector_menu_digest()
    assert len(rows) == 7500
    assert Counter((row["label"], row["split"]) for row in rows) == Counter(
        {
            (label, split): count
            for label in NETWORK_EXACT_TOOL_LABELS
            for split, count in {"train": 240, "dev": 30, "test": 30}.items()
        }
    )
    assert _sha256(DATASET / "cases.jsonl") == manifest["files"]["cases.jsonl"]["sha256"]
    assert manifest["similarity_audit"]["algorithm"] == "utf8-byte-5gram-cosine.v1"
    assert manifest["similarity_projection"] == "canonical-json-selector-projection-task-stage-role-progress.v1"
    assert manifest["similarity_audit"]["threshold"] == 0.95
    assert manifest["similarity_audit"]["threshold_violation_count"] == 0
    assert manifest["similarity_audit"]["cross_split_violation_count"] == 0

    for row in rows:
        projection = row["selector_projection"]
        progress = projection["progress"]
        value = NetworkSelectorInput.create(
            task_request=projection["task_request"],
            stage_objective=projection["stage_objective"],
            stage_role=projection["stage_role"],
            progress=NetworkSelectorProgress(
                completed_stage_count=progress["completed_stage_count"],
                action_index=progress["action_index"],
                succeeded_operations=tuple(progress["succeeded_operations"]),
                failed_operations=tuple(progress["failed_operations"]),
                protocol_rejection_count=progress["protocol_rejection_count"],
            ),
        )
        assert value.render() == row["rendered_input"]
        assert hashlib.sha256(value.render().encode("utf-8")).hexdigest() == row["rendered_input_sha256"]
        rendered = value.render()
        for forbidden in (
            '"parameters"',
            '"arguments"',
            '"result"',
            '"reasoning"',
            '"executor_state"',
            '"workspace_contents"',
        ):
            assert forbidden not in rendered
