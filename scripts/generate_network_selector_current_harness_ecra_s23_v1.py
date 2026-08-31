#!/usr/bin/env python3
"""Freeze current direct-Harness Selector decision points from ECRA120 traces."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

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
CASES = ROOT / "data/datasets/rwkv_lh_ecra_route_v1/cases.json"
TRACE = (
    ROOT
    / "data/experiments/RWKV_STATE_TUNING_STAGE4_TO_STAGE6_V1_20260827"
    / "stage4_balanced_boundary/ecra_route120_B_child/results.json"
)
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_current_harness_s23_v1"
ROWS = OUTPUT / "decision_points.jsonl"
MANIFEST = OUTPUT / "manifest.json"
README = OUTPUT / "README.md"
EXPECTED = {
    "cases": "7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a",
    "trace": "f97fb1b3fee939fc8b3de31f0e14d2009ca87e5663150029b40ea9168c13ded0",
}
SCHEMA = "rwkv-lh.network-selector-current-harness-s23.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parent_checkpoint(action_index: int) -> ModelCheckpoint | None:
    if action_index == 0:
        return None
    return ModelCheckpoint(
        checkpoint_id=f"DATASET-PARENT-{action_index:02d}",
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


def append_action(state: RunState, raw: dict[str, object], sequence: int) -> None:
    result = dict(raw.get("result") or {})
    success = bool(result.get("success"))
    status = ActionStatus.SUCCEEDED if success else ActionStatus.FAILED
    action_id = str(raw.get("action_id") or f"A{sequence:05d}")
    state.actions[action_id] = ActionRecord(
        action_id=action_id,
        sequence=sequence,
        status=status,
        action_type=str(raw.get("operation") or ""),
        arguments=dict(raw.get("arguments") or {}),
        wire_arguments=dict(raw.get("arguments") or {}),
        action_fingerprint="",
        idempotency_key="",
        decision_id="",
        request_id="",
        started_at="",
        ended_at="",
        result=result,
        outcome_type=str(result.get("outcome_type") or "pending"),
    )


def historical_next(trace_case: dict[str, object], index: int) -> str:
    actual = dict(trace_case["actual"])
    operations = [str(item) for item in actual.get("operations") or []]
    if index < len(operations):
        return operations[index]
    if actual.get("run_status") == "completed":
        return "final_answer"
    return "ABSTAIN"


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S23 current-Harness dataset")
    if sha256_file(CASES) != EXPECTED["cases"]:
        raise RuntimeError("ECRA120 case source identity changed")
    if sha256_file(TRACE) != EXPECTED["trace"]:
        raise RuntimeError("historical direct-Harness trace identity changed")
    cases = json.loads(CASES.read_text(encoding="utf-8"))["cases"]
    traces = json.loads(TRACE.read_text(encoding="utf-8"))["cases"]
    trace_by_id = {str(item["case_id"]): item for item in traces}
    if len(cases) != 120 or len(trace_by_id) != 120:
        raise RuntimeError("S23 requires the complete aligned ECRA120 sources")

    records: list[dict[str, object]] = []
    for case in cases:
        case_id = str(case["case_id"])
        trace_case = trace_by_id[case_id]
        expected = [str(item) for item in case["expected"]["tool_sequence"]]
        actual_actions = list(trace_case["actual"]["actions"])
        state = RunState(
            run_id=f"DATASET-{case_id}",
            goal=GoalState.create(
                request=str(case["instruction"]),
                constraints=(),
                workspace_root=ROOT / "temp/s23-projection-workspace",
            ),
        )
        prefix_available = True
        for selection_index in range(len(expected) + 1):
            if selection_index > 0:
                action_index = selection_index - 1
                if (
                    action_index >= len(actual_actions)
                    or str(actual_actions[action_index].get("operation") or "")
                    != expected[action_index]
                ):
                    prefix_available = False
                if not prefix_available:
                    break
                append_action(state, dict(actual_actions[action_index]), selection_index)

            label = (
                expected[selection_index]
                if selection_index < len(expected)
                else "final_answer"
            )
            selector_input = build_network_selector_input(
                state,
                parent_checkpoint(selection_index),
            )
            historical = historical_next(trace_case, selection_index)
            records.append(
                {
                    "schema_version": SCHEMA,
                    "sample_id": f"S23-{case_id}-{selection_index:02d}",
                    "case_id": case_id,
                    "category": str(case["category"]),
                    "language": str(case["language"]),
                    "selection_index": selection_index,
                    "phase": "first" if selection_index == 0 else "continuation",
                    "label": label,
                    "historical_selected_operation": historical,
                    "historical_exact": historical == label,
                    "expected_tool_sequence": expected,
                    "selector_input": selector_input.to_dict(),
                    "selector_input_digest": canonical_digest(
                        selector_input.to_dict()
                    ),
                    "bootstrap": selector_input.render_bootstrap(),
                    "step": selector_input.render_step(),
                    "source_action_result_digest": (
                        canonical_digest(state.actions[f"A{selection_index:05d}"].result)
                        if selection_index > 0
                        and f"A{selection_index:05d}" in state.actions
                        else ""
                    ),
                    "full_result_content_in_selector_input": False,
                    "tool_schema_in_selector_input": False,
                    "executor_text_in_selector_input": False,
                }
            )

    if not records or any(str(row["label"]) not in NETWORK_EXACT_TOOL_LABELS for row in records):
        raise RuntimeError("S23 produced an invalid label set")
    if len({str(row["sample_id"]) for row in records}) != len(records):
        raise RuntimeError("S23 sample ids are not unique")
    OUTPUT.mkdir(parents=True)
    ROWS.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
            for row in records
        ),
        encoding="utf-8",
    )
    generator = Path(__file__).resolve()
    counts = Counter(str(row["label"]) for row in records)
    phases = Counter(str(row["phase"]) for row in records)
    categories = Counter(str(row["category"]) for row in records)
    historical_exact = sum(bool(row["historical_exact"]) for row in records)
    manifest = {
        "schema_version": SCHEMA,
        "dataset_id": "rwkv_lh_network_selector_current_harness_s23_v1",
        "created_date": "2026-08-28",
        "purpose": (
            "fixed direct-LongHorizonModel Selector retention and causal-lane "
            "evaluation; never Planner-atomic evaluation"
        ),
        "sources": [
            {"path": str(CASES.relative_to(ROOT)), "sha256": EXPECTED["cases"]},
            {"path": str(TRACE.relative_to(ROOT)), "sha256": EXPECTED["trace"]},
        ],
        "generator": {
            "path": str(generator.relative_to(ROOT)),
            "sha256": sha256_file(generator),
            "command": (
                "uv run python /home/chase/GitHub/RWKV-LH/scripts/"
                "generate_network_selector_current_harness_ecra_s23_v1.py"
            ),
        },
        "rows": len(records),
        "case_count": len(cases),
        "phase_counts": dict(sorted(phases.items())),
        "category_counts": dict(sorted(categories.items())),
        "label_counts": dict(sorted(counts.items())),
        "historical_direct_baseline": {
            "exact": historical_exact,
            "rows": len(records),
            "accuracy": historical_exact / len(records),
        },
        "selector_projection_version": SELECTOR_STAGE_PROJECTION_VERSION,
        "records": {
            "path": str(ROWS.relative_to(ROOT)),
            "sha256": sha256_file(ROWS),
        },
        "contains_full_tool_results": False,
        "contains_tool_schemas": False,
        "contains_executor_text": False,
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    README.write_text(
        "# Current direct-Harness Selector ECRA S23 v1\n\n"
        "- 来源、摘要、生成命令、标签分布和历史基线见 `manifest.json`。\n"
        "- 用途：按当前 `LongHorizonModel` 双 state 架构评估 2.9B Selector；不是 Planner 原子目标数据。\n"
        "- 每个 continuation 只含 operation/success/outcome/complete/truncated 的紧凑投影；不含参数 schema、完整结果、Executor 文本。\n"
        "- 标签：冻结 ECRA 期望序列及完成后的 `final_answer`；只有历史动作前缀正确时才构造后续决策点。\n"
        "- `historical_selected_operation` 是同一决策位置的旧 13.3B 直接路由结果，用作保留基线，不被当作真值。\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
