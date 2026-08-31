#!/usr/bin/env python3
"""Generate S65 by removing the split-specific focus-lexicon shortcut."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping

from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path("/home/chase/GitHub/RWKV-LH")
BASE = ROOT / "scripts/generate_network_selector_transaction_continuation_s61_v1.py"
PREREGISTRATION = ROOT / "data/experiments/NETWORK_SELECTOR_LEXICON_DIVERSITY_S65_20260830/PREREGISTRATION.md"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_lexicon_diverse_s65_v1"

BASE_SHA256 = "59add9db322229b599b563f3d36184e79ac45be90ba290e812533bcec8c157e4"
PREREGISTRATION_SHA256 = "c3e52c0e6b3a0bfd6c1cecf1df1fa5eabb59051712768ac1c642feef0576102f"
DATASET_VERSION = "rwkv-lh.network-selector.lexicon-diverse-s65.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-lexicon-diverse-prefix.s65.v1"
STATE_ROW_SCHEMA = "rwkv-lh.network-selector-state-tuning-row.s65.v1"
SEED = 1065


TRAIN_LEXICONS = (
    {"root": "amber-forge", "subject": "otter bundle", "zh_subject": "琥珀锻造批次"},
    {"root": "birch-atelier", "subject": "ibis packet", "zh_subject": "桦木工坊批次"},
    {"root": "cobalt-depot", "subject": "marten crate", "zh_subject": "钴蓝仓站批次"},
    {"root": "dahlia-lab", "subject": "finch capsule", "zh_subject": "大丽花实验批次"},
    {"root": "ember-yard", "subject": "badger parcel", "zh_subject": "余烬场站批次"},
    {"root": "fir-studio", "subject": "heron docket", "zh_subject": "冷杉工作室批次"},
    {"root": "granite-bay", "subject": "pika bundle", "zh_subject": "花岗湾区批次"},
    {"root": "hazel-mill", "subject": "tern capsule", "zh_subject": "榛木工厂批次"},
    {"root": "ivory-bench", "subject": "lynx packet", "zh_subject": "象牙工台批次"},
    {"root": "juniper-hall", "subject": "rook parcel", "zh_subject": "杜松大厅批次"},
    {"root": "kelp-foundry", "subject": "seal crate", "zh_subject": "海藻铸造批次"},
    {"root": "lilac-dock", "subject": "wren bundle", "zh_subject": "丁香码头批次"},
    {"root": "maple-vault", "subject": "vole docket", "zh_subject": "枫木库房批次"},
    {"root": "nickel-loft", "subject": "kite capsule", "zh_subject": "镍色阁楼批次"},
    {"root": "opal-works", "subject": "yak packet", "zh_subject": "蛋白石工场批次"},
    {"root": "pine-hangar", "subject": "mink parcel", "zh_subject": "松木机库批次"},
)
DEV_LEXICONS = (
    {"root": "indigo-foundry", "subject": "tern packet", "zh_subject": "靛蓝铸造批次"},
    {"root": "russet-lab", "subject": "egret crate", "zh_subject": "赤褐实验批次"},
    {"root": "silver-yard", "subject": "stoat docket", "zh_subject": "银色场站批次"},
    {"root": "topaz-atelier", "subject": "gull bundle", "zh_subject": "黄玉工坊批次"},
    {"root": "umber-depot", "subject": "fox capsule", "zh_subject": "棕土仓站批次"},
    {"root": "violet-bay", "subject": "lark packet", "zh_subject": "紫罗兰湾批次"},
    {"root": "willow-mill", "subject": "hare parcel", "zh_subject": "柳木工厂批次"},
    {"root": "xenon-bench", "subject": "crane crate", "zh_subject": "氙光工台批次"},
)
TEST_LEXICONS = (
    {"root": "saffron-studio", "subject": "lynx parcel", "zh_subject": "藏红花工作室批次"},
    {"root": "yarrow-hall", "subject": "raven docket", "zh_subject": "蓍草大厅批次"},
    {"root": "zircon-dock", "subject": "puffin bundle", "zh_subject": "锆石码头批次"},
    {"root": "acacia-vault", "subject": "otter capsule", "zh_subject": "金合欢库房批次"},
    {"root": "bronze-works", "subject": "ibis packet", "zh_subject": "青铜工场批次"},
    {"root": "coral-hangar", "subject": "marten parcel", "zh_subject": "珊瑚机库批次"},
    {"root": "denim-loft", "subject": "finch crate", "zh_subject": "丹宁阁楼批次"},
    {"root": "elm-forge", "subject": "badger bundle", "zh_subject": "榆木锻造批次"},
)
LEXICONS = {"train": TRAIN_LEXICONS, "dev": DEV_LEXICONS, "test": TEST_LEXICONS}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_base() -> ModuleType:
    if sha256_file(BASE) != BASE_SHA256:
        raise RuntimeError("frozen S61 generator changed")
    spec = importlib.util.spec_from_file_location("rwkv_lh_s65_generator_base", BASE)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import frozen S61 generator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    original = module.stable_hex

    def s65_stable_hex(*parts: object) -> str:
        values = list(parts)
        if values and str(values[0]).startswith("S61"):
            values[0] = str(values[0]).replace("S61", "S65", 1)
        return original(*values)

    module.stable_hex = s65_stable_hex
    module.DATASET_VERSION = DATASET_VERSION
    module.ROW_SCHEMA = ROW_SCHEMA
    module.STATE_ROW_SCHEMA = STATE_ROW_SCHEMA
    module.SEED = SEED
    return module


def canonical_row(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(canonical_row(row) + "\n")


def normalize_identity(row: dict[str, Any]) -> dict[str, Any]:
    for key in ("sample_id", "trajectory_id", "source_family_id"):
        row[key] = str(row[key]).replace("S61", "S65").replace("s61", "s65")
    row["dataset_version"] = DATASET_VERSION
    row["schema_version"] = ROW_SCHEMA
    return row


def focus_rows(base: ModuleType) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {split: [] for split in base.SPLITS}
    for split in base.SPLITS:
        pool = LEXICONS[split]
        for index in range(base.FOCUS_COUNTS[split]):
            scenario_index = index % len(base.FOCUS_SCENARIOS)
            occurrence = index // len(base.FOCUS_SCENARIOS)
            lexicon = pool[(occurrence + 3 * scenario_index) % len(pool)]
            base.SPLIT_LEXICON[split] = dict(lexicon)
            row = normalize_identity(base.focus_row(split, index))
            row["lexicon_root"] = str(lexicon["root"])
            row["lexicon_pool"] = split
            result[split].append(row)
    return result


def normalize_retention(rows: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    for split_rows in rows.values():
        for row in split_rows:
            normalize_identity(row)
            row["lexicon_root"] = ""
            row["lexicon_pool"] = "retention"
    return rows


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S65 dataset")
    for path, expected in {BASE: BASE_SHA256, PREREGISTRATION: PREREGISTRATION_SHA256}.items():
        if not path.is_file() or sha256_file(path) != expected:
            raise RuntimeError(f"S65 frozen input changed: {path}")
    roots = {split: {str(value["root"]) for value in pool} for split, pool in LEXICONS.items()}
    for left_index, left in enumerate(("train", "dev", "test")):
        for right in ("train", "dev", "test")[left_index + 1 :]:
            if roots[left] & roots[right]:
                raise RuntimeError(f"S65 lexicon pools overlap: {left}/{right}")

    base = load_base()
    tokenizer = RWKVTokenizer()
    holdout_references, forbidden_paths, task_ids = base.ladder_contract()
    focus = focus_rows(base)
    for split, rows in focus.items():
        if Counter(row["language"] for row in rows) != Counter({"en": len(rows) // 2, "zh": len(rows) // 2}):
            raise RuntimeError(f"S65 focus language balance changed: {split}")
        scenario_roots: dict[str, set[str]] = {
            scenario: {str(row["lexicon_root"]) for row in rows if row["focus_scenario"] == scenario}
            for scenario in base.FOCUS_SCENARIOS
        }
        if any(len(value) != len(LEXICONS[split]) for value in scenario_roots.values()):
            raise RuntimeError(f"S65 scenario lexicon coverage changed: {split}/{scenario_roots}")
        for row in rows:
            if base.contains_holdout_literal(str(row["task_request"]), forbidden_paths=forbidden_paths, task_ids=task_ids):
                raise RuntimeError(f"S65 focus contains Ladder literal: {row['sample_id']}")
    retention = normalize_retention(
        base.select_retention(tokenizer, forbidden_paths=forbidden_paths, task_ids=task_ids)
    )
    rows_by_split = {split: focus[split] + retention[split] for split in base.SPLITS}
    expected_counts = {"train": 2000, "dev": 500, "test": 500}
    if {split: len(rows) for split, rows in rows_by_split.items()} != expected_counts:
        raise RuntimeError("S65 split counts changed")
    all_rows = [row for split in base.SPLITS for row in rows_by_split[split]]
    if len({str(row["sample_id"]) for row in all_rows}) != len(all_rows):
        raise RuntimeError("S65 sample ids are not unique")
    if len({str(row["rendered_input_sha256"]) for row in all_rows}) != len(all_rows):
        raise RuntimeError("S65 rendered prompts are not unique")
    role_fields = (
        "contains_parameter_schemas",
        "contains_full_tool_results",
        "contains_executor_text",
        "contains_planner_text",
        "generated_rwkv_text",
        "hidden_acceptance_used",
    )
    if any(bool(row[field]) for row in all_rows for field in role_fields):
        raise RuntimeError("S65 role purity changed")
    request_splits = {split: {str(row["task_request"]) for row in rows_by_split[split]} for split in base.SPLITS}
    family_splits = {split: {str(row["source_family_id"]) for row in rows_by_split[split]} for split in base.SPLITS}
    rendered_splits = {split: {str(row["rendered_input_sha256"]) for row in rows_by_split[split]} for split in base.SPLITS}
    for left_index, left in enumerate(base.SPLITS):
        for right in base.SPLITS[left_index + 1 :]:
            if request_splits[left] & request_splits[right]:
                raise RuntimeError(f"S65 request overlap: {left}/{right}")
            if family_splits[left] & family_splits[right]:
                raise RuntimeError(f"S65 source-family overlap: {left}/{right}")
            if rendered_splits[left] & rendered_splits[right]:
                raise RuntimeError(f"S65 rendered overlap: {left}/{right}")

    reference_grams = [(identity, base.byte_ngrams(request)) for identity, request in holdout_references]
    maximum_similarity: dict[str, Any] = {"score": -1.0, "sample_id": "", "holdout_id": ""}
    cache: dict[str, Counter[bytes]] = {}
    for row in all_rows:
        request = str(row["task_request"])
        grams = cache.setdefault(request, base.byte_ngrams(request))
        for holdout_id, reference in reference_grams:
            score = base.cosine(grams, reference)
            if score > float(maximum_similarity["score"]):
                maximum_similarity = {"score": score, "sample_id": row["sample_id"], "holdout_id": holdout_id}
    if float(maximum_similarity["score"]) >= 0.95:
        raise RuntimeError(f"S65 Ladder similarity gate failed: {maximum_similarity}")

    state_rows, token_stats = base.validate_and_export_state_rows(tokenizer, rows_by_split)
    for split, rows in state_rows.items():
        for index, row in enumerate(rows):
            row["sample_id"] = f"S65-STATE-{split.upper()}-{index:04d}"
            row["dataset_version"] = DATASET_VERSION
            row["schema_version"] = STATE_ROW_SCHEMA
    staging = Path(tempfile.mkdtemp(prefix=f".{OUTPUT.name}.", dir=OUTPUT.parent))
    cases_path = staging / "cases.jsonl"
    write_jsonl(cases_path, all_rows)
    state_paths = {
        split: staging / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        for split in ("train", "dev")
    }
    for split, path in state_paths.items():
        write_jsonl(path, state_rows[split])
    manifest = {
        "schema_version": "rwkv-lh.network-selector-lexicon-diverse-manifest.s65.v1",
        "dataset_version": DATASET_VERSION,
        "purpose": "remove split-specific lexicon shortcuts while preserving S61 mechanical trajectories",
        "counts": expected_counts,
        "cohort_counts": {split: dict(sorted(Counter(row["cohort"] for row in rows).items())) for split, rows in rows_by_split.items()},
        "label_counts": {split: dict(sorted(Counter(row["label"] for row in rows).items())) for split, rows in rows_by_split.items()},
        "focus_label_counts": {split: dict(sorted(Counter(row["label"] for row in focus[split]).items())) for split in base.SPLITS},
        "focus_scenario_counts": {split: dict(sorted(Counter(row["focus_scenario"] for row in focus[split]).items())) for split in base.SPLITS},
        "language_counts": {split: dict(sorted(Counter(row["language"] for row in rows).items())) for split, rows in rows_by_split.items()},
        "lexicon_diversity": {
            "assignment": "(scenario_occurrence + 3 * scenario_index) mod pool_size",
            "pool_sizes": {split: len(pool) for split, pool in LEXICONS.items()},
            "pool_roots": {split: sorted(values) for split, values in roots.items()},
            "pool_intersection_count": 0,
            "distinct_roots_per_scenario": {split: len(LEXICONS[split]) for split in base.SPLITS},
            "single_split_root_shortcut": False,
        },
        "retention": {
            "source": str(base.S60.relative_to(ROOT)),
            "cases_sha256": base.FROZEN[base.S60 / "cases.jsonl"],
            "manifest_sha256": base.FROZEN[base.S60 / "manifest.json"],
            "per_label_language": base.RETENTION_PER_LABEL_LANGUAGE,
            "labels_changed": False,
        },
        "protocol": {
            "schema_version": base.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
            "renderer": str(base.RENDERER.relative_to(ROOT)),
            "renderer_sha256": base.FROZEN[base.RENDERER],
            "complete_requirement_final_semantic_field": True,
            "literal_requirement_byte_tail": True,
            "persistent_history_replayed": True,
            "projection_version": base.SELECTOR_STAGE_PROJECTION_VERSION,
        },
        "state_training_contract": {
            "train_rows": 2000,
            "dev_rows": 500,
            "dev_optimizer_use": False,
            "loss_mask": "target_suffix",
            "target_prefix": base.TARGET_PREFIX,
            "jsonl_bos_token_id": 0,
            "ctx_len": base.CTX_LEN,
            "seed": SEED,
            "physical_gpu": 0,
            **token_stats,
            "target_boundary_additive": True,
            "target_truncation_count": 0,
        },
        "holdout": {
            "tasks_path": str((base.LADDER / "tasks.json").relative_to(ROOT)),
            "tasks_sha256": base.FROZEN[base.LADDER / "tasks.json"],
            "acceptance_path": str((base.LADDER / "acceptance.json").relative_to(ROOT)),
            "acceptance_sha256": base.FROZEN[base.LADDER / "acceptance.json"],
            "optimizer_use": False,
            "candidate_selection_use": False,
            "similarity_algorithm": "utf8-byte-5gram-cosine.v1",
            "threshold_exclusive": 0.95,
            "maximum_similarity": maximum_similarity,
        },
        "split_integrity": {"exact_request_overlap": 0, "source_family_overlap": 0, "rendered_input_overlap": 0},
        "role_purity": {
            "parameter_schema_count": 0,
            "full_tool_result_count": 0,
            "executor_text_count": 0,
            "planner_text_count": 0,
            "generated_rwkv_text_count": 0,
            "hidden_acceptance_count": 0,
            "sampling_invoked": False,
            "raw_rwkv_output_modified": False,
        },
        "preregistration": {"path": str(PREREGISTRATION.relative_to(ROOT)), "sha256": PREREGISTRATION_SHA256},
        "generator": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
            "frozen_base_path": str(BASE.relative_to(ROOT)),
            "frozen_base_sha256": BASE_SHA256,
        },
        "files": {
            "cases.jsonl": {"rows": len(all_rows), "bytes": cases_path.stat().st_size, "sha256": sha256_file(cases_path)},
            **{
                path.name: {"rows": len(state_rows[split]), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
                for split, path in state_paths.items()
            },
        },
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (staging / "README.md").write_text(
        "# S65 lexicon-diverse Selector corpus\n\n"
        "2,000 train, 500 dev, and 500 locked-test V7 prefixes. Focus scenarios use "
        "16/8/8 disjoint lexicon pools so one root cannot identify a split. Labels are "
        "mechanical; no RWKV text was generated.\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "s65_dataset_finalized",
                "counts": expected_counts,
                "pool_sizes": manifest["lexicon_diversity"]["pool_sizes"],
                "maximum_ladder_similarity": maximum_similarity,
                "cases_sha256": sha256_file(OUTPUT / "cases.jsonl"),
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
