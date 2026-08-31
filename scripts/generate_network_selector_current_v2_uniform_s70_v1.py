#!/usr/bin/env python3
"""Generate the preregistered current-V2 S70 uniform semantic corpus."""

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
    ROOT
    / "data/experiments/NETWORK_SELECTOR_CURRENT_V2_UNIFORM_S70_V1_20260831"
)
PREREGISTRATION = EXPERIMENT / "PREREGISTRATION.md"
S69_FAILURE = (
    ROOT
    / "data/experiments/NETWORK_SELECTOR_UNIFORM_SEMANTIC_S69_V1_20260831"
    / "GENERATION_ATTEMPT_1.md"
)
BASE_GENERATOR = ROOT / "scripts/generate_network_selector_v2_contract_s67_v1.py"
FORMAL_SOURCE = ROOT / "scripts/generate_network_selector_uniform_semantic_s69_v1.py"
S68 = ROOT / "data/datasets/rwkv_lh_network_selector_semantic_boundary_s68_v1"
S68_LOCKED_RESULT = (
    ROOT
    / "data/experiments/NETWORK_SELECTOR_SEMANTIC_BOUNDARY_S68_V1_20260831"
    / "run_locked_test/RESULT.json"
)
S68_LOCKED_ANALYSIS = (
    ROOT
    / "data/experiments/NETWORK_SELECTOR_SEMANTIC_BOUNDARY_S68_V1_20260831"
    / "LOCKED_TEST_ANALYSIS.md"
)
S66_LOCKED_RESULT = (
    ROOT
    / "data/experiments/NETWORK_SELECTOR_DIVERSE_SOFT_MOE_S66_20260830"
    / "run_s66_m1_locked_tests/LOCKED_TEST_RESULT.json"
)
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_current_v2_uniform_s70_v1"

PREREGISTRATION_SHA256 = (
    "68e464f0a63617521c54a8b2ac8fb66e60733fb18635e146bb448c8f57b1b146"
)
BASE_GENERATOR_SHA256 = (
    "ed3d929824ffdc6fff7ad0af1466fa09f1ac5580ec3d91d92a5abb7583c65987"
)
FORMAL_SOURCE_SHA256 = (
    "1d0fb078952a0531f410e77a2b0a97c148f2df2defb6d7c0857ce1a953c93e50"
)
S68_FAILURE_SHA256 = "a56bdaa3196e3be1eac35afb53d208178f8789b5f8dcccd8a3c7ee06da96eb7f"
S69_FAILURE_SHA256 = "da08aeadbd30bc63ee5e7e4f1d262f7f4e1b769bd26f81dcc529c97e968f8f05"
S68_CASES_SHA256 = (
    "8b0f1a17f25863f448858d082c7b6cf7dec5cb76414f635f5f2ab8416566d218"
)
S68_MANIFEST_SHA256 = (
    "4a6e201e3d1dc6dff63f72660a08455ae619c1186b45c95c7f9d86ffc985ea0c"
)
S68_LOCKED_RESULT_SHA256 = (
    "b3e33b98e9ba7d5d9742fbb805331ae273142e94124e6dd1770f2ee0a6904c0a"
)
S66_LOCKED_RESULT_SHA256 = (
    "5d24d7abedaa54d0cb586e5500a39ffb8a62f918f1fbb7bd3e418b78f153ed0d"
)

DATASET_VERSION = "rwkv-lh.network-selector-current-v2-uniform-s70.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-current-v2-uniform-prefix.s70.v1"
STATE_ROW_SCHEMA = "rwkv-lh.network-selector-state-tuning-row.s70.v1"
SPLIT_PATTERN = re.compile(r'"split":"(train|dev|test)"')

