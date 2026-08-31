#!/usr/bin/env python3
"""Generate the frozen S51 natural-Harness Selector trajectory dataset."""

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
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
)
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
EXPERIMENT = (
    ROOT
    / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828"
)
PREREGISTRATION = (
    EXPERIMENT / "SEL_2P9_S51_NATURAL_HARNESS_ROUTE_PREREGISTRATION.md"
)
ROUND132 = ROOT / "data/experiments/Round132_empty_pool_canonical_full90_20260821"
ROUND132_RESULTS = ROUND132 / "results.json"
VISIBLE_TASKS = (
    ROOT / "benchmarks/rwkv_e2e/rwkv_e2e_30/tasks.json",
    ROOT / "benchmarks/rwkv_e2e/rwkv_e2e_lh12/tasks.json",
    ROOT / "benchmarks/rwkv_e2e/rwkv_e2e_extension48/tasks.json",
)
LIVE_CASES = ROOT / "data/datasets/rwkv_lh_live_network_rwkv_e2e_v1/cases.jsonl"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_natural_harness_s51_v1"

VERSION = "rwkv-lh.network-selector.natural-harness-s51.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-natural-harness-prefix.s51.v1"
CANARY_TEST = frozenset(
    {"E2E-B01", "E2E-B02", "E2E-B10", "E2E-M03", "E2E-H10", "E2E-M12"}
)
SYNTHETIC_PER_PLAN = {"train": 20, "dev": 5, "test": 5}
SUPPORTED = frozenset(NETWORK_EXACT_TOOL_LABELS)


