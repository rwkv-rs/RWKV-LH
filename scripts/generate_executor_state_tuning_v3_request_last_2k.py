#!/usr/bin/env python3
"""Derive the closed request-last Executor V3 dataset from frozen V2 rows.

This is a byte-layout transformation only. Targets, splits, source provenance,
and similarity projections remain unchanged. No model is called.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from rwkv_lh.model_io import (
    INDEPENDENT_EXECUTOR_REQUEST_LAST_PROTOCOL,
    render_independent_executor_bootstrap,
    render_independent_executor_tool_disclosure,
)
from rwkv_lh.token_budget import get_token_count


ROOT = Path("/home/chase/GitHub/RWKV-LH")
SOURCE = ROOT / "data/datasets/rwkv_lh_executor_state_tuning_v2_2k"
OUTPUT = ROOT / "data/datasets/rwkv_lh_executor_state_tuning_v3_request_last_2k"
DATASET_VERSION = "rwkv-lh.executor-state-tuning.v3-request-last-2k"
SCHEMA_VERSION = "rwkv-lh.executor-stage-sft.v3"
STAGE_FILES = ("stage_sft.train.jsonl", "stage_sft.dev.jsonl")
TRAINING_FILES = (
    "rwkv_state_tuning.train.requires_target_suffix.jsonl",
    "rwkv_state_tuning.dev.requires_target_suffix.jsonl",
)

STATE_MARKER = "User: Executor task state: "
WAIT_MARKER = "\nWait for the controller-selected operation contract."
CONTRACT_MARKER = "\n\nUser: Controller-selected operation contract: "
RETURN_MARKER = "\nReturn only one direct JSON function call"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not an object")
            rows.append(value)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )


def parse_v2_prompt(prompt: str) -> tuple[dict[str, Any], dict[str, Any]]:
    state_start = prompt.index(STATE_MARKER) + len(STATE_MARKER)
    state_end = prompt.index(WAIT_MARKER, state_start)
    assignment = json.loads(prompt[state_start:state_end])
    contract_start = prompt.index(CONTRACT_MARKER, state_end) + len(CONTRACT_MARKER)
    contract_end = prompt.index(RETURN_MARKER, contract_start)
    contract = json.loads(prompt[contract_start:contract_end])
    if not isinstance(assignment, dict) or not isinstance(contract, dict):
        raise ValueError("V2 prompt state and contract must be JSON objects")
    return assignment, contract


def transform_prompt(row: dict[str, Any]) -> str:
    assignment, contract = parse_v2_prompt(str(row["prompt"]))
    requirement = assignment.pop("immutable_request", None)
    if not isinstance(requirement, str) or not requirement.strip():
        raise ValueError(f"{row['sample_id']} has no authoritative Executor request")
    assignment["protocol"] = INDEPENDENT_EXECUTOR_REQUEST_LAST_PROTOCOL
    selected_operation = str(contract.get("selected_operation") or "")
    definition = contract.get("selected_tool_contract")
    if selected_operation != row["selected_operation"] or not isinstance(
        definition, dict
    ):
        raise ValueError(f"{row['sample_id']} selected contract changed")
    prompt = render_independent_executor_bootstrap(
        json.dumps(assignment, ensure_ascii=False, sort_keys=False)
    ) + render_independent_executor_tool_disclosure(definition, str(requirement))
    tail = prompt.rsplit("\n\nUser: Executor continuation input: ", 1)[1]
    payload_text, suffix = tail.split("\n\nAssistant:", 1)
    payload = json.loads(payload_text)
    if list(payload)[-1] != "current_requirement":
        raise ValueError(f"{row['sample_id']} requirement is not the final field")
    if payload["current_requirement"] != requirement:
        raise ValueError(f"{row['sample_id']} requirement bytes changed")
    if suffix != " ```json\n":
        raise ValueError(f"{row['sample_id']} continuation anchor changed")
    if "immutable_request" in assignment:
        raise ValueError(f"{row['sample_id']} duplicated the request in bootstrap")
    return prompt


def transform_stage_rows(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for source in source_rows:
        row = dict(source)
        prompt = transform_prompt(row)
        target = str(row["target"])
        row.update(
            {
                "schema_version": SCHEMA_VERSION,
                "dataset_version": DATASET_VERSION,
                "prompt": prompt,
                "prompt_sha256": sha256_bytes(prompt.encode("utf-8")),
                "prompt_tokens_local": get_token_count(prompt),
                "text": prompt + target,
                "text_sha256": sha256_bytes((prompt + target).encode("utf-8")),
                "request_delivery": "single_closed_json_final_field",
                "request_last_protocol": INDEPENDENT_EXECUTOR_REQUEST_LAST_PROTOCOL,
                "selector_task_request_matches_executor_requirement": (
                    dict(row.get("similarity_projection") or {}).get("task_request")
                    == parse_v2_prompt(str(source["prompt"]))[0].get(
                        "immutable_request"
                    )
                ),
            }
        )
        result.append(row)
    return result


def transform_training_rows(
    source_rows: list[dict[str, Any]],
    stage_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if len(source_rows) != len(stage_rows):
        raise ValueError("training and stage row counts differ")
    result: list[dict[str, Any]] = []
    for source, stage in zip(source_rows, stage_rows, strict=True):
        if source["target"] != stage["target"]:
            raise ValueError("training target order differs from stage rows")
        result.append(
            {
                "prompt": stage["prompt"],
                "target": stage["target"],
                "text": stage["text"],
                "tier": source["tier"],
            }
        )
    return result


def main() -> int:
    if OUTPUT.exists():
        raise SystemExit(f"refusing to overwrite {OUTPUT}")
    OUTPUT.mkdir(parents=True)
    transformed_by_split: dict[str, list[dict[str, Any]]] = {}
    source_hashes: dict[str, str] = {}
    for name in STAGE_FILES:
        source_path = SOURCE / name
        source_hashes[name] = sha256_file(source_path)
        rows = transform_stage_rows(read_jsonl(source_path))
        write_jsonl(OUTPUT / name, rows)
        transformed_by_split[name] = rows
    for name, stage_name in zip(TRAINING_FILES, STAGE_FILES, strict=True):
        source_path = SOURCE / name
        source_hashes[name] = sha256_file(source_path)
        rows = transform_training_rows(
            read_jsonl(source_path),
            transformed_by_split[stage_name],
        )
        write_jsonl(OUTPUT / name, rows)

    files: dict[str, dict[str, Any]] = {}
    for path in sorted(OUTPUT.glob("*.jsonl")):
        files[path.name] = {
            "bytes": path.stat().st_size,
            "rows": sum(1 for _ in path.open(encoding="utf-8")),
            "sha256": sha256_file(path),
        }
    all_stage = [
        *transformed_by_split["stage_sft.train.jsonl"],
        *transformed_by_split["stage_sft.dev.jsonl"],
    ]
    manifest = {
        "schema_version": "rwkv-lh.executor-dataset-manifest.v3",
        "dataset_version": DATASET_VERSION,
        "purpose": (
            "Closed request-last input ablation and optional 13.3B Executor state tuning"
        ),
        "generation": "scripts/generate_executor_state_tuning_v3_request_last_2k.py",
        "model_calls": 0,
        "generated_rwkv_text": False,
        "source_dataset": str(SOURCE.relative_to(ROOT)),
        "source_manifest_sha256": sha256_file(SOURCE / "manifest.json"),
        "source_files": source_hashes,
        "executor_protocol": INDEPENDENT_EXECUTOR_REQUEST_LAST_PROTOCOL,
        "request_delivery": "single_closed_json_final_field",
        "target_bytes_changed": False,
        "split_membership_changed": False,
        "similarity_projection_changed": False,
        "counts": {
            "train": len(transformed_by_split["stage_sft.train.jsonl"]),
            "dev": len(transformed_by_split["stage_sft.dev.jsonl"]),
        },
        "prompt_tokens_local": {
            "min": min(int(row["prompt_tokens_local"]) for row in all_stage),
            "max": max(int(row["prompt_tokens_local"]) for row in all_stage),
        },
        "files": files,
        "training_ready": False,
        "training_blocker": "authoritative remote tokenizer/target-mask validation",
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (OUTPUT / "README.md").write_text(
        "# Executor V3 request-last 2K\n\n"
        "This dataset preserves every V2 target and split while relocating the exact "
        "request into the final field of one closed Executor continuation JSON object. "
        "The bootstrap contains no duplicate request. No model generated any label.\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
