from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_atomic_objective_s22_v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_s22_atomic_objective_projection_is_frozen_and_complete() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in (DATASET / "queries.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert manifest["dataset_version"] == "rwkv-lh.network-selector.atomic-objective-s22.v1"
    assert manifest["source"]["sha256"] == (
        "d60ad4a2404fda0f9401a5858070bb5e3063d408be68c9f88e1c0431eed1313c"
    )
    assert _sha256(DATASET / "queries.jsonl") == (
        "8655cfc4050b0e7241bc2defe5442ddc829a736e29266ec1ef667309cccdc6db"
    )
    assert len(rows) == 9076
    assert len({row["sample_id"] for row in rows}) == 9076
    assert Counter(row["split"] for row in rows) == Counter(
        {"train": 7400, "dev": 926, "test": 750}
    )
    assert sum(
        row["split"] == "dev" and row["source_kind"] == "stage3_natural"
        for row in rows
    ) == 176
    assert max(row["prompt_tokens_including_bos"] for row in rows) == 287
    assert all(
        row["rendered_input"].startswith("SelectorObjectiveV4: ")
        and row["generated_rwkv_text"] is False
        for row in rows
    )
