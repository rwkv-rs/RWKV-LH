from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_state_s54_v1"


def _rows(split: str) -> list[dict[str, object]]:
    path = DATASET / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_s54_frozen_identity_balance_and_context() -> None:
    expected = {
        "rwkv_state_tuning.train.requires_target_suffix.jsonl": "32f0be0fc00a0b5717ba4bfb85de71f2966c21dc2194a4b0a1cdada46deb8978",
        "rwkv_state_tuning.dev.requires_target_suffix.jsonl": "43f8b503c812c1bd9ed2a16db7738666ee4656575ac84012d7fdd889cf4ced91",
        "manifest.json": "ec9fb875e7594a24c3f82462ae82141eedb9a82cb141013252753a08dda4db57",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((DATASET / name).read_bytes()).hexdigest() == digest
    for split, per_class, per_language in (("train", 80, 1000), ("dev", 20, 250)):
        rows = _rows(split)
        assert Counter(row["label"] for row in rows) == Counter(
            {label: per_class for label in Counter(row["label"] for row in rows)}
        )
        assert len(Counter(row["label"] for row in rows)) == 25
        assert Counter(row["language"] for row in rows) == Counter(
            {"en": per_language, "zh": per_language}
        )
        assert max(int(row["text_tokens_including_bos"]) for row in rows) <= 2497


def test_s54_every_prompt_has_current_question_at_tail_and_exact_target_suffix() -> None:
    for split in ("train", "dev"):
        for row in _rows(split):
            prompt = str(row["prompt"])
            payload = json.loads(prompt.rsplit("SelectorStepV4: ", 1)[1])
            assert list(payload)[-1] == "stage_objective"
            assert str(row["target"]) == "\nSelectorLabelV4: " + str(row["label"])
            assert str(row["text"]) == prompt + str(row["target"])
            assert row["persistent_history_replayed"]
            assert row["request_last"]
            assert not row["generated_rwkv_text"]
