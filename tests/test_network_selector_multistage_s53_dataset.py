from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_multistage_s53_v1"


def _rows() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (DATASET / "cases.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_s53_frozen_identity_and_counts() -> None:
    cases = DATASET / "cases.jsonl"
    manifest = DATASET / "manifest.json"
    assert hashlib.sha256(cases.read_bytes()).hexdigest() == (
        "bd3701c925717eb1d9f75d439c7fbb8b75a4905cc0099e348fa5314b98d1efde"
    )
    assert hashlib.sha256(manifest.read_bytes()).hexdigest() == (
        "532e1d1f6e5bc18bb2da15a7b39b57d03372b216a4228beacdf22ca573ea2fee"
    )
    rows = _rows()
    assert len(rows) == 1950
    assert Counter(str(row["split"]) for row in rows) == Counter(
        {"train": 1300, "dev": 325, "test": 325}
    )
    assert len({str(row["trajectory_id"]) for row in rows}) == 300


def test_s53_is_prefix_closed_and_request_last() -> None:
    rows = _rows()
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["trajectory_id"]), []).append(row)
    for trajectory in grouped.values():
        assert [int(row["trajectory_position"]) for row in trajectory] == list(
            range(len(trajectory))
        )
        assert str(trajectory[-1]["label"]) == "final_answer"
        for row in trajectory:
            step = str(row["step"])
            payload = json.loads(step.removeprefix("SelectorStepV4: "))
            assert list(payload)[-1] == "stage_objective"
            expected = str(row["bootstrap"]) + "".join(
                "\n" + str(item)
                for item in [*list(row["prior_steps"]), step]
            )
            assert str(row["rendered_input"]) == expected


def test_s53_contains_multiread_and_failure_recovery_without_forbidden_content() -> None:
    rows = _rows()
    grouped: dict[str, list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault(str(row["trajectory_id"]), []).append(row)
        assert not row["generated_rwkv_text"]
        assert not row["contains_parameter_schemas"]
        assert not row["contains_full_tool_results"]
        assert not row["contains_executor_text"]
        assert not row["hidden_acceptance_used"]
    sequences = [tuple(str(row["label"]) for row in group) for group in grouped.values()]
    assert any(sequence[:4] == ("list_directory", "read_file", "read_file", "read_file") for sequence in sequences)
    assert any(
        str(row["stage_group"]) == "recovery"
        and tuple(dict(row["selector_input"])["progress"]["failed_operations"])
        == ("check_command",)
        for row in rows
    )
