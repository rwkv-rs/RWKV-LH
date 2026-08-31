from __future__ import annotations

import hashlib
import json
from pathlib import Path

from rwkv_lh.model_io import canonical_json


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_state_tuning_seed_v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_state_tuning_seed_package_is_current_and_holdout_clean() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    contracts = json.loads(
        (DATASET / "tool_contracts.json").read_text(encoding="utf-8")
    )
    seeds = [
        json.loads(line)
        for line in (DATASET / "seed_templates.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]

    assert manifest["dataset_version"] == "rwkv-lh.action-state-tuning-seed.v1"
    assert manifest["training_ready"] is False
    assert manifest["artifact_kind"] == "synthesis_seed"
    assert manifest["seed_count"] == len(seeds) == 20
    assert manifest["minimum_recommended_expansions"] == sum(
        item["minimum_expansions"] for item in seeds
    )
    assert manifest["validation"]["holdout_request_count"] == 210
    assert manifest["validation"]["exact_overlap_count"] == 0
    assert manifest["validation"]["maximum_blueprint_holdout_similarity"] < 0.75
    assert manifest["validation"]["similarity_version"] == (
        "utf8-byte-ngram-cosine.v1"
    )
    assert all(
        _sha256(ROOT / path) == value["sha256"]
        for path, value in manifest["holdout_files"].items()
    )
    assert all(
        _sha256(
            ROOT / path
            if path.startswith("scripts/")
            else DATASET / path
        )
        == value["sha256"]
        for path, value in manifest["files"].items()
    )

    definitions = contracts["definitions"]
    names = {item["name"] for item in definitions}
    assert contracts["tool_disclosure_mode"] == "progressive"
    assert contracts["selector_operation"] == "select_tool"
    assert contracts["definition_count"] == len(definitions) == 23
    assert {"read_file", "read_json", "web_search", "connector_lookup"} <= names
    assert {"calculator", "date_diff", "current_time", "final_answer"} <= names
    assert manifest["tool_contract_digest"] == hashlib.sha256(
        canonical_json(definitions).encode("utf-8")
    ).hexdigest()

    identifiers = {item["seed_id"] for item in seeds}
    assert len(identifiers) == len(seeds)
    for seed in seeds:
        assert seed["schema_version"] == (
            "rwkv-lh.action-state-tuning-seed-template.v1"
        )
        assert seed["lane"] == "rwkv_action"
        assert seed["positive_source"] == "synthesized_then_controller_verified"
        assert seed["negative_use"] == "filter_or_preference_only_never_positive"
        assert seed["target_turns"]
        for turn in seed["target_turns"]:
            operation = turn["target_operation"]
            if operation.startswith("${"):
                continue
            assert operation in names
            assert turn["selector_target"] == canonical_json(
                {"function": "select_tool", "params": {"name": operation}}
            )

    for identifier in ("ST-ACT-013", "ST-ACT-014"):
        privacy = next(item for item in seeds if item["seed_id"] == identifier)
        assert any(
            turn["target_operation"] == "web_search"
            for turn in privacy["target_turns"]
        )
        rejection = next(
            event
            for event in privacy["controller_event_blueprints"]
            if event.get("error_type") == "network_policy_rejected"
        )
        assert rejection["backend_execution_count"] == 0
