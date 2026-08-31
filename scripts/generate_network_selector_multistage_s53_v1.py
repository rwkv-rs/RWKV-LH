#!/usr/bin/env python3
"""Generate the S53 request-last multistage Selector trajectories."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from rwkv_lh.exact_tool_selector.compact_protocol_v4 import (
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
EXPERIMENT = (
    ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828"
)
PREREGISTRATION = (
    EXPERIMENT / "SEL_2P9_S53_EXE_G3_MULTISTAGE_DUAL_STATE_PREREGISTRATION.md"
)
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_multistage_s53_v1"
VISIBLE_TASKS = (
    ROOT / "benchmarks/rwkv_e2e/rwkv_e2e_30/tasks.json",
    ROOT / "benchmarks/rwkv_e2e/rwkv_e2e_lh12/tasks.json",
    ROOT / "benchmarks/rwkv_e2e/rwkv_e2e_extension48/tasks.json",
)
LIVE_CASES = ROOT / "data/datasets/rwkv_lh_live_network_rwkv_e2e_v1/cases.jsonl"

VERSION = "rwkv-lh.network-selector.multistage-s53.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-multistage-prefix.s53.v1"
PREREGISTRATION_SHA256 = (
    "503a063fc79f8757b96ea1a7f1dd3458de157b4b494d40b0dd633c5d2d59d91b"
)
SYNTHETIC_PER_PLAN = {"train": 20, "dev": 5, "test": 5}
SUPPORTED = frozenset(NETWORK_EXACT_TOOL_LABELS)


PLANS: tuple[dict[str, Any], ...] = (
    {
        "id": "implementation_and_tests",
        "sequence": (
            "list_directory",
            "read_file",
            "read_file",
            "write_file",
            "check_command",
            "final_answer",
        ),
        "en": (
            "Inspect the bounded workspace, read both {implementation} and {test_file}, "
            "make the smallest complete implementation change in {output_text}, run the "
            "read-only test file, and finish only after it succeeds. Reference {ticket}."
        ),
        "zh": (
            "检查有界工作区，依次读取 {implementation} 和 {test_file}，在 {output_text} 中完成最小且完整的实现修改，"
            "运行只读测试文件，成功后才结束。任务标识 {ticket}。"
        ),
    },
    {
        "id": "csv_policy_verifier_release",
        "sequence": (
            "list_directory",
            "read_file",
            "read_json",
            "read_file",
            "write_json",
            "write_file",
            "check_command",
            "final_answer",
        ),
        "en": (
            "List the workspace; read {source_csv}, parse {policy_json}, and read {verifier}. "
            "Use only those observations to create {output_json} and {report_text}; run the "
            "verifier and finish only when both outputs agree. Reference {ticket}."
        ),
        "zh": (
            "先列出工作区；读取 {source_csv}、解析 {policy_json} 并读取 {verifier}。只依据这些观察创建 "
            "{output_json} 和 {report_text}，运行验证器，两个输出一致后才结束。任务标识 {ticket}。"
        ),
    },
    {
        "id": "three_text_inputs_dual_release",
        "sequence": (
            "list_directory",
            "read_file",
            "read_file",
            "read_file",
            "write_json",
            "write_file",
            "check_command",
            "final_answer",
        ),
        "en": (
            "Discover the scoped files, read {source_a}, {source_b}, and {verifier}, then "
            "derive {output_json} and {report_text}. Run the read-only verifier before "
            "completion. Reference {ticket}."
        ),
        "zh": (
            "发现限定文件后，读取 {source_a}、{source_b} 和 {verifier}，再生成 {output_json} 与 "
            "{report_text}。完成前运行只读验证器。任务标识 {ticket}。"
        ),
    },
    {
        "id": "failed_check_then_repair",
        "sequence": (
            "list_directory",
            "read_file",
            "read_file",
            "write_file",
            "check_command",
            "read_file",
            "write_file",
            "check_command",
            "final_answer",
        ),
        "outcomes": (True, True, True, True, False, True, True, True),
        "en": (
            "Inspect {implementation} and {test_file}, update {output_text}, and run the "
            "read-only check. If it fails, observe the relevant file again, correct the "
            "implementation, and rerun the same check before finishing. Reference {ticket}."
        ),
        "zh": (
            "检查 {implementation} 与 {test_file}，更新 {output_text} 并运行只读检查。若失败，重新观察相关文件，"
            "修正实现并再次运行同一检查，成功后才结束。任务标识 {ticket}。"
        ),
    },
    {
        "id": "two_json_merge",
        "sequence": (
            "list_directory",
            "read_json",
            "read_json",
            "write_json",
            "read_json",
            "check_command",
            "final_answer",
        ),
        "en": (
            "List the scoped workspace, parse both {source_json} and {policy_json}, merge "
            "their requested fields into {output_json}, parse the output, then run the "
            "read-only validator before finishing. Reference {ticket}."
        ),
        "zh": (
            "列出限定工作区，解析 {source_json} 和 {policy_json}，把要求字段合并到 {output_json}，"
            "解析输出并运行只读验证器后再结束。任务标识 {ticket}。"
        ),
    },
    {
        "id": "two_sources_two_outputs",
        "sequence": (
            "list_directory",
            "read_file",
            "read_file",
            "write_file",
            "write_json",
            "check_command",
            "final_answer",
        ),
        "en": (
            "Inspect the workspace and read {source_a} plus {source_b}. Create the grounded "
            "text in {report_text} and the matching structured value in {output_json}; run "
            "the validator and finish only after success. Reference {ticket}."
        ),
        "zh": (
            "检查工作区并读取 {source_a} 与 {source_b}。在 {report_text} 创建有依据的文本，在 "
            "{output_json} 创建一致的结构化值；验证成功后才结束。任务标识 {ticket}。"
        ),
    },
    {
        "id": "web_evidence_file",
        "sequence": (
            "web_search",
            "write_file",
            "read_file",
            "check_command",
            "final_answer",
        ),
        "en": (
            "Search the public web for current sourced facts about {entity}, write the URL, "
            "title, and exact evidence to {report_text}, reopen it, and run the read-only "
            "evidence check before finishing. Reference {ticket}."
        ),
        "zh": (
            "联网检索 {entity} 的当前来源事实，把 URL、标题和精确证据写入 {report_text}，重新读取并运行"
            "只读证据检查后再结束。任务标识 {ticket}。"
        ),
    },
    {
        "id": "connector_record_file",
        "sequence": (
            "connector_lookup",
            "write_json",
            "read_json",
            "check_command",
            "final_answer",
        ),
        "en": (
            "Query the structured public source for {repository}, save the requested record "
            "in {output_json}, parse it, and run the read-only schema check before finishing. "
            "Reference {ticket}."
        ),
        "zh": (
            "通过结构化公共源查询 {repository}，把要求记录保存到 {output_json}，解析后运行只读 schema 检查，"
            "然后结束。任务标识 {ticket}。"
        ),
    },
    {
        "id": "search_read_replace_check",
        "sequence": (
            "search_text",
            "read_file",
            "replace_text",
            "check_command",
            "final_answer",
        ),
        "en": (
            "Search local text for {marker}, read the matched file, replace the one exact "
            "occurrence, and run the read-only check before completion. Reference {ticket}."
        ),
        "zh": (
            "在本地文本中搜索 {marker}，读取匹配文件，只替换一个精确出现位置，并在完成前运行只读检查。"
            "任务标识 {ticket}。"
        ),
    },
    {
        "id": "generator_then_check",
        "sequence": (
            "list_directory",
            "read_file",
            "run_command",
            "check_command",
            "final_answer",
        ),
        "en": (
            "List the workspace, read {source_a}, run the authorized local generator argv "
            "that creates only {output_text}, then run the separate read-only check before "
            "finishing. Reference {ticket}."
        ),
        "zh": (
            "列出工作区并读取 {source_a}，运行获准的本地生成 argv（只创建 {output_text}），再运行独立的"
            "只读检查后结束。任务标识 {ticket}。"
        ),
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
        checkpoint_id=f"S53-PARENT-{action_index:03d}",
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


def append_action(
    state: RunState,
    operation: str,
    sequence: int,
    *,
    success: bool,
) -> None:
    metadata: dict[str, object] = {}
    if operation in {
        "list_directory",
        "read_file",
        "read_json",
        "web_search",
        "connector_lookup",
    }:
        metadata = {"complete": success, "truncated": False}
    outcome = "success" if success else "nonzero"
    state.actions[f"S53-A{sequence:03d}"] = ActionRecord(
        action_id=f"S53-A{sequence:03d}",
        sequence=sequence,
        status=ActionStatus.SUCCEEDED if success else ActionStatus.FAILED,
        action_type=operation,
        arguments={},
        wire_arguments={},
        action_fingerprint="",
        idempotency_key="",
        decision_id="",
        request_id="",
        started_at="",
        ended_at="",
        result={"success": success, "outcome_type": outcome, "metadata": metadata},
        outcome_type=outcome,
    )


def trajectory_rows(
    *,
    trajectory_id: str,
    split: str,
    language: str,
    task_request: str,
    sequence: tuple[str, ...],
    outcomes: tuple[bool, ...],
    source_id: str,
) -> list[dict[str, object]]:
    if not sequence or any(operation not in SUPPORTED for operation in sequence):
        raise RuntimeError(f"unsupported S53 sequence: {sequence}")
    if sequence[-1] != "final_answer" or len(outcomes) != len(sequence) - 1:
        raise RuntimeError("S53 sequence/outcome contract changed")
    state = RunState(
        run_id=f"S53-DATA-{trajectory_id}",
        goal=GoalState.create(
            request=task_request,
            constraints=(),
            workspace_root=ROOT / "temp/s53-projection-workspace",
        ),
    )
    prior_steps: list[str] = []
    rows: list[dict[str, object]] = []
    for position, label in enumerate(sequence):
        current = build_network_selector_input(
            state,
            None if position == 0 else parent_checkpoint(position - 1),
        )
        bootstrap = render_compact_selector_bootstrap(current)
        step = render_compact_selector_step(current)
        if list(json.loads(step.removeprefix("SelectorStepV4: ")))[-1] != "stage_objective":
            raise RuntimeError("S53 current question is not last")
        rendered = bootstrap + "".join(
            "\n" + item for item in [*prior_steps, step]
        )
        sample_id = "S53-P-" + stable_hex(trajectory_id, position, label)[:24]
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
                    else "first"
                    if position == 0
                    else "recovery"
                    if position and outcomes[position - 1] is False
                    else "continuation"
                ),
                "source_kind": "synthetic_multistage_disjoint",
                "source_id": source_id,
                "selector_input": current.to_dict(),
                "selector_input_sha256": canonical_digest(current.to_dict()),
                "bootstrap": bootstrap,
                "step": step,
                "prior_steps": list(prior_steps),
                "rendered_input": rendered,
                "rendered_input_sha256": hashlib.sha256(
                    rendered.encode("utf-8")
                ).hexdigest(),
                "compact_input_schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
                "compact_menu_digest": compact_selector_menu_digest(),
                "projection_version": SELECTOR_STAGE_PROJECTION_VERSION,
                "request_last": True,
                "generated_rwkv_text": False,
                "contains_parameter_schemas": False,
                "contains_full_tool_results": False,
                "contains_executor_text": False,
                "hidden_acceptance_used": False,
            }
        )
        prior_steps.append(step)
        if label != "final_answer":
            append_action(state, label, position + 1, success=outcomes[position])
    return rows


def values(split: str, plan_id: str, index: int) -> dict[str, str]:
    token = stable_hex("S53", split, plan_id, index)[:12]
    return {
        "ticket": f"flow-{split}-{token}",
        "entity": f"Cobalt-{token}",
        "repository": f"harbor-{token}/ledger-{token[:6]}",
        "implementation": f"src/{split}/module-{token}.py",
        "test_file": f"checks/{split}/test-module-{token}.py",
        "verifier": f"checks/{split}/verify-bundle-{token}.py",
        "source_csv": f"inputs/{split}/records-{token}.csv",
        "source_json": f"inputs/{split}/records-{token}.json",
        "policy_json": f"rules/{split}/policy-{token}.json",
        "source_a": f"inputs/{split}/source-a-{token}.txt",
        "source_b": f"inputs/{split}/source-b-{token}.txt",
        "output_text": f"build/{split}/module-{token}.py",
        "output_json": f"release/{split}/bundle-{token}.json",
        "report_text": f"release/{split}/report-{token}.md",
        "marker": f"TOKEN_{token.upper()}",
    }


def holdout_requests() -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for path in VISIBLE_TASKS:
        payload = json.loads(path.read_text(encoding="utf-8"))
        result.extend(
            (str(task["task_id"]), str(task["user_request"]))
            for task in payload["tasks"]
        )
    result.extend(
        (str(item["case_id"]), str(item["request"]))
        for item in (
            json.loads(line)
            for line in LIVE_CASES.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    )
    return result


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S53 dataset")
    if sha256_file(PREREGISTRATION) != PREREGISTRATION_SHA256:
        raise RuntimeError("S53 preregistration identity changed")
    if len(PLANS) != 10 or sum(len(plan["sequence"]) for plan in PLANS) != 65:
        raise RuntimeError("S53 frozen plan inventory changed")

    rows: list[dict[str, object]] = []
    trajectory_splits: Counter[str] = Counter()
    for split, count in SYNTHETIC_PER_PLAN.items():
        for plan_index, plan in enumerate(PLANS):
            sequence = tuple(str(item) for item in plan["sequence"])
            outcomes = tuple(
                bool(item)
                for item in plan.get("outcomes", (True,) * (len(sequence) - 1))
            )
            for index in range(count):
                language = "en" if (index + plan_index) % 2 == 0 else "zh"
                source_id = f"{plan['id']}:{split}:{index:02d}"
                task_values = values(split, str(plan["id"]), index)
                request = str(plan[language]).format(**task_values)
                trajectory_id = "S53-T-" + stable_hex(source_id)[:24]
                rows.extend(
                    trajectory_rows(
                        trajectory_id=trajectory_id,
                        split=split,
                        language=language,
                        task_request=request,
                        sequence=sequence,
                        outcomes=outcomes,
                        source_id=source_id,
                    )
                )
                trajectory_splits[split] += 1

    expected_prefixes = Counter({"train": 1300, "dev": 325, "test": 325})
    expected_trajectories = Counter({"train": 200, "dev": 50, "test": 50})
    if Counter(str(row["split"]) for row in rows) != expected_prefixes:
        raise RuntimeError("S53 prefix counts changed")
    if trajectory_splits != expected_trajectories:
        raise RuntimeError("S53 trajectory counts changed")
    if len(rows) != 1950 or len({str(row["sample_id"]) for row in rows}) != 1950:
        raise RuntimeError("S53 row identity changed")
    if len({str(row["rendered_input_sha256"]) for row in rows}) != 1950:
        raise RuntimeError("S53 rendered prompts are not unique")

    forbidden = (
        "generated_rwkv_text",
        "contains_parameter_schemas",
        "contains_full_tool_results",
        "contains_executor_text",
        "hidden_acceptance_used",
    )
    if any(bool(row[field]) for row in rows for field in forbidden):
        raise RuntimeError("S53 forbidden-content marker changed")

    references = [(case_id, byte_ngrams(text)) for case_id, text in holdout_requests()]
    maximum = {"score": -1.0, "sample_id": "", "holdout_id": ""}
    for row in rows:
        if row["trajectory_position"] != 0:
            continue
        grams = byte_ngrams(str(dict(row["selector_input"])["task_request"]))
        for holdout_id, reference in references:
            score = cosine(grams, reference)
            if score > float(maximum["score"]):
                maximum = {
                    "score": score,
                    "sample_id": row["sample_id"],
                    "holdout_id": holdout_id,
                }
    if float(maximum["score"]) >= 0.75:
        raise RuntimeError(f"S53 visible-holdout similarity failed: {maximum}")

    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_s53.", dir=OUTPUT.parent))
    cases_path = staging / "cases.jsonl"
    with cases_path.open("w", encoding="utf-8") as stream:
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
    label_counts = {
        split: dict(
            sorted(
                Counter(
                    str(row["label"])
                    for row in rows
                    if row["split"] == split
                ).items()
            )
        )
        for split in ("train", "dev", "test")
    }
    manifest = {
        "schema_version": "rwkv-lh.network-selector-multistage-manifest.s53.v1",
        "dataset_version": VERSION,
        "purpose": "request-last long-chain route coverage for the independent 2.9B Selector",
        "rows": len(rows),
        "trajectories": sum(trajectory_splits.values()),
        "split_prefix_counts": dict(sorted(expected_prefixes.items())),
        "split_trajectory_counts": dict(sorted(trajectory_splits.items())),
        "label_counts": label_counts,
        "sources": {
            "visible_e2e_requests": [
                {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": sha256_file(path),
                    "use": "similarity exclusion only",
                }
                for path in VISIBLE_TASKS
            ],
            "live_network_holdout": {
                "path": str(LIVE_CASES.relative_to(ROOT)),
                "sha256": sha256_file(LIVE_CASES),
                "use": "similarity exclusion only",
            },
        },
        "generation": {
            "script": str(Path(__file__).resolve().relative_to(ROOT)),
            "script_sha256": sha256_file(Path(__file__).resolve()),
            "preregistration": str(PREREGISTRATION.relative_to(ROOT)),
            "preregistration_sha256": PREREGISTRATION_SHA256,
            "plan_count": len(PLANS),
            "per_plan": SYNTHETIC_PER_PLAN,
            "maximum_visible_holdout_byte_5gram_cosine": maximum,
        },
        "contracts": {
            "production_v4_render_byte_exact": True,
            "bootstrap_task_request_last": True,
            "step_stage_objective_last": True,
            "task_entities_split_isolated": True,
            "parameter_schemas_present": False,
            "tool_results_present": False,
            "executor_text_present": False,
            "hidden_acceptance_used": False,
            "generated_rwkv_text": False,
            "sampling_invoked": False,
        },
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (staging / "README.md").write_text(
        "# S53 multistage Selector trajectories\n\n"
        "Ten disjoint workflow families provide 300 prefix-closed V4 trajectories. "
        "Sources, hashes and generation rules are recorded in `manifest.json`.\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "s53_dataset_finalized",
                "rows": len(rows),
                "trajectories": sum(trajectory_splits.values()),
                "cases_sha256": sha256_file(OUTPUT / "cases.jsonl"),
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
                "maximum_holdout_similarity": maximum,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
