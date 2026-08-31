from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from rwkv_lh.exact_tool_selector.compact_protocol_v3 import (
    render_compact_selector_bootstrap,
    render_compact_selector_step,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
    NetworkSelectorProgress,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_full_variant_matched_prefix_s39_v1"
CASES_SHA256 = "b85ff487cd0902743ede4299c651f3af4a5fa92f0a1240edb3e89b68b7ac0dab"
OPAQUE_ID = re.compile(r"^S39-[PT]-[0-9a-f]{24}$")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selector_input(value: dict[str, object]) -> NetworkSelectorInput:
    progress = value["progress"]
    assert isinstance(progress, dict)
    return NetworkSelectorInput.create(
        task_request=str(value["task_request"]),
        stage_objective=str(value["stage_objective"]),
        stage_role=str(value["stage_role"]),
        progress=NetworkSelectorProgress(
            completed_stage_count=int(progress["completed_stage_count"]),
            action_index=int(progress["action_index"]),
            succeeded_operations=tuple(progress["succeeded_operations"]),
            failed_operations=tuple(progress["failed_operations"]),
            protocol_rejection_count=int(progress["protocol_rejection_count"]),
        ),
    )


def test_s39_manifest_freezes_full_variants_and_matched_splits() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    assert sha256_file(DATASET / "cases.jsonl") == CASES_SHA256
    assert manifest["files"]["cases.jsonl"] == {
        "rows": 5142,
        "sha256": CASES_SHA256,
    }
    assert manifest["eligible_contract_variants_by_split"] == {
        split: [0, 1, 2, 3, 4, 5] for split in ("train", "dev", "test")
    }
    assert manifest["validation"]["prefix_counts"] == {
        "train": 3428,
        "dev": 857,
        "test": 857,
    }
    assert manifest["validation"]["operation_source_split_overlap"] == 0
    assert manifest["validation"]["trajectory_split_overlap"] == 0
    assert manifest["source_partition_audit"]["source_usage_distinct_ids"] == {
        "train": 1710,
        "dev": 335,
        "test": 341,
    }
    assert sha256_file(ROOT / manifest["generator"]["path"]) == manifest["generator"]["sha256"]
    assert sha256_file(ROOT / manifest["frozen_s38_generator_dependency"]["path"]) == manifest["frozen_s38_generator_dependency"]["sha256"]
    assert sha256_file(ROOT / manifest["preregistration"]["path"]) == manifest["preregistration"]["sha256"]


def test_s39_rows_keep_opaque_ids_and_exact_v3_rendering() -> None:
    rows = [
        json.loads(line)
        for line in (DATASET / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(rows) == 5142
    assert len({row["sample_id"] for row in rows}) == 5142
    assert len({row["trajectory_id"] for row in rows}) == 3000
    for row in rows:
        assert row["label"] in NETWORK_EXACT_TOOL_LABELS
        assert OPAQUE_ID.fullmatch(str(row["sample_id"]))
        assert OPAQUE_ID.fullmatch(str(row["trajectory_id"]))
        value = selector_input(row["selector_input"])
        assert render_compact_selector_bootstrap(value) == row["bootstrap"]
        assert render_compact_selector_step(value) == row["step"]
        assert row["rendered_input"] == row["bootstrap"] + "".join(
            "\n" + item for item in [*row["prior_steps"], row["step"]]
        )
