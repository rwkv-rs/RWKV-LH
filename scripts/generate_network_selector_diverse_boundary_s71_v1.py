#!/usr/bin/env python3
"""Generate the preregistered S71 diverse-boundary current-V2 corpus."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path("/home/chase/GitHub/RWKV-LH")
EXPERIMENT = (
    ROOT / "data/experiments/NETWORK_SELECTOR_DIVERSE_BOUNDARY_S71_V1_20260831"
)
PREREGISTRATION = EXPERIMENT / "PREREGISTRATION.md"
BASE_GENERATOR = ROOT / "scripts/generate_network_selector_v2_contract_s67_v1.py"
FORMAL_SOURCE = ROOT / "scripts/generate_network_selector_uniform_semantic_s69_v1.py"
S70_GENERATOR = ROOT / "scripts/generate_network_selector_current_v2_uniform_s70_v1.py"
S70_DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_current_v2_uniform_s70_v1"
S70_ANALYSIS = (
    ROOT
    / "data/experiments/NETWORK_SELECTOR_CURRENT_V2_UNIFORM_S70_V1_20260831"
    / "STATE_DEV_FAILURE_ANALYSIS.json"
)
S70_CONTAMINATION = (
    ROOT
    / "data/experiments/NETWORK_SELECTOR_CURRENT_V2_UNIFORM_S70_V1_20260831"
    / "LOCKED_TEST_CONTAMINATION_20260831.md"
)
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_diverse_boundary_s71_v1"

PREREGISTRATION_SHA256 = "31c8ac0950661135de6b205cac93dd1ff23ea2bb9a8f26122bc8e1f75d8e8bf9"
BASE_GENERATOR_SHA256 = "ed3d929824ffdc6fff7ad0af1466fa09f1ac5580ec3d91d92a5abb7583c65987"
FORMAL_SOURCE_SHA256 = "1d0fb078952a0531f410e77a2b0a97c148f2df2defb6d7c0857ce1a953c93e50"
S70_GENERATOR_SHA256 = "c0f5c281a214cd01e5473654af9f33e96487a42ba486cb964114fe26c9d27fa3"
S70_CASES_SHA256 = "2895e10545ab4a1c98e4746b38a135167a1794c9dcfdb804ffd61358ea8d4f98"
S70_MANIFEST_SHA256 = "34584d0c755f40e4c8cc286d907eca8d840f5f9bc84614d1d2dcac019aac5f21"
S70_ANALYSIS_SHA256 = "ae03f33bae3fbe1f808c4ff85877ed8fb7c87e3c85c874627ece41ef86af5793"
S70_CONTAMINATION_SHA256 = "9d3b92994ad9014594fe9b28d3b8feca90d7bb11a8498c2e0ef03c115780bc2f"

DATASET_VERSION = "rwkv-lh.network-selector-diverse-boundary-s71.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-diverse-boundary-prefix.s71.v1"
STATE_ROW_SCHEMA = "rwkv-lh.network-selector-state-tuning-row.s71.v1"
SPLIT_PATTERN = re.compile(r'"split":"(train|dev|test)"')

LEXICONS = {
    "train": (
        "amber-harbor",
        "birch-forum",
        "cobalt-yard",
        "driftwood-court",
        "ember-landing",
        "frost-garden",
        "granite-loop",
        "heather-port",
    ),
    "test": (
        "acacia-ridge",
        "brook-meadow",
        "cinder-wharf",
        "dogwood-square",
        "evergreen-arch",
        "fjord-passage",
        "ginger-bay",
        "hawthorn-gate",
    ),
}

TRAIN_EN_MODIFIERS = (
    "For this one bounded operation",
    "Inside the current atomic responsibility",
    "Choose only the next observable effect",
    "For the isolated contract action",
    "At this exact local decision",
    "Within the present single-purpose step",
    "For this scoped action alone",
    "Under the current effect ceiling",
    "At the next operation boundary",
    "For this one required transition",
)
TRAIN_ZH_MODIFIERS = (
    "针对这一项有界操作",
    "在当前原子职责内",
    "只选择下一项可观察效果",
    "针对这项隔离合同动作",
    "在这个准确的本地决策中",
    "处于当前单一目的步骤",
    "只考虑这项限定动作",
    "在当前效果上限内",
    "处于下一操作边界",
    "针对这一项必要状态变化",
)
TEST_EN_MODIFIERS = (
    "Resolve the operation from the exact before-and-after relation",
    "Use only the named observable transition",
    "At this sealed responsibility boundary",
    "Select by what must remain and what must change",
    "Apply the narrowest operation semantics",
)
TEST_ZH_MODIFIERS = (
    "根据准确的前后状态关系确定操作",
    "只使用明确的可观察变化",
    "在这个封存职责边界上",
    "依据必须保留和必须改变的内容选择",
    "采用最窄的操作语义",
)

# New sealed S71 effect/relation inventory.  It is not used by train or visible dev.
SEALED_EN: dict[str, tuple[str, str]] = {
    "list_directory": ("obtain entry-name, entry-kind, and size tuples for {directory} without opening a child", "inspect any child payload or alter the container"),
    "search_text": ("locate workspace line occurrences of {marker} below {directory} and return their positions", "consult public pages or return only directory entries"),
    "read_file": ("observe a bounded byte slice of ordinary UTF-8 document {text_path} while leaving it unchanged", "decode it as structured JSON or write bytes"),
    "read_json": ("decode the complete structured value stored at {json_path} without changing the document", "treat it as an opaque text slice or replace it"),
    "file_digest": ("learn the content fingerprint and length of {text_path} without exposing its body", "return document content or mutate the path"),
    "write_file": ("make the supplied complete plain-text value the entire contents of {text_path}", "retain an old prefix by appending or edit only one span"),
    "write_json": ("make the supplied full object or array the entire structured document {json_path}", "merge only selected keys or serialize it as plain text"),
    "patch_json": ("change only named top-level members of {json_path} and keep every unmentioned member", "discard the old object through whole-document replacement"),
    "replace_text": ("change exactly one matching {old_marker} substring in {text_path} to {new_marker} with all other bytes stable", "append new bytes or recreate the whole document"),
    "remove_line": ("remove one whole line matching {old_marker} from {text_path} while the file and remaining lines persist", "delete the file or perform an inline substitution"),
    "append_file": ("place {new_marker} strictly after the previous final byte of {text_path}", "overwrite prior bytes or modify an interior occurrence"),
    "make_directory": ("cause {directory} to exist as a directory container", "create a regular file at that location"),
    "copy_file": ("create {dest_path} with byte identity to {source_path} while both source and destination exist", "relocate the source or remove its original name"),
    "move_file": ("relocate the artifact from {source_path} to {dest_path} so only the destination name remains", "leave the original in place as a second copy"),
    "delete_file": ("make the explicitly scoped path {text_path} absent", "leave the path present after removing only content or a line"),
    "bind_evidence": ("retain a previously observed span from {text_path} together with its exact locator and quotation", "perform fresh discovery or edit the evidence source"),
    "check_command": ("execute python {check_path} as a non-writing verification and observe its exit evidence", "authorize intended workspace mutation"),
    "run_command": ("execute python {script_path} with the declared permission to change scoped workspace artifacts", "restrict the process to inspection-only behavior"),
    "web_search": ("discover current open-web material answering {query}", "search workspace files or request one typed registry record"),
    "connector_lookup": ("retrieve the typed public repository record identified by {repository}", "browse general webpages or inspect local paths"),
    "calculator": ("derive the numerical result of known expression {expression} without external observation", "fetch unknown facts or read a live clock"),
    "date_diff": ("derive the absolute calendar-day count separating {date_a} and {date_b}", "observe current time or infer from missing dates"),
    "current_time": ("observe the present wall-clock value in IANA zone {timezone}", "calculate a date interval or reuse a cached timestamp"),
    "final_answer": ("return the grounded response now because no operation remains outstanding", "invoke another tool despite completion"),
    "ABSTAIN": ("emit no tool choice because the single safe operation is not identifiable from available facts", "guess a listed operation under ambiguity or unsupported scope"),
}

SEALED_ZH: dict[str, tuple[str, str]] = {
    "list_directory": ("取得 {directory} 的子项名称、类型和大小元组，但不打开任何子项", "检查子项正文或改变目录"),
    "search_text": ("定位 {directory} 下工作区文本中 {marker} 的行级出现位置", "查询公开网页或只返回目录项"),
    "read_file": ("观察普通 UTF-8 文档 {text_path} 的有界字节片段且保持不变", "按结构化 JSON 解码或写入字节"),
    "read_json": ("解码 {json_path} 保存的完整结构化值而不改变文档", "当作不透明文本片段或替换它"),
    "file_digest": ("获知 {text_path} 的内容指纹和长度但不暴露正文", "返回文档内容或修改路径"),
    "write_file": ("让给定的完整纯文本值成为 {text_path} 的全部内容", "通过追加保留旧前缀或只编辑一个片段"),
    "write_json": ("让给定的完整对象或数组成为 {json_path} 的整份结构化文档", "只合并部分键或写成普通文本"),
    "patch_json": ("只修改 {json_path} 中命名的顶层成员并保留所有未提及成员", "通过整份替换丢弃旧对象"),
    "replace_text": ("把 {text_path} 中恰好一个 {old_marker} 子串改成 {new_marker}，其余字节稳定", "追加新字节或重建整个文档"),
    "remove_line": ("从 {text_path} 移除一整行 {old_marker}，同时文件和其余行继续存在", "删除文件或进行行内替换"),
    "append_file": ("把 {new_marker} 严格放在 {text_path} 原最后字节之后", "覆盖已有字节或修改内部匹配"),
    "make_directory": ("使 {directory} 作为目录容器存在", "在该位置创建普通文件"),
    "copy_file": ("创建与 {source_path} 字节相同的 {dest_path}，并让源和目标同时存在", "迁移源或移除原名称"),
    "move_file": ("把产物从 {source_path} 迁移到 {dest_path}，最终只保留目标名称", "把原路径留下作为第二份副本"),
    "delete_file": ("让明确限定的路径 {text_path} 不存在", "只移除内容或一行而让路径继续存在"),
    "bind_evidence": ("保留先前观察到的 {text_path} 片段及其准确定位和引文", "重新发现信息或编辑证据来源"),
    "check_command": ("把 python {check_path} 作为不写入的校验执行并观察退出证据", "授权预期的工作区变更"),
    "run_command": ("在声明允许改变限定产物的条件下执行 python {script_path}", "把进程限制为纯检查"),
    "web_search": ("发现回答 {query} 的当前开放网络材料", "搜索工作区文件或只请求类型化注册记录"),
    "connector_lookup": ("取得 {repository} 标识的类型化公共仓库记录", "浏览普通网页或检查本地路径"),
    "calculator": ("在不进行外部观察的情况下求出已知表达式 {expression} 的数值", "获取未知事实或读取实时钟表"),
    "date_diff": ("求出 {date_a} 与 {date_b} 相隔的绝对日历日数", "观察当前时间或根据缺失日期推断"),
    "current_time": ("观察 IANA 时区 {timezone} 的当前墙上时间", "计算日期区间或复用缓存时间戳"),
    "final_answer": ("由于没有未完成操作，立即返回有依据的答复", "在已经完成时继续调用工具"),
    "ABSTAIN": ("因为无法从已有事实确定唯一安全操作，所以不输出工具选择", "在含糊或不支持的范围下猜测工具"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(canonical_json(row) + "\n")


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import frozen module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def context_for(base: ModuleType, split: str, label: str, index: int) -> dict[str, str]:
    shared = split == "test"
    token = base.stable_hex(
        "S71-sealed-frame" if shared else "S71-train-context",
        split,
        "" if shared else label,
        index,
    )[:14]
    root = LEXICONS[split][index % len(LEXICONS[split])]
    stem = f"scopes/{root}/{token}"
    return {
        "token": token,
        "root": root,
        "text_path": stem + (".txt" if index % 2 == 0 else ".md"),
        "json_path": stem + ".json",
        "directory": stem + "-folder",
        "source_path": f"incoming/{root}/{token}-source.bin",
        "dest_path": f"outgoing/{root}/{token}-destination.bin",
        "check_path": f"checks/{root}/{token}-verify.py",
        "script_path": f"build/{root}/{token}-generate.py",
        "marker": f"needle-{token[:8]}",
        "old_marker": f"legacy-{token[:8]}",
        "new_marker": f"active-{token[:8]}",
        "query": f"current public evidence {root} {token[:8]}",
        "repository": f"{root}/{token[:8]}-repository",
        "package": f"{root}-{token[:8]}-package",
        "expression": f"({index + 43} * 7) - 11",
        "date_a": f"2023-{(index % 9) + 1:02d}-{(index % 18) + 1:02d}",
        "date_b": f"2026-{((index + 4) % 9) + 1:02d}-{((index + 7) % 18) + 1:02d}",
        "timezone": "America/Vancouver" if index % 2 == 0 else "Europe/Oslo",
    }


def install_construction(base: ModuleType, formal: ModuleType) -> None:
    def installed_context(split: str, label: str, index: int) -> dict[str, str]:
        if split == "dev":
            raise RuntimeError("S71 dev rows must come from explicit S70 reclassification")
        return context_for(base, split, label, index)

    def request_for(
        split: str,
        label: str,
        index: int,
        language: str,
        context: Mapping[str, str],
    ) -> str:
        occurrence = index // 2
        if split == "train":
            core_id = occurrence % 4
            if core_id < 2:
                core = (base.EN_PHRASES if language == "en" else base.ZH_PHRASES)[label][core_id]
            else:
                core = (formal.TEST_EN if language == "en" else formal.TEST_ZH)[label][core_id - 2]
            rendered = core.format(**context)
            modifiers = TRAIN_EN_MODIFIERS if language == "en" else TRAIN_ZH_MODIFIERS
            modifier = modifiers[occurrence // 4]
            if language == "en":
                return f"{modifier}, {rendered}. Scope reference {context['token']}; perform only this operation."
            return f"{modifier}，{rendered}。范围标识 {context['token']}；只执行这一项操作。"
        inventory = SEALED_EN if language == "en" else SEALED_ZH
        desired, forbidden = (value.format(**context) for value in inventory[label])
        modifiers = TEST_EN_MODIFIERS if language == "en" else TEST_ZH_MODIFIERS
        modifier = modifiers[occurrence % len(modifiers)]
        if language == "en" and occurrence % 2 == 0:
            core = f"the required transition is that we {desired}; reject any choice that would {forbidden}"
        elif language == "en":
            core = f"choose the operation whose sole result is to {desired}, because it must not {forbidden}"
        elif occurrence % 2 == 0:
            core = f"必要变化是：{desired}；任何会{forbidden}的选择都应排除"
        else:
            core = f"选择唯一能够做到“{desired}”且不会{forbidden}的操作"
        if language == "en":
            return f"{modifier}; {core}. Sealed reference {context['token']}; perform only this operation."
        return f"{modifier}；{core}。封存标识 {context['token']}；只执行这一项操作。"

    base.context_for = installed_context
    base.request_for = request_for


def build_generated_row(base: ModuleType, split: str, label: str, index: int) -> dict[str, Any]:
    row = dict(base.build_row(split, label, index))
    occurrence = index // 2
    token = base.stable_hex("S71-row", split, label, index, row["rendered_input_sha256"])[:24]
    source = (
        ("s71-diverse-four-core-train", occurrence % 4)
        if split == "train"
        else ("s71-sealed-relation-effect", occurrence % 2)
    )
    row.update(
        {
            "schema_version": ROW_SCHEMA,
            "dataset_version": DATASET_VERSION,
            "sample_id": f"S71-{split.upper()}-{token}",
            "trajectory_id": f"S71-TRAJECTORY-{token}",
            "source_family_id": f"s71:{split}:{label}:{token}",
            "semantic_source": source[0],
            "semantic_core_variant": source[1],
            "contrastive_frame_id": (
                f"S71-TEST-FRAME-{index:03d}"
                if split == "test"
                else f"S71-TRAIN-{label}-{index:03d}"
            ),
            "label_generation": "diverse_semantic_core_plus_canonical_current_v2_contract_progress",
        }
    )
    context = base.context_for(split, label, index)
    shared = {
        "root": context["root"],
        "token": context["token"],
        "text_path": context["text_path"],
        "json_path": context["json_path"],
        "source_path": context["source_path"],
        "dest_path": context["dest_path"],
        "language": row["language"],
    }
    row["contrastive_context_sha256"] = hashlib.sha256(
        canonical_json(shared).encode("utf-8")
    ).hexdigest()
    return row


def reclassified_dev_rows(base: ModuleType) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows: list[dict[str, Any]] = []
    skipped = Counter()
    with (S70_DATASET / "cases.jsonl").open("r", encoding="utf-8") as stream:
        for line in stream:
            match = SPLIT_PATTERN.search(line)
            if match is None:
                raise RuntimeError("S71 S70 split marker missing")
            split = match.group(1)
            if split != "test":
                skipped[split] += 1
                continue
            source = json.loads(line)
            row = dict(source)
            token = base.stable_hex(
                "S71-visible-dev-reclassification",
                source["sample_id"],
                source["rendered_input_sha256"],
            )[:24]
            row.update(
                {
                    "schema_version": ROW_SCHEMA,
                    "dataset_version": DATASET_VERSION,
                    "split": "dev",
                    "sample_id": f"S71-DEV-{token}",
                    "trajectory_id": f"S71-TRAJECTORY-{token}",
                    "source_family_id": f"s71:visible-dev:{token}",
                    "semantic_source": "s70-quarantined-former-locked-visible-dev",
                    "contrastive_frame_id": str(source["contrastive_frame_id"]).replace(
                        "S70-TEST", "S71-DEV"
                    ),
                    "label_generation": "visible_reclassified_s70_effect_postcondition_dev",
                }
            )
            rows.append(row)
    if len(rows) != 500 or skipped != Counter({"train": 2000, "dev": 500}):
        raise RuntimeError(f"S71 visible-dev reclassification changed: {len(rows)}/{skipped}")
    return rows, {
        "s70_train_rows_skipped_before_json_parse": skipped["train"],
        "s70_dev_rows_skipped_before_json_parse": skipped["dev"],
        "s70_quarantined_test_rows_reclassified_and_json_parsed": len(rows),
        "s70_quarantined_test_labels_reclassified_for_visible_dev": len(rows),
    }


def validate_rows(base: ModuleType, rows_by_split: Mapping[str, list[dict[str, Any]]]) -> None:
    if {split: len(rows) for split, rows in rows_by_split.items()} != base.EXPECTED_COUNTS:
        raise RuntimeError("S71 split counts changed")
    for split, rows in rows_by_split.items():
        if Counter(str(row["label"]) for row in rows) != Counter(
            {label: base.COUNTS_PER_LABEL[split] for label in NETWORK_EXACT_TOOL_LABELS}
        ):
            raise RuntimeError(f"S71 label balance changed: {split}")
        if Counter(str(row["language"]) for row in rows) != Counter(
            {"en": len(rows) // 2, "zh": len(rows) // 2}
        ):
            raise RuntimeError(f"S71 language balance changed: {split}")
        for label in NETWORK_EXACT_TOOL_LABELS:
            selected = [row for row in rows if row["label"] == label]
            for language in ("en", "zh"):
                variants = Counter(
                    int(row["semantic_core_variant"])
                    for row in selected
                    if row["language"] == language
                )
                expected = Counter({0: 10, 1: 10, 2: 10, 3: 10}) if split == "train" else Counter({0: 5, 1: 5})
                if variants != expected:
                    raise RuntimeError(
                        f"S71 semantic variants changed: {split}/{label}/{language}/{variants}"
                    )
    frames: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows_by_split["test"]:
        frames[str(row["contrastive_frame_id"])].append(row)
    if len(frames) != 20:
        raise RuntimeError("S71 sealed frame count changed")
    for frame, members in frames.items():
        if {str(row["label"]) for row in members} != set(NETWORK_EXACT_TOOL_LABELS):
            raise RuntimeError(f"S71 sealed frame labels changed: {frame}")
        if len({str(row["contrastive_context_sha256"]) for row in members}) != 1:
            raise RuntimeError(f"S71 sealed frame context changed: {frame}")
    all_rows = [row for split in base.SPLITS for row in rows_by_split[split]]
    for key in ("sample_id", "source_family_id", "rendered_input_sha256"):
        if len({str(row[key]) for row in all_rows}) != len(all_rows):
            raise RuntimeError(f"S71 {key} values are not unique")
    purity_fields = (
        "contains_parameter_schemas",
        "contains_full_tool_results",
        "contains_executor_text",
        "contains_planner_raw_json",
        "generated_rwkv_text",
        "hidden_acceptance_used",
    )
    if any(bool(row[field]) for row in all_rows for field in purity_fields):
        raise RuntimeError("S71 role purity changed")
    for left_index, left in enumerate(base.SPLITS):
        for right in base.SPLITS[left_index + 1 :]:
            for key in ("task_request", "source_family_id", "rendered_input_sha256"):
                if {str(row[key]) for row in rows_by_split[left]} & {
                    str(row[key]) for row in rows_by_split[right]
                }:
                    raise RuntimeError(f"S71 {key} overlap: {left}/{right}")


def cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    if not dot:
        return 0.0
    return dot / math.sqrt(
        sum(value * value for value in left.values())
        * sum(value * value for value in right.values())
    )


def maximum_similarity(
    base: ModuleType,
    rows: Iterable[Mapping[str, Any]],
    references: Iterable[tuple[str, str]],
) -> dict[str, Any]:
    maximum: dict[str, Any] = {"score": -1.0, "sample_id": "", "holdout_id": ""}
    cached = [(identity, base.byte_ngrams(text)) for identity, text in references]
    for row in rows:
        grams = base.byte_ngrams(str(row["task_request"]))
        for identity, reference in cached:
            score = cosine(grams, reference)
            if score > float(maximum["score"]):
                maximum = {
                    "score": score,
                    "sample_id": row["sample_id"],
                    "holdout_id": identity,
                }
    return maximum


def main() -> None:
    frozen = {
        PREREGISTRATION: PREREGISTRATION_SHA256,
        BASE_GENERATOR: BASE_GENERATOR_SHA256,
        FORMAL_SOURCE: FORMAL_SOURCE_SHA256,
        S70_GENERATOR: S70_GENERATOR_SHA256,
        S70_DATASET / "cases.jsonl": S70_CASES_SHA256,
        S70_DATASET / "manifest.json": S70_MANIFEST_SHA256,
        S70_ANALYSIS: S70_ANALYSIS_SHA256,
        S70_CONTAMINATION: S70_CONTAMINATION_SHA256,
    }
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S71 dataset")
    for path, expected in frozen.items():
        actual = sha256_file(path) if path.is_file() else "missing"
        if actual != expected:
            raise RuntimeError(f"S71 frozen input changed: {path}: {actual}")
    if set(SEALED_EN) != set(NETWORK_EXACT_TOOL_LABELS) or set(SEALED_ZH) != set(
        NETWORK_EXACT_TOOL_LABELS
    ):
        raise RuntimeError("S71 sealed semantic labels changed")
    base = load_module("rwkv_lh_s71_base", BASE_GENERATOR)
    formal = load_module("rwkv_lh_s71_formal", FORMAL_SOURCE)
    install_construction(base, formal)
    visible_dev, reclassification = reclassified_dev_rows(base)
    rows_by_split = {
        "train": [
            build_generated_row(base, "train", label, index)
            for label in NETWORK_EXACT_TOOL_LABELS
            for index in range(base.COUNTS_PER_LABEL["train"])
        ],
        "dev": visible_dev,
        "test": [
            build_generated_row(base, "test", label, index)
            for label in NETWORK_EXACT_TOOL_LABELS
            for index in range(base.COUNTS_PER_LABEL["test"])
        ],
    }
    validate_rows(base, rows_by_split)
    all_rows = [row for split in base.SPLITS for row in rows_by_split[split]]

    ladder, forbidden_paths, task_ids, audit_hashes = base.holdout_contract()
    forbidden_literals = {value for value in forbidden_paths | task_ids if len(value) >= 6}
    for row in all_rows:
        matches = [value for value in forbidden_literals if value in str(row["task_request"])]
        if matches:
            raise RuntimeError(f"S71 row contains holdout literal: {row['sample_id']}:{matches[:3]}")
    ladder_maximum = maximum_similarity(base, all_rows, ladder)
    if float(ladder_maximum["score"]) >= 0.95:
        raise RuntimeError(f"S71 Ladder holdout similarity failed: {ladder_maximum}")

    s70_requests: list[tuple[str, str]] = []
    with (S70_DATASET / "cases.jsonl").open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            row = json.loads(line)
            s70_requests.append((f"s70-line-{line_number}", str(row["task_request"])))
    generated_rows = [*rows_by_split["train"], *rows_by_split["test"]]
    s70_maximum = maximum_similarity(base, generated_rows, s70_requests)
    if float(s70_maximum["score"]) >= 0.95:
        raise RuntimeError(f"S71 generated/S70 similarity failed: {s70_maximum}")
    exact_s70_overlap = len(
        {str(row["task_request"]) for row in generated_rows}
        & {request for _identity, request in s70_requests}
    )
    if exact_s70_overlap:
        raise RuntimeError("S71 generated rows reuse S70 requests")

    base.DATASET_VERSION = DATASET_VERSION
    base.STATE_ROW_SCHEMA = STATE_ROW_SCHEMA
    exported, token_stats = base.state_rows(RWKVTokenizer(), rows_by_split)
    for split, rows in exported.items():
        for index, row in enumerate(rows):
            row["schema_version"] = STATE_ROW_SCHEMA
            row["dataset_version"] = DATASET_VERSION
            row["sample_id"] = f"S71-STATE-{split.upper()}-{index:04d}"

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
    manifest = {
        "schema_version": "rwkv-lh.network-selector-diverse-boundary-manifest.s71.v1",
        "dataset_version": DATASET_VERSION,
        "purpose": "preserve the 2K budget while replacing repeated cores with balanced near-effect semantic diversity",
        "counts": base.EXPECTED_COUNTS,
        "label_counts": {
            split: dict(sorted(Counter(str(row["label"]) for row in rows).items()))
            for split, rows in rows_by_split.items()
        },
        "language_counts": {
            split: dict(sorted(Counter(str(row["language"]) for row in rows).items()))
            for split, rows in rows_by_split.items()
        },
        "semantic_sources": {
            split: dict(sorted(Counter(str(row["semantic_source"]) for row in rows).items()))
            for split, rows in rows_by_split.items()
        },
        "architecture": {
            "single_responsibility_current_v2_only": True,
            "legacy_v1_rows": 0,
            "compact_schema_version": base.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
            "contract_projection_version": base.SELECTOR_CONTRACT_STAGE_PROJECTION_VERSION,
            "literal_requirement_byte_tail": True,
            "persistent_history_replayed": True,
        },
        "train_diversity": {
            "semantic_cores_per_label_language": 4,
            "rows_per_core_per_label_language": 10,
            "core_sources": [
                "s67-canonical-core-0",
                "s67-held-out-core-1",
                "s69-formal-core-0",
                "s69-formal-core-1",
            ],
            "total_rows": len(rows_by_split["train"]),
        },
        "visible_dev_reclassification": {
            "source": "S70 quarantined former locked split",
            "optimizer_use": False,
            "candidate_selection_use": True,
            "blind_or_locked": False,
            "source_cases_sha256": S70_CASES_SHA256,
            "contamination_record_sha256": S70_CONTAMINATION_SHA256,
            **reclassification,
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
            "ladder_acceptance_sha256": base.FROZEN[base.LADDER / "acceptance.json"],
            "e3_results_sha256": base.FROZEN[base.E3_RUN / "results.json"],
            "e3_audit_sha256": dict(sorted(audit_hashes.items())),
            "similarity_algorithm": "utf8-byte-5gram-cosine.v1",
            "threshold_exclusive": 0.95,
            "maximum_ladder_similarity": ladder_maximum,
            "maximum_generated_s70_similarity": s70_maximum,
            "exact_generated_s70_request_overlap": exact_s70_overlap,
        },
        "split_integrity": {
            "exact_request_overlap": 0,
            "source_family_overlap": 0,
            "rendered_input_overlap": 0,
        },
        "locked_test": {
            "source": "new S71 sealed relation/effect inventory",
            "variants_per_label_language": 2,
            "shared_contrastive_frames": 20,
            "opened_by_model_runner": False,
            "test_rows_json_parsed_after_dataset_commit": 0,
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
            "base_sha256": BASE_GENERATOR_SHA256,
            "formal_source_sha256": FORMAL_SOURCE_SHA256,
            "s70_generator_sha256": S70_GENERATOR_SHA256,
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
        "# S71 diverse-boundary current-V2 Selector corpus\n\n"
        "The 2K train budget is distributed across four semantic cores; S70's "
        "quarantined test is visible dev, and S71 owns a new sealed test.\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "s71_diverse_boundary_dataset_finalized",
                "counts": base.EXPECTED_COUNTS,
                "maximum_ladder_similarity": ladder_maximum,
                "maximum_generated_s70_similarity": s70_maximum,
                "cases_sha256": sha256_file(OUTPUT / "cases.jsonl"),
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
