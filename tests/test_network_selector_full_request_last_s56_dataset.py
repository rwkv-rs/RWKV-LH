from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.compact_protocol_v5 import (
    COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_full_request_last_s56_v1"
CASES_SHA256 = "8bd02a2368f29657bbd87d8ba103a410ec92fd04cc5c99a8286ac49064548697"
MANIFEST_SHA256 = "9c2a890366800c7332a9382331118c6400236662682f7393bd74832af1025d96"
PREREGISTRATION_SHA256 = "8c29c7de04e108e5630beab815df0437c8ac8b2ca256d0ddd2e1970b0cddf442"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_s56_manifest_and_source_identities_are_frozen() -> None:
    manifest_path = DATASET / "manifest.json"
    assert sha256_file(manifest_path) == MANIFEST_SHA256
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["counts"] == {"train": 13143, "dev": 2571, "test": 2579}
    assert manifest["protocol"] == {
        "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "renderer": "rwkv_lh/exact_tool_selector/compact_protocol_v5.py",
        "renderer_sha256": "3d19665e4a85d5296b336acf616a087f4d1e272aa8acebfc5855d7a02edab7bf",
        "complete_current_requirement_last": True,
        "repeated_at_every_causal_step": True,
    }
    assert manifest["preregistration"]["sha256"] == PREREGISTRATION_SHA256
    assert manifest["files"]["cases.jsonl"]["sha256"] == CASES_SHA256
    assert sha256_file(DATASET / "cases.jsonl") == CASES_SHA256
    assert manifest["validation"] == {
        "executor_text_present": False,
        "generated_rwkv_text": False,
        "labels_changed": False,
        "parameter_schemas_present": False,
        "rendered_prompt_duplicates": 0,
        "sampling_invoked": False,
        "split_membership_changed": False,
        "tool_result_bodies_present": False,
    }


def test_every_s56_prefix_has_full_requirement_at_the_continuation_edge() -> None:
    counts: Counter[str] = Counter()
    sources: Counter[tuple[str, str]] = Counter()
    labels: dict[str, set[str]] = {split: set() for split in ("train", "dev", "test")}
    identities: set[str] = set()
    prompt_hashes: set[str] = set()
    row_count = 0
    with (DATASET / "cases.jsonl").open("r", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            row_count += 1
            split = str(row["split"])
            counts[split] += 1
            sources[(str(row["source_dataset"]), split)] += 1
            labels[split].add(str(row["label"]))
            identities.add(str(row["sample_id"]))
            prompt_hashes.add(str(row["rendered_input_sha256"]))

            assert row["compact_input_schema_version"] == COMPACT_SELECTOR_INPUT_SCHEMA_VERSION
            assert row["bootstrap"].startswith("SelectorMenuV5: ")
            assert "\nSelectorTaskIdentityV5: " in row["bootstrap"]
            assert row["step"].startswith("SelectorStepV5: ")
            step = json.loads(row["step"].removeprefix("SelectorStepV5: "))
            assert list(step)[-1] == "current_requirement"
            requirement = step["current_requirement"]
            assert isinstance(requirement, str) and requirement.strip()
            assert requirement not in row["bootstrap"]
            for prior in row["prior_steps"]:
                prior_payload = json.loads(prior.removeprefix("SelectorStepV5: "))
                assert list(prior_payload)[-1] == "current_requirement"
                assert prior_payload["current_requirement"] == requirement
            assert row["rendered_input"] == row["bootstrap"] + "".join(
                "\n" + value for value in [*row["prior_steps"], row["step"]]
            )
            assert row["rendered_input"].endswith(
                json.dumps(requirement, ensure_ascii=False) + "}"
            )
            assert hashlib.sha256(row["rendered_input"].encode("utf-8")).hexdigest() == row[
                "rendered_input_sha256"
            ]
            assert row["request_last"] is True
            assert row["current_requirement_is_full_task"] is True
            assert row["generated_rwkv_text"] is False
            assert row["hidden_acceptance_used"] is False
            assert row["contains_parameter_schemas"] is False
            assert row["contains_full_tool_results"] is False
            assert row["contains_executor_text"] is False

    assert row_count == 18293
    assert counts == {"train": 13143, "dev": 2571, "test": 2579}
    assert len(identities) == len(prompt_hashes) == row_count
    assert all(value == set(NETWORK_EXACT_TOOL_LABELS) for value in labels.values())
    assert sources == {
        ("s28", "train"): 6000,
        ("s28", "dev"): 750,
        ("s28", "test"): 750,
        ("s39", "train"): 3428,
        ("s39", "dev"): 857,
        ("s39", "test"): 857,
        ("s52", "train"): 1615,
        ("s52", "dev"): 399,
        ("s52", "test"): 407,
        ("s53", "train"): 1300,
        ("s53", "dev"): 325,
        ("s53", "test"): 325,
        ("s55", "train"): 800,
        ("s55", "dev"): 240,
        ("s55", "test"): 240,
    }
