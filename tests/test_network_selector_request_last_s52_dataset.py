from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
S51 = ROOT / "data/datasets/rwkv_lh_network_selector_natural_harness_s51_v1"
S52 = ROOT / "data/datasets/rwkv_lh_network_selector_request_last_s52_v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rows(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
    ]


def test_s52_is_a_complete_semantic_pair_of_s51() -> None:
    control = rows(S51 / "cases.jsonl")
    request_last = rows(S52 / "cases.jsonl")
    fields = (
        "selector_input",
        "selector_input_sha256",
        "label",
        "split",
        "language",
        "prefix_kind",
        "trajectory_position",
        "trajectory_length",
        "stage_group",
        "source_kind",
        "source_id",
    )

    assert len(control) == len(request_last) == 2421
    assert Counter(row["split"] for row in request_last) == {
        "train": 1615,
        "dev": 399,
        "test": 407,
    }
    for left, right in zip(control, request_last, strict=True):
        assert all(left[field] == right[field] for field in fields)
        assert right["paired_source_sample_id"] == left["sample_id"]
        assert right["paired_source_rendered_input_sha256"] == left[
            "rendered_input_sha256"
        ]


def test_every_s52_generation_point_has_the_current_question_last() -> None:
    for row in rows(S52 / "cases.jsonl"):
        bootstrap = str(row["bootstrap"])
        step = str(row["step"])
        task = json.loads(bootstrap.split("\nSelectorTaskV4: ", 1)[1])
        current = json.loads(step.removeprefix("SelectorStepV4: "))

        assert list(task)[-1] == "task_request"
        assert list(current)[-1] == "stage_objective"
        assert current["stage_objective"] == row["selector_input"][
            "stage_objective"
        ]
        assert str(row["rendered_input"]).endswith(step)
        assert row["generated_rwkv_text"] is False
        assert row["contains_parameter_schemas"] is False


def test_s52_dataset_frozen_identity() -> None:
    assert sha256_file(S52 / "cases.jsonl") == (
        "1cb1a1b2597a16c63b92753e402529239d4a765698964e0102640bf70dab7faf"
    )
    assert sha256_file(S52 / "manifest.json") == (
        "79c56635778886e891d0f271ade9320d5d214bdfd4461b8f0adf7232d5ee1ff1"
    )
