"""Analyze one frozen RWKV-E2E round without participating in generation.

This script is intentionally post-run only. It reads completed audit artifacts,
joins the frozen Codex references, and writes deterministic metrics and causal
integrity checks. It never feeds any result back into a model request.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

from rwkv_lh.token_budget import get_token_count


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REFERENCE_PATH = (
    PROJECT_ROOT / "data/datasets/rwkv_e2e_90_v1/codex_reference_answers.json"
)
GROUPS = ("basic", "medium", "hard")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _byte_ngrams(value: str, n: int = 5) -> Counter[bytes]:
    raw = str(value or "").encode("utf-8")
    if not raw:
        return Counter()
    if len(raw) < n:
        return Counter({raw: 1})
    return Counter(raw[index : index + n] for index in range(len(raw) - n + 1))


def byte_ngram_cosine(left: str, right: str, n: int = 5) -> float:
    """Fixed utf8-byte-ngram-cosine.v1 similarity."""

    a = _byte_ngrams(left, n)
    b = _byte_ngrams(right, n)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    dot = sum(count * b.get(token, 0) for token, count in a.items())
    norm_a = math.sqrt(sum(count * count for count in a.values()))
    norm_b = math.sqrt(sum(count * count for count in b.values()))
    return round(dot / (norm_a * norm_b), 12)


def _parse_time(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _duration_ms(decision: Mapping[str, Any]) -> float | None:
    started = _parse_time(str(decision.get("started_at") or ""))
    ended = _parse_time(str(decision.get("ended_at") or ""))
    if started is None or ended is None:
        return None
    return round(max(0.0, (ended - started).total_seconds() * 1000), 3)


def _mean(values: Iterable[float]) -> float | None:
    materialized = list(values)
    return round(sum(materialized) / len(materialized), 12) if materialized else None


def _artifact_pairs(checks: Iterable[Mapping[str, Any]]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for check in checks:
        observation = check.get("observation")
        if not isinstance(observation, Mapping):
            continue
        if "actual" not in observation:
            continue
        target_key = "target" if "target" in observation else "expected"
        if target_key not in observation:
            continue
        actual = observation["actual"]
        target = observation[target_key]
        render = lambda item: (
            item
            if isinstance(item, str)
            else json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
        pairs.append((render(actual), render(target)))
    return pairs


def _failure_label(audit: Mapping[str, Any]) -> str:
    if audit.get("failure"):
        return str(audit["failure"]).split(":", 1)[0]
    if audit.get("verifier_failure"):
        return "verifier_failure"
    events = audit.get("events") or []
    for event in reversed(events):
        event_type = str(event.get("type") or "")
        if event_type in {
            "model_protocol_blocked",
            "run_blocked",
            "run_failed",
            "run_interrupted",
            "model_contract_error",
            "model_protocol_error",
            "validation_failed",
            "action_failed",
        }:
            return event_type
    state = audit.get("run_state")
    if isinstance(state, Mapping):
        return str(state.get("status") or "unknown")
    return "not_created"


def _normalize_terminal_reason(value: str) -> str:
    reason = str(value or "").strip()
    if reason.startswith("plan has no direct satisfaction claim"):
        return "plan_missing_direct_criterion_claims"
    if reason == "plan requires a non-empty tasks array":
        return "plan_tasks_array_missing"
    if reason == "invalid plan schema":
        return "invalid_plan_schema"
    if reason.startswith("G1i tool call has unknown fields"):
        if "function_call" in reason:
            return "g1i_function_call_envelope_rejected"
        if "'function'" in reason and "'type'" in reason:
            return "g1i_typed_function_envelope_rejected"
        return "g1i_function_envelope_rejected"
    if reason == "model output does not contain a complete JSON object":
        return "truncated_or_incomplete_json"
    if reason == "replacement cannot depend on failed task":
        return "replacement_depends_on_failed_task"
    if "failure analysis decision must be" in reason:
        return "invalid_failure_analysis_decision"
    return reason or "unspecified"


def _terminal_classification(
    result: Mapping[str, Any], audit: Mapping[str, Any]
) -> tuple[str, str]:
    if bool(result.get("passed")):
        return "passed", "passed"
    if bool(result.get("agent_completed")) and not bool(result.get("external_passed")):
        return "external_acceptance", "agent_completed_external_failed"
    if not bool(result.get("agent_completed")) and bool(result.get("external_passed")):
        return "controller_completion", "external_correct_controller_not_completed"
    blocked = [
        event
        for event in audit.get("events") or []
        if event.get("type") == "model_protocol_blocked"
    ]
    if blocked:
        data = blocked[-1].get("data") or {}
        return (
            str(data.get("phase") or "model_protocol"),
            _normalize_terminal_reason(str(data.get("error") or data.get("message") or "")),
        )
    if audit.get("failure"):
        failure = str(audit["failure"])
        return "runner_exception", _normalize_terminal_reason(failure.split(": ", 1)[-1])
    state = audit.get("run_state")
    status = str(state.get("status") or "not_created") if isinstance(state, Mapping) else "not_created"
    return status, _failure_label(audit)


def _verify_causal_artifacts(round_path: Path, audit: Mapping[str, Any]) -> dict[str, Any]:
    case_path = round_path / "cases" / str(audit["task_id"])
    declared = audit.get("causal_artifacts") or {}
    checks: dict[str, Any] = {}
    for name in ("model_trace", "event_log", "state_timeline"):
        metadata = declared.get(name) if isinstance(declared, Mapping) else None
        path = case_path / str((metadata or {}).get("path") or "")
        exists = path.is_file()
        actual_hash = _sha256(path) if exists else ""
        checks[name] = {
            "exists": exists,
            "declared_sha256": str((metadata or {}).get("sha256") or ""),
            "actual_sha256": actual_hash,
            "hash_matches": exists
            and actual_hash == str((metadata or {}).get("sha256") or ""),
        }
    timeline_path = case_path / "state_timeline.json"
    event_path = case_path / "event_log.json"
    timeline = _read_json(timeline_path) if timeline_path.is_file() else []
    events = _read_json(event_path) if event_path.is_file() else []
    revisions = [int(item["revision"]) for item in timeline]
    checks["state_sequence"] = {
        "timeline_records": len(timeline),
        "event_records": len(events),
        "one_snapshot_per_event": len(timeline) == len(events),
        "strict_revision_order": all(
            revisions[index] > revisions[index - 1]
            for index in range(1, len(revisions))
        ),
        "every_transition_has_delta": all(
            isinstance(item.get("changes_from_previous"), list)
            and bool(item["changes_from_previous"])
            for item in timeline
        ),
    }
    trace = audit.get("model_trace") or []
    by_request: dict[str, list[str]] = {}
    request_types: dict[str, str] = {}
    for event in trace:
        request_id = str(event.get("request_id") or "")
        if not request_id:
            continue
        by_request.setdefault(request_id, []).append(str(event.get("type") or ""))
        request_types[request_id] = str(event.get("request_type") or "")
    incomplete: list[dict[str, Any]] = []
    for request_id, event_types in by_request.items():
        terminal = any(
            item in event_types
            for item in (
                "model_request_returned",
                "model_request_failed",
                "model_request_unknown",
            )
        )
        returned = "model_request_returned" in event_types
        needs_protocol = returned and request_types.get(request_id) != "final_answer"
        protocol_observed = any(
            item in event_types
            for item in (
                "model_protocol_parsed",
                "model_protocol_error",
            )
        )
        if not terminal or (needs_protocol and not protocol_observed):
            incomplete.append(
                {
                    "request_id": request_id,
                    "request_type": request_types.get(request_id, ""),
                    "events": event_types,
                }
            )
    checks["model_exchange_sequence"] = {
        "request_count": len(by_request),
        "incomplete": incomplete,
        "complete": not incomplete,
    }
    checks["complete"] = all(
        item.get("hash_matches", False)
        for key, item in checks.items()
        if key in {"model_trace", "event_log", "state_timeline"}
    ) and all(
        (
            checks["state_sequence"]["one_snapshot_per_event"],
            checks["state_sequence"]["strict_revision_order"],
            checks["state_sequence"]["every_transition_has_delta"],
            checks["model_exchange_sequence"]["complete"],
        )
    )
    return checks


def analyze(round_path: Path, previous_path: Path | None = None) -> dict[str, Any]:
    protocol = _read_json(round_path / "RUN_PROTOCOL.json")
    results_document = _read_json(round_path / "results.json")
    results = list(results_document.get("results") or [])
    references_document = _read_json(REFERENCE_PATH)
    references = {
        str(item["task_id"]): item for item in references_document.get("cases") or []
    }
    expected_ids = [str(item) for item in protocol.get("selected_case_ids") or []]
    result_ids = [str(item["task_id"]) for item in results]
    if len(results) != 90 or len(set(result_ids)) != 90 or set(result_ids) != set(expected_ids):
        raise ValueError(
            f"formal round is incomplete: results={len(results)}, unique={len(set(result_ids))}, "
            f"missing={sorted(set(expected_ids) - set(result_ids))}"
        )
    if set(result_ids) != set(references):
        raise ValueError("frozen reference answers do not cover this exact 90-case round")

    cases: list[dict[str, Any]] = []
    failure_counts: Counter[str] = Counter()
    terminal_stage_counts: Counter[str] = Counter()
    terminal_reason_counts: Counter[str] = Counter()
    event_type_counts: Counter[str] = Counter()
    request_type_counts: Counter[str] = Counter()
    protocol_event_counts: Counter[str] = Counter()
    check_kind_counts: Counter[str] = Counter()
    check_kind_passes: Counter[str] = Counter()
    artifact_similarities: list[float] = []
    latencies: list[float] = []
    total_prompt_tokens = 0
    total_output_tokens = 0
    causal_complete = 0
    completed_external_failure_checks: Counter[str] = Counter()
    nested_task_graph_rejections: list[str] = []
    observation_gate_counts: Counter[str] = Counter()

    for result in results:
        task_id = str(result["task_id"])
        audit_path = round_path / str(result["audit"])
        audit = _read_json(audit_path)
        reference = references[task_id]
        checks = list(audit.get("external_checks") or [])
        for check in checks:
            kind = str(check.get("kind") or "unknown")
            check_kind_counts[kind] += 1
            check_kind_passes[kind] += int(bool(check.get("passed")))
            if (
                bool(result.get("agent_completed"))
                and not bool(result.get("external_passed"))
                and not bool(check.get("passed"))
            ):
                completed_external_failure_checks[kind] += 1
        case_artifact_similarities = [
            byte_ngram_cosine(actual, target)
            for actual, target in _artifact_pairs(checks)
        ]
        artifact_similarities.extend(case_artifact_similarities)
        trace = list(audit.get("model_trace") or [])
        for event in trace:
            event_type = str(event.get("type") or "")
            if event_type == "model_request_started":
                request_type_counts[str(event.get("request_type") or "unknown")] += 1
            if event_type.startswith("model_protocol_"):
                protocol_event_counts[event_type] += 1
            if event_type == "model_request_returned":
                total_prompt_tokens += int(event.get("prompt_tokens_local") or 0)
                total_output_tokens += get_token_count(str(event.get("raw_output") or ""))
        for event in audit.get("events") or []:
            event_type = str(event.get("type") or "unknown")
            event_type_counts[event_type] += 1
            data = event.get("data") or {}
            if event_type == "cross_check_observation_prepared":
                observation_gate_counts["prepared"] += 1
                observation_gate_counts[
                    "cacheable" if bool(data.get("cacheable")) else "uncacheable"
                ] += 1
            elif event_type == "failed_cross_check_observation_registered":
                observations = data.get("observations") or []
                observation_gate_counts["registered"] += max(
                    1,
                    len(observations) if isinstance(observations, list) else 0,
                )
            elif event_type == "unchanged_observation_cross_check_suppressed":
                observation_gate_counts["suppressed"] += 1
        state = audit.get("run_state")
        if isinstance(state, Mapping):
            for decision in state.get("temp_decisions") or []:
                duration = _duration_ms(decision)
                if duration is not None:
                    latencies.append(duration)
        causal = _verify_causal_artifacts(round_path, audit)
        causal_complete += int(bool(causal["complete"]))
        failure = "" if result.get("passed") else _failure_label(audit)
        if failure:
            failure_counts[failure] += 1
        terminal_stage, terminal_reason = _terminal_classification(result, audit)
        terminal_stage_counts[terminal_stage] += 1
        terminal_reason_counts[terminal_reason] += 1
        if terminal_reason == "plan_tasks_array_missing":
            rejected_outputs = [
                str((event.get("data") or {}).get("output") or "")
                for event in audit.get("events") or []
                if event.get("type") == "model_contract_error"
                and (event.get("data") or {}).get("request_type") == "task_decomposition"
            ]
            if rejected_outputs and '"task_graph"' in rejected_outputs[-1]:
                nested_task_graph_rejections.append(task_id)
        final_output = str(audit.get("final_output") or "")
        cases.append(
            {
                "task_id": task_id,
                "group": result["difficulty_group"],
                "native_level": result["level"],
                "strict_passed": bool(result["passed"]),
                "agent_completed": bool(result["agent_completed"]),
                "external_passed": bool(result["external_passed"]),
                "false_positive": bool(result["agent_completed"])
                and not bool(result["external_passed"]),
                "false_negative": not bool(result["agent_completed"])
                and bool(result["external_passed"]),
                "failure_label": failure,
                "terminal_stage": terminal_stage,
                "terminal_reason": terminal_reason,
                "reference_answer": reference["answer_summary"],
                "reference_observable": reference["reference_observable"],
                "final_answer_reference_similarity": byte_ngram_cosine(
                    final_output, str(reference["answer_summary"])
                ),
                "artifact_similarities": case_artifact_similarities,
                "causal_chain": causal,
                "output_non_intervention": audit.get("output_non_intervention"),
            }
        )

    def group_metrics(group: str | None) -> dict[str, Any]:
        subset = [item for item in results if group is None or item["difficulty_group"] == group]
        count = len(subset)
        strict = sum(bool(item["passed"]) for item in subset)
        external = sum(bool(item["external_passed"]) for item in subset)
        completed = sum(bool(item["agent_completed"]) for item in subset)
        false_positive = sum(
            bool(item["agent_completed"]) and not bool(item["external_passed"])
            for item in subset
        )
        false_negative = sum(
            not bool(item["agent_completed"]) and bool(item["external_passed"])
            for item in subset
        )
        return {
            "cases": count,
            "strict_passed": strict,
            "strict_rate": round(strict / count, 12),
            "external_passed": external,
            "external_rate": round(external / count, 12),
            "agent_completed": completed,
            "agent_completion_rate": round(completed / count, 12),
            "false_positive": false_positive,
            "false_negative": false_negative,
        }

    metrics = {
        "overall": group_metrics(None),
        "groups": {group: group_metrics(group) for group in GROUPS},
        "causal_complete_cases": causal_complete,
        "non_intervention_exact_cases": sum(
            bool((item.get("output_non_intervention") or {}).get("byte_exact_match"))
            for item in cases
            if item["agent_completed"]
        ),
        "completed_cases_requiring_final_output": sum(item["agent_completed"] for item in cases),
        "model_requests": sum(request_type_counts.values()),
        "prompt_tokens_local": total_prompt_tokens,
        "output_tokens_local": total_output_tokens,
        "mean_model_decision_latency_ms": _mean(latencies),
        "mean_exact_artifact_similarity": _mean(artifact_similarities),
        "artifact_similarity_samples": len(artifact_similarities),
        "mean_final_answer_reference_similarity": _mean(
            item["final_answer_reference_similarity"] for item in cases
        ),
    }
    previous_summary = None
    if previous_path is not None:
        previous_file = previous_path / "causal_analysis.json"
        if previous_file.is_file():
            previous_summary = _read_json(previous_file).get("metrics")
    comparison = {
        "schema_version": "rwkv-lh.round-comparison.v1",
        "current_round": round_path.name,
        "previous_round": previous_path.name if previous_path is not None else None,
        "same_metric": "RWKV-E2E-90 external acceptance and strict E2E",
        "current": metrics,
        "previous": previous_summary,
        "deltas": None,
    }
    if previous_summary:
        comparison["deltas"] = {
            "external_passed": metrics["overall"]["external_passed"]
            - previous_summary["overall"]["external_passed"],
            "strict_passed": metrics["overall"]["strict_passed"]
            - previous_summary["overall"]["strict_passed"],
            "false_positive": metrics["overall"]["false_positive"]
            - previous_summary["overall"]["false_positive"],
        }
    goal_capacity_failures = sum(
        count
        for reason, count in terminal_reason_counts.items()
        if reason.startswith("goal proposal has ") and "; maximum is " in reason
    )
    wrapper_failures = sum(
        count
        for reason, count in terminal_reason_counts.items()
        if reason
        in {
            "g1i_function_envelope_rejected",
            "g1i_function_call_envelope_rejected",
            "g1i_typed_function_envelope_rejected",
        }
    )
    candidate_evidence = [
        {
            "name": "criterion_evidence_boundary",
            "affected_cases": metrics["overall"]["false_positive"],
            "evidence": "agent completed while external acceptance failed",
        },
        {
            "name": "goal_obligation_planning",
            "affected_cases": terminal_reason_counts[
                "plan_missing_direct_criterion_claims"
            ],
            "evidence": "initial plan rejected before execution for missing direct claims",
        },
        {
            "name": "goal_criterion_capacity",
            "affected_cases": goal_capacity_failures,
            "evidence": "goal proposal exceeded the fixed five-criterion contract",
        },
        {
            "name": "transparent_protocol_envelope_normalization",
            "affected_cases": len(nested_task_graph_rejections) + wrapper_failures,
            "evidence": "complete task/function objects remained under known wire envelopes",
        },
    ]
    candidate_evidence.sort(
        key=lambda item: (-int(item["affected_cases"]), str(item["name"]))
    )
    return {
        "schema_version": "rwkv-lh.causal-analysis.v1",
        "round": round_path.name,
        "protocol_sha256": _sha256(round_path / "RUN_PROTOCOL.json"),
        "results_sha256": _sha256(round_path / "results.json"),
        "reference_answers_sha256": _sha256(REFERENCE_PATH),
        "metric": {
            "name": "utf8-byte-ngram-cosine.v1",
            "n": 5,
            "near_duplicate_threshold": 0.95,
            "role": "diagnostic only; hidden acceptance remains the primary score",
        },
        "metrics": metrics,
        "failure_counts": dict(failure_counts.most_common()),
        "terminal_stage_counts": dict(terminal_stage_counts.most_common()),
        "terminal_reason_counts": dict(terminal_reason_counts.most_common()),
        "transparent_format_findings": {
            "nested_task_graph_rejected_cases": sorted(nested_task_graph_rejections),
            "nested_task_graph_rejected_count": len(nested_task_graph_rejections),
            "g1i_wrapper_rejected_count": wrapper_failures,
            "interpretation": (
                "Observed model payloads contain complete task/function objects under known wire-format "
                "envelopes; any future normalization must preserve the parsed semantic payload exactly."
            ),
        },
        "completed_external_failure_check_kinds": dict(
            completed_external_failure_checks.most_common()
        ),
        "strict_pass_case_ids": sorted(
            item["task_id"] for item in cases if item["strict_passed"]
        ),
        "false_positive_case_ids": sorted(
            item["task_id"] for item in cases if item["false_positive"]
        ),
        "false_negative_case_ids": sorted(
            item["task_id"] for item in cases if item["false_negative"]
        ),
        "observation_gate": {
            "prepared": observation_gate_counts["prepared"],
            "cacheable": observation_gate_counts["cacheable"],
            "uncacheable": observation_gate_counts["uncacheable"],
            "registered_failed_rwkv_observations": observation_gate_counts[
                "registered"
            ],
            "suppressed_cross_checks": observation_gate_counts["suppressed"],
            "causal_interpretation": (
                "suppressed_cross_checks is the only count attributable to failed-equivalent-observation "
                "reuse; request-count changes must not be attributed to the gate when it is zero"
            ),
        },
        "next_ablation": {
            "name": "not_selected_by_post_run_analyzer",
            "reason": (
                "The analyzer reports comparable causal evidence only. The next single variable must be "
                "pre-registered separately and cannot be selected by hidden acceptance or reference answers."
            ),
            "candidate_evidence": candidate_evidence,
        },
        "event_type_counts": dict(event_type_counts.most_common()),
        "request_type_counts": dict(request_type_counts.most_common()),
        "protocol_event_counts": dict(protocol_event_counts.most_common()),
        "external_check_kinds": {
            kind: {
                "total": count,
                "passed": check_kind_passes[kind],
                "rate": round(check_kind_passes[kind] / count, 12),
            }
            for kind, count in check_kind_counts.most_common()
        },
        "reference_comparison": cases,
        "comparison": comparison,
    }


def _write_markdown(path: Path, analysis: Mapping[str, Any]) -> None:
    metrics = analysis["metrics"]
    overall = metrics["overall"]
    lines = [
        f"# {analysis['round']} 因果分析",
        "",
        "本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。",
        "",
        "## 固定主指标",
        "",
        f"- External acceptance：{overall['external_passed']}/90（{overall['external_rate']:.2%}）",
        f"- Strict E2E：{overall['strict_passed']}/90（{overall['strict_rate']:.2%}）",
        f"- Agent completed：{overall['agent_completed']}/90",
        f"- False positive / false negative：{overall['false_positive']} / {overall['false_negative']}",
        f"- 因果链完整：{metrics['causal_complete_cases']}/90",
        "",
        "| 难度 | External | Strict | Agent completed | FP | FN |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for group in GROUPS:
        item = metrics["groups"][group]
        lines.append(
            f"| {group} | {item['external_passed']}/{item['cases']} | "
            f"{item['strict_passed']}/{item['cases']} | {item['agent_completed']}/{item['cases']} | "
            f"{item['false_positive']} | {item['false_negative']} |"
        )
    lines.extend(
        [
            "",
            "## 固定诊断指标",
            "",
            f"- 模型请求：{metrics['model_requests']}",
            f"- 本地输入 / 输出 token：{metrics['prompt_tokens_local']} / {metrics['output_tokens_local']}",
            f"- 平均模型决策时延：{metrics['mean_model_decision_latency_ms']} ms",
            f"- 可配对产物 byte-5gram 平均相似度：{metrics['mean_exact_artifact_similarity']}",
            f"- 最终回答与 Codex 摘要平均相似度：{metrics['mean_final_answer_reference_similarity']}（仅诊断）",
            "",
            "## 终止阶段与根因入口",
            "",
        ]
    )
    for label, count in list(analysis["terminal_reason_counts"].items())[:15]:
        lines.append(f"- {label}: {count}")
    findings = analysis["transparent_format_findings"]
    lines.extend(
        [
            "",
            "## 透明格式层发现",
            "",
            f"- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：{findings['nested_task_graph_rejected_count']} 题。",
            f"- 完整 G1i/OpenAI function 外壳被拒绝：{findings['g1i_wrapper_rejected_count']} 题。",
            "- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。",
            "",
            "## 完成边界",
            "",
            f"- Strict pass case：{', '.join(analysis['strict_pass_case_ids'])}",
            f"- False positive case：{', '.join(analysis['false_positive_case_ids'])}",
            f"- False negative case：{', '.join(analysis['false_negative_case_ids'])}",
            "",
            "## 本轮 observation gate 触发情况",
            "",
            f"- Prepared：{analysis['observation_gate']['prepared']}",
            f"- Cacheable / uncacheable：{analysis['observation_gate']['cacheable']} / "
            f"{analysis['observation_gate']['uncacheable']}",
            f"- 首次有效 RWKV 失败记录：{analysis['observation_gate']['registered_failed_rwkv_observations']}",
            f"- 实际抑制：{analysis['observation_gate']['suppressed_cross_checks']}",
            "- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。",
            "",
            "## 下一轮候选证据（不自动选方案）",
            "",
        ]
    )
    for item in analysis["next_ablation"]["candidate_evidence"]:
        lines.append(
            f"- {item['name']}: {item['affected_cases']} 题；{item['evidence']}。"
        )
    lines.extend(
        [
            "",
            "下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze one complete RWKV-E2E-90 round")
    parser.add_argument("--round", required=True, dest="round_path")
    parser.add_argument("--previous", default=None, dest="previous_path")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    round_path = Path(arguments.round_path).expanduser().resolve()
    previous_path = (
        Path(arguments.previous_path).expanduser().resolve()
        if arguments.previous_path
        else None
    )
    analysis = analyze(round_path, previous_path)
    analysis_path = round_path / "causal_analysis.json"
    analysis_path.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    comparison_path = round_path / "comparison_vs_previous.json"
    comparison_path.write_text(
        json.dumps(analysis["comparison"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_markdown(round_path / "CAUSAL_ANALYSIS.md", analysis)
    print(json.dumps(analysis["metrics"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
