from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_takeover_selector_s10_v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_s10_dataset_is_bound_deduplicated_and_schema_free() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    cases = DATASET / "cases.jsonl"
    rows = [json.loads(line) for line in cases.read_text(encoding="utf-8").splitlines()]

    assert manifest["files"]["cases.jsonl"] == {
        "rows": 1354,
        "sha256": _sha256(cases),
    }
    assert Counter(row["split"] for row in rows) == Counter(
        {"train": 946, "dev": 203, "test": 205}
    )
    assert Counter(row["label"] for row in rows) == Counter(
        {"DEFER": 879, "web_search": 250, "connector_lookup": 225}
    )
    assert len({row["rendered_input"] for row in rows}) == len(rows)
    assert len({row["sample_id"] for row in rows}) == len(rows)
    forbidden = (
        '"summary"', '"result"', '"history"', '"rationale"',
        '"parameter_schema"', '"executor_state"', '"executor_text"',
    )
    assert all(not any(item in row["rendered_input"] for item in forbidden) for row in rows)
    assert all(row["generated_rwkv_text"] is False for row in rows)


def test_s10_semantic_families_do_not_cross_splits() -> None:
    rows = [
        json.loads(line)
        for line in (DATASET / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    families = {
        split: {row["semantic_family_id"] for row in rows if row["split"] == split}
        for split in ("train", "dev", "test")
    }
    assert not families["train"] & families["dev"]
    assert not families["train"] & families["test"]
    assert not families["dev"] & families["test"]
