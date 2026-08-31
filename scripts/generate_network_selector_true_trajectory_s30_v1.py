#!/usr/bin/env python3
"""Generate the frozen S30 natural true-trajectory Selector dataset."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections import Counter
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
PROTOCOL = ROOT / "rwkv_lh/exact_tool_selector/compact_protocol_v3.py"
PREREGISTRATION = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S30_TRUE_TRAJECTORY_ZERO_STATE_96_PREREGISTRATION.md"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_true_trajectory_s30_v1"
SOURCE_SHA256 = "78c90285defed1925691dc45325ea4380093345c39763c3bb32373e23733e9fc"
ECRA_SHA256 = "7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a"
PROTOCOL_SHA256 = "976309b22a2d4328500fe9f69ff24d550704f0857024929fcc9396073c4e0508"
PREREGISTRATION_SHA256 = "a5dd5b78e2350672f4aac592c81d64c4d9f5a85db47c90676b17a2a0505c083c"
VERSION = "rwkv-lh.network-selector.true-trajectory-s30.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-true-trajectory-row.s30.v1"
SPLIT_PER_LABEL = {"train": 80, "dev": 20, "test": 20}
VARIANTS = {"train": (0, 1, 2, 3), "dev": (4,), "test": (5,)}
EXECUTABLE_LABELS = NETWORK_EXACT_TOOL_LABELS[:-2]

PREDECESSORS = {
    "list_directory": ("make_directory", "file_digest"),
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
    "connector_lookup": ("read_json", "read_file"),
    "calculator": ("read_file", "read_json"),
    "date_diff": ("read_json", "read_file"),
    "current_time": ("read_json", "read_file"),
    "ABSTAIN": ("read_file", "list_directory"),
}

SUCCESSORS = {
    "list_directory": ("read_file", "search_text"),
    "search_text": ("read_file", "bind_evidence"),
    "read_file": ("connector_lookup", "web_search"),
    "read_json": ("connector_lookup", "date_diff"),
    "file_digest": ("copy_file", "move_file"),
    "write_file": ("check_command", "read_file"),
    "write_json": ("check_command", "read_json"),
    "patch_json": ("check_command", "read_json"),
    "replace_text": ("check_command", "read_file"),
    "remove_line": ("check_command", "read_file"),
    "append_file": ("check_command", "read_file"),
    "make_directory": ("write_file", "list_directory"),
    "copy_file": ("file_digest", "check_command"),
    "move_file": ("list_directory", "check_command"),
    "delete_file": ("list_directory", "check_command"),
    "bind_evidence": ("check_command", "write_file"),
    "check_command": ("bind_evidence", "read_file"),
    "run_command": ("check_command", "list_directory"),
    "web_search": ("bind_evidence", "write_file"),
    "connector_lookup": ("calculator", "bind_evidence"),
    "calculator": ("write_file", "bind_evidence"),
    "date_diff": ("write_file", "bind_evidence"),
    "current_time": ("write_file", "bind_evidence"),
}

ZH_CORE = {
    "list_directory": "列出 {path} 下有界的路径、类型和大小，不读取文件正文",
    "search_text": "只在本地项目文本中查找 {marker} 的行匹配，不访问互联网",
    "read_file": "读取本地非 JSON 文件 {path}/notes.txt 的有界 UTF-8 内容",
    "read_json": "解析本地 {path}/record.json 并观察其中的规范 JSON 内容",
    "file_digest": "取得 {path}/payload.bin 的 SHA-256 与字节数且不修改它",
    "write_file": "把已知的完整非 JSON 文本写入 {path}/result.txt",
    "write_json": "把已知的完整 JSON 值写入 {path}/result.json",
    "patch_json": "只更新 {path}/record.json 的指定顶层键并保留其他键",
    "replace_text": "把 {path}/notes.txt 中唯一的 OLD_{suffix} 替换为 NEW_{suffix}",
    "remove_line": "从 {path}/app.env 删除完整一行 LEGACY_{suffix} 并保留其余行",
    "append_file": "把给定记录追加到 {path}/events.log 的现有内容之后",
    "make_directory": "创建工作区目录 {path}/output 而不是文件",
    "copy_file": "将 {path}/source.bin 原样复制到 backup.bin 并保留源文件",
    "move_file": "将 {path}/old.log 移动到 verified.log 使旧路径消失",
    "delete_file": "只删除明确限定的工作区文件 {path}/obsolete.tmp",
    "bind_evidence": "绑定 {path}/report.md 已观察行的定位与精确原文",
    "check_command": "运行不会修改工作区的测试、检查或状态命令",
    "run_command": "运行预期可能修改工作区内容的本地 argv 命令",
    "web_search": "在公开互联网查找 {marker} 并保留网页来源证据",
    "connector_lookup": "通过结构化公开源查询精确记录 {marker}",
    "calculator": "只用已经给出的操作数计算表达式 ({number}+19)*4",
    "date_diff": "计算已知日期 2025-02-03 与 2026-04-{day} 的日历天数差",
    "current_time": "观察 Asia/Shanghai IANA 时区的当前时间",
    "ABSTAIN": "请求中的下一项工作含糊或不受支持，无法安全确定唯一操作",
}

EN_FRAMES = {
    "train": (
        "Please {sequence}, then report the verified outcome for request {token}.",
        "For request {token}, {sequence}; return only the grounded result afterward.",
        "Complete this ordered workspace task: {sequence}. Reference {token}.",
        "Within the authorized scope {token}, {sequence}, and summarize what was established.",
    ),
    "dev": (
        "Carry out the following ordered request ({token}): {sequence}. Report the result.",
        "The requested workflow for {token} is: {sequence}. Give a grounded response afterward.",
    ),
    "test": (
        "Handle request {token} in this order: {sequence}. Then provide the supported outcome.",
        "For the scoped job {token}, do the following sequence: {sequence}; report what is verified.",
    ),
}

ZH_FRAMES = {
    "train": (
        "请按顺序完成请求 {token}：{sequence}；随后报告经过验证的结果。",
        "对于范围 {token}，依次{sequence}，完成后给出有依据的答复。",
        "任务 {token} 的操作顺序是：{sequence}；最后汇报真实结果。",
        "在授权范围 {token} 内，先后{sequence}，再说明已经确认的结果。",
    ),
    "dev": (
        "请处理有界任务 {token}：依次{sequence}；之后返回可靠结果。",
        "请求 {token} 要求按这个顺序执行：{sequence}；完成后作答。",
    ),
    "test": (
        "针对范围 {token}，按顺序{sequence}，然后给出有证据的结果。",
        "请依照任务 {token} 的流程{sequence}；随后报告已验证内容。",
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_key(*parts: object) -> str:
    return hashlib.sha256(
        "|".join(str(part) for part in parts).encode("utf-8")
    ).hexdigest()


def byte_ngrams(text: str, n: int = 5) -> Counter[bytes]:
    raw = text.encode("utf-8")
    return Counter(raw[index : index + n] for index in range(max(0, len(raw) - n + 1)))


def cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    return dot / math.sqrt(
        sum(value * value for value in left.values())
        * sum(value * value for value in right.values())
    )


def compact_source_objective(row: dict[str, Any]) -> str:
    return (
        str(row["selector_projection"]["stage_objective"])
        .split(" The unique task scope is the ", 1)[0]
        .strip()
        .rstrip(".")
    )


def values_for(split: str, language: str, token: str, ordinal: int) -> dict[str, object]:
    digest = stable_key("S30-values", split, language, token, ordinal)
    return {
        "path": f"scope/{split}/{digest[:12]}",
        "marker": f"MARKER_{digest[12:24].upper()}",
        "suffix": digest[24:34],
        "number": 10 + int(digest[34:38], 16) % 80,
        "day": 1 + int(digest[38:42], 16) % 27,
    }


def english_intent(
    source_by_label: dict[str, list[dict[str, Any]]],
    *,
    label: str,
    split: str,
    token: str,
    ordinal: int,
) -> tuple[str, str]:
    allowed = VARIANTS[split]
    rows = [
        row
        for index, row in enumerate(source_by_label[label])
        if index % 6 in allowed
    ]
    selected = rows[int(stable_key(label, split, token, ordinal), 16) % len(rows)]
    return compact_source_objective(selected), str(selected["sample_id"])


def chinese_intent(
    *, label: str, split: str, token: str, ordinal: int
) -> tuple[str, str]:
    values = values_for(split, "zh", token, ordinal)
    return ZH_CORE[label].format(**values), f"s30-zh-{split}-{label}-{ordinal % 4}"


def ordered_sequence(language: str, intents: list[str]) -> str:
    values = [item.rstrip("。.") for item in intents]
    if language == "zh":
        if len(values) == 1:
            return values[0]
        if len(values) == 2:
            return f"{values[0]}；成功后，{values[1]}"
        return "；接着，".join(values[:-1]) + f"；这些完成后，{values[-1]}"
    if len(values) == 1:
        return values[0][0].lower() + values[0][1:]
    if len(values) == 2:
        return f"{values[0][0].lower() + values[0][1:]}; after that succeeds, {values[1][0].lower() + values[1][1:]}"
    lowered = [item[0].lower() + item[1:] for item in values]
    return "; next, ".join(lowered[:-1]) + f"; once those finish, {lowered[-1]}"


def depth_schedule(split: str, language_index: int) -> int:
    count = SPLIT_PER_LABEL[split] // 2
    if count == 40:
        values = [0] * 20 + [1] * 12 + [2] * 8
    else:
        values = [0] * 5 + [1] * 3 + [2] * 2
    ordered = sorted(
        enumerate(values),
        key=lambda item: stable_key("S30-depth", split, language_index, item[0], item[1]),
    )
    return ordered[language_index][1]


def future_depth(label: str, history_depth: int, index: int) -> int:
    if label in {"final_answer", "ABSTAIN"}:
        return 0
    if history_depth == 0:
        return (1, 2, 1, 0)[index % 4]
    return (1, 0, 1, 0)[index % 4]


def parent_checkpoint(action_index: int) -> ModelCheckpoint:
    return ModelCheckpoint(
        checkpoint_id=f"S30-PARENT-{action_index:02d}",
        lane_id="LANE:SELECTOR",
        lane_kind=ModelLaneKind.SELECTOR,
        parent_checkpoint_id=None,
        model="dataset-projection-only",
        transport="none",
        transcript="",
        transcript_digest="0" * 64,
        token_count=0,
        native_state_metadata={"action_index": action_index},
    )


def append_success(state: RunState, operation: str, sequence: int) -> None:
    metadata: dict[str, object] = {}
    if operation in {
        "list_directory",
        "read_file",
        "read_json",
        "web_search",
        "connector_lookup",
    }:
        metadata = {"complete": True, "truncated": False}
    state.actions[f"S30-A{sequence:02d}"] = ActionRecord(
        action_id=f"S30-A{sequence:02d}",
        sequence=sequence,
        status=ActionStatus.SUCCEEDED,
        action_type=operation,
        arguments={},
        wire_arguments={},
        action_fingerprint="",
        idempotency_key="",
        decision_id="",
        request_id="",
        started_at="",
        ended_at="",
        result={"success": True, "outcome_type": "success", "metadata": metadata},
        outcome_type="success",
    )


def sequence_labels(label: str, history_depth: int, future_count: int, index: int) -> tuple[list[str], list[str]]:
    if label == "final_answer":
        history_depth = 1 + (index % 2)
        start = (index * 2) % len(EXECUTABLE_LABELS)
        history = [
            EXECUTABLE_LABELS[(start + offset * 7) % len(EXECUTABLE_LABELS)]
            for offset in range(history_depth)
        ]
        return history, []
    predecessors = PREDECESSORS.get(label, ())
    history = [predecessors[offset % len(predecessors)] for offset in range(history_depth)] if predecessors else []
    successors = SUCCESSORS.get(label, ())
    future = [successors[(index + offset) % len(successors)] for offset in range(future_count)] if successors else []
    return history, future


def build_row(
    source_by_label: dict[str, list[dict[str, Any]]],
    *,
    label: str,
    split: str,
    language: str,
    language_index: int,
) -> dict[str, object]:
    row_index = language_index + (0 if language == "en" else SPLIT_PER_LABEL[split] // 2)
    token = stable_key("S30-row", label, split, language, language_index)[:12]
    if label == "final_answer":
        history_depth = 1 + (row_index % 2)
    elif label == "ABSTAIN":
        history_depth = 1 if row_index % 4 == 0 else 0
    else:
        history_depth = depth_schedule(split, language_index)
    future_count = future_depth(label, history_depth, row_index)
    history_labels, future_labels = sequence_labels(
        label, history_depth, future_count, row_index
    )
    operation_sequence = list(history_labels)
    if label in EXECUTABLE_LABELS:
        operation_sequence.append(label)
        operation_sequence.extend(future_labels)
    elif label == "ABSTAIN":
        operation_sequence.append("ABSTAIN")
    sources: list[dict[str, str]] = []
    intents: list[str] = []
    for ordinal, operation in enumerate(operation_sequence):
        if language == "en":
            intent, source_id = english_intent(
                source_by_label,
                label=operation,
                split=split,
                token=token,
                ordinal=ordinal,
            )
        else:
            intent, source_id = chinese_intent(
                label=operation,
                split=split,
                token=token,
                ordinal=ordinal,
            )
        intents.append(intent)
        sources.append({"operation": operation, "source_id": source_id})
    sequence_text = ordered_sequence(language, intents)
    frames = EN_FRAMES[split] if language == "en" else ZH_FRAMES[split]
    frame_index = language_index % len(frames)
    request = frames[frame_index].format(sequence=sequence_text, token=token)
    if label == "final_answer" and any(
        marker in request.lower()
        for marker in (
            "final_answer",
            "no tool",
            "no operation",
            "不再调用",
            "无需工具",
        )
    ):
        raise RuntimeError("S30 completion request contains a classifier hint")
    state = RunState(
        run_id=f"S30-DATA-{token}",
        goal=GoalState.create(
            request=request,
            constraints=(),
            workspace_root=ROOT / "temp/s30-projection-workspace",
        ),
    )
    history_inputs: list[dict[str, object]] = []
    history_steps: list[str] = []
    parent_action_index: int | None = None
    for sequence, operation in enumerate(history_labels, 1):
        selector_input = build_network_selector_input(
            state,
            None
            if parent_action_index is None
            else parent_checkpoint(parent_action_index),
        )
        history_inputs.append(selector_input.to_dict())
        history_steps.append(render_compact_selector_step(selector_input))
        parent_action_index = len(state.actions)
        append_success(state, operation, sequence)
    current = build_network_selector_input(
        state,
        None if parent_action_index is None else parent_checkpoint(parent_action_index),
    )
    current_dict = current.to_dict()
    expected_delta = [history_labels[-1]] if history_labels else []
    if current_dict["progress"]["succeeded_operations"] != expected_delta or current_dict["progress"]["failed_operations"] != []:
        raise RuntimeError("S30 current progress does not match production parent semantics")
    bootstrap = render_compact_selector_bootstrap(current)
    step = render_compact_selector_step(current)
    trajectory = bootstrap + "".join("\n" + item for item in [*history_steps, step])
    stage_group = "completion" if label == "final_answer" else ("continuation" if history_labels else "first")
    return {
        "schema_version": ROW_SCHEMA,
        "dataset_version": VERSION,
        "sample_id": f"NETSEL-S30-{split.upper()}-{label.upper()}-{language.upper()}-{language_index:03d}",
        "semantic_family_id": f"S30-{split}-{label}-{language}-{language_index:03d}",
        "lexical_family_id": f"S30-{split}-{language}-frame{frame_index}-variants{'-'.join(str(item) for item in VARIANTS[split])}",
        "entity_family_id": token,
        "trajectory_family_id": f"S30-trajectory-{split}-{token}",
        "split": split,
        "label": label,
        "language": language,
        "phase": "first" if not history_labels else f"continuation_{len(history_labels)}",
        "stage_group": stage_group,
        "decision_index": len(history_labels),
        "expected_history_labels": history_labels,
        "future_labels": future_labels,
        "has_future_tool_distractor": bool(future_labels),
        "operation_sequence": operation_sequence,
        "current_sequence_position": len(history_labels),
        "completion_inferred": label == "final_answer",
        "history_selector_inputs": history_inputs,
        "history_steps": history_steps,
        "selector_input": current_dict,
        "selector_input_sha256": canonical_digest(current_dict),
        "bootstrap": bootstrap,
        "step": step,
        "trajectory_rendered_input": trajectory,
        "trajectory_rendered_input_sha256": hashlib.sha256(trajectory.encode("utf-8")).hexdigest(),
        "compact_input_schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "compact_menu_digest": compact_selector_menu_digest(),
        "projection_version": SELECTOR_STAGE_PROJECTION_VERSION,
        "sources": sources,
        "generated_rwkv_text": False,
        "contains_parameter_schemas": False,
        "contains_full_tool_results": False,
        "contains_executor_text": False,
    }


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S30 dataset")
    for path, expected in {
        SOURCE: SOURCE_SHA256,
        ECRA: ECRA_SHA256,
        PROTOCOL: PROTOCOL_SHA256,
        PREREGISTRATION: PREREGISTRATION_SHA256,
    }.items():
        if sha256_file(path) != expected:
            raise RuntimeError(f"S30 source identity changed: {path}")
    source_rows = [
        json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines()
    ]
    source_by_label = {
        label: [
            row
            for row in source_rows
            if row["split"] == "train" and row["label"] == label
        ]
        for label in NETWORK_EXACT_TOOL_LABELS
    }
    if any(len(rows) != 240 for rows in source_by_label.values()):
        raise RuntimeError("S30 v2.4 source balance changed")
    rows: list[dict[str, object]] = []
    for split in ("train", "dev", "test"):
        per_language = SPLIT_PER_LABEL[split] // 2
        for label in NETWORK_EXACT_TOOL_LABELS:
            for language in ("en", "zh"):
                for index in range(per_language):
                    rows.append(
                        build_row(
                            source_by_label,
                            label=label,
                            split=split,
                            language=language,
                            language_index=index,
                        )
                    )
    expected_split = {
        split: per_label * len(NETWORK_EXACT_TOOL_LABELS)
        for split, per_label in SPLIT_PER_LABEL.items()
    }
    split_counts = Counter(str(row["split"]) for row in rows)
    if split_counts != Counter(expected_split):
        raise RuntimeError(f"S30 split counts changed: {split_counts}")
    label_counts = {
        split: Counter(str(row["label"]) for row in rows if row["split"] == split)
        for split in SPLIT_PER_LABEL
    }
    if any(
        values
        != Counter(
            {label: SPLIT_PER_LABEL[split] for label in NETWORK_EXACT_TOOL_LABELS}
        )
        for split, values in label_counts.items()
    ):
        raise RuntimeError("S30 label balance changed")
    language_by_label = Counter(
        (str(row["split"]), str(row["label"]), str(row["language"]))
        for row in rows
    )
    for split, per_label in SPLIT_PER_LABEL.items():
        for label in NETWORK_EXACT_TOOL_LABELS:
            for language in ("en", "zh"):
                if language_by_label[(split, label, language)] != per_label // 2:
                    raise RuntimeError("S30 language balance changed")
    if len({str(row["sample_id"]) for row in rows}) != len(rows) or len(
        {str(row["trajectory_rendered_input_sha256"]) for row in rows}
    ) != len(rows):
        raise RuntimeError("S30 row or trajectory identity is not unique")
    for field in (
        "semantic_family_id",
        "lexical_family_id",
        "entity_family_id",
        "trajectory_family_id",
    ):
        values = {
            split: {str(row[field]) for row in rows if row["split"] == split}
            for split in SPLIT_PER_LABEL
        }
        if any(
            values[left] & values[right]
            for left, right in (("train", "dev"), ("train", "test"), ("dev", "test"))
        ):
            raise RuntimeError(f"S30 {field} crosses splits")
    for row in rows:
        if len(row["history_steps"]) != int(row["decision_index"]):
            raise RuntimeError("S30 history replay depth changed")
        if row["label"] == "final_answer" and (
            not row["completion_inferred"] or row["future_labels"]
        ):
            raise RuntimeError("S30 completion contract changed")
        if any(
            bool(row[key])
            for key in (
                "generated_rwkv_text",
                "contains_parameter_schemas",
                "contains_full_tool_results",
                "contains_executor_text",
            )
        ):
            raise RuntimeError("S30 forbidden content marker changed")
    first_noncontrol = [
        row
        for row in rows
        if row["label"] in EXECUTABLE_LABELS and row["stage_group"] == "first"
    ]
    future_first_ratio = sum(
        bool(row["has_future_tool_distractor"]) for row in first_noncontrol
    ) / len(first_noncontrol)
    if future_first_ratio < 0.5:
        raise RuntimeError("S30 lacks first-step future-tool contrast")
    holdout = json.loads(ECRA.read_text(encoding="utf-8"))["cases"]
    holdout_grams = [
        (str(case["case_id"]), byte_ngrams(str(case["instruction"])))
        for case in holdout
    ]
    maximum: dict[str, object] = {"score": -1.0, "sample_id": "", "holdout_id": ""}
    for row in rows:
        grams = byte_ngrams(str(row["selector_input"]["task_request"]))
        for holdout_id, reference in holdout_grams:
            score = cosine(grams, reference)
            if score > float(maximum["score"]):
                maximum = {
                    "score": score,
                    "sample_id": row["sample_id"],
                    "holdout_id": holdout_id,
                }
    if float(maximum["score"]) >= 0.75:
        raise RuntimeError(f"S30 ECRA similarity gate failed: {maximum}")
    staging = Path(
        tempfile.mkdtemp(prefix=".rwkv_lh_network_selector_s30.", dir=OUTPUT.parent)
    )
    cases_path = staging / "cases.jsonl"
    with cases_path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(
                json.dumps(
                    row, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                + "\n"
            )
    phase_counts = {
        split: dict(
            sorted(
                Counter(
                    str(row["stage_group"])
                    for row in rows
                    if row["split"] == split
                ).items()
            )
        )
        for split in SPLIT_PER_LABEL
    }
    future_counts = {
        split: sum(
            bool(row["has_future_tool_distractor"])
            for row in rows
            if row["split"] == split
        )
        for split in SPLIT_PER_LABEL
    }
    generator = Path(__file__).resolve()
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": "zero-state 2.9B exact-tool training on real persistent Harness trajectory shapes",
        "architecture": "current-direct-LongHorizonModel-dual-state",
        "counts": dict(sorted(split_counts.items())),
        "label_counts": {
            split: dict(sorted(values.items()))
            for split, values in label_counts.items()
        },
        "stage_group_counts": phase_counts,
        "future_tool_distractor_counts": future_counts,
        "first_noncontrol_future_tool_ratio": future_first_ratio,
        "class_count": 25,
        "executable_tool_count": 23,
        "control_label_count": 2,
        "input_protocol": {
            "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
            "menu_digest": compact_selector_menu_digest(),
            "source_path": str(PROTOCOL.relative_to(ROOT)),
            "source_sha256": PROTOCOL_SHA256,
            "names_and_descriptions_only": True,
        },
        "projection": {
            "version": SELECTOR_STAGE_PROJECTION_VERSION,
            "production_parent_index_semantics": True,
            "persistent_history_replay": True,
            "maximum_history_steps": 2,
            "maximum_future_tool_mentions": 2,
            "every_history_step_supervised_by_registered_label": True,
        },
        "generated_rwkv_text_count": 0,
        "contains_parameter_schemas": False,
        "contains_full_tool_results": False,
        "contains_executor_text": False,
        "validation": {
            "all_labels_balanced_in_every_split": True,
            "languages_balanced_in_every_label_split": True,
            "exact_trajectory_duplicates": 0,
            "cross_split_semantic_family_overlap": 0,
            "cross_split_lexical_family_overlap": 0,
            "cross_split_entity_family_overlap": 0,
            "cross_split_trajectory_family_overlap": 0,
            "completion_rows_inferred_without_classifier_hint": True,
            "holdout_similarity": {
                "algorithm": "utf8-byte-5gram-cosine.v1",
                "compared_field": "selector_input.task_request",
                "threshold_exclusive": 0.75,
                "maximum": maximum,
                "holdout_sha256": ECRA_SHA256,
            },
        },
        "sources": {
            "v2_4_operation_contract": {
                "path": str(SOURCE.relative_to(ROOT)),
                "sha256": SOURCE_SHA256,
                "usage": "split-disjoint English operation intent fragments",
            },
            "ecra120_similarity_audit_only": {
                "path": str(ECRA.relative_to(ROOT)),
                "sha256": ECRA_SHA256,
                "labels_or_text_used_for_generation": False,
            },
        },
        "preregistration": {
            "path": str(PREREGISTRATION.relative_to(ROOT)),
            "sha256": PREREGISTRATION_SHA256,
        },
        "generation": f"uv run --no-sync python {generator}",
        "generator": {
            "path": str(generator.relative_to(ROOT)),
            "sha256": sha256_file(generator),
        },
        "files": {
            "cases.jsonl": {"rows": len(rows), "sha256": sha256_file(cases_path)}
        },
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (staging / "README.md").write_text(
        "# S30 true persistent trajectories\n\n"
        "- Source/version/purpose/hashes/generation are frozen in `manifest.json`.\n"
        "- Train/dev/blind test are 2000/500/500 with every one of 25 classes balanced.\n"
        "- Unlike S28, tasks retain ordered future-tool mentions and completion is inferred from replayed actions.\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