PLAN_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "id": "public_web_text_report",
        "sequence": ("web_search", "write_file", "read_file", "final_answer"),
        "en": "Use the public web to obtain current, sourced information about {entity}; do not rely on memory. Put the source URL, title, and one exact evidence fragment in {text_path}. Re-open that file to verify it before reporting completion.",
        "zh": "必须联网取得关于 {entity} 的当前来源信息，不得凭记忆。把来源 URL、标题和一个精确证据片段写入 {text_path}，重新读取该文件核验后再完成任务。",
    },
    {
        "id": "structured_repository_json",
        "sequence": ("connector_lookup", "write_json", "read_json", "final_answer"),
        "en": "Query a structured public repository source for {repository}. Save its canonical name, default branch, and public URL as valid JSON in {json_path}; parse the saved JSON to verify all three fields, then finish.",
        "zh": "通过结构化公共源查询仓库 {repository}，把规范名称、默认分支和公开 URL 作为有效 JSON 写入 {json_path}；解析保存的 JSON 核验三个字段后再完成。",
    },
    {
        "id": "text_to_json",
        "sequence": ("read_file", "write_json", "read_json", "final_answer"),
        "en": "Read {source_text} before deriving any value. Create {json_path} from the observed project and count fields, then parse the written JSON to verify the exact result before finishing.",
        "zh": "先读取 {source_text}，任何值都必须从原文推导。根据已观察的项目和计数字段创建 {json_path}，再解析写入的 JSON 核验精确结果后完成。",
    },
    {
        "id": "json_calculation_report",
        "sequence": ("read_json", "calculator", "write_json", "read_json", "final_answer"),
        "en": "Parse {source_json} first. Calculate the requested total only from its observed numeric fields, write the complete result object to {json_path}, and parse that output once more before reporting.",
        "zh": "先解析 {source_json}，只使用已观察的数字字段计算所需总数，把完整结果对象写入 {json_path}，再次解析输出核验后再报告。",
    },
    {
        "id": "inspect_implement_test",
        "sequence": ("list_directory", "read_file", "write_file", "check_command", "final_answer"),
        "en": "Inspect the bounded workspace layout before opening the relevant implementation file. Create the requested corrected file at {text_path}, run a read-only test command, and finish only after the test succeeds.",
        "zh": "先检查工作区的有界目录结构，再打开相关实现文件。把修正后的完整文件创建到 {text_path}，运行只读测试，测试成功后才完成。",
    },
    {
        "id": "find_replace_test",
        "sequence": ("search_text", "replace_text", "check_command", "final_answer"),
        "en": "Find the unique local line containing {marker}, replace its exact old text with the required new text, then run the non-mutating verification command before finishing.",
        "zh": "在本地文本中找到包含 {marker} 的唯一行，把精确旧文本替换为要求的新文本，再运行不修改文件的验证命令后完成。",
    },
    {
        "id": "remove_line_verify",
        "sequence": ("read_file", "remove_line", "read_file", "final_answer"),
        "en": "Read {source_text}, remove exactly the complete line containing {marker} while preserving every other byte, and read the file again to verify the deletion before replying.",
        "zh": "读取 {source_text}，只删除包含 {marker} 的完整一行并保留其他内容，再次读取文件核验后回复。",
    },
    {
        "id": "append_verify",
        "sequence": ("read_file", "append_file", "read_file", "final_answer"),
        "en": "Read the existing contents of {source_text}, append the supplied record after those bytes, then read the file again to verify ordering before reporting.",
        "zh": "先读取 {source_text} 的现有内容，把给定记录追加在原字节之后，再次读取核验顺序后报告。",
    },
    {
        "id": "digest_copy_digest",
        "sequence": ("file_digest", "copy_file", "file_digest", "final_answer"),
        "en": "Observe the SHA-256 and size of {binary_path} without opening it, copy its exact bytes to {copy_path}, and digest the copy to prove equality before finishing.",
        "zh": "不打开 {binary_path}，先观察其 SHA-256 和大小，把精确字节复制到 {copy_path}，再计算副本摘要证明一致后完成。",
    },
    {
        "id": "move_verify_layout",
        "sequence": ("list_directory", "move_file", "list_directory", "final_answer"),
        "en": "List the scoped paths first, move {source_text} to {text_path} so the old path disappears, and list the directory again to verify the new layout before replying.",
        "zh": "先列出限定范围内的路径，把 {source_text} 移动到 {text_path} 并让旧路径消失，再次列目录核验新布局后回复。",
    },
    {
        "id": "delete_verify_layout",
        "sequence": ("list_directory", "delete_file", "list_directory", "final_answer"),
        "en": "Inspect the scoped directory, delete only {obsolete_path}, and inspect the directory once more to verify that no other path changed before finishing.",
        "zh": "检查限定目录，只删除 {obsolete_path}，再次检查目录确认其他路径未改变后完成。",
    },
    {
        "id": "directory_then_file",
        "sequence": ("make_directory", "write_file", "list_directory", "final_answer"),
        "en": "Create the directory {directory_path}, place the complete required text in {text_path}, and list the bounded parent directory to verify both artifacts before reporting.",
        "zh": "创建目录 {directory_path}，把要求的完整文本写入 {text_path}，再列出有界父目录核验两个产物后报告。",
    },
    {
        "id": "clock_json",
        "sequence": ("current_time", "write_json", "read_json", "final_answer"),
        "en": "Observe the current clock reading for Asia/Shanghai, save the timezone and observed timestamp in {json_path}, then parse that JSON to verify it before answering.",
        "zh": "观察 Asia/Shanghai 的当前时间，把时区和观察到的时间戳写入 {json_path}，再解析 JSON 核验后回答。",
    },
    {
        "id": "date_distance_json",
        "sequence": ("date_diff", "write_json", "read_json", "final_answer"),
        "en": "Compute the calendar-day distance between the two supplied ISO dates, store both dates and the distance in {json_path}, and parse the saved JSON before finishing.",
        "zh": "计算给定两个 ISO 日期的日历天数差，把日期和差值写入 {json_path}，解析保存的 JSON 核验后完成。",
    },
    {
        "id": "arithmetic_json",
        "sequence": ("calculator", "write_json", "read_json", "final_answer"),
        "en": "Evaluate the provided arithmetic expression from its already known operands, save the expression and result as complete JSON in {json_path}, and parse it once before replying.",
        "zh": "使用已经给出的操作数计算表达式，把表达式和结果作为完整 JSON 写入 {json_path}，解析核验一次后回复。",
    },
    {
        "id": "patch_json_verify",
        "sequence": ("read_json", "patch_json", "read_json", "final_answer"),
        "en": "Parse {source_json}, update only the named top-level status and owner keys while preserving every unspecified key, then parse the file again to verify the patch before finishing.",
        "zh": "解析 {source_json}，只更新指定的顶层 status 和 owner 键并保留所有未指定键，再次解析文件核验补丁后完成。",
    },
    {
        "id": "search_bind_report",
        "sequence": ("search_text", "bind_evidence", "write_file", "final_answer"),
        "en": "Search local project text for {marker}, bind the exact observed line with its locator, and write that grounded quote to {text_path} before reporting.",
        "zh": "在本地项目文本中搜索 {marker}，绑定观察到的精确行及定位，把有依据的引文写入 {text_path} 后报告。",
    },
    {
        "id": "mutate_then_check",
        "sequence": ("run_command", "check_command", "final_answer"),
        "en": "Run the authorized local argv that intentionally regenerates the scoped artifact, then run the separate read-only verification argv; finish only after the check succeeds.",
        "zh": "运行获准的本地 argv 有意重新生成限定产物，再运行独立的只读验证 argv；检查成功后才完成。",
    },
    {
        "id": "ambiguous_stop",
        "sequence": ("ABSTAIN",),
        "en": "A destructive change is requested, but neither the target path nor the desired replacement is specified. Choose no operation because a unique safe next tool cannot be determined.",
        "zh": "请求要求破坏性修改，但没有给出目标路径或替换内容。由于无法确定唯一安全的下一工具，应选择不执行操作。",
    },
    {
        "id": "known_final",
        "sequence": ("final_answer",),
        "en": "All required facts are already present in this request and no workspace or public observation is needed. Return the supplied completion statement directly.",
        "zh": "请求已经给出全部所需事实，不需要工作区或公开来源观察。直接返回给定的完成说明。",
    },
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hex(*parts: object) -> str:
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