LEXICONS = {
    "train": (
        "alder-campus",
        "brass-depot",
        "clover-exchange",
        "dune-gallery",
        "elm-market",
        "flint-observatory",
        "garnet-park",
        "harbor-quarters",
    ),
    "dev": (
        "iris-arcade",
        "jade-crossing",
        "linen-terminal",
        "moss-village",
        "northwind-plaza",
        "onyx-reserve",
        "pearl-station",
        "reed-terrace",
    ),
    "test": (
        "spruce-avenue",
        "tulip-borough",
        "ultramarine-court",
        "vermilion-dock",
        "wheat-enclave",
        "xylem-promenade",
        "yucca-range",
        "zinc-square",
    ),
}

EN_MODIFIERS = {
    "train": (
        "For the current bounded responsibility",
        "Within this isolated operation",
        "For the next exact effect only",
        "Inside the declared local scope",
    ),
    "dev": (
        "For this independent decision",
        "Within the present contract step",
        "For the scoped operation at hand",
        "Inside this separate evidence stage",
    ),
    "test": (
        "Judge only the required observable effect",
        "At this decision boundary",
        "Use the declared postcondition alone",
        "For this exact responsibility boundary",
        "Choose by the resulting state",
    ),
}
ZH_MODIFIERS = {
    "train": (
        "针对当前有界职责",
        "在这项隔离操作内",
        "只考虑下一项准确效果",
        "在声明的本地范围中",
    ),
    "dev": (
        "针对这次独立决策",
        "在当前合同步骤内",
        "只处理眼前的限定操作",
        "处于这项单独证据阶段",
    ),
    "test": (
        "只依据要求的可观察效果判断",
        "处于这个决策边界",
        "仅使用声明的完成后条件",
        "针对这项准确职责边界",
        "按照最终状态选择",
    ),
}

# Test-only effect and negative-boundary inventory.  No item is used by train or dev.
LOCKED_EN: dict[str, tuple[str, str]] = {
    "list_directory": ("bounded child names, kinds, and sizes under {directory} are returned without any body being opened", "reads a listed file body or changes a path"),
    "search_text": ("local matching lines for {marker} beneath {directory} are returned with their locators", "uses the public internet or merely lists directory metadata"),
    "read_file": ("a bounded UTF-8 body range from the ordinary text file {text_path} is observed unchanged", "parses the path as JSON or mutates its bytes"),
    "read_json": ("the structured value in {json_path} is decoded as canonical JSON without edits", "treats the document as arbitrary text or writes a replacement"),
    "file_digest": ("only the SHA-256 identity and byte length of {text_path} become known", "returns the body or modifies the artifact"),
    "write_file": ("the entire non-JSON text value at {text_path} is created or replaced", "adds only a suffix or updates a small span"),
    "write_json": ("one complete object or array becomes the whole JSON document at {json_path}", "preserves unspecified old keys through a partial merge or emits plain text"),
    "patch_json": ("named top-level keys in {json_path} change while every unspecified key survives", "replaces the entire JSON value"),
    "replace_text": ("one exact {old_marker} span in {text_path} becomes {new_marker} and all surrounding bytes remain", "rewrites the whole file or appends at EOF"),
    "remove_line": ("the complete line equal to {old_marker} disappears while {text_path} and every other line remain", "deletes the path itself or substitutes inline text"),
    "append_file": ("{new_marker} is concatenated after all existing bytes in {text_path}", "overwrites the earlier body or edits a middle span"),
    "make_directory": ("the workspace directory {directory} exists as a folder", "creates a document at that path"),
    "copy_file": ("{dest_path} contains the exact bytes of {source_path} and the source still exists", "removes or renames the source"),
    "move_file": ("the bytes formerly at {source_path} are at {dest_path} and the origin path is absent", "keeps a second source copy"),
    "delete_file": ("the explicitly named workspace path {text_path} no longer exists", "only removes a line or clears part of its content"),
    "bind_evidence": ("an already observed line span from {text_path} is retained with exact locator and quote", "performs a new search or edits the source"),
    "check_command": ("python {check_path} runs as a non-mutating validation and its process result is observed", "authorizes intended workspace changes"),
    "run_command": ("python {script_path} runs with permission to create or update scoped artifacts", "limits execution to read-only inspection"),
    "web_search": ("current evidence for {query} is discovered from open web pages", "searches only local workspace text or a typed registry"),
    "connector_lookup": ("a typed public registry record for {repository} is returned", "performs a general webpage search or local file scan"),
    "calculator": ("the exact value of the already known formula {expression} is computed locally", "looks up external information or reads the clock"),
    "date_diff": ("the absolute calendar-day separation between {date_a} and {date_b} is computed", "reports a duration from unknown dates or the current time"),
    "current_time": ("the live wall-clock reading for IANA zone {timezone} is observed", "computes a date interval or uses a stale known value"),
    "final_answer": ("the grounded user-facing response is returned because every required operation and check is complete", "calls another tool while a final response alone is due"),
    "ABSTAIN": ("no operation is selected because the required private or ambiguous capability cannot be chosen safely", "guesses one listed operation without enough observable support"),
}

