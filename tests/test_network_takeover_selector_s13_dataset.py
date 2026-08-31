from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_takeover_selector_s13_compact_v1"


def test_s13_compact_dataset_contract() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    cases_path = DATASET / "cases.jsonl"
    rows = [json.loads(line) for line in cases_path.read_text(encoding="utf-8").splitlines()]
    assert manifest["dataset_version"] == "rwkv-lh.network-takeover-selector.s13.compact.v1"
    assert len(rows) == len({row["sample_id"] for row in rows}) == 2000
    assert hashlib.sha256(cases_path.read_bytes()).hexdigest() == manifest["files"]["cases.jsonl"]["sha256"]
    assert Counter(row["split"] for row in rows) == Counter(train=1506, dev=289, test=205)
    assert Counter(row["label"] for row in rows) == Counter(DEFER=1405, connector_lookup=285, web_search=310)
    compact = [row for row in rows if row["source_kind"] == "compact_natural"]
    assert len(compact) == 600
    assert Counter(row["failure_cluster"] for row in compact) == Counter({
        "mixed_local_first": 180,
        "compact_local_only": 120,
        "deterministic_retention": 120,
        "privacy_local_first": 60,
        "ordinary_web": 60,
        "natural_connector": 60,
    })
    assert not any(row["generated_rwkv_text"] for row in rows)
    assert manifest["validation"]["contamination"]["exact_overlap_count"] == 0
    assert manifest["validation"]["contamination"]["maximum"]["score"] < 0.75
    families = {
        split: {row["semantic_family_id"] for row in rows if row["split"] == split}
        for split in ("train", "dev", "test")
    }
    assert not (families["train"] & families["dev"])
    assert not (families["train"] & families["test"])
    assert not (families["dev"] & families["test"])
