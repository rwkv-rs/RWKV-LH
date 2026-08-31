from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.model_io import parse_model_command


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_executor_multistage_g3_2k"
CONTINUATION = "\n\nUser: Executor continuation input: "
ANCHOR = "\n\nAssistant: ```json\n"


def _rows(split: str) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (DATASET / f"stage_sft.{split}.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]


def test_executor_g3_frozen_identity_and_source_mass() -> None:
    expected = {
        "stage_sft.train.jsonl": "8a34c9af03a5070620af870734ed40683cc91406ca686ee8d271cedf799fb1d8",
        "stage_sft.dev.jsonl": "68fb951c630255cd5c3cf37c5be51552368013ce51cdc03cbf09d3893453e75d",
        "manifest.json": "c510b434be71cf1304aeb75de6ba4156756aaebcae2566f56d528dcce844f5e1",
    }
    for name, digest in expected.items():
        assert hashlib.sha256((DATASET / name).read_bytes()).hexdigest() == digest
    train = _rows("train")
    dev = _rows("dev")
    assert len(train) == 2000
    assert len(dev) == 480
    assert Counter(row["source_kind"] for row in train) == Counter(
        {"g2_frozen_first_action_retention": 1200, "synthetic_multistage_request_last": 800}
    )
    assert Counter(row["source_kind"] for row in dev) == Counter(
        {"g2_frozen_first_action_retention": 240, "synthetic_multistage_request_last": 240}
    )


def test_executor_g3_request_is_last_and_targets_remain_raw_direct_calls() -> None:
    for split in ("train", "dev"):
        for row in _rows(split):
            prompt = str(row["prompt"])
            tail = prompt.rsplit(CONTINUATION, 1)[1]
            payload_text, suffix = tail.split(ANCHOR, 1)
            assert suffix == ""
            payload = json.loads(payload_text)
            assert list(payload)[-1] == "current_requirement"
            command = parse_model_command(str(row["target"]))
            assert command.name == row["selected_operation"]
            assert str(row["text"]) == prompt + str(row["target"])
            assert not row["generated_rwkv_text"]
            assert not row["raw_output_modified"]


def test_executor_g3_covers_real_multistage_counts_and_critical_families() -> None:
    rows = [*_rows("train"), *_rows("dev")]
    multistage = [row for row in rows if row["source_kind"] == "synthetic_multistage_request_last"]
    assert multistage
    assert {int(row["recent_action_count"]) for row in multistage} == {1, 2, 3, 4, 5}
    assert all(1 <= int(row["recent_action_count"]) <= 5 for row in multistage)
    assert {
        "read_file",
        "read_json",
        "write_file",
        "write_json",
        "check_command",
        "run_command",
        "final_answer",
    }.issubset({str(row["critical_multistage_family"]) for row in multistage})
