from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from rwkv_lh.exact_tool_selector.compact_protocol_v3 import (
    COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
    compact_selector_menu_digest,
    render_compact_selector_bootstrap,
    render_compact_selector_step,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
    NetworkSelectorProgress,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_prefix_closed_s36_v1"
CASES_SHA256 = "e837eee8772ce3cfb9d34f2492d8a6bffed78b5b158969bc39f75fd1931c1ca5"
OPAQUE_ID = re.compile(r"^S36-[PT]-[0-9a-f]{24}$")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load() -> tuple[dict[str, object], list[dict[str, object]]]:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in (DATASET / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    return manifest, rows


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


def test_s36_manifest_freezes_source_generator_and_counts() -> None:
    manifest, rows = load()
    assert sha256_file(DATASET / "cases.jsonl") == CASES_SHA256
    assert manifest["files"]["cases.jsonl"] == {
        "rows": 5096,
        "sha256": CASES_SHA256,
    }
    assert sha256_file(ROOT / manifest["source"]["path"]) == manifest["source"]["sha256"]
    assert sha256_file(ROOT / manifest["generator"]["path"]) == manifest["generator"]["sha256"]
    assert sha256_file(ROOT / manifest["preregistration"]["path"]) == manifest["preregistration"]["sha256"]
    assert manifest["validation"]["prefix_counts"] == {
        "train": 3336,
        "dev": 765,
        "test": 995,
    }
    assert manifest["validation"]["trajectory_counts"] == {
        "train": 2000,
        "dev": 500,
        "test": 500,
    }
    assert len(rows) == 5096


def test_s36_is_prefix_closed_with_exact_v3_rendering() -> None:
    manifest, rows = load()
    assert manifest["input_protocol"]["schema_version"] == COMPACT_SELECTOR_INPUT_SCHEMA_VERSION
    assert manifest["input_protocol"]["menu_digest"] == compact_selector_menu_digest()
    grouped: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        assert row["label"] in NETWORK_EXACT_TOOL_LABELS
        assert OPAQUE_ID.fullmatch(str(row["sample_id"]))
        assert OPAQUE_ID.fullmatch(str(row["trajectory_id"]))
        assert all(
            label.lower() not in str(row["sample_id"]).lower()
            and label.lower() not in str(row["trajectory_id"]).lower()
            for label in NETWORK_EXACT_TOOL_LABELS
        )
        value = selector_input(row["selector_input"])
        assert render_compact_selector_bootstrap(value) == row["bootstrap"]
        assert render_compact_selector_step(value) == row["step"]
        assert row["rendered_input"] == row["bootstrap"] + "".join(
            "\n" + item for item in [*row["prior_steps"], row["step"]]
        )
        assert len(row["prior_steps"]) == row["trajectory_position"]
        assert not row["contains_parameter_schemas"]
        assert not row["contains_full_tool_results"]
        assert not row["contains_executor_text"]
        assert not row["generated_rwkv_text"]
        assert not row["sampling_invoked"]
        grouped[str(row["trajectory_id"])].append(row)
    assert len(grouped) == 3000
    for trajectory in grouped.values():
        assert [row["trajectory_position"] for row in trajectory] == list(
            range(len(trajectory))
        )
        assert all(row["trajectory_length"] == len(trajectory) for row in trajectory)
        assert sum(row["prefix_kind"] == "current" for row in trajectory) == 1
        assert trajectory[-1]["prefix_kind"] == "current"


def test_s36_preserves_all_classes_and_split_isolation() -> None:
    _manifest, rows = load()
    assert Counter(row["prefix_kind"] for row in rows) == {
        "history": 2096,
        "current": 3000,
    }
    for split in ("train", "dev", "test"):
        assert set(row["label"] for row in rows if row["split"] == split) == set(
            NETWORK_EXACT_TOOL_LABELS
        )
    trajectories = {
        split: {
            row["trajectory_id"] for row in rows if row["split"] == split
        }
        for split in ("train", "dev", "test")
    }
    assert not trajectories["train"] & trajectories["dev"]
    assert not trajectories["train"] & trajectories["test"]
    assert not trajectories["dev"] & trajectories["test"]