def parent_checkpoint(action_index: int) -> ModelCheckpoint:
    return ModelCheckpoint(
        checkpoint_id=f"S51-PARENT-{action_index:03d}",
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
    state.actions[f"S51-A{sequence:03d}"] = ActionRecord(
        action_id=f"S51-A{sequence:03d}",
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


def trajectory_rows(
    *,
    trajectory_id: str,
    split: str,
    language: str,
    task_request: str,
    sequence: tuple[str, ...],
    source_kind: str,
    source_id: str,
) -> list[dict[str, object]]:
    if not sequence or any(operation not in SUPPORTED for operation in sequence):
        raise RuntimeError(f"unsupported S51 sequence: {sequence}")
    if sequence[-1] not in {"final_answer", "ABSTAIN"}:
        raise RuntimeError("S51 trajectory must terminate in final_answer or ABSTAIN")
    if any(operation in {"final_answer", "ABSTAIN"} for operation in sequence[:-1]):
        raise RuntimeError("S51 control operation appears before trajectory end")
    state = RunState(
        run_id=f"S51-DATA-{trajectory_id}",
        goal=GoalState.create(
            request=task_request,
            constraints=(),
            workspace_root=ROOT / "temp/s51-projection-workspace",
        ),
    )
    steps: list[str] = []
    rows: list[dict[str, object]] = []
    for position, label in enumerate(sequence):
        current = build_network_selector_input(
            state,
            None if position == 0 else parent_checkpoint(position - 1),
        )
        bootstrap = render_compact_selector_bootstrap(current)
        step = render_compact_selector_step(current)
        rendered = bootstrap + "".join("\n" + item for item in [*steps, step])
        sample_id = "S51-P-" + stable_hex(trajectory_id, position, label)[:24]
        rows.append(
            {
                "schema_version": ROW_SCHEMA,
                "dataset_version": VERSION,
                "sample_id": sample_id,
                "trajectory_id": trajectory_id,
                "split": split,
                "label": label,
                "language": language,
                "prefix_kind": "current" if position == 0 else "history",
                "trajectory_position": position,
                "trajectory_length": len(sequence),
                "stage_group": (
                    "completion"
                    if label == "final_answer"
                    else "abstain"
                    if label == "ABSTAIN"
                    else "first"
                    if position == 0
                    else "continuation"
                ),
                "source_kind": source_kind,
                "source_id": source_id,
                "selector_input": current.to_dict(),
                "selector_input_sha256": canonical_digest(current.to_dict()),
                "bootstrap": bootstrap,
                "step": step,
                "prior_steps": list(steps),
                "rendered_input": rendered,
                "rendered_input_sha256": hashlib.sha256(
                    rendered.encode("utf-8")
                ).hexdigest(),
                "compact_input_schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
                "compact_menu_digest": compact_selector_menu_digest(),
                "projection_version": SELECTOR_STAGE_PROJECTION_VERSION,
                "generated_rwkv_text": False,
                "contains_parameter_schemas": False,
                "contains_full_tool_results": False,
                "contains_executor_text": False,
                "hidden_acceptance_used": False,
            }
        )
        steps.append(step)
        if label not in {"final_answer", "ABSTAIN"}:
            append_success(state, label, position + 1)
    return rows


def load_visible_requests() -> dict[str, str]:
    requests: dict[str, str] = {}
    for path in VISIBLE_TASKS:
        value = json.loads(path.read_text(encoding="utf-8"))
        for task in value["tasks"]:
            task_id = str(task["task_id"])
            if task_id in requests:
                raise RuntimeError(f"duplicate visible task: {task_id}")
            requests[task_id] = str(task["user_request"])
    if len(requests) != 90:
        raise RuntimeError("visible E2E task count changed")
    return requests


def historical_rows() -> tuple[list[dict[str, object]], dict[str, object]]:
    requests = load_visible_requests()
    results = json.loads(ROUND132_RESULTS.read_text(encoding="utf-8"))["results"]
    passed = sorted(
        str(item["task_id"])
        for item in results
        if item.get("external_passed") is True
    )
    if len(passed) != 34 or not CANARY_TEST.issubset(passed):
        raise RuntimeError("R132 externally passed source set changed")
    candidates = sorted(
        (stable_hex("S51-DEV", task_id), task_id)
        for task_id in passed
        if task_id not in CANARY_TEST
    )
    dev = {task_id for _, task_id in candidates[:5]}
    train = set(passed) - set(CANARY_TEST) - dev
    if len(train) != 23 or len(dev) != 5:
        raise RuntimeError("S51 historical task split changed")
    rows: list[dict[str, object]] = []
    source_hashes: dict[str, str] = {}
    split_by_task: dict[str, str] = {}
    for task_id in passed:
        split = "test" if task_id in CANARY_TEST else "dev" if task_id in dev else "train"
        audit_path = ROUND132 / "cases" / task_id / "audit.json"
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        actions = sorted(
            audit["action_ledger"].values(), key=lambda item: int(item["sequence"])
        )
        sequence = tuple(str(item["action_type"]) for item in actions) + (
            "final_answer",
        )
        if any(operation not in SUPPORTED for operation in sequence):
            raise RuntimeError(f"unsupported R132 operation in {task_id}")
        rows.extend(
            trajectory_rows(
                trajectory_id="S51-T-H-" + stable_hex(task_id)[:24],
                split=split,
                language="zh" if any("\u4e00" <= char <= "\u9fff" for char in requests[task_id]) else "en",
                task_request=requests[task_id],
                sequence=sequence,
                source_kind="r132_external_passed_original_route",
                source_id=task_id,
            )
        )
        split_by_task[task_id] = split
        source_hashes[task_id] = sha256_file(audit_path)
    return rows, {
        "externally_passed_cases": len(passed),
        "train_cases": sorted(train),
        "dev_cases": sorted(dev),
        "test_cases": sorted(CANARY_TEST),
        "split_by_task": dict(sorted(split_by_task.items())),
        "audit_sha256": dict(sorted(source_hashes.items())),
    }


def synthetic_values(split: str, plan_id: str, index: int) -> dict[str, str]:
    token = stable_hex("S51-SYN", split, plan_id, index)[:12]
    return {
        "entity": f"Aurora-{token}",
        "repository": f"northstar-{token}/engine-{token[:6]}",
        "text_path": f"reports/{split}/brief-{token}.md",
        "json_path": f"reports/{split}/record-{token}.json",
        "source_text": f"inputs/{split}/source-{token}.txt",
        "source_json": f"inputs/{split}/source-{token}.json",
        "binary_path": f"inputs/{split}/payload-{token}.bin",
        "copy_path": f"copies/{split}/payload-{token}.bin",
        "directory_path": f"artifacts/{split}/bundle-{token}",
        "obsolete_path": f"obsolete/{split}/item-{token}.tmp",
        "marker": f"MARKER_{token.upper()}",
    }


def synthetic_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for split, count in SYNTHETIC_PER_PLAN.items():
        for plan_index, plan in enumerate(PLAN_TEMPLATES):
            for index in range(count):
                language = "en" if (index + plan_index) % 2 == 0 else "zh"
                values = synthetic_values(split, str(plan["id"]), index)
                request = str(plan[language]).format(**values)
                request += (
                    f" Request reference: {values['entity']}."
                    if language == "en"
                    else f" 请求标识：{values['entity']}。"
                )
                source_id = f"{plan['id']}:{split}:{index:02d}"
                rows.extend(
                    trajectory_rows(
                        trajectory_id="S51-T-S-" + stable_hex(source_id)[:24],
                        split=split,
                        language=language,
                        task_request=request,
                        sequence=tuple(plan["sequence"]),
                        source_kind="synthetic_natural_disjoint",
                        source_id=source_id,
                    )
                )
    return rows


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S51 dataset")
    historical, historical_manifest = historical_rows()
    synthetic = synthetic_rows()
    rows = [*historical, *synthetic]
    trajectory_order: list[str] = []
    for row in rows:
        trajectory_id = str(row["trajectory_id"])
        if not trajectory_order or trajectory_order[-1] != trajectory_id:
            trajectory_order.append(trajectory_id)
    if len(trajectory_order) != 634:
        raise RuntimeError(f"S51 trajectory count changed: {len(trajectory_order)}")
    if len({str(row["sample_id"]) for row in rows}) != len(rows):
        raise RuntimeError("S51 sample IDs are not unique")
    if len({str(row["rendered_input_sha256"]) for row in rows}) != len(rows):
        raise RuntimeError("S51 rendered prefixes are not unique")
    split_prefix_counts = Counter(str(row["split"]) for row in rows)
    split_trajectory_counts = Counter()
    for trajectory_id in trajectory_order:
        group = [row for row in rows if row["trajectory_id"] == trajectory_id]
        if [int(row["trajectory_position"]) for row in group] != list(range(len(group))):
            raise RuntimeError("S51 prefix closure changed")
        if any(
            str(row["rendered_input"])
            != str(row["bootstrap"])
            + "".join("\n" + str(item) for item in [*row["prior_steps"], row["step"]])
            for row in group
        ):
            raise RuntimeError("S51 production render equality changed")
        split_trajectory_counts[str(group[0]["split"])] += 1
    if split_trajectory_counts != Counter({"train": 423, "dev": 105, "test": 106}):
        raise RuntimeError(f"S51 trajectory split counts changed: {split_trajectory_counts}")
    forbidden = (
        "generated_rwkv_text",
        "contains_parameter_schemas",
        "contains_full_tool_results",
        "contains_executor_text",
        "hidden_acceptance_used",
    )
    if any(bool(row[field]) for row in rows for field in forbidden):
        raise RuntimeError("S51 forbidden-content marker changed")
    live = [json.loads(line) for line in LIVE_CASES.read_text(encoding="utf-8").splitlines()]
    maximum = {"score": -1.0, "sample_id": "", "live_case_id": ""}
    live_grams = [(str(item["case_id"]), byte_ngrams(str(item["request"]))) for item in live]
    for row in synthetic:
        request = str(row["selector_input"]["task_request"])
        grams = byte_ngrams(request)
        for case_id, reference in live_grams:
            score = cosine(grams, reference)
            if score > float(maximum["score"]):
                maximum = {
                    "score": score,
                    "sample_id": row["sample_id"],
                    "live_case_id": case_id,
                }
    if float(maximum["score"]) >= 0.75:
        raise RuntimeError(f"S51 synthetic/live similarity gate failed: {maximum}")

    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_s51.", dir=OUTPUT.parent))
    cases_path = staging / "cases.jsonl"
    with cases_path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
            )
    label_counts = {
        split: dict(sorted(Counter(str(row["label"]) for row in rows if row["split"] == split).items()))
        for split in ("train", "dev", "test")
    }
    manifest = {
        "schema_version": "rwkv-lh.network-selector-natural-harness-dataset-manifest.s51.v1",
        "dataset_version": VERSION,
        "purpose": "natural current-Harness route remediation for the independent 2.9B Selector",
        "rows": len(rows),
        "trajectories": len(trajectory_order),
        "split_prefix_counts": dict(sorted(split_prefix_counts.items())),
        "split_trajectory_counts": dict(sorted(split_trajectory_counts.items())),
        "label_counts": label_counts,
        "sources": {
            "round132_results": {
                "path": str(ROUND132_RESULTS.relative_to(ROOT)),
                "sha256": sha256_file(ROUND132_RESULTS),
                "use": "select external_passed route trajectories only",
            },
            "visible_tasks": [
                {"path": str(path.relative_to(ROOT)), "sha256": sha256_file(path), "use": "visible request text only"}
                for path in VISIBLE_TASKS
            ],
            "historical_route_audits": historical_manifest,
            "live_network_holdout": {
                "path": str(LIVE_CASES.relative_to(ROOT)),
                "sha256": sha256_file(LIVE_CASES),
                "use": "similarity exclusion only; expected labels not copied",
            },
        },
        "generation": {
            "script": str(Path(__file__).resolve().relative_to(ROOT)),
            "script_sha256": sha256_file(Path(__file__).resolve()),
            "preregistration": str(PREREGISTRATION.relative_to(ROOT)),
            "preregistration_sha256": sha256_file(PREREGISTRATION),
            "synthetic_plan_count": len(PLAN_TEMPLATES),
            "synthetic_per_plan": SYNTHETIC_PER_PLAN,
            "synthetic_trajectories": 600,
            "historical_trajectories": 34,
            "maximum_synthetic_live_byte_5gram_cosine": maximum,
        },
        "contracts": {
            "production_render_byte_exact": True,
            "task_level_historical_split_isolated": True,
            "synthetic_entity_split_isolated": True,
            "hidden_acceptance_used": False,
            "parameter_schemas_present": False,
            "tool_results_present": False,
            "executor_text_present": False,
            "generated_rwkv_text": False,
            "sampling_invoked": False,
        },
    }
    manifest_path = staging / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (staging / "README.md").write_text(
        "# S51 natural Harness route dataset\n\n"
        f"Rows: {len(rows)}; trajectories: {len(trajectory_order)}.\n\n"
        "Sources, split policy, purpose, generator and hashes are recorded in `manifest.json`.\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "s51_dataset_finalized",
                "rows": len(rows),
                "trajectories": len(trajectory_order),
                "split_prefix_counts": dict(sorted(split_prefix_counts.items())),
                "split_trajectory_counts": dict(sorted(split_trajectory_counts.items())),
                "cases_sha256": sha256_file(OUTPUT / "cases.jsonl"),
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
                "maximum_synthetic_live_similarity": maximum,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
