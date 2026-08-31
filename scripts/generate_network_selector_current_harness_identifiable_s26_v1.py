#!/usr/bin/env python3
"""Build S26 request-identifiable trajectories at the current Harness boundary."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

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
PROTOCOL = ROOT / (
    "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/"
    "SEL_2P9_S26_CURRENT_HARNESS_IDENTIFIABLE_TRAJECTORY_2K_PREREGISTRATION.md"
)
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_current_harness_identifiable_s26_v1"
SOURCE_SHA256 = "78c90285defed1925691dc45325ea4380093345c39763c3bb32373e23733e9fc"
ECRA_SHA256 = "7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a"
VERSION = "rwkv-lh.network-selector.current-harness-identifiable-s26.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-current-harness-identifiable-row.s26.v1"
SPLIT_PER_LABEL = {"train": 80, "dev": 20, "test": 20}
LANGUAGE_PER_LABEL = {"train": 40, "dev": 10, "test": 10}
PHASE_PER_LANGUAGE = {
    "train": {0: 20, 1: 16, 2: 4},
    "dev": {0: 5, 1: 4, 2: 1},
    "test": {0: 5, 1: 4, 2: 1},
}

WORK_LABELS = tuple(
    label for label in NETWORK_EXACT_TOOL_LABELS if label not in {"final_answer", "ABSTAIN"}
)

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

EN_SHORT = {
    "list_directory": "list bounded directory metadata under work/{id}",
    "search_text": "search local UTF-8 files for MARKER_{id}",
    "read_file": "read a bounded range from work/{id}/notes.txt",
    "read_json": "parse and read work/{id}/record.json",
    "file_digest": "observe the SHA-256 of work/{id}/artifact.bin",
    "write_file": "write the complete text to work/{id}/result.txt",
    "write_json": "write the complete JSON value to work/{id}/result.json",
    "patch_json": "patch named keys in work/{id}/record.json",
    "replace_text": "replace one exact phrase in work/{id}/notes.txt",
    "remove_line": "remove one exact line from work/{id}/app.env",
    "append_file": "append the supplied text to work/{id}/events.log",
    "make_directory": "create the scoped directory work/{id}/output",
    "copy_file": "copy work/{id}/source.bin to its named destination",
    "move_file": "move work/{id}/old.bin to its named destination",
    "delete_file": "delete the explicitly scoped work/{id}/obsolete.tmp",
    "bind_evidence": "bind the exact observed line span in work/{id}/report.md",
    "check_command": "run the named read-only verification command",
    "run_command": "run the named potentially mutating local command",
    "web_search": "search the public web for the current record {id}",
    "connector_lookup": "query the structured public repository record {id}",
    "calculator": "calculate the already-known expression ({n}+17)*3",
    "date_diff": "calculate the day distance between 2025-01-02 and 2026-03-{day}",
    "current_time": "observe the current clock time in Asia/Shanghai",
}

ZH_SHORT = {
    "list_directory": "列出 work/{id} 下有界的路径、类型和大小信息，不读取文件内容",
    "search_text": "在本地 UTF-8 文件中搜索 MARKER_{id}，不要搜索互联网",
    "read_file": "读取 work/{id}/notes.txt 的一个有界字节范围",
    "read_json": "解析并读取 work/{id}/record.json 的规范 JSON 内容",
    "file_digest": "只观察 work/{id}/artifact.bin 的 SHA-256 和字节数",
    "write_file": "把完整文本原子写入 work/{id}/result.txt",
    "write_json": "把完整 JSON 值原子写入 work/{id}/result.json",
    "patch_json": "只更新 work/{id}/record.json 中指定的顶层键",
    "replace_text": "替换 work/{id}/notes.txt 中唯一的精确文本片段",
    "remove_line": "删除 work/{id}/app.env 中一整行精确文本",
    "append_file": "把给定文本追加到 work/{id}/events.log",
    "make_directory": "创建限定目录 work/{id}/output",
    "copy_file": "把 work/{id}/source.bin 原样复制到指定目标",
    "move_file": "把 work/{id}/old.bin 移动到指定目标",
    "delete_file": "删除明确限定的 work/{id}/obsolete.tmp",
    "bind_evidence": "绑定 work/{id}/report.md 中已观察到的精确行区间作为证据",
    "check_command": "运行指定的只读测试或检查命令",
    "run_command": "运行指定的可能修改本地内容的命令",
    "web_search": "在公开互联网中检索当前记录 {id}，保留来源证据",
    "connector_lookup": "从结构化公开数据源查询精确记录 {id}",
    "calculator": "计算已知表达式 ({n}+17)*3",
    "date_diff": "计算 2025-01-02 与 2026-03-{day} 的日历天数差",
    "current_time": "观察 Asia/Shanghai 时区的当前时间",
}

ZH_FRAMES = (
    "请{intent}。",
    "当前只需要{intent}。",
    "在限定范围内{intent}，不要改做其他操作。",
    "下一项明确工作是{intent}。",
    "按可审计要求{intent}。",
    "请完成这一项直接操作：{intent}。",
)

ZH_ABSTAIN = (
    "目标和范围都不明确，当前无法唯一选择一个安全操作。",
    "请求同时要求两个互相冲突的下一步，而且没有说明优先级。",
    "请求要求访问工具菜单不支持的私人账户。",
    "破坏性目标没有明确路径，不能猜测执行对象。",
    "完成任务所需的可观察信息缺失，当前没有唯一操作。",
    "当前要求自相矛盾，不能映射到一个授权工具。",
)

ZH_FINAL = (
    "所需工作和验证都已完成，现在直接给出结果。",
    "所有必要事实已经获得，不再需要调用工具，请回答用户。",
    "限定修改已经验证通过，请提交真实的最终总结。",
    "当前没有未完成阶段，直接返回最终答复。",
    "所需证据均已绑定，请在不调用工具的情况下完成回答。",
    "执行与检查已经成功，结束任务并给出结果。",
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def stable_key(*parts: object) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()


def compact_english_objective(row: dict[str, Any]) -> str:
    objective = str(row["selector_projection"]["stage_objective"])
    return objective.split(" The unique task scope is the ", 1)[0].strip()


def direct_intent(language: str, label: str, variant: int, token: str) -> str:
    if language == "zh":
        if label == "ABSTAIN":
            return ZH_ABSTAIN[variant]
        if label == "final_answer":
            return ZH_FINAL[variant]
        clause = ZH_SHORT[label].format(
            id=token, n=17 + int(token[-2:], 16) % 50, day=1 + int(token[:2], 16) % 27
        )
        return ZH_FRAMES[variant].format(intent=clause)
    if label == "ABSTAIN":
        values = (
            "The current target and scope are too ambiguous to identify one safe operation.",
            "Two incompatible next operations are requested without any priority.",
            "The request requires an unsupported private-account action.",
            "A destructive request has no explicit target, so no operation may be guessed.",
            "Required observable information is missing and no unique operation is available.",
            "The current requirement is contradictory and cannot map to one authorized tool.",
        )
        return values[variant]
    if label == "final_answer":
        values = (
            "All requested work and checks are complete; return the grounded result now.",
            "All necessary facts are already available and no tool is still needed; answer the user.",
            "The scoped work passed verification; finish with an honest summary.",
            "No unresolved stage remains; return the final response.",
            "The required evidence is bound; synthesize the answer without another operation.",
            "Execution and validation succeeded; end the run with the result.",
        )
        return values[variant]
    return EN_SHORT[label].format(
        id=token, n=17 + int(token[-2:], 16) % 50, day=1 + int(token[:2], 16) % 27
    ) + "."


def sequence_request(language: str, target: str, prerequisites: tuple[str, ...], token: str) -> str:
    target_clause = target.rstrip("。.")
    prior = [direct_intent(language, label, 0, f"{token}{index}").rstrip("。.") for index, label in enumerate(prerequisites)]
    if not prior:
        return (
            f"{target.rstrip('。')} 范围记录：{token}。"
            if language == "zh"
            else f"{target.rstrip('.')} Scope record: {token}."
        )
    if language == "zh":
        if len(prior) == 1:
            return f"先{prior[0]}；成功后，{target_clause}。范围记录：{token}。"
        return f"先{prior[0]}；然后{prior[1]}；两步都成功后，{target_clause}。范围记录：{token}。"
    if len(prior) == 1:
        return f"First, {prior[0]}. After it succeeds, {target_clause}. Scope record: {token}."
    return f"First, {prior[0]}. Then, {prior[1]}. After both succeed, {target_clause}. Scope record: {token}."


def parent_checkpoint(action_index: int) -> ModelCheckpoint:
    return ModelCheckpoint(
        checkpoint_id=f"S26-PARENT-{action_index:02d}",
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
    if operation in {"list_directory", "read_file", "read_json", "web_search", "connector_lookup"}:
        metadata = {"complete": True, "truncated": False}
    state.actions[f"S26-A{sequence:02d}"] = ActionRecord(
        action_id=f"S26-A{sequence:02d}",
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


def build_row(
    *,
    label: str,
    split: str,
    language: str,
    index: int,
    variant: int,
    phase_depth: int,
    target_intent: str,
    source: dict[str, object],
) -> dict[str, object]:
    token = stable_key("S26", label, split, language, index)[:10]
    prerequisites = PREDECESSORS[label][:phase_depth]
    request = sequence_request(language, target_intent, prerequisites, token)
    state = RunState(
        run_id=f"S26-DATA-{token}",
        goal=GoalState.create(
            request=request,
            constraints=(),
            workspace_root=ROOT / "temp/s26-projection-workspace",
        ),
    )
    history_steps: list[str] = []
    history_inputs: list[dict[str, object]] = []
    parent_action_index: int | None = None
    for sequence, operation in enumerate(prerequisites, 1):
        selector_input = build_network_selector_input(
            state,
            None if parent_action_index is None else parent_checkpoint(parent_action_index),
        )
        history_steps.append(selector_input.render_step())
        history_inputs.append(selector_input.to_dict())
        parent_action_index = len(state.actions)
        append_success(state, operation, sequence)
    selector_input = build_network_selector_input(
        state,
        None if parent_action_index is None else parent_checkpoint(parent_action_index),
    )
    sample_id = f"NETSEL-S26-{split.upper()}-{label.upper()}-{language.upper()}-{index:03d}"
    family_id = f"S26-{label.lower().replace('_', '-')}-{split}-{language}-{index:03d}"
    trajectory_text = selector_input.render_bootstrap() + "".join(
        "\n" + step for step in [*history_steps, selector_input.render_step()]
    )
    return {
        "schema_version": ROW_SCHEMA,
        "dataset_version": VERSION,
        "sample_id": sample_id,
        "semantic_family_id": family_id,
        "split": split,
        "label": label,
        "language": language,
        "surface_variant": variant,
        "phase": "first" if phase_depth == 0 else f"continuation_{phase_depth}",
        "decision_index": phase_depth,
        "expected_history_labels": list(prerequisites),
        "history_steps": history_steps,
        "history_selector_inputs": history_inputs,
        "selector_input": selector_input.to_dict(),
        "selector_input_sha256": canonical_digest(selector_input.to_dict()),
        "bootstrap": selector_input.render_bootstrap(),
        "step": selector_input.render_step(),
        "trajectory_rendered_input": trajectory_text,
        "trajectory_rendered_input_sha256": hashlib.sha256(trajectory_text.encode("utf-8")).hexdigest(),
        "projection_version": SELECTOR_STAGE_PROJECTION_VERSION,
        "request_identifiable": True,
        "persistent_history_replay_required": bool(history_steps),
        "source": source,
        "generated_rwkv_text": False,
        "contains_full_tool_results": False,
        "contains_tool_schemas": False,
        "contains_executor_text": False,
    }


def phase_depths(split: str, label: str, language: str) -> list[int]:
    values = [depth for depth, count in PHASE_PER_LANGUAGE[split].items() for _ in range(count)]
    ordered = sorted(
        enumerate(values),
        key=lambda item: stable_key(
            "phase", split, label, language, item[0], item[1]
        ),
    )
    return [depth for _index, depth in ordered]


def english_sources(rows: list[dict[str, Any]], label: str, split: str) -> list[tuple[int, dict[str, Any]]]:
    candidates = [row for row in rows if row["split"] == "train" and row["label"] == label]
    variants = (0, 1, 2, 3) if split == "train" else ((4,) if split == "dev" else (5,))
    per_variant = 10
    selected: list[tuple[int, dict[str, Any]]] = []
    for variant in variants:
        matching = [(index, row) for index, row in enumerate(candidates) if index >= 24 and index % 6 == variant]
        if len(matching) < per_variant:
            raise RuntimeError(f"not enough S26 English surfaces for {split}/{label}/{variant}")
        selected.extend(matching[:per_variant])
    return selected


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S26 dataset")
    if sha256_file(SOURCE) != SOURCE_SHA256 or sha256_file(ECRA) != ECRA_SHA256:
        raise RuntimeError("S26 source identity changed")
    if not PROTOCOL.is_file():
        raise RuntimeError("S26 preregistration is missing")
    source_rows = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines()]

    rows: list[dict[str, object]] = []
    for split in ("train", "dev", "test"):
        for label in NETWORK_EXACT_TOOL_LABELS:
            for language in ("en", "zh"):
                depths = phase_depths(split, label, language)
                if language == "en":
                    surfaces = english_sources(source_rows, label, split)
                    if len(surfaces) != LANGUAGE_PER_LABEL[split]:
                        raise RuntimeError("S26 English surface count changed")
                    for local_index, ((source_index, source_row), depth) in enumerate(zip(surfaces, depths)):
                        variant = source_index % 6
                        rows.append(build_row(
                            label=label, split=split, language=language,
                            index=local_index, variant=variant, phase_depth=depth,
                            target_intent=compact_english_objective(source_row),
                            source={
                                "kind": "v2_4_explicit_intent_promoted_to_literal_request",
                                "sample_id": source_row["sample_id"],
                                "semantic_family_id": source_row["semantic_family_id"],
                            },
                        ))
                else:
                    count = LANGUAGE_PER_LABEL[split]
                    variants = [index % 4 for index in range(count)] if split == "train" else [4 if split == "dev" else 5] * count
                    for local_index, (variant, depth) in enumerate(zip(variants, depths)):
                        token = stable_key("zh-target", label, split, local_index)[:10]
                        rows.append(build_row(
                            label=label, split=split, language=language,
                            index=local_index, variant=variant, phase_depth=depth,
                            target_intent=direct_intent(language, label, variant, token),
                            source={
                                "kind": "deterministic_bilingual_tool_contract_fixture",
                                "contract_label": label,
                                "surface_variant": variant,
                            },
                        ))

    expected_counts = {split: count * len(NETWORK_EXACT_TOOL_LABELS) for split, count in SPLIT_PER_LABEL.items()}
    split_counts = Counter(str(row["split"]) for row in rows)
    if split_counts != Counter(expected_counts):
        raise RuntimeError(f"S26 split counts changed: {split_counts}")
    label_counts = {
        split: Counter(str(row["label"]) for row in rows if row["split"] == split)
        for split in expected_counts
    }
    if any(counts != Counter({label: SPLIT_PER_LABEL[split] for label in NETWORK_EXACT_TOOL_LABELS}) for split, counts in label_counts.items()):
        raise RuntimeError("S26 label balance changed")
    language_counts = {
        split: Counter(str(row["language"]) for row in rows if row["split"] == split)
        for split in expected_counts
    }
    expected_languages = {
        split: Counter({language: LANGUAGE_PER_LABEL[split] * len(NETWORK_EXACT_TOOL_LABELS) for language in ("en", "zh")})
        for split in expected_counts
    }
    if language_counts != expected_languages:
        raise RuntimeError("S26 language balance changed")
    if len({str(row["sample_id"]) for row in rows}) != len(rows):
        raise RuntimeError("S26 sample ids are not unique")
    if len({str(row["trajectory_rendered_input"]) for row in rows}) != len(rows):
        raise RuntimeError("S26 contains exact trajectory duplicates")
    families = {
        split: {str(row["semantic_family_id"]) for row in rows if row["split"] == split}
        for split in expected_counts
    }
    if any(families[left] & families[right] for left, right in (("train", "dev"), ("train", "test"), ("dev", "test"))):
        raise RuntimeError("S26 semantic families cross splits")
    for row in rows:
        decision_index = int(row["decision_index"])
        if len(row["history_steps"]) != decision_index or len(row["expected_history_labels"]) != decision_index:
            raise RuntimeError("S26 persistent trajectory depth changed")
        current = dict(row["selector_input"])
        progress = dict(current["progress"])
        if int(progress["action_index"]) != decision_index or int(progress["completed_stage_count"]) != decision_index:
            raise RuntimeError("S26 current progress is not cumulative")
        if current["stage_objective"].startswith("CurrentDirectStageV1: ") is False:
            raise RuntimeError("S26 current stage projection changed")

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
        raise RuntimeError(f"S26 ECRA similarity gate failed: {maximum}")

    phase_counts = {
        split: Counter(str(row["phase"]) for row in rows if row["split"] == split)
        for split in expected_counts
    }
    source_counts = Counter(str(row["source"]["kind"]) for row in rows)
    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_network_selector_s26.", dir=OUTPUT.parent))
    cases_path = staging / "cases.jsonl"
    write_jsonl(cases_path, rows)
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": "current direct-Harness 2.9B Selector request-identifiable persistent-trajectory training",
        "architecture": "current-direct-LongHorizonModel-dual-state",
        "counts": dict(sorted(split_counts.items())),
        "label_counts": {split: dict(sorted(counts.items())) for split, counts in label_counts.items()},
        "language_counts": {split: dict(sorted(counts.items())) for split, counts in language_counts.items()},
        "phase_counts": {split: dict(sorted(counts.items())) for split, counts in phase_counts.items()},
        "source_kind_counts": dict(sorted(source_counts.items())),
        "projection": {
            "version": SELECTOR_STAGE_PROJECTION_VERSION,
            "stage_role": "work",
            "persistent_history_replay": True,
            "maximum_history_steps": 2,
            "current_feature_segment_only": True,
        },
        "generated_rwkv_text_count": 0,
        "contains_full_tool_results": False,
        "contains_tool_schemas": False,
        "contains_executor_text": False,
        "validation": {
            "request_identifiable_rows": len(rows),
            "exact_trajectory_duplicates": 0,
            "cross_split_family_overlap": 0,
            "all_labels_balanced_in_every_split": True,
            "english_chinese_balanced_in_every_label_split": True,
            "surface_variant_partition": {"train": [0, 1, 2, 3], "dev": [4], "test": [5]},
            "holdout_similarity": {
                "algorithm": "utf8-byte-5gram-cosine.v1",
                "compared_field": "selector_input.task_request",
                "threshold_exclusive": 0.75,
                "maximum": maximum,
                "holdout_sha256": ECRA_SHA256,
            },
        },
        "sources": {
            "v2_4_operation_contract": {"path": str(SOURCE.relative_to(ROOT)), "sha256": SOURCE_SHA256},
            "ecra120_evaluation_only": {"path": str(ECRA.relative_to(ROOT)), "sha256": ECRA_SHA256},
        },
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256_file(PROTOCOL)},
        "generation": f"uv run python {Path(__file__).resolve()}",
        "generator": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": sha256_file(Path(__file__).resolve())},
        "files": {"cases.jsonl": {"rows": len(rows), "sha256": sha256_file(cases_path)}},
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (staging / "README.md").write_text(
        "# Current direct-Harness identifiable Selector S26 v1\n\n"
        "- 训练/开发/盲测为 2000/500/500；每个 split 的 25 类与中英文均严格平衡。\n"
        "- literal request 自身决定当前工具；stage 仍为产品的通用 CurrentDirectStageV1。\n"
        "- continuation 必须依次复放 history_steps，禁止重新 bootstrap 当前 step。\n"
        "- 不含参数 schema、完整工具结果、Executor 文本或生成的 RWKV 文本；来源与摘要见 manifest。\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
