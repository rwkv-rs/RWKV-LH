from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
V2 = ROOT / "data/datasets/rwkv_lh_executor_state_tuning_v2_2k"
V3 = ROOT / "data/datasets/rwkv_lh_executor_state_tuning_v3_request_last_2k"


def rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def assignment(prompt: str) -> dict[str, object]:
    marker = "User: Executor task state: "
    start = prompt.index(marker) + len(marker)
    end = prompt.index("\nWait for the controller-selected", start)
    return json.loads(prompt[start:end])


def continuation(prompt: str) -> dict[str, object]:
    marker = "\n\nUser: Executor continuation input: "
    text = prompt.rsplit(marker, 1)[1].split("\n\nAssistant:", 1)[0]
    return json.loads(text)


def test_v3_preserves_every_v2_target_and_split() -> None:
    for name in ("stage_sft.train.jsonl", "stage_sft.dev.jsonl"):
        before = rows(V2 / name)
        after = rows(V3 / name)
        assert len(before) == len(after)
        assert [row["sample_id"] for row in after] == [
            row["sample_id"] for row in before
        ]
        assert [row["target"] for row in after] == [row["target"] for row in before]
        assert [row["similarity_projection"] for row in after] == [
            row["similarity_projection"] for row in before
        ]


def test_v3_has_one_closed_authoritative_request_at_continuation_tail() -> None:
    for name in ("stage_sft.train.jsonl", "stage_sft.dev.jsonl"):
        for row in rows(V3 / name):
            prompt = str(row["prompt"])
            state = assignment(prompt)
            tail = continuation(prompt)
            assert "immutable_request" not in state
            assert list(tail)[-1] == "current_requirement"
            assert isinstance(tail["current_requirement"], str)
            assert str(tail["current_requirement"]).strip()
            assert tail["selected_operation"] == row["selected_operation"]
            assert prompt.endswith("\n\nAssistant: ```json\n")
            assert "Available operation menu" not in prompt
            assert '"function":"select_tool"' not in prompt


def test_v3_training_rows_are_exact_target_suffixes() -> None:
    pairs = (
        (
            "stage_sft.train.jsonl",
            "rwkv_state_tuning.train.requires_target_suffix.jsonl",
        ),
        (
            "stage_sft.dev.jsonl",
            "rwkv_state_tuning.dev.requires_target_suffix.jsonl",
        ),
    )
    for stage_name, training_name in pairs:
        stage = rows(V3 / stage_name)
        training = rows(V3 / training_name)
        assert len(stage) == len(training)
        for source, rendered in zip(stage, training, strict=True):
            assert rendered["prompt"] == source["prompt"]
            assert rendered["target"] == source["target"]
            assert rendered["text"] == source["prompt"] + source["target"]
