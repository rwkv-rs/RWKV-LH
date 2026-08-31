from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_short_objective_s20_v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_s20_short_objective_dataset_is_balanced_compact_and_isolated() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    path = DATASET / "queries.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    assert _sha256(path) == "8e4d3dfa285a17259722468716e81eeeb39cc961e628f0fdf19a7935a2972e50"
    assert len(rows) == 3000
    assert manifest["counts"] == {"dev": 500, "test": 500, "train": 2000}
    assert manifest["validation"]["maximum_prompt_tokens_including_bos"] <= 128
    assert manifest["validation"]["holdout_similarity"]["maximum"]["score"] < 0.75
    assert manifest["generated_rwkv_text_count"] == 0
    assert manifest["sampling_invocation_count"] == 0

    for split, per_label in (("train", 80), ("dev", 20), ("test", 20)):
        split_rows = [row for row in rows if row["split"] == split]
        assert Counter(str(row["label"]) for row in split_rows) == Counter(
            {label: per_label for label in manifest["class_order"]}
        )
    for field in ("sample_id", "semantic_family_id", "stage_objective", "rendered_input"):
        assert len({str(row[field]) for row in rows}) == len(rows)

    families = {
        split: {str(row["semantic_family_id"]) for row in rows if row["split"] == split}
        for split in ("train", "dev", "test")
    }
    assert families["train"].isdisjoint(families["dev"])
    assert families["train"].isdisjoint(families["test"])
    assert families["dev"].isdisjoint(families["test"])
    for row in rows:
        assert row["generated_rwkv_text"] is False
        assert int(row["prompt_tokens_including_bos"]) <= 128
        prefix = "SelectorObjectiveV4: "
        assert str(row["rendered_input"]).startswith(prefix)
        payload = json.loads(str(row["rendered_input"])[len(prefix):])
        assert payload == {
            "objective": row["stage_objective"],
            "schema_version": "rwkv-lh.selector-objective.s20.v1",
        }
        assert set(payload) == {"objective", "schema_version"}
