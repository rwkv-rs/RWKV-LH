#!/usr/bin/env python3
"""Generate the frozen compact current-Harness S28 96%-gate dataset."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from rwkv_lh.exact_tool_selector.compact_protocol_v3 import (
    COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
    compact_selector_menu_digest,
    render_compact_selector_bootstrap,
    render_compact_selector_step,
)
from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.exact_tool_selector.protocol import canonical_digest
from rwkv_lh.exact_tool_selector.runtime_projection import (
    SELECTOR_STAGE_PROJECTION_VERSION,
    build_network_selector_input,
)
from rwkv_lh.schema import (
    ActionRecord,
    ActionStatus,
    GoalState,
    ModelCheckpoint,
    ModelLaneKind,
    RunState,
)


ROOT = Path("/home/chase/GitHub/RWKV-LH")
SOURCE = ROOT / "data/datasets/rwkv_lh_network_exact_tool_selector_v2_4/cases.jsonl"
ECRA = ROOT / "data/datasets/rwkv_lh_ecra_route_v1/cases.json"
PROTOCOL_SOURCE = ROOT / "rwkv_lh/exact_tool_selector/compact_protocol_v3.py"
PREREGISTRATION = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S28_COMPACT_CURRENT_HARNESS_96_PREREGISTRATION.md"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_compact_current_harness_s28_v1"
SOURCE_SHA256 = "78c90285defed1925691dc45325ea4380093345c39763c3bb32373e23733e9fc"
ECRA_SHA256 = "7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a"
PROTOCOL_SOURCE_SHA256 = "976309b22a2d4328500fe9f69ff24d550704f0857024929fcc9396073c4e0508"
PREREGISTRATION_SHA256 = "aed6c54e19c9ab07a058aead57a4d88c5862a720323e157c64851a925e8935dc"
VERSION = "rwkv-lh.network-selector.compact-current-harness-s28.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-compact-current-harness-row.s28.v1"

SPLIT_PER_LABEL = {"train": 240, "dev": 30, "test": 30}
LANGUAGE_PER_LABEL = {
    "train": {"en": 160, "zh": 80},
    "dev": {"en": 15, "zh": 15},
    "test": {"en": 15, "zh": 15},
}
PHASE_PER_LANGUAGE = {
    "train": {
        "en": {0: 80, 1: 64, 2: 16},
        "zh": {0: 40, 1: 32, 2: 8},
    },
    "dev": {"en": {0: 7, 1: 6, 2: 2}, "zh": {0: 7, 1: 6, 2: 2}},
    "test": {"en": {0: 7, 1: 6, 2: 2}, "zh": {0: 7, 1: 6, 2: 2}},
}

PREDECESSORS = {
    "list_directory": ("make_directory", "move_file"),
    "search_text": ("list_directory", "read_file"),
    "read_file": ("list_directory", "search_text"),
    "read_json": ("list_directory", "search_text"),
    "file_digest": ("list_directory", "read_file"),
    "write_file": ("make_directory", "read_file"),
    "write_json": ("make_directory", "read_json"),
    "patch_json": ("read_json", "bind_evidence"),
    "replace_text": ("search_text", "read_file"),
    "remove_line": ("search_text", "read_file"),
    "append_file": ("read_file", "make_directory"),
    "make_directory": ("list_directory", "read_file"),
    "copy_file": ("list_directory", "file_digest"),
    "move_file": ("list_directory", "file_digest"),
    "delete_file": ("list_directory", "file_digest"),
    "bind_evidence": ("search_text", "read_file"),
    "check_command": ("read_file", "search_text"),
    "run_command": ("read_file", "search_text"),
    "web_search": ("read_file", "search_text"),
    "connector_lookup": ("web_search", "read_file"),
    "calculator": ("connector_lookup", "read_json"),
    "date_diff": ("read_json", "connector_lookup"),
    "current_time": ("read_file", "connector_lookup"),
    "final_answer": ("check_command", "bind_evidence"),
    "ABSTAIN": ("read_file", "web_search"),
}

EN_HELDOUT = {
    "list_directory": (
        "Return only entry names, kinds, and sizes beneath {path}; do not open file bodies",
        "Inventory filesystem metadata under {path}; content inspection is not requested",
    ),
    "search_text": (
        "Locate {marker} in local project text and report bounded file-and-line matches without going online",
        "Find workspace lines matching {marker}; this is local source search rather than internet discovery",
    ),
    "read_file": (
        "Continue observing a bounded plain-text byte slice from the non-JSON file {path}/status.txt",
        "Show the next limited UTF-8 range of {path}/notes.log as ordinary text, not parsed JSON",
    ),
    "read_json": (
        "Parse {path}/state.json and expose the next bounded segment of its canonical JSON value",
        "Inspect structured content from the local JSON document {path}/record.json rather than raw text bytes",
    ),
    "file_digest": (
        "Report only the SHA-256 identity and byte length of {path}/payload.bin, leaving it untouched",
        "Fingerprint {path}/archive.dat by checksum and size without opening, copying, or executing it",
    ),
    "write_file": (
        "Materialize the complete supplied non-JSON text atomically at {path}/summary.txt",
        "Create or replace {path}/answer.md with the entire known UTF-8 document, not a JSON value",
    ),
    "write_json": (
        "Persist the entire supplied JSON value atomically at {path}/result.json",
        "Create or replace {path}/state.json from the complete structured value, removing omitted keys",
    ),
    "patch_json": (
        "Change only the named top-level fields in {path}/record.json and retain every unspecified field",
        "Merge the explicit partial object into {path}/settings.json instead of replacing the full JSON document",
    ),
    "replace_text": (
        "Substitute the single exact phrase OLD_{suffix} with NEW_{suffix} inside {path}/notes.txt",
        "Change one precisely observed text occurrence in {path}/README.md while preserving all other bytes",
    ),
    "remove_line": (
        "Drop the one complete line LEGACY_{suffix} from {path}/app.env and retain adjacent lines",
        "Erase exactly one full matching UTF-8 line from {path}/requirements.txt, not the file",
    ),
    "append_file": (
        "Add the supplied audit record after the existing bytes of {path}/events.log",
        "Extend {path}/CHANGELOG.md with the known trailing paragraph without replacing current content",
    ),
    "make_directory": (
        "Create the empty workspace folder {path}/artifacts without writing a file",
        "Ensure the scoped directory tree {path}/output/current exists; no document content is involved",
    ),
    "copy_file": (
        "Duplicate exact bytes from {path}/source.bin to {path}/backup.bin while keeping source.bin",
        "Create a byte-identical second file at {path}/copy.dat and leave {path}/original.dat present",
    ),
    "move_file": (
        "Rename {path}/draft.log to {path}/verified.log so the former path disappears",
        "Relocate {path}/incoming.bin to {path}/archive.bin rather than leaving a copied source",
    ),
    "delete_file": (
        "Remove only the explicitly scoped workspace file {path}/obsolete.tmp",
        "Delete {path}/retired.log without touching siblings or a broader directory",
    ),
    "bind_evidence": (
        "Retain the already observed lines 8 through 12 of {path}/report.md with their locator and exact quote",
        "Bind a precise local source span from {path}/audit.log as citable evidence, including line provenance",
    ),
    "check_command": (
        "Execute the read-only verification argv for {path} and observe its registered exit code",
        "Run a non-mutating test, lint, or status inspection in {path} with shell disabled",
    ),
    "run_command": (
        "Launch the approved local argv in {path} that may intentionally update generated artifacts",
        "Execute the scoped build, formatter, installation, or migration command whose expected effect changes files",
    ),
    "web_search": (
        "Discover public internet pages about {marker} and retain web-source evidence; do not search workspace files",
        "Fetch or search the public web for current information on {marker}, without assuming a structured record API",
    ),
    "connector_lookup": (
        "Query a structured public source for the exact package or repository record {marker}",
        "Look up the precise paper, weather, alert, or package entity {marker} through a structured connector",
    ),
    "calculator": (
        "Evaluate the already-known arithmetic expression ({number}+19)*4 without discovering new facts",
        "Compute the numeric result of ({number}*7)-11 using only the supplied operands",
    ),
    "date_diff": (
        "Compute the absolute calendar-day gap between 2025-02-03 and 2026-04-{day}",
        "Return the number of days separating the two known ISO dates 2024-06-11 and 2026-01-{day}",
    ),
    "current_time": (
        "Observe the live clock reading in the Asia/Shanghai IANA timezone",
        "Report the current time for Europe/Berlin rather than calculating from a stored timestamp",
    ),
    "final_answer": (
        "All required actions and checks are complete; return the grounded user-facing result without another tool",
        "No operation remains and the necessary evidence is available, so finish with the honest final response",
    ),
    "ABSTAIN": (
        "The requested next action is ambiguous and no single authorized tool can be selected safely",
        "Required observable scope is missing or unsupported, so choose no operation rather than guessing",
    ),
}

ZH_CORE = {
    "list_directory": "只列出 {path} 下有界的路径、类型和大小，不读取文件正文",
    "search_text": "只在本地工作区文本中查找 {marker} 的有界行匹配，不访问互联网",
    "read_file": "读取本地非 JSON 文件 {path}/notes.txt 的下一段有界 UTF-8 字节",
    "read_json": "解析本地 {path}/record.json，并读取规范 JSON 的有界区间",
    "file_digest": "只观察 {path}/payload.bin 的 SHA-256 与字节数，不读取或修改内容",
    "write_file": "把完整的非 JSON 文本原子写入 {path}/result.txt",
    "write_json": "把完整 JSON 值原子写入 {path}/result.json",
    "patch_json": "仅更新 {path}/record.json 的指定顶层键并保留其余键",
    "replace_text": "把 {path}/notes.txt 中唯一的 OLD_{suffix} 精确替换为 NEW_{suffix}",
    "remove_line": "从 {path}/app.env 中删除一整行 LEGACY_{suffix}，保留其他行",
    "append_file": "把给定记录追加到 {path}/events.log 的现有内容之后",
    "make_directory": "创建工作区目录 {path}/output，不创建文件",
    "copy_file": "把 {path}/source.bin 原样复制到 backup.bin，并保留源文件",
    "move_file": "把 {path}/old.log 移动或重命名为 verified.log，使旧路径消失",
    "delete_file": "只删除明确限定的工作区路径 {path}/obsolete.tmp",
    "bind_evidence": "绑定 {path}/report.md 中已观察到的精确行区间、定位与原文",
    "check_command": "运行 {path} 中不会修改内容的测试、检查或状态命令",
    "run_command": "运行 {path} 中预期可能修改工作区内容的本地命令",
    "web_search": "在公开互联网检索 {marker} 并保留网页来源证据，不搜索本地文件",
    "connector_lookup": "通过结构化公开数据源查询精确记录 {marker}",
    "calculator": "只用已知操作数计算表达式 ({number}+19)*4",
    "date_diff": "计算已知日期 2025-02-03 与 2026-04-{day} 的日历天数差",
    "current_time": "观察 Asia/Shanghai IANA 时区的当前时间",
    "final_answer": "所有操作与检查均已完成，不再调用工具，直接返回真实结果",
    "ABSTAIN": "当前目标含糊、缺少范围或不受支持，无法安全选择唯一工具",
}

TRAIN_ZH_FRAMES = (
    "请{intent}。", "当前唯一的下一步是{intent}。", "按限定范围{intent}。", "这一步需要{intent}。",
    "请直接完成：{intent}。", "为了继续任务，先{intent}。", "按审计要求{intent}。", "不要改做其他操作，只{intent}。",
)
DEV_ZH_FRAMES = ("此刻应当{intent}。", "下一项明确工作：{intent}。", "在当前阶段仅需{intent}。")
TEST_ZH_FRAMES = ("现在执行这一项：{intent}。", "后续正确动作是{intent}。", "请在本轮只完成{intent}。")
DEV_EN_FRAMES = (
    "At this stage, {intent}.", "The one required next operation is to {intent}.",
    "Proceed only by doing this: {intent}.", "For the current bounded scope, {intent}.",
    "The run now needs you to {intent}.",
)
TEST_EN_FRAMES = (
    "The immediate action must {intent}.", "Continue the run by doing exactly this: {intent}.",
    "For this step alone, {intent}.", "The next concrete operation is to {intent}.",
    "Within the authorized scope, {intent}.",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_key(*parts: object) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()


def compact_source_objective(row: dict[str, Any]) -> str:
    return str(row["selector_projection"]["stage_objective"]).split(" The unique task scope is the ", 1)[0].strip()


def surface_values(label: str, split: str, language: str, index: int) -> dict[str, object]:
    digest = stable_key("S28", label, split, language, index)
    suffix = digest[:10]
    return {
        "path": f"work/{split}/{label.lower().replace('_', '-')}-{suffix}",
        "marker": f"MARKER_{label.upper()}_{suffix.upper()}",
        "suffix": suffix,
        "number": 10 + int(digest[:4], 16) % 80,
        "day": 1 + int(digest[4:8], 16) % 27,
    }


def heldout_english_intent(label: str, split: str, index: int) -> tuple[str, str]:
    values = surface_values(label, split, "en", index)
    core_index = 0 if split == "dev" else 1
    core = EN_HELDOUT[label][core_index].format(**values)
    frames = DEV_EN_FRAMES if split == "dev" else TEST_EN_FRAMES
    frame_index = index % len(frames)
    return frames[frame_index].format(intent=core).rstrip("."), f"{split}-en-core{core_index}-frame{frame_index}"


def chinese_intent(label: str, split: str, index: int) -> tuple[str, str]:
    values = surface_values(label, split, "zh", index)
    core = ZH_CORE[label].format(**values)
    frames = TRAIN_ZH_FRAMES if split == "train" else (DEV_ZH_FRAMES if split == "dev" else TEST_ZH_FRAMES)
    frame_index = index % len(frames)
    return frames[frame_index].format(intent=core).rstrip("。"), f"{split}-zh-frame{frame_index}"


def prior_intent(language: str, label: str, token: str) -> str:
    values = {
        "path": f"work/history/{label.lower().replace('_', '-')}-{token}",
        "marker": f"HISTORY_{label.upper()}_{token.upper()}",
        "suffix": token,
        "number": 31,
        "day": 17,
    }
    if language == "zh":
        return ZH_CORE[label].format(**values)
    return EN_HELDOUT[label][0].format(**values)


def sequence_request(language: str, target: str, predecessors: tuple[str, ...], token: str) -> str:
    prior = [prior_intent(language, label, f"{token}{index}").rstrip("。.") for index, label in enumerate(predecessors)]
    target = target.rstrip("。.")
    if not prior:
        return f"{target}。范围编号：{token}。" if language == "zh" else f"{target}. Scope id: {token}."
    if language == "zh":
        if len(prior) == 1:
            return f"先{prior[0]}；成功后，{target}。范围编号：{token}。"
        return f"先{prior[0]}；然后{prior[1]}；两项均成功后，{target}。范围编号：{token}。"
    if len(prior) == 1:
        return f"First, {prior[0]}. After it succeeds, {target}. Scope id: {token}."
    return f"First, {prior[0]}. Then, {prior[1]}. After both succeed, {target}. Scope id: {token}."


def parent_checkpoint(action_index: int) -> ModelCheckpoint:
    return ModelCheckpoint(
        checkpoint_id=f"S28-PARENT-{action_index:02d}", lane_id="LANE:SELECTOR",
        lane_kind=ModelLaneKind.SELECTOR, parent_checkpoint_id=None,
        model="dataset-projection-only", transport="none", transcript="",
        transcript_digest="0" * 64, token_count=0,
        native_state_metadata={"action_index": action_index},
    )


def append_success(state: RunState, operation: str, sequence: int) -> None:
    metadata: dict[str, object] = {}
    if operation in {"list_directory", "read_file", "read_json", "web_search", "connector_lookup"}:
        metadata = {"complete": True, "truncated": False}
    state.actions[f"S28-A{sequence:02d}"] = ActionRecord(
        action_id=f"S28-A{sequence:02d}", sequence=sequence, status=ActionStatus.SUCCEEDED,
        action_type=operation, arguments={}, wire_arguments={}, action_fingerprint="",
        idempotency_key="", decision_id="", request_id="", started_at="", ended_at="",
        result={"success": True, "outcome_type": "success", "metadata": metadata}, outcome_type="success",
    )


def phase_depths(split: str, language: str, label: str) -> list[int]:
    values = [depth for depth, count in PHASE_PER_LANGUAGE[split][language].items() for _ in range(count)]
    return [value for _index, value in sorted(enumerate(values), key=lambda item: stable_key("phase", split, language, label, item[0], item[1]))]


def build_row(
    *, label: str, split: str, language: str, index: int, phase_depth: int,
    target_intent: str, lexical_family_id: str, source: dict[str, object],
) -> dict[str, object]:
    token = stable_key("S28-row", label, split, language, index)[:12]
    predecessors = PREDECESSORS[label][:phase_depth]
    request = sequence_request(language, target_intent, predecessors, token)
    state = RunState(
        run_id=f"S28-DATA-{token}",
        goal=GoalState.create(request=request, constraints=(), workspace_root=ROOT / "temp/s28-projection-workspace"),
    )
    history_inputs: list[dict[str, object]] = []
    history_steps: list[str] = []
    parent_action_index: int | None = None
    for sequence, operation in enumerate(predecessors, 1):
        selector_input = build_network_selector_input(state, None if parent_action_index is None else parent_checkpoint(parent_action_index))
        history_inputs.append(selector_input.to_dict())
        history_steps.append(render_compact_selector_step(selector_input))
        parent_action_index = len(state.actions)
        append_success(state, operation, sequence)
    selector_input = build_network_selector_input(state, None if parent_action_index is None else parent_checkpoint(parent_action_index))
    bootstrap = render_compact_selector_bootstrap(selector_input)
    step = render_compact_selector_step(selector_input)
    trajectory = bootstrap + "".join("\n" + item for item in [*history_steps, step])
    sample_id = f"NETSEL-S28-{split.upper()}-{label.upper()}-{language.upper()}-{index:03d}"
    return {
        "schema_version": ROW_SCHEMA,
        "dataset_version": VERSION,
        "sample_id": sample_id,
        "semantic_family_id": f"S28-{split}-{label.lower()}-{language}-{index:03d}",
        "lexical_family_id": lexical_family_id,
        "entity_family_id": token,
        "split": split,
        "label": label,
        "language": language,
        "phase": "first" if phase_depth == 0 else f"continuation_{phase_depth}",
        "decision_index": phase_depth,
        "expected_history_labels": list(predecessors),
        "history_steps": history_steps,
        "history_selector_inputs": history_inputs,
        "selector_input": selector_input.to_dict(),
        "selector_input_sha256": canonical_digest(selector_input.to_dict()),
        "compact_input_schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "compact_menu_digest": compact_selector_menu_digest(),
        "bootstrap": bootstrap,
        "step": step,
        "trajectory_rendered_input": trajectory,
        "trajectory_rendered_input_sha256": hashlib.sha256(trajectory.encode("utf-8")).hexdigest(),
        "projection_version": SELECTOR_STAGE_PROJECTION_VERSION,
        "request_identifiable": True,
        "persistent_history_replay_required": bool(history_steps),
        "source": source,
        "generated_rwkv_text": False,
        "contains_parameter_schemas": False,
        "contains_full_tool_results": False,
        "contains_executor_text": False,
    }


def byte_ngrams(text: str, n: int = 5) -> Counter[bytes]:
    raw = text.encode("utf-8")
    return Counter(raw[index:index+n] for index in range(max(0, len(raw)-n+1)))


def cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    return dot / math.sqrt(sum(value * value for value in left.values()) * sum(value * value for value in right.values()))


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S28 dataset")
    expected_hashes = {
        SOURCE: SOURCE_SHA256, ECRA: ECRA_SHA256, PROTOCOL_SOURCE: PROTOCOL_SOURCE_SHA256,
        PREREGISTRATION: PREREGISTRATION_SHA256,
    }
    for path, expected in expected_hashes.items():
        if sha256_file(path) != expected:
            raise RuntimeError(f"S28 frozen source identity changed: {path}")
    source_rows = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines()]
    source_by_label = {
        label: [row for row in source_rows if row["split"] == "train" and row["label"] == label]
        for label in NETWORK_EXACT_TOOL_LABELS
    }
    if any(len(rows) != 240 for rows in source_by_label.values()):
        raise RuntimeError("S28 v2.4 source class balance changed")

    rows: list[dict[str, object]] = []
    for split in ("train", "dev", "test"):
        for label in NETWORK_EXACT_TOOL_LABELS:
            for language in ("en", "zh"):
                count = LANGUAGE_PER_LABEL[split][language]
                depths = phase_depths(split, language, label)
                if len(depths) != count:
                    raise RuntimeError("S28 phase schedule changed")
                if split == "train" and language == "en":
                    candidates = source_by_label[label]
                    selected_indices = sorted(
                        range(len(candidates)),
                        key=lambda index: (index % 6, stable_key("source", label, index)),
                    )
                    # Round-robin over all six operation-contract variants.
                    buckets = {variant: [index for index in selected_indices if index % 6 == variant] for variant in range(6)}
                    selected: list[int] = []
                    while len(selected) < count:
                        for variant in range(6):
                            if buckets[variant] and len(selected) < count:
                                selected.append(buckets[variant].pop(0))
                    for index, (source_index, depth) in enumerate(zip(selected, depths)):
                        source = candidates[source_index]
                        rows.append(build_row(
                            label=label, split=split, language=language, index=index, phase_depth=depth,
                            target_intent=compact_source_objective(source),
                            lexical_family_id=f"train-en-v24-contract-{source_index % 6}",
                            source={"kind": "v2_4_all_six_contract_variants", "sample_id": source["sample_id"], "semantic_family_id": source["semantic_family_id"], "variant": source_index % 6},
                        ))
                else:
                    for index, depth in enumerate(depths):
                        if language == "en":
                            intent, family = heldout_english_intent(label, split, index)
                            source = {"kind": "heldout_english_contrast_family", "split": split, "family": family}
                        else:
                            intent, family = chinese_intent(label, split, index)
                            source = {"kind": "partitioned_chinese_contract_family", "split": split, "family": family}
                        rows.append(build_row(
                            label=label, split=split, language=language, index=index,
                            phase_depth=depth, target_intent=intent,
                            lexical_family_id=f"{label.lower()}-{family}", source=source,
                        ))

    expected_split = {split: count * len(NETWORK_EXACT_TOOL_LABELS) for split, count in SPLIT_PER_LABEL.items()}
    split_counts = Counter(str(row["split"]) for row in rows)
    if split_counts != Counter(expected_split):
        raise RuntimeError(f"S28 split counts changed: {split_counts}")
    label_counts = {split: Counter(str(row["label"]) for row in rows if row["split"] == split) for split in expected_split}
    if any(value != Counter({label: SPLIT_PER_LABEL[split] for label in NETWORK_EXACT_TOOL_LABELS}) for split, value in label_counts.items()):
        raise RuntimeError("S28 class balance changed")
    language_counts = {split: Counter(str(row["language"]) for row in rows if row["split"] == split) for split in expected_split}
    expected_language_counts = {
        split: Counter({language: LANGUAGE_PER_LABEL[split][language] * 25 for language in ("en", "zh")})
        for split in expected_split
    }
    if language_counts != expected_language_counts:
        raise RuntimeError("S28 language balance changed")
    phase_counts = {split: Counter(str(row["phase"]) for row in rows if row["split"] == split) for split in expected_split}
    if len({str(row["sample_id"]) for row in rows}) != len(rows) or len({str(row["trajectory_rendered_input"]) for row in rows}) != len(rows):
        raise RuntimeError("S28 exact row identity or trajectory uniqueness changed")
    for field in ("semantic_family_id", "lexical_family_id", "entity_family_id"):
        values = {split: {str(row[field]) for row in rows if row["split"] == split} for split in expected_split}
        if any(values[left] & values[right] for left, right in (("train", "dev"), ("train", "test"), ("dev", "test"))):
            raise RuntimeError(f"S28 {field} crosses splits")
    for row in rows:
        if len(row["history_steps"]) != int(row["decision_index"]):
            raise RuntimeError("S28 history depth changed")
        if not str(row["bootstrap"]).startswith("SelectorMenuV3: ") or "\nSelectorTaskV3: " not in str(row["bootstrap"]):
            raise RuntimeError("S28 compact bootstrap changed")
        if not str(row["step"]).startswith("SelectorStepV3: "):
            raise RuntimeError("S28 compact step changed")
        if any(bool(row[key]) for key in ("generated_rwkv_text", "contains_parameter_schemas", "contains_full_tool_results", "contains_executor_text")):
            raise RuntimeError("S28 forbidden content marker changed")

    holdout = json.loads(ECRA.read_text(encoding="utf-8"))["cases"]
    holdout_grams = [(str(case["case_id"]), byte_ngrams(str(case["instruction"]))) for case in holdout]
    maximum: dict[str, object] = {"score": -1.0, "sample_id": "", "holdout_id": ""}
    for row in rows:
        grams = byte_ngrams(str(row["selector_input"]["task_request"]))
        for holdout_id, reference in holdout_grams:
            score = cosine(grams, reference)
            if score > float(maximum["score"]):
                maximum = {"score": score, "sample_id": row["sample_id"], "holdout_id": holdout_id}
    if float(maximum["score"]) >= 0.75:
        raise RuntimeError(f"S28 ECRA similarity gate failed: {maximum}")

    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_network_selector_s28.", dir=OUTPUT.parent))
    cases = staging / "cases.jsonl"
    write_jsonl(cases, rows)
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": "compact current-Harness 2.9B exact-tool classification with a frozen >=96% blind gate",
        "architecture": "current-direct-LongHorizonModel-dual-state",
        "counts": dict(sorted(split_counts.items())),
        "label_counts": {split: dict(sorted(value.items())) for split, value in label_counts.items()},
        "language_counts": {split: dict(sorted(value.items())) for split, value in language_counts.items()},
        "phase_counts": {split: dict(sorted(value.items())) for split, value in phase_counts.items()},
        "class_count": 25,
        "executable_tool_count": 23,
        "control_label_count": 2,
        "input_protocol": {
            "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
            "menu_digest": compact_selector_menu_digest(),
            "source_path": str(PROTOCOL_SOURCE.relative_to(ROOT)),
            "source_sha256": PROTOCOL_SOURCE_SHA256,
            "menu_first_task_last": True,
            "names_and_descriptions_only": True,
        },
        "projection": {"version": SELECTOR_STAGE_PROJECTION_VERSION, "persistent_history_replay": True, "maximum_history_steps": 2, "current_feature_segment_only": True},
        "generated_rwkv_text_count": 0,
        "contains_parameter_schemas": False,
        "contains_full_tool_results": False,
        "contains_executor_text": False,
        "validation": {
            "request_identifiable_rows": len(rows), "exact_trajectory_duplicates": 0,
            "cross_split_semantic_family_overlap": 0, "cross_split_lexical_family_overlap": 0,
            "cross_split_entity_family_overlap": 0, "all_labels_balanced_in_every_split": True,
            "holdout_similarity": {"algorithm": "utf8-byte-5gram-cosine.v1", "compared_field": "selector_input.task_request", "threshold_exclusive": 0.75, "maximum": maximum, "holdout_sha256": ECRA_SHA256},
        },
        "sources": {
            "v2_4_operation_contract": {"path": str(SOURCE.relative_to(ROOT)), "sha256": SOURCE_SHA256},
            "ecra120_evaluation_only": {"path": str(ECRA.relative_to(ROOT)), "sha256": ECRA_SHA256},
        },
        "preregistration": {"path": str(PREREGISTRATION.relative_to(ROOT)), "sha256": PREREGISTRATION_SHA256},
        "generation": f"uv run --no-sync python {Path(__file__).resolve()}",
        "generator": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": sha256_file(Path(__file__).resolve())},
        "files": {"cases.jsonl": {"rows": len(rows), "sha256": sha256_file(cases)}},
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (staging / "README.md").write_text(
        "# Compact current-Harness Selector S28 v1\n\n"
        "- Fixed train/dev/blind test: 6000/750/750, all 25 labels balanced.\n"
        "- V3 keeps all tools, renders compact menu first and literal task last.\n"
        "- Test is excluded from candidate training and selection; see manifest and preregistration.\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
