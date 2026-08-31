#!/usr/bin/env python3
"""Generate the preregistered S68 semantic-boundary Selector corpus."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path("/home/chase/GitHub/RWKV-LH")
EXPERIMENT = (
    ROOT / "data/experiments/NETWORK_SELECTOR_SEMANTIC_BOUNDARY_S68_V1_20260831"
)
PREREGISTRATION = EXPERIMENT / "PREREGISTRATION.md"
BASE_GENERATOR = ROOT / "scripts/generate_network_selector_v2_contract_s67_v1.py"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_semantic_boundary_s68_v1"
S67_DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_v2_contract_s67_v1"
FUSION_RESULT = (
    ROOT
    / "data/experiments/NETWORK_SELECTOR_S67_GLOBAL_TAIL_FUSION_ABLATION_V1_20260831"
    / "run_global_tail_fusion/ABLATION_RESULT.json"
)
DATA_ANALYSIS = (
    ROOT
    / "data/experiments/NETWORK_SELECTOR_S67_GLOBAL_TAIL_FUSION_ABLATION_V1_20260831"
    / "DATA_DIVERSITY_ANALYSIS.md"
)

PREREGISTRATION_SHA256 = "4e5f0a29560fbce4ab60509e14aaf81dad380b5c0e1f7ba7713758d14779d08b"
BASE_GENERATOR_SHA256 = "ed3d929824ffdc6fff7ad0af1466fa09f1ac5580ec3d91d92a5abb7583c65987"
S67_CASES_SHA256 = "0401966e7633c77cb3950019857324f23a625cc9a290b13c80804001400fd859"
S67_MANIFEST_SHA256 = "0707bd65c64a4a96dd484085abc79c8b5ec199426bb777408ef2671e6be8ea46"
FUSION_RESULT_SHA256 = "aa94aa036254f8b7e7953b715d4f924ecdd5b44c0a40cb10f653aa5ada73c678"
DATA_ANALYSIS_SHA256 = "82c577bef82aa230d8ba40d8cba6def400281b5a8d27f4f800dbaec362703efa"

DATASET_VERSION = "rwkv-lh.network-selector-semantic-boundary-s68.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-semantic-boundary-prefix.s68.v1"
STATE_ROW_SCHEMA = "rwkv-lh.network-selector-state-tuning-row.s68.v1"
FOCUS_LABELS = (
    "append_file",
    "write_file",
    "replace_text",
    "copy_file",
    "move_file",
)
VARIANTS_BY_SPLIT = {
    "train": (0, 1, 2, 3, 4),
    "dev": (5, 6),
    "test": (7, 8),
}

FOCUS_EN: dict[str, tuple[str, ...]] = {
    "append_file": (
        "append {new_marker} after the existing bytes in {text_path} without overwriting prior content",
        "add one trailing line {new_marker} to {text_path} and retain everything already there",
        "extend {text_path} at EOF with {new_marker}; do not replace the file",
        "place {new_marker} at the end of {text_path} while preserving its current prefix",
        "write only the additional suffix {new_marker} onto {text_path}, leaving old bytes intact",
        "keep the current contents of {text_path} and tack {new_marker} onto the tail",
        "grow {text_path} by one final record {new_marker}, with no full-file rewrite",
        "concatenate {new_marker} after all existing data in {text_path}",
        "retain the file body and add {new_marker} as new terminal text in {text_path}",
    ),
    "write_file": (
        "create or completely overwrite {text_path} with the requested full UTF-8 document",
        "materialize the entire text artifact at {text_path}, replacing any previous file body",
        "write a complete new non-JSON file at {text_path}, not merely a suffix or fragment",
        "atomically set the whole contents of {text_path} to the requested text",
        "produce the full source file {text_path} from start to finish and replace an old version",
        "store the complete requested text as {text_path}, overwriting the file as one value",
        "rebuild all bytes of {text_path} as the supplied full text artifact",
        "replace the entire file body at {text_path} with one complete UTF-8 value",
        "create {text_path} as a whole text file rather than appending to existing bytes",
    ),
    "replace_text": (
        "change exactly one {old_marker} occurrence to {new_marker} inside {text_path} and preserve all other text",
        "substitute the declared old fragment {old_marker} with {new_marker} in {text_path} without rewriting unrelated bytes",
        "edit only the matching token {old_marker} in {text_path}, replacing it by {new_marker}",
        "perform one in-file exact replacement from {old_marker} to {new_marker} within {text_path}",
        "keep the file intact except for swapping one precise {old_marker} span for {new_marker} in {text_path}",
        "locate a single literal {old_marker} in {text_path} and revise only that span to {new_marker}",
        "preserve the surrounding document while replacing the specified {old_marker} text with {new_marker} in {text_path}",
        "make a targeted text substitution in {text_path}: {old_marker} becomes {new_marker}, once",
        "alter only one exact fragment of {text_path} from {old_marker} to {new_marker}; leave the rest unchanged",
    ),
    "copy_file": (
        "duplicate every byte of {source_path} at {dest_path} and keep the original source path",
        "create {dest_path} as an identical copy of {source_path} without removing the source",
        "clone the scoped file {source_path} into {dest_path}; both paths must remain afterward",
        "copy {source_path} to {dest_path} with exact contents while retaining {source_path}",
        "materialize a second file at {dest_path} from {source_path}, leaving the first file in place",
        "preserve {source_path} and reproduce its bytes unchanged at {dest_path}",
        "make an additional identical file at {dest_path} from {source_path}; do not move it",
        "replicate {source_path} at {dest_path} so the source continues to exist",
        "produce a byte-for-byte duplicate of {source_path} in {dest_path}, keeping both files",
    ),
    "move_file": (
        "relocate {source_path} to {dest_path} so the old source path no longer exists",
        "move or rename {source_path} as {dest_path}, preserving bytes but removing the original path",
        "transfer the existing file from {source_path} into {dest_path} without leaving a source copy",
        "rename {source_path} to {dest_path}; only the destination must remain",
        "place the file at {dest_path} and delete its former location {source_path} as part of the move",
        "migrate {source_path} into {dest_path}, retaining contents but not the old pathname",
        "change the file location from {source_path} to {dest_path} rather than duplicating it",
        "relocate the single existing file to {dest_path} and make {source_path} absent",
        "move the exact bytes from {source_path} to {dest_path}, leaving no file at the origin",
    ),
}

FOCUS_ZH: dict[str, tuple[str, ...]] = {
    "append_file": (
        "在 {text_path} 现有字节之后追加 {new_marker}，不得覆盖原内容",
        "给 {text_path} 增加末尾一行 {new_marker}，并保留文件里已有的一切",
        "在 {text_path} 的结尾续写 {new_marker}，不要重建整个文件",
        "把 {new_marker} 接到 {text_path} 尾部，同时保持当前前缀不变",
        "只向 {text_path} 写入新增后缀 {new_marker}，原有字节必须完整保留",
        "保留 {text_path} 当前内容，并把 {new_marker} 附加到末端",
        "给 {text_path} 扩展最后一条记录 {new_marker}，不得整文件覆盖",
        "将 {new_marker} 拼接到 {text_path} 全部既有数据之后",
        "文件正文保持不变，只在 {text_path} 最后加入新文本 {new_marker}",
    ),
    "write_file": (
        "创建 {text_path} 或用请求的完整 UTF-8 文档彻底覆盖它",
        "把整个文本产物写成 {text_path}，替换此前的全部文件正文",
        "在 {text_path} 写入完整的新非 JSON 文件，而不是只追加或改片段",
        "以原子方式把 {text_path} 的全部内容设为请求文本",
        "从头到尾生成完整源文件 {text_path}，如有旧版本则整体替换",
        "将完整请求文本作为一个整体保存到 {text_path} 并覆盖原文件",
        "按照提供的全文重新生成 {text_path} 的所有字节",
        "用一个完整 UTF-8 值替换 {text_path} 的整个文件正文",
        "把 {text_path} 创建为完整文本文件，而不是在已有字节后追加",
    ),
    "replace_text": (
        "只把 {text_path} 中一个 {old_marker} 精确替换为 {new_marker}，其他文本全部保留",
        "在 {text_path} 内将声明的旧片段 {old_marker} 换成 {new_marker}，不得重写无关字节",
        "仅编辑 {text_path} 中匹配的标记 {old_marker}，改为 {new_marker}",
        "在 {text_path} 里执行一次从 {old_marker} 到 {new_marker} 的精确局部替换",
        "保持文件其余部分不变，只把 {text_path} 中一个准确的 {old_marker} 片段换成 {new_marker}",
        "在 {text_path} 找到单个字面值 {old_marker}，仅将该范围修改为 {new_marker}",
        "保留周围文档，只在 {text_path} 中把指定文本 {old_marker} 替换为 {new_marker}",
        "对 {text_path} 做一次定点文本替换：{old_marker} 变为 {new_marker}",
        "仅把 {text_path} 的一个精确片段从 {old_marker} 改成 {new_marker}，其余不动",
    ),
    "copy_file": (
        "把 {source_path} 的每个字节复制到 {dest_path}，并保留原始源路径",
        "在不删除源文件的情况下，为 {source_path} 在 {dest_path} 创建相同副本",
        "将限定文件 {source_path} 克隆到 {dest_path}，完成后两个路径都必须存在",
        "把 {source_path} 精确复制到 {dest_path}，同时保留 {source_path}",
        "由 {source_path} 在 {dest_path} 生成第二个文件，原文件保持原位",
        "保留 {source_path}，并在 {dest_path} 原样复现其字节",
        "从 {source_path} 在 {dest_path} 创建额外的相同文件，不要移动源文件",
        "把 {source_path} 复刻到 {dest_path}，使源路径继续存在",
        "在 {dest_path} 生成 {source_path} 的逐字节副本，并保留两个文件",
    ),
    "move_file": (
        "将 {source_path} 迁移到 {dest_path}，使旧源路径不再存在",
        "把 {source_path} 移动或重命名为 {dest_path}，保留字节但删除原路径",
        "将现有文件从 {source_path} 转移到 {dest_path}，不要留下源副本",
        "把 {source_path} 重命名为 {dest_path}，最终只保留目标路径",
        "把文件放到 {dest_path}，并在移动过程中清除原位置 {source_path}",
        "将 {source_path} 搬迁到 {dest_path}，内容保留但旧路径不保留",
        "把文件位置从 {source_path} 改到 {dest_path}，而不是复制一份",
        "将唯一现有文件迁移至 {dest_path}，并使 {source_path} 不存在",
        "把精确字节从 {source_path} 移到 {dest_path}，原处不能留下文件",
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_jsonl(path: Path, rows: list[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(canonical_json(row) + "\n")


def load_base() -> ModuleType:
    if sha256_file(BASE_GENERATOR) != BASE_GENERATOR_SHA256:
        raise RuntimeError("frozen S67 generator changed")
    spec = importlib.util.spec_from_file_location(
        "rwkv_lh_s68_semantic_boundary_base", BASE_GENERATOR
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot import frozen S67 generator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def focus_variant(split: str, index: int) -> int:
    values = VARIANTS_BY_SPLIT[split]
    return values[(index // 2) % len(values)]


def install_s68_construction(base: ModuleType) -> None:
    original_request_for = base.request_for

    def context_for(split: str, label: str, index: int) -> dict[str, str]:
        is_focus = label in FOCUS_LABELS
        token = base.stable_hex(
            "S68-frame" if is_focus else "S68-retention",
            split,
            index if is_focus else label,
            "" if is_focus else index,
        )[:14]
        roots = base.LEXICONS[split]
        root = roots[
            index % len(roots)
            if is_focus
            else (index + NETWORK_EXACT_TOOL_LABELS.index(label) * 3) % len(roots)
        ]
        stem = f"scopes/{root}/{token}"
        return {
            "token": token,
            "root": root,
            "text_path": stem + (".py" if index % 2 == 0 else ".md"),
            "json_path": stem + ".json",
            "directory": stem + "-bundle",
            "source_path": f"inputs/{root}/{token}-source.txt",
            "dest_path": f"outputs/{root}/{token}-destination.txt",
            "check_path": f"checks/{root}/{token}-verify.py",
            "script_path": f"build/{root}/{token}-generate.py",
            "marker": f"marker-{token[:8]}",
            "old_marker": f"old-{token[:8]}",
            "new_marker": f"new-{token[:8]}",
            "query": f"public release evidence {root} {token[:8]}",
            "repository": f"{root}/{token[:8]}-repository",
            "package": f"{root}-{token[:8]}-package",
            "expression": f"({index + 17} * 3) + {NETWORK_EXACT_TOOL_LABELS.index(label) + 5}",
            "date_a": f"2025-{(index % 9) + 1:02d}-{(index % 18) + 1:02d}",
            "date_b": f"2026-{((index + 3) % 9) + 1:02d}-{((index + 5) % 18) + 1:02d}",
            "timezone": "Asia/Shanghai" if index % 2 == 0 else "Europe/Amsterdam",
        }

    def request_for(
        split: str,
        label: str,
        index: int,
        language: str,
        context: Mapping[str, str],
    ) -> str:
        if label not in FOCUS_LABELS:
            return original_request_for(split, label, index, language, context)
        variant = focus_variant(split, index)
        inventory = FOCUS_EN if language == "en" else FOCUS_ZH
        core = inventory[label][variant].format(**context)
        modifiers = base.EN_MODIFIERS[split] if language == "en" else base.ZH_MODIFIERS[split]
        modifier = modifiers[(index // 2) % len(modifiers)]
        if language == "en":
            return (
                f"{modifier}, {core}. Batch reference {context['token']}; "
                "do only this atom responsibility."
            )
        return (
            f"{modifier}，{core}。批次标识 {context['token']}；"
            "只完成这一原子职责。"
        )

    base.context_for = context_for
    base.request_for = request_for


def build_row(base: ModuleType, split: str, label: str, index: int) -> dict[str, Any]:
    row = dict(base.build_row(split, label, index))
    token = base.stable_hex(
        "S68-row", split, label, index, row["rendered_input_sha256"]
    )[:24]
    row.update(
        {
            "schema_version": ROW_SCHEMA,
            "dataset_version": DATASET_VERSION,
            "sample_id": f"S68-{split.upper()}-{token}",
            "trajectory_id": f"S68-TRAJECTORY-{token}",
            "source_family_id": f"s68:{split}:{label}:{token}",
            "semantic_boundary_focus": label in FOCUS_LABELS,
            "semantic_core_variant": (
                focus_variant(split, index) if label in FOCUS_LABELS else split
            ),
            "contrastive_frame_id": (
                f"S68-FRAME-{split}-{index:03d}"
                if label in FOCUS_LABELS
                else f"S68-RETENTION-{split}-{label}-{index:03d}"
            ),
            "label_generation": (
                "preregistered_contrastive_semantic_boundary_plus_canonical_contract_progress"
                if label in FOCUS_LABELS
                else "frozen_s67_retention_plus_canonical_contract_progress"
            ),
        }
    )
    context = base.context_for(split, label, index)
    modifier_pool = (
        base.EN_MODIFIERS[split]
        if row["language"] == "en"
        else base.ZH_MODIFIERS[split]
    )
    modifier = (
        modifier_pool[(index // 2) % len(modifier_pool)]
        if label in FOCUS_LABELS
        else modifier_pool[
            (index + NETWORK_EXACT_TOOL_LABELS.index(label)) % len(modifier_pool)
        ]
    )
    row["contrastive_context_sha256"] = hashlib.sha256(
        canonical_json(
            {
                "root": context["root"],
                "token": context["token"],
                "text_path": context["text_path"],
                "source_path": context["source_path"],
                "dest_path": context["dest_path"],
                "modifier": modifier,
                "language": row["language"],
            }
        ).encode("utf-8")
    ).hexdigest()
    return row


def validate_rows(base: ModuleType, rows_by_split: Mapping[str, list[dict[str, Any]]]) -> None:
    if {split: len(rows) for split, rows in rows_by_split.items()} != base.EXPECTED_COUNTS:
        raise RuntimeError("S68 split counts changed")
    for split, rows in rows_by_split.items():
        expected = Counter(
            {
                label: base.COUNTS_PER_LABEL[split]
                for label in NETWORK_EXACT_TOOL_LABELS
            }
        )
        if Counter(str(row["label"]) for row in rows) != expected:
            raise RuntimeError(f"S68 label balance changed: {split}")
        if Counter(str(row["language"]) for row in rows) != Counter(
            {"en": len(rows) // 2, "zh": len(rows) // 2}
        ):
            raise RuntimeError(f"S68 language balance changed: {split}")
        for label in FOCUS_LABELS:
            for language in ("en", "zh"):
                variants = {
                    int(row["semantic_core_variant"])
                    for row in rows
                    if row["label"] == label and row["language"] == language
                }
                if variants != set(VARIANTS_BY_SPLIT[split]):
                    raise RuntimeError(
                        f"S68 semantic variants changed: {split}/{label}/{language}/{variants}"
                    )
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            if row["semantic_boundary_focus"]:
                grouped[str(row["contrastive_frame_id"])].append(row)
        expected_frame_count = base.COUNTS_PER_LABEL[split]
        if len(grouped) != expected_frame_count:
            raise RuntimeError(f"S68 contrastive frame count changed: {split}")
        for frame, members in grouped.items():
            if {str(row["label"]) for row in members} != set(FOCUS_LABELS):
                raise RuntimeError(f"S68 contrastive frame labels changed: {frame}")
            if len({str(row["contrastive_context_sha256"]) for row in members}) != 1:
                raise RuntimeError(f"S68 contrastive frame context changed: {frame}")

    all_rows = [row for split in base.SPLITS for row in rows_by_split[split]]
    if len({str(row["sample_id"]) for row in all_rows}) != len(all_rows):
        raise RuntimeError("S68 sample IDs are not unique")
    if len({str(row["rendered_input_sha256"]) for row in all_rows}) != len(all_rows):
        raise RuntimeError("S68 rendered inputs are not unique")
    purity_fields = (
        "contains_parameter_schemas",
        "contains_full_tool_results",
        "contains_executor_text",
        "contains_planner_raw_json",
        "generated_rwkv_text",
        "hidden_acceptance_used",
    )
    if any(bool(row[field]) for row in all_rows for field in purity_fields):
        raise RuntimeError("S68 role purity changed")
    for left_index, left in enumerate(base.SPLITS):
        for right in base.SPLITS[left_index + 1 :]:
            for key in ("task_request", "source_family_id", "rendered_input_sha256"):
                left_values = {str(row[key]) for row in rows_by_split[left]}
                right_values = {str(row[key]) for row in rows_by_split[right]}
                if left_values & right_values:
                    raise RuntimeError(f"S68 {key} overlap: {left}/{right}")
            left_variants = {
                (str(row["label"]), str(row["language"]), int(row["semantic_core_variant"]))
                for row in rows_by_split[left]
                if row["semantic_boundary_focus"]
            }
            right_variants = {
                (str(row["label"]), str(row["language"]), int(row["semantic_core_variant"]))
                for row in rows_by_split[right]
                if row["semantic_boundary_focus"]
            }
            if left_variants & right_variants:
                raise RuntimeError(f"S68 semantic variant overlap: {left}/{right}")


def main() -> None:
    frozen = {
        PREREGISTRATION: PREREGISTRATION_SHA256,
        BASE_GENERATOR: BASE_GENERATOR_SHA256,
        S67_DATASET / "cases.jsonl": S67_CASES_SHA256,
        S67_DATASET / "manifest.json": S67_MANIFEST_SHA256,
        FUSION_RESULT: FUSION_RESULT_SHA256,
        DATA_ANALYSIS: DATA_ANALYSIS_SHA256,
    }
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S68 dataset")
    for path, expected in frozen.items():
        actual = sha256_file(path) if path.is_file() else "missing"
        if actual != expected:
            raise RuntimeError(f"S68 frozen input changed: {path}: {actual}")
    if set(FOCUS_EN) != set(FOCUS_LABELS) or set(FOCUS_ZH) != set(FOCUS_LABELS):
        raise RuntimeError("S68 focus phrase labels changed")
    if any(len(values) != 9 for values in [*FOCUS_EN.values(), *FOCUS_ZH.values()]):
        raise RuntimeError("S68 focus phrase count changed")

    base = load_base()
    install_s68_construction(base)
    lexicons = {split: set(base.LEXICONS[split]) for split in base.SPLITS}
    for left_index, left in enumerate(base.SPLITS):
        for right in base.SPLITS[left_index + 1 :]:
            if lexicons[left] & lexicons[right]:
                raise RuntimeError(f"S68 lexicon overlap: {left}/{right}")

    references, forbidden_paths, task_ids, audit_hashes = base.holdout_contract()
    rows_by_split = {
        split: [
            build_row(base, split, label, index)
            for label in NETWORK_EXACT_TOOL_LABELS
            for index in range(base.COUNTS_PER_LABEL[split])
        ]
        for split in base.SPLITS
    }
    validate_rows(base, rows_by_split)
    all_rows = [row for split in base.SPLITS for row in rows_by_split[split]]

    forbidden_literals = {
        value for value in forbidden_paths | task_ids if len(value) >= 6
    }
    for row in all_rows:
        matches = [
            value
            for value in forbidden_literals
            if value in str(row["task_request"])
        ]
        if matches:
            raise RuntimeError(
                f"S68 row contains holdout literal: {row['sample_id']}:{matches[:3]}"
            )
    reference_grams = [
        (identity, base.byte_ngrams(text)) for identity, text in references
    ]
    maximum_similarity: dict[str, Any] = {
        "score": -1.0,
        "sample_id": "",
        "holdout_id": "",
    }
    for row in all_rows:
        grams = base.byte_ngrams(str(row["task_request"]))
        for identity, reference in reference_grams:
            score = base.cosine(grams, reference)
            if score > float(maximum_similarity["score"]):
                maximum_similarity = {
                    "score": score,
                    "sample_id": row["sample_id"],
                    "holdout_id": identity,
                }
    if float(maximum_similarity["score"]) >= 0.95:
        raise RuntimeError(f"S68 holdout similarity gate failed: {maximum_similarity}")

    base.DATASET_VERSION = DATASET_VERSION
    base.STATE_ROW_SCHEMA = STATE_ROW_SCHEMA
    exported, token_stats = base.state_rows(RWKVTokenizer(), rows_by_split)
    for split, rows in exported.items():
        for index, row in enumerate(rows):
            row["schema_version"] = STATE_ROW_SCHEMA
            row["dataset_version"] = DATASET_VERSION
            row["sample_id"] = f"S68-STATE-{split.upper()}-{index:04d}"

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{OUTPUT.name}.", dir=OUTPUT.parent))
    cases_path = staging / "cases.jsonl"
    write_jsonl(cases_path, all_rows)
    state_paths = {
        split: staging / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        for split in ("train", "dev")
    }
    for split, path in state_paths.items():
        write_jsonl(path, exported[split])

    phrase_counts = {
        split: {
            language: {
                label: len(
                    {
                        int(row["semantic_core_variant"])
                        for row in rows_by_split[split]
                        if row["semantic_boundary_focus"]
                        and row["language"] == language
                        and row["label"] == label
                    }
                )
                for label in FOCUS_LABELS
            }
            for language in ("en", "zh")
        }
        for split in base.SPLITS
    }
    manifest = {
        "schema_version": "rwkv-lh.network-selector-semantic-boundary-manifest.s68.v1",
        "dataset_version": DATASET_VERSION,
        "purpose": "repair five fully-audited semantic boundaries while retaining all 25 CurrentDirectStageV2 classes",
        "counts": base.EXPECTED_COUNTS,
        "label_counts": {
            split: dict(
                sorted(Counter(str(row["label"]) for row in rows).items())
            )
            for split, rows in rows_by_split.items()
        },
        "language_counts": {
            split: dict(
                sorted(Counter(str(row["language"]) for row in rows).items())
            )
            for split, rows in rows_by_split.items()
        },
        "semantic_boundary": {
            "focus_labels": list(FOCUS_LABELS),
            "variants_by_split": {
                split: list(values) for split, values in VARIANTS_BY_SPLIT.items()
            },
            "distinct_variant_counts": phrase_counts,
            "paired_contrastive_frames": {
                split: base.COUNTS_PER_LABEL[split] for split in base.SPLITS
            },
            "shared_context_within_frame": True,
            "cross_split_variant_intersection_count": 0,
            "source": {
                "fusion_result_sha256": FUSION_RESULT_SHA256,
                "data_analysis_sha256": DATA_ANALYSIS_SHA256,
            },
        },
        "protocol": {
            "compact_schema_version": base.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
            "contract_projection_version": base.SELECTOR_CONTRACT_STAGE_PROJECTION_VERSION,
            "renderer": str(base.RENDERER.relative_to(ROOT)),
            "renderer_sha256": base.FROZEN[base.RENDERER],
            "runtime_projection": str(base.RUNTIME_PROJECTION.relative_to(ROOT)),
            "runtime_projection_sha256": base.FROZEN[base.RUNTIME_PROJECTION],
            "contract_progress": str(base.CONTRACT_PROGRESS.relative_to(ROOT)),
            "contract_progress_sha256": base.FROZEN[base.CONTRACT_PROGRESS],
            "canonical_runtime_construction": True,
            "literal_requirement_byte_tail": True,
            "persistent_history_replayed": True,
        },
        "state_training_contract": {
            "train_rows": len(exported["train"]),
            "dev_rows": len(exported["dev"]),
            "dev_optimizer_use": False,
            "loss_mask": "target_suffix",
            "target_prefix": base.TARGET_PREFIX,
            "jsonl_bos_token_id": 0,
            "ctx_len": base.CTX_LEN,
            "seed": base.SEED,
            "physical_gpu": 0,
            **token_stats,
            "target_boundary_additive": True,
            "target_truncation_count": 0,
        },
        "holdout": {
            "ladder_tasks_sha256": base.FROZEN[base.LADDER / "tasks.json"],
            "ladder_acceptance_sha256": base.FROZEN[
                base.LADDER / "acceptance.json"
            ],
            "e3_results_sha256": base.FROZEN[base.E3_RUN / "results.json"],
            "e3_audit_sha256": dict(sorted(audit_hashes.items())),
            "reference_count": len(references),
            "similarity_algorithm": "utf8-byte-5gram-cosine.v1",
            "threshold_exclusive": 0.95,
            "maximum_similarity": maximum_similarity,
            "optimizer_use": False,
            "candidate_selection_use": False,
        },
        "split_integrity": {
            "lexicon_pool_intersection_count": 0,
            "semantic_variant_intersection_count": 0,
            "exact_request_overlap": 0,
            "source_family_overlap": 0,
            "rendered_input_overlap": 0,
        },
        "role_purity": {
            "parameter_schema_count": 0,
            "full_tool_result_count": 0,
            "executor_text_count": 0,
            "planner_raw_json_count": 0,
            "generated_rwkv_text_count": 0,
            "hidden_acceptance_count": 0,
            "sampling_invoked": False,
            "raw_rwkv_output_modified": False,
        },
        "preregistration": {
            "path": str(PREREGISTRATION.relative_to(ROOT)),
            "sha256": PREREGISTRATION_SHA256,
        },
        "generator": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
            "frozen_base_path": str(BASE_GENERATOR.relative_to(ROOT)),
            "frozen_base_sha256": BASE_GENERATOR_SHA256,
        },
        "files": {
            "cases.jsonl": {
                "rows": len(all_rows),
                "bytes": cases_path.stat().st_size,
                "sha256": sha256_file(cases_path),
            },
            **{
                path.name: {
                    "rows": len(exported[split]),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
                for split, path in state_paths.items()
            },
        },
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (staging / "README.md").write_text(
        "# S68 semantic-boundary Selector corpus\n\n"
        "A 2K/500/500 bilingual CurrentDirectStageV2 corpus. Five audited "
        "operation boundaries use paired contexts and split-disjoint semantic "
        "phrases; all 25 classes remain present.\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "s68_semantic_boundary_dataset_finalized",
                "counts": base.EXPECTED_COUNTS,
                "maximum_holdout_similarity": maximum_similarity,
                "cases_sha256": sha256_file(OUTPUT / "cases.jsonl"),
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
