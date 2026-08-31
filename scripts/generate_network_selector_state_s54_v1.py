#!/usr/bin/env python3
"""Build the balanced request-last S54 Selector state-tuning dataset."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from rwkv_lh.exact_tool_selector.compact_protocol_v4 import (
    COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
    render_compact_selector_bootstrap,
    render_compact_selector_step,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
    NetworkSelectorProgress,
)
from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path("/home/chase/GitHub/RWKV-LH")
EXPERIMENT = (
    ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828"
)
PREREGISTRATION = (
    EXPERIMENT / "SEL_2P9_S53_EXE_G3_MULTISTAGE_DUAL_STATE_PREREGISTRATION.md"
)
AMENDMENT = EXPERIMENT / "SEL_2P9_S54_STATE_TUNING_CTX2496_AMENDMENT.md"
S53 = ROOT / "data/datasets/rwkv_lh_network_selector_multistage_s53_v1"
S52 = ROOT / "data/datasets/rwkv_lh_network_selector_request_last_s52_v1"
S30 = ROOT / "data/datasets/rwkv_lh_network_selector_true_trajectory_s30_v1"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_state_s54_v1"

VERSION = "rwkv-lh.network-selector.state-s54-request-last-2k.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-state-tuning-row.s54.v1"
TARGET_PREFIX = "\nSelectorLabelV4: "
CTX_LEN = 2496
SEED = 1054

FROZEN = {
    PREREGISTRATION: "503a063fc79f8757b96ea1a7f1dd3458de157b4b494d40b0dd633c5d2d59d91b",
    AMENDMENT: "be67aaf12572ae54e7495c54ebe436fc292664b0b5a59a123d8b03815026a215",
    S53 / "cases.jsonl": "bd3701c925717eb1d9f75d439c7fbb8b75a4905cc0099e348fa5314b98d1efde",
    S53 / "manifest.json": "532e1d1f6e5bc18bb2da15a7b39b57d03372b216a4228beacdf22ca573ea2fee",
    S52 / "cases.jsonl": "1cb1a1b2597a16c63b92753e402529239d4a765698964e0102640bf70dab7faf",
    S52 / "manifest.json": "79c56635778886e891d0f271ade9320d5d214bdfd4461b8f0adf7232d5ee1ff1",
    S30 / "cases.jsonl": "5b4225389787ba2c55e4f6dc9aace19c9a89d6d35bccf6793e8218be9a002305",
    S30 / "manifest.json": "4ccf7e6868d024815144cbf7b184bf127efcd7c7fd9037b43cd8ebf06ec6a996",
}

SOURCE_CAPS = {
    "train": {"s53": 20, "s52": 10},
    "dev": {"s53": 4, "s52": 2},
}
LANGUAGE_QUOTAS = {"train": 40, "dev": 10}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )


def selector_input(value: dict[str, Any]) -> NetworkSelectorInput:
    progress = dict(value["progress"])
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


def v4_from_s30(row: dict[str, Any]) -> str:
    current = selector_input(dict(row["selector_input"]))
    bootstrap = render_compact_selector_bootstrap(current)
    history = [
        render_compact_selector_step(selector_input(dict(value)))
        for value in row["history_selector_inputs"]
    ]
    step = render_compact_selector_step(current)
    return bootstrap + "".join("\n" + item for item in [*history, step])


def candidate_rows() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for source_name, root in (("s53", S53), ("s52", S52)):
        for row in read_jsonl(root / "cases.jsonl"):
            if row["split"] not in {"train", "dev"}:
                continue
            result.append(
                {
                    "source": source_name,
                    "source_sample_id": str(row["sample_id"]),
                    "source_family_id": (
                        f"{source_name}:"
                        + str(row.get("source_id") or row["trajectory_id"])
                    ),
                    "split": str(row["split"]),
                    "label": str(row["label"]),
                    "language": str(row["language"]),
                    "prompt": str(row["rendered_input"]),
                    "stage_group": str(row["stage_group"]),
                    "trajectory_position": int(row["trajectory_position"]),
                }
            )
    for row in read_jsonl(S30 / "cases.jsonl"):
        if row["split"] not in {"train", "dev"}:
            continue
        result.append(
            {
                "source": "s30_v4_rerender",
                "source_sample_id": str(row["sample_id"]),
                "source_family_id": "s30:" + str(row["semantic_family_id"]),
                "split": str(row["split"]),
                "label": str(row["label"]),
                "language": str(row["language"]),
                "prompt": v4_from_s30(row),
                "stage_group": str(row["stage_group"]),
                "trajectory_position": int(row["decision_index"]),
            }
        )
    return result


def select_balanced(candidates: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in candidates:
        grouped[(row["split"], row["label"], row["language"], row["source"])].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda item: str(item["source_sample_id"]))

    result: dict[str, list[dict[str, Any]]] = {"train": [], "dev": []}
    for split in ("train", "dev"):
        quota = LANGUAGE_QUOTAS[split]
        caps = SOURCE_CAPS[split]
        for label in NETWORK_EXACT_TOOL_LABELS:
            for language in ("en", "zh"):
                chosen: list[dict[str, Any]] = []
                for source in ("s53", "s52"):
                    chosen.extend(
                        grouped[(split, label, language, source)][: caps[source]]
                    )
                remaining = quota - len(chosen)
                if remaining < 0:
                    raise RuntimeError("S54 source caps exceed language quota")
                chosen.extend(
                    grouped[(split, label, language, "s30_v4_rerender")][
                        :remaining
                    ]
                )
                if len(chosen) != quota:
                    raise RuntimeError(
                        f"S54 quota unavailable: {split}:{label}:{language}:"
                        f"{len(chosen)}/{quota}"
                    )
                result[split].extend(chosen)
    return result


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S54 dataset")
    for path, expected in FROZEN.items():
        actual = sha256_file(path) if path.is_file() else "missing"
        if actual != expected:
            raise RuntimeError(f"S54 frozen source changed: {path}: {actual}")

    tokenizer = RWKVTokenizer()
    selected = select_balanced(candidate_rows())
    exports: dict[str, list[dict[str, Any]]] = {"train": [], "dev": []}
    prompt_digests: set[str] = set()
    for split in ("train", "dev"):
        for index, source in enumerate(selected[split]):
            label = str(source["label"])
            prompt = str(source["prompt"])
            if not prompt.endswith(str(json.dumps(json.loads(prompt.rsplit("SelectorStepV4: ", 1)[1]), ensure_ascii=False, sort_keys=False, separators=(",", ":")))):
                # The exact renderer suffix is validated below; this branch only
                # prevents an unparseable continuation from becoming training data.
                raise RuntimeError("S54 prompt does not end in one V4 step")
            final_payload = json.loads(prompt.rsplit("SelectorStepV4: ", 1)[1])
            if list(final_payload)[-1] != "stage_objective":
                raise RuntimeError("S54 current question is not last")
            target = TARGET_PREFIX + label
            prompt_tokens = tokenizer.encode(prompt)
            target_tokens = tokenizer.encode(target)
            text_tokens = tokenizer.encode(prompt + target)
            if text_tokens != prompt_tokens + target_tokens:
                raise RuntimeError("S54 target boundary is not additive")
            if 1 + len(text_tokens) > CTX_LEN + 1:
                raise RuntimeError(
                    f"S54 target truncation: {source['source_sample_id']}:"
                    f"{1 + len(text_tokens)}"
                )
            digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            if digest in prompt_digests:
                raise RuntimeError("S54 duplicate prompt")
            prompt_digests.add(digest)
            exports[split].append(
                {
                    "schema_version": ROW_SCHEMA,
                    "dataset_version": VERSION,
                    "sample_id": f"S54-{split.upper()}-{index:04d}",
                    "source": source["source"],
                    "source_sample_id": source["source_sample_id"],
                    "source_family_id": source["source_family_id"],
                    "split": split,
                    "label": label,
                    "language": source["language"],
                    "stage_group": source["stage_group"],
                    "trajectory_position": source["trajectory_position"],
                    "prompt": prompt,
                    "prompt_sha256": digest,
                    "target": target,
                    "text": prompt + target,
                    "prompt_tokens_including_bos": 1 + len(prompt_tokens),
                    "target_tokens": len(target_tokens),
                    "text_tokens_including_bos": 1 + len(text_tokens),
                    "loss_mask": "target_suffix",
                    "jsonl_bos_token_id": 0,
                    "persistent_history_replayed": True,
                    "request_last": True,
                    "contains_parameter_schemas": False,
                    "contains_full_tool_results": False,
                    "contains_executor_text": False,
                    "generated_rwkv_text": False,
                }
            )

    expected_counts = {"train": 2000, "dev": 500}
    if {split: len(rows) for split, rows in exports.items()} != expected_counts:
        raise RuntimeError("S54 split counts changed")
    for split, per_class in (("train", 80), ("dev", 20)):
        if Counter(row["label"] for row in exports[split]) != Counter(
            {label: per_class for label in NETWORK_EXACT_TOOL_LABELS}
        ):
            raise RuntimeError(f"S54 class balance changed: {split}")
        per_language = len(exports[split]) // 2
        if Counter(row["language"] for row in exports[split]) != Counter(
            {"en": per_language, "zh": per_language}
        ):
            raise RuntimeError(f"S54 language balance changed: {split}")
    train_families = {row["source_family_id"] for row in exports["train"]}
    dev_families = {row["source_family_id"] for row in exports["dev"]}
    if train_families & dev_families:
        raise RuntimeError("S54 train/dev families overlap")

    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_s54.", dir=OUTPUT.parent))
    paths = {
        split: staging / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        for split in exports
    }
    for split, path in paths.items():
        write_jsonl(path, exports[split])
    all_rows = [row for rows in exports.values() for row in rows]
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": "balanced V4 request-last multistage 2.9B Selector state tuning",
        "architecture": "current-direct-LongHorizonModel-dual-state",
        "sources": [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": digest,
                "use": "balanced train/dev prompt selection or registered protocol",
            }
            for path, digest in FROZEN.items()
        ],
        "selection": {
            "language_quota_per_class": LANGUAGE_QUOTAS,
            "source_caps_per_class_language": SOURCE_CAPS,
            "fallback_source": "S30 semantic inputs rerendered byte-exact with V4",
        },
        "counts": expected_counts,
        "label_counts": {
            split: dict(sorted(Counter(row["label"] for row in rows).items()))
            for split, rows in exports.items()
        },
        "language_counts": {
            split: dict(sorted(Counter(row["language"] for row in rows).items()))
            for split, rows in exports.items()
        },
        "source_counts": {
            split: dict(sorted(Counter(row["source"] for row in rows).items()))
            for split, rows in exports.items()
        },
        "target_prefix": TARGET_PREFIX,
        "training_contract": {
            "loss_mask": "target_suffix",
            "jsonl_bos_token_id": 0,
            "ctx_len": CTX_LEN,
            "epoch_steps": 2000,
            "epoch_count": 1,
            "step_save": 500,
            "seed": SEED,
            "persistent_history_replayed": True,
            "parent_state": "zero",
            "physical_gpu": 0,
        },
        "validation": {
            "exact_prompt_duplicates": 0,
            "train_dev_source_family_overlap": 0,
            "all_25_labels_balanced": True,
            "languages_balanced": True,
            "minimum_prompt_tokens_including_bos": min(
                row["prompt_tokens_including_bos"] for row in all_rows
            ),
            "maximum_prompt_tokens_including_bos": max(
                row["prompt_tokens_including_bos"] for row in all_rows
            ),
            "maximum_text_tokens_including_bos": max(
                row["text_tokens_including_bos"] for row in all_rows
            ),
            "target_truncation_count": 0,
            "target_boundary_additive": True,
            "current_question_last": True,
            "generated_rwkv_text_count": 0,
            "parameter_schema_count": 0,
            "full_tool_result_count": 0,
            "executor_text_count": 0,
        },
        "optimizer_rows": "train_only",
        "dev_optimizer_use": False,
        "generation": {
            "script": str(Path(__file__).resolve().relative_to(ROOT)),
            "script_sha256": sha256_file(Path(__file__).resolve()),
        },
        "files": {
            path.name: {"rows": len(exports[split]), "sha256": sha256_file(path)}
            for split, path in paths.items()
        },
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (staging / "README.md").write_text(
        "# S54 request-last Selector state tuning\n\n"
        "Exactly 2,000 train and 500 development prompts are balanced across all "
        "25 labels and both languages. The target-only loss teaches an independent "
        "initial Selector state; no RWKV output was generated to create labels.\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "s54_dataset_finalized",
                "train": len(exports["train"]),
                "dev": len(exports["dev"]),
                "train_sha256": sha256_file(
                    OUTPUT / "rwkv_state_tuning.train.requires_target_suffix.jsonl"
                ),
                "dev_sha256": sha256_file(
                    OUTPUT / "rwkv_state_tuning.dev.requires_target_suffix.jsonl"
                ),
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