LOCKED_ZH: dict[str, tuple[str, str]] = {
    "list_directory": ("只返回 {directory} 下有界的子项名称、类型和大小，不打开任何正文", "读取所列文件内容或改变路径"),
    "search_text": ("返回 {directory} 下与 {marker} 匹配的本地文本行及定位", "使用公网或仅列目录元数据"),
    "read_file": ("观察普通文本文件 {text_path} 的有界 UTF-8 正文范围且字节不变", "把路径解析成 JSON 或修改内容"),
    "read_json": ("把 {json_path} 的结构化值解码为规范 JSON 且不编辑", "当成任意文本读取或写入替代值"),
    "file_digest": ("只获知 {text_path} 的 SHA-256 身份与字节长度", "返回正文或改变产物"),
    "write_file": ("创建或整体替换 {text_path} 的完整非 JSON 文本值", "只增加后缀或只修改一个小片段"),
    "write_json": ("让一个完整对象或数组成为 {json_path} 的整份 JSON 文档", "通过局部合并保留旧键或写成普通文本"),
    "patch_json": ("修改 {json_path} 的指定顶层键并保留每个未指定键", "替换完整 JSON 值"),
    "replace_text": ("仅把 {text_path} 中一个 {old_marker} 范围改为 {new_marker}，周围字节保留", "重写全文件或在末尾追加"),
    "remove_line": ("完整等于 {old_marker} 的一行消失，但 {text_path} 和其他行继续存在", "删除路径本身或做行内替换"),
    "append_file": ("把 {new_marker} 拼接到 {text_path} 全部已有字节之后", "覆盖原正文或编辑中间范围"),
    "make_directory": ("工作区目录 {directory} 作为文件夹存在", "在该路径创建文档"),
    "copy_file": ("{dest_path} 具有 {source_path} 的精确字节且源仍存在", "移除或重命名源路径"),
    "move_file": ("原在 {source_path} 的字节到达 {dest_path}，并且源路径消失", "保留第二份源副本"),
    "delete_file": ("明确命名的工作区路径 {text_path} 不再存在", "只删除一行或清除部分内容"),
    "bind_evidence": ("把已观察的 {text_path} 行范围连同精确定位和引文保留为证据", "重新搜索或编辑来源"),
    "check_command": ("python {check_path} 作为非变更校验运行并观察进程结果", "授权预期的工作区修改"),
    "run_command": ("python {script_path} 在允许创建或更新限定产物的条件下运行", "把执行限制成只读检查"),
    "web_search": ("从开放网页发现关于 {query} 的当前证据", "只搜索本地文本或类型化注册表"),
    "connector_lookup": ("返回 {repository} 的类型化公共注册记录", "执行普通网页搜索或本地文件扫描"),
    "calculator": ("在本地算出已知公式 {expression} 的精确值", "查询外部信息或读取时钟"),
    "date_diff": ("计算 {date_a} 与 {date_b} 的绝对日历日间隔", "使用未知日期报告时长或读取当前时间"),
    "current_time": ("观察 IANA 时区 {timezone} 的实时墙上时钟", "计算日期间隔或复述过期值"),
    "final_answer": ("因为全部操作和检查已完成，返回有依据的面向用户答复", "在只需最终答复时继续调用工具"),
    "ABSTAIN": ("由于所需私有或含糊能力无法安全选择，因此不选择任何操作", "在缺少可观察依据时猜一个工具"),
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


def test_core(
    *, label: str, language: str, variant: int, context: Mapping[str, str]
) -> str:
    inventory = LOCKED_EN if language == "en" else LOCKED_ZH
    desired, forbidden = (value.format(**context) for value in inventory[label])
    if language == "en" and variant == 0:
        return f"make this postcondition true: {desired}; an operation that {forbidden} is outside scope"
    if language == "en":
        return f"select the effect where {desired}, rather than any effect that {forbidden}"
    if variant == 0:
        return f"使这个完成后条件成立：{desired}；会{forbidden}的操作不在范围内"
    return f"选择能够做到“{desired}”的效果，而不是会{forbidden}的效果"


def install_construction(base: ModuleType, formal: ModuleType) -> None:
    def context_for(split: str, label: str, index: int) -> dict[str, str]:
        shared = split == "test"
        token = base.stable_hex(
            "S70-shared-frame" if shared else "S70-row-context",
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
            "query": f"open release evidence {root} {token[:8]}",
            "repository": f"{root}/{token[:8]}-repository",
            "package": f"{root}-{token[:8]}-package",
            "expression": f"({index + 31} * 5) - 9",
            "date_a": f"2024-{(index % 9) + 1:02d}-{(index % 18) + 1:02d}",
            "date_b": f"2026-{((index + 5) % 9) + 1:02d}-{((index + 8) % 18) + 1:02d}",
            "timezone": "Pacific/Auckland" if index % 2 == 0 else "Europe/Zurich",
        }

    def request_for(
        split: str,
        label: str,
        index: int,
        language: str,
        context: Mapping[str, str],
    ) -> str:
        occurrence = index // 2
        modifiers = EN_MODIFIERS[split] if language == "en" else ZH_MODIFIERS[split]
        modifier = modifiers[occurrence % len(modifiers)]
        if split == "train":
            if occurrence < 20:
                core = (base.EN_PHRASES if language == "en" else base.ZH_PHRASES)[label][0].format(**context)
            else:
                core = (formal.TEST_EN if language == "en" else formal.TEST_ZH)[label][0].format(**context)
        elif split == "dev":
            if occurrence < 5:
                core = (base.EN_PHRASES if language == "en" else base.ZH_PHRASES)[label][1].format(**context)
            else:
                core = (formal.TEST_EN if language == "en" else formal.TEST_ZH)[label][1].format(**context)
        else:
            core = test_core(
                label=label,
                language=language,
                variant=occurrence % 2,
                context=context,
            )
        if language == "en":
            return f"{modifier}, {core}. Scope reference {context['token']}; perform only this operation."
        return f"{modifier}，{core}。范围标识 {context['token']}；只执行这一项操作。"

    base.context_for = context_for
    base.request_for = request_for


def semantic_source(split: str, index: int) -> tuple[str, int]:
    occurrence = index // 2
    if split == "train":
        return ("s67-current-train", 0) if occurrence < 20 else ("s69-unused-formal-train", 0)
    if split == "dev":
        return ("s67-current-dev", 1) if occurrence < 5 else ("s69-unused-formal-dev", 1)
    return "s70-locked-effect-postcondition", occurrence % 2


def build_row(base: ModuleType, split: str, label: str, index: int) -> dict[str, Any]:
    row = dict(base.build_row(split, label, index))
    source, variant = semantic_source(split, index)
    token = base.stable_hex("S70-row", split, label, index, row["rendered_input_sha256"])[:24]
    row.update(
        {
            "schema_version": ROW_SCHEMA,
            "dataset_version": DATASET_VERSION,
            "sample_id": f"S70-{split.upper()}-{token}",
            "trajectory_id": f"S70-TRAJECTORY-{token}",
            "source_family_id": f"s70:{split}:{label}:{token}",
            "semantic_source": source,
            "semantic_core_variant": variant,
            "contrastive_frame_id": (
                f"S70-TEST-FRAME-{index:03d}"
                if split == "test"
                else f"S70-{split.upper()}-{label}-{index:03d}"
            ),
            "label_generation": "uniform_semantic_core_plus_canonical_current_v2_contract_progress",
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


def validate_rows(base: ModuleType, rows_by_split: Mapping[str, list[dict[str, Any]]]) -> None:
    if {split: len(rows) for split, rows in rows_by_split.items()} != base.EXPECTED_COUNTS:
        raise RuntimeError("S70 split counts changed")
    expected_sources = {
        "train": Counter({"s67-current-train": 40, "s69-unused-formal-train": 40}),
        "dev": Counter({"s67-current-dev": 10, "s69-unused-formal-dev": 10}),
        "test": Counter({"s70-locked-effect-postcondition": 20}),
    }
    for split, rows in rows_by_split.items():
        if Counter(str(row["label"]) for row in rows) != Counter(
            {label: base.COUNTS_PER_LABEL[split] for label in NETWORK_EXACT_TOOL_LABELS}
        ):
            raise RuntimeError(f"S70 label balance changed: {split}")
        if Counter(str(row["language"]) for row in rows) != Counter(
            {"en": len(rows) // 2, "zh": len(rows) // 2}
        ):
            raise RuntimeError(f"S70 language balance changed: {split}")
        for label in NETWORK_EXACT_TOOL_LABELS:
            selected = [row for row in rows if row["label"] == label]
            if Counter(str(row["semantic_source"]) for row in selected) != expected_sources[split]:
                raise RuntimeError(f"S70 semantic source balance changed: {split}/{label}")
            for language in ("en", "zh"):
                variants = {
                    int(row["semantic_core_variant"])
                    for row in selected
                    if row["language"] == language
                }
                if variants != ({0, 1} if split == "test" else ({0} if split == "train" else {1})):
                    raise RuntimeError(f"S70 semantic variants changed: {split}/{label}/{language}/{variants}")
    frames: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows_by_split["test"]:
        frames[str(row["contrastive_frame_id"])].append(row)
    if len(frames) != 20:
        raise RuntimeError("S70 locked frame count changed")
    for frame, members in frames.items():
        if {str(row["label"]) for row in members} != set(NETWORK_EXACT_TOOL_LABELS):
            raise RuntimeError(f"S70 locked frame labels changed: {frame}")
        if len({str(row["contrastive_context_sha256"]) for row in members}) != 1:
            raise RuntimeError(f"S70 locked frame context changed: {frame}")
    all_rows = [row for split in base.SPLITS for row in rows_by_split[split]]
    for key in ("sample_id", "source_family_id", "rendered_input_sha256"):
        if len({str(row[key]) for row in all_rows}) != len(all_rows):
            raise RuntimeError(f"S70 {key} values are not unique")
    purity_fields = (
        "contains_parameter_schemas",
        "contains_full_tool_results",
        "contains_executor_text",
        "contains_planner_raw_json",
        "generated_rwkv_text",
        "hidden_acceptance_used",
    )
    if any(bool(row[field]) for row in all_rows for field in purity_fields):
        raise RuntimeError("S70 role purity changed")
    for left_index, left in enumerate(base.SPLITS):
        for right in base.SPLITS[left_index + 1 :]:
            for key in ("task_request", "source_family_id", "rendered_input_sha256"):
                if {str(row[key]) for row in rows_by_split[left]} & {
                    str(row[key]) for row in rows_by_split[right]
                }:
                    raise RuntimeError(f"S70 {key} overlap: {left}/{right}")
    roots = {split: set(LEXICONS[split]) for split in base.SPLITS}
    for left_index, left in enumerate(base.SPLITS):
        for right in base.SPLITS[left_index + 1 :]:
            if roots[left] & roots[right]:
                raise RuntimeError(f"S70 root overlap: {left}/{right}")


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


def s68_locked_isolation() -> tuple[list[tuple[str, Counter[bytes]]], set[str], dict[str, int]]:
    references: list[tuple[str, Counter[bytes]]] = []
    digests: set[str] = set()
    parsed = 0
    skipped: Counter[str] = Counter()
    with (S68 / "cases.jsonl").open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            match = SPLIT_PATTERN.search(line)
            if match is None:
                raise RuntimeError("S70 S68 isolation split marker missing")
            split = match.group(1)
            if split != "test":
                skipped[split] += 1
                continue
            row = json.loads(line)
            request = str(row["task_request"])
            encoded = request.encode("utf-8")
            references.append(
                (
                    f"s68-test-line-{line_number}",
                    Counter(encoded[index : index + 5] for index in range(max(0, len(encoded) - 4))),
                )
            )
            digests.add(hashlib.sha256(encoded).hexdigest())
            parsed += 1
    if parsed != 500 or skipped != Counter({"train": 2000, "dev": 500}):
        raise RuntimeError("S70 S68 isolation scan changed")
    return references, digests, {
        "s68_test_rows_json_parsed_for_similarity_only": parsed,
        "s68_test_labels_accessed": 0,
        "s68_test_requests_persisted": 0,
    }


def maximum_similarity(
    base: ModuleType,
    rows: Iterable[Mapping[str, Any]],
    references: Iterable[tuple[str, Counter[bytes]]],
) -> dict[str, Any]:
    maximum: dict[str, Any] = {"score": -1.0, "sample_id": "", "holdout_id": ""}
    cached = list(references)
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
        S69_FAILURE: S69_FAILURE_SHA256,
        S68 / "cases.jsonl": S68_CASES_SHA256,
        S68 / "manifest.json": S68_MANIFEST_SHA256,
        S68_LOCKED_RESULT: S68_LOCKED_RESULT_SHA256,
        S68_LOCKED_ANALYSIS: S68_FAILURE_SHA256,
        S66_LOCKED_RESULT: S66_LOCKED_RESULT_SHA256,
    }
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S70 dataset")
    for path, expected in frozen.items():
        actual = sha256_file(path) if path.is_file() else "missing"
        if actual != expected:
            raise RuntimeError(f"S70 frozen input changed: {path}: {actual}")
    if set(LOCKED_EN) != set(NETWORK_EXACT_TOOL_LABELS) or set(LOCKED_ZH) != set(
        NETWORK_EXACT_TOOL_LABELS
    ):
        raise RuntimeError("S70 locked semantic labels changed")
    base = load_module("rwkv_lh_s70_base", BASE_GENERATOR)
    formal = load_module("rwkv_lh_s70_formal", FORMAL_SOURCE)
    if set(formal.TEST_EN) != set(NETWORK_EXACT_TOOL_LABELS) or set(
        formal.TEST_ZH
    ) != set(NETWORK_EXACT_TOOL_LABELS):
        raise RuntimeError("S70 formal source labels changed")
    install_construction(base, formal)
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

    ladder, forbidden_paths, task_ids, audit_hashes = base.holdout_contract()
    forbidden_literals = {value for value in forbidden_paths | task_ids if len(value) >= 6}
    for row in all_rows:
        matches = [value for value in forbidden_literals if value in str(row["task_request"])]
        if matches:
            raise RuntimeError(f"S70 row contains holdout literal: {row['sample_id']}:{matches[:3]}")
    ladder_maximum = maximum_similarity(
        base,
        all_rows,
        ((identity, base.byte_ngrams(text)) for identity, text in ladder),
    )
    if float(ladder_maximum["score"]) >= 0.95:
        raise RuntimeError(f"S70 Ladder holdout similarity failed: {ladder_maximum}")

    s68_references, s68_digests, s68_isolation = s68_locked_isolation()
    for row in all_rows:
        digest = hashlib.sha256(str(row["task_request"]).encode("utf-8")).hexdigest()
        if digest in s68_digests:
            raise RuntimeError(f"S70 reused an S68 locked request: {row['sample_id']}")
    s68_maximum = maximum_similarity(base, all_rows, s68_references)
    if float(s68_maximum["score"]) >= 0.95:
        raise RuntimeError(f"S70 S68-locked similarity failed: {s68_maximum}")

    base.DATASET_VERSION = DATASET_VERSION
    base.STATE_ROW_SCHEMA = STATE_ROW_SCHEMA
    exported, token_stats = base.state_rows(RWKVTokenizer(), rows_by_split)
    for split, rows in exported.items():
        for index, row in enumerate(rows):
            row["schema_version"] = STATE_ROW_SCHEMA
            row["dataset_version"] = DATASET_VERSION
            row["sample_id"] = f"S70-STATE-{split.upper()}-{index:04d}"

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
        "schema_version": "rwkv-lh.network-selector-current-v2-uniform-manifest.s70.v1",
        "dataset_version": DATASET_VERSION,
        "purpose": "uniformly train all 25 operation semantics inside the current single-responsibility V2 architecture",
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
            "s65_training_rows": 0,
            "s69_failure_record": str(S69_FAILURE.relative_to(ROOT)),
            "s69_failure_record_sha256": sha256_file(S69_FAILURE),
            "compact_schema_version": base.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
            "contract_projection_version": base.SELECTOR_CONTRACT_STAGE_PROJECTION_VERSION,
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
            "ladder_acceptance_sha256": base.FROZEN[base.LADDER / "acceptance.json"],
            "e3_results_sha256": base.FROZEN[base.E3_RUN / "results.json"],
            "e3_audit_sha256": dict(sorted(audit_hashes.items())),
            "similarity_algorithm": "utf8-byte-5gram-cosine.v1",
            "threshold_exclusive": 0.95,
            "maximum_ladder_similarity": ladder_maximum,
            "maximum_s68_locked_similarity": s68_maximum,
            "exact_s68_locked_request_overlap": 0,
            **s68_isolation,
            "optimizer_use": False,
            "candidate_selection_use": False,
        },
        "split_integrity": {
            "root_pool_intersection_count": 0,
            "exact_request_overlap": 0,
            "source_family_overlap": 0,
            "rendered_input_overlap": 0,
        },
        "locked_test": {
            "source": "new effect/postcondition and negative-boundary inventory",
            "variants_per_label_language": 2,
            "shared_contrastive_frames": 20,
            "opened_by_model_runner": False,
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
            "base_path": str(BASE_GENERATOR.relative_to(ROOT)),
            "base_sha256": BASE_GENERATOR_SHA256,
            "formal_source_path": str(FORMAL_SOURCE.relative_to(ROOT)),
            "formal_source_sha256": FORMAL_SOURCE_SHA256,
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
        "# S70 current-V2 uniform semantic Selector corpus\n\n"
        "All rows are fresh single-responsibility CurrentDirectStageV2 inputs; "
        "the new locked test is effect/postcondition based.\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "s70_current_v2_uniform_dataset_finalized",
                "counts": base.EXPECTED_COUNTS,
                "maximum_ladder_similarity": ladder_maximum,
                "maximum_s68_locked_similarity": s68_maximum,
                "cases_sha256": sha256_file(OUTPUT / "cases.jsonl"),
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
