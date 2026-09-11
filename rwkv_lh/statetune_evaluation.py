"""Fixed Selector regression through the production builder, client and vote rule.

Role qualification is evidence for the next collection stage. Only the separate
registered Agent comparison can retain a State combination for the product.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import shutil
import time
from typing import Callable, Mapping, Sequence

from rwkv_lh import statetune_core as core
from rwkv_lh.exact_tool_selector.native_network_client import NativeNetworkSelectorClient, NativeNetworkSelectorSettings
from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_SELECTOR_MENU_ORDER_IDS, NetworkSelectorInput
from rwkv_lh.goal_state_protocols import role_trace_dataset_v1 as trace, selector_intent_v7
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.role_trace_artifacts import _validate_prior
from rwkv_lh.role_trace_inputs import rebuild_role_input
from rwkv_lh.statetune_data import DATASET_SCHEMA, _member, _protocol, normalize_row, sealed
from rwkv_lh.statetune_native_runtime import verify_project_source
from rwkv_lh.token_budget import tokenizer

PLAN_SCHEMA = "rwkv-lh.statetune-selector-evaluation-plan.v1"
RUN_SCHEMA = "rwkv-lh.statetune-selector-evaluation-run.v1"
SPLITS = ("dev", "confirmation")


def validate_plan(plan: Mapping) -> None:
    core.require(plan.get("schema_version") == PLAN_SCHEMA and plan.get("role") == "selector_intent",
                 "current evaluation requires a registered Selector plan")
    fingerprint = plan.get("regression_fingerprint")
    core.require(isinstance(fingerprint, str) and len(fingerprint) == 64
                 and all(c in "0123456789abcdef" for c in fingerprint), "invalid regression fingerprint")
    core.require(plan.get("metrics") == ["menu_accuracy", "ensemble_accuracy", "transport_failures"]
                 and plan.get("agent_metrics") == ["strict", "completed", "mutation", "termination_reasons"]
                 and plan.get("retention_rule") == "role_qualification_then_separate_agent_acceptance",
                 "registered role/Agent metrics or retention rule differ")
    thresholds = plan.get("thresholds", {})
    core.require(set(thresholds) == {"menu_accuracy", "ensemble_accuracy", "max_transport_failures", "max_regressions"},
                 "evaluation thresholds differ")
    for key in ("menu_accuracy", "ensemble_accuracy"):
        value = thresholds[key]
        core.require(type(value) in (int, float) and math.isfinite(value) and 0 < value <= 1,
                     "invalid evaluation accuracy threshold")
    core.require(all(type(thresholds[k]) is int and thresholds[k] == 0
                     for k in ("max_transport_failures", "max_regressions")),
                 "qualification requires zero transport failures and zero regressions")


def validate_arms(arms: Mapping[str, NativeNetworkSelectorSettings]) -> None:
    core.require(set(arms) == {"zero", "candidate"}, "evaluation requires both registered arms")
    zero, candidate = arms["zero"], arms["candidate"]
    core.require(zero.state_profile_id == "zero" and zero.state_profile_sha256 == "0" * 64,
                 "the baseline must be explicit zero State")
    core.require(candidate.state_profile_id != "zero" and candidate.state_profile_sha256 != "0" * 64,
                 "candidate must bind its exported State")
    ignored = {"profile_id", "profile_sha256", "profile_manifest_sha256"}
    core.require({k: v for k, v in zero.runtime_identity().items() if k not in ignored}
                 == {k: v for k, v in candidate.runtime_identity().items() if k not in ignored},
                 "both arms require the same model, decoder, protocol, context and arithmetic")


@dataclass(frozen=True)
class SelectorCase:
    sample_id: str
    split: str
    group: tuple[str, str, str]
    network: NetworkSelectorInput
    target: str


def rebuild_case(row: Mapping, source: trace.SourceRun, settings: NativeNetworkSelectorSettings) -> SelectorCase:
    core.require(row.get("split") in SPLITS, "evaluation cannot consume train rows")
    bos = row.get("context", {}).get("input_bos_token_ids")
    core.require(isinstance(bos, list) and len(bos) == 1 and type(bos[0]) is int and bos[0] >= 0,
                 "regression requires the actual server BOS token")
    normalize_row(row, role="selector_intent", model_sha256=settings.model_sha256,
                  context_tokens=settings.context_tokens,
                  vocab_size=max(max(tokenizer().idx2token), bos[0]) + 1, bos_token_id=bos[0],
                  expected_split=row["split"])
    core.require(all(row.get(key) == source.registration[key] for key in ("source_run_id", "run_id")),
                 "regression source identity differs")
    boundary = row["boundary_event_id"]
    core.require(boundary in source.snapshots, "regression lacks its durable boundary snapshot")
    menu = row["context"]["menu_order_id"]
    rebuilt = rebuild_role_input("selector_intent", source.snapshots[boundary],
                                {"boundary_event_id": boundary, "menu_order_id": menu})
    core.require(rebuilt["full_input_text"] == row["input_text"], "regression input differs from production builder")
    value = rebuilt["network_input"]
    network = NetworkSelectorInput.create(current_subtask=value["current_subtask"],
        current_progress=value["current_progress"], eligible_labels=value["eligible_labels"], menu_order_id=menu)
    core.require(network.to_dict() == value, "rebuilt network input differs")
    target = selector_intent_v7.parse_target(row["target_text"])
    core.require(target in network.eligible_labels, "regression target is outside durable eligibility")
    return SelectorCase(row["sample_id"], row["split"],
                        (row["source_run_id"], row["run_id"], boundary), network, target)


def prepare_cases(dataset_reference: Mapping, *, fingerprint: str,
                  settings: NativeNetworkSelectorSettings) -> tuple[dict, list[SelectorCase]]:
    dataset = sealed(dataset_reference)
    protocol, protocol_sha = _protocol("selector_intent")
    core.require(dataset.get("schema_version") == DATASET_SCHEMA and dataset.get("purpose") == "frozen_role_training"
                 and dataset.get("role") == "selector_intent"
                 and dataset.get("input_protocol") == protocol and dataset.get("protocol_sha256") == protocol_sha
                 and dataset.get("model_sha256") == settings.model_sha256
                 and dataset["regression"]["fingerprint"] == fingerprint,
                 "evaluation requires the exact frozen role dataset")
    core.require(dataset["candidate_audit"]["status"] == "valid"
                 and all(dataset["candidate_audit"]["quality_gates"].values()), "dataset audit failed")
    root = Path(dataset_reference["path"]).parent
    regression_path = _member(root, dataset["regression"])
    regression = _validate_prior(json.loads(regression_path.read_text()), fingerprint)
    core.require(regression["roles"] == ["selector_intent"], "regression role differs")
    freeze = sealed(dataset["freeze_registration"])
    source_reference = freeze["source_registration"]
    sealed(source_reference)
    registration = trace.read_registration(Path(source_reference["path"]))
    records = {(r["source_run_id"], r["run_id"]): r for r in registration["source_runs"]}
    sources, cases = {}, []
    for split in SPLITS:
        rows = regression["samples_by_split"][split]
        core.require(len(rows) == dataset["counts"][split], "fixed regression counts differ")
        for row in rows:
            key = (row["source_run_id"], row["run_id"])
            core.require(key in records, "regression source is absent from freeze registration")
            if key not in sources:
                sources[key] = trace.load_source_run(records[key], base_dir=Path(source_reference["path"]).parent,
                    coverage_scope_sha256=registration.get("coverage_scope", {}).get("sha256"))
            cases.append(rebuild_case(row, sources[key], settings))
    validate_cases(cases)
    core.verify_file(regression_path, dataset["regression"]["sha256"])
    return dataset, cases


def validate_cases(cases: Sequence[SelectorCase]) -> dict:
    core.require(bool(cases) and len({c.sample_id for c in cases}) == len(cases), "duplicate or empty regression identities")
    core.require({c.split for c in cases} == set(SPLITS), "both fixed regression splits are required")
    groups = defaultdict(dict)
    for case in cases:
        group = groups[(case.split, case.group)]
        core.require(case.network.menu_order_id not in group, "duplicate menu at a regression boundary")
        group[case.network.menu_order_id] = case
    for lanes in groups.values():
        core.require(len({c.target for c in lanes.values()}) == 1
                     and len({c.network.eligible_labels for c in lanes.values()}) == 1,
                     "regression boundary has conflicting labels or eligibility")
    return groups


def evaluate_arm(cases: Sequence[SelectorCase], client: NativeNetworkSelectorClient, *, run_id: str,
                 arm: str, max_seconds: float, record: Callable[[dict], None], clock=time.monotonic) -> dict:
    groups = validate_cases(cases)
    core.require(type(max_seconds) in (int, float) and math.isfinite(max_seconds) and max_seconds > 0,
                 "invalid evaluation time budget")
    start = clock()
    results = {split: {"menu_total": 0, "menu_correct": 0, "ensemble_total": 0, "ensemble_correct": 0,
        "transport_failures": 0, "not_run": 0, "incomplete_menu_groups": 0,
        "correctness": {}, "ensemble_correctness": {}} for split in SPLITS}
    outputs = {}
    for index, case in enumerate(cases):
        result = results[case.split]
        result["menu_total"] += 1
        result["correctness"][case.sample_id] = False
        entry = {"event": "menu_evaluated", "arm": arm, "sample_id": case.sample_id,
                 "split": case.split, "group": case.group, "menu_order_id": case.network.menu_order_id,
                 "target": case.target}
        if clock() - start >= max_seconds:
            result["not_run"] += 1
            entry.update(status="not_run", reason="registered_wall_time_budget")
        else:
            try:
                selection, checkpoint = client.select(case.network, run_id=run_id,
                    trace_id=f"{run_id}:{arm}:{index}")
                outputs[case.sample_id] = selection
                correct = selection.selected_operation == case.target
                result["menu_correct"] += int(correct)
                result["correctness"][case.sample_id] = correct
                entry.update(status="returned", correct=correct, selection=selection.raw_record(),
                             checkpoint_id=checkpoint.checkpoint_id)
            except Exception as exc:
                result["transport_failures"] += 1
                entry.update(status="failed", error_type=type(exc).__name__, error=str(exc))
        record(entry)
    for (split, group_key), lanes in groups.items():
        result = results[split]
        if set(lanes) != set(NETWORK_SELECTOR_MENU_ORDER_IDS):
            result["incomplete_menu_groups"] += 1
            continue
        result["ensemble_total"] += 1
        group_id = json.dumps(group_key, ensure_ascii=False, separators=(",", ":"))
        result["ensemble_correctness"][group_id] = False
        if not all(c.sample_id in outputs for c in lanes.values()):
            continue
        ordered = [lanes[menu] for menu in NETWORK_SELECTOR_MENU_ORDER_IDS]
        selected, evidence = LongHorizonModel._selector_ensemble_choice(
            [outputs[c.sample_id] for c in ordered], eligible_labels=ordered[0].network.eligible_labels)
        correct = selected == ordered[0].target
        result["ensemble_correct"] += int(correct)
        result["ensemble_correctness"][group_id] = correct
        record({"event": "ensemble_evaluated", "arm": arm, "split": split, "group": group_key,
                "correct": correct, "ensemble": evidence})
    elapsed = clock() - start
    for result in results.values():
        result["menu_accuracy"] = result["menu_correct"] / result["menu_total"]
        result["ensemble_accuracy"] = result["ensemble_correct"] / result["ensemble_total"] if result["ensemble_total"] else None
        result["budget_exceeded"] = elapsed >= max_seconds
    return results


def compare_arms(arms: Mapping, plan: Mapping) -> dict:
    validate_plan(plan)
    thresholds = plan["thresholds"]
    core.require(set(arms) == {"zero", "candidate"}, "missing comparison arm")
    regressions, ensemble_regressions = {}, {}
    for split in SPLITS:
        zero, candidate = arms["zero"][split], arms["candidate"][split]
        core.require(set(zero["correctness"]) == set(candidate["correctness"]), "comparison sample identities differ")
        regressions[split] = [key for key in zero["correctness"] if zero["correctness"][key] and not candidate["correctness"][key]]
        core.require(set(zero["ensemble_correctness"]) == set(candidate["ensemble_correctness"]),
                     "comparison ensemble identities differ")
        ensemble_regressions[split] = [key for key in zero["ensemble_correctness"]
            if zero["ensemble_correctness"][key] and not candidate["ensemble_correctness"][key]]

    def qualified(arm):
        return all(value["transport_failures"] == 0 and value["not_run"] == 0 and not value["budget_exceeded"]
            and value["menu_accuracy"] >= thresholds["menu_accuracy"]
            and value["ensemble_accuracy"] is not None and value["ensemble_accuracy"] >= thresholds["ensemble_accuracy"]
            for value in arms[arm].values())

    zero_ok = qualified("zero")
    candidate_ok = qualified("candidate") and not any(regressions.values()) and not any(ensemble_regressions.values())
    improved = any(arms["candidate"][split]["menu_correct"] > arms["zero"][split]["menu_correct"]
                   or arms["candidate"][split]["ensemble_correct"] > arms["zero"][split]["ensemble_correct"] for split in SPLITS)
    preferred = "candidate" if candidate_ok and (not zero_ok or improved) else "zero" if zero_ok else None
    return {"zero_qualified": zero_ok, "candidate_qualified": candidate_ok, "regressions": regressions,
            "ensemble_regressions": ensemble_regressions,
            "preferred_state": preferred, "retained": False, "agent_evaluation_status": "not_run"}


def run_evaluation(reference: Mapping, output: Path, *, source_root: Path) -> dict:
    from rwkv_lh.statetune_training import _atomic_json
    registration = sealed(reference)
    core.require(registration.get("schema_version") == RUN_SCHEMA, "unknown evaluation run registration")
    plan = sealed(registration["evaluation_registration"])
    validate_plan(plan)
    arms = {key: NativeNetworkSelectorSettings(**value) for key, value in registration["arms"].items()}
    validate_arms(arms)
    output = Path(output).absolute()
    trace._source_path(output)
    core.require(output == Path(registration["ledger_root"]).absolute() / registration["run_id"],
                 "evaluation output must use its registered immutable run id")
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(reference["path"], output / "REGISTRATION.json")
    core.verify_file(output / "REGISTRATION.json", reference["sha256"])
    report = {"schema_version": RUN_SCHEMA, "registration": dict(reference), "status": "running",
        "started_at": datetime.now(timezone.utc).isoformat(), "retained": False, "agent_evaluation_status": "not_run"}
    log = output / "events.jsonl"

    def record(value):
        with log.open("a") as handle:
            handle.write(json.dumps({"at": datetime.now(timezone.utc).isoformat(), **value}, ensure_ascii=False, allow_nan=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    record({"event": "evaluation_started"})
    _atomic_json(output / "RESULT.json", report)
    try:
        verify_project_source(registration["source_manifest"], source_root)
        trained = sealed(registration["training_result"])
        training = sealed(trained["registration"])
        candidate = arms["candidate"]
        core.require(trained["optimizer_steps"] > 0 and trained.get("serving_loader_verified") is True
            and trained["run_id"] == candidate.state_profile_id
            and trained["output_state"]["sha256"] == candidate.state_profile_sha256
            and trained["output_profile"]["sha256"] == candidate.state_profile_manifest_sha256
            and training["evaluation_registration"]["sha256"] == registration["evaluation_registration"]["sha256"]
            and training["dataset"]["sha256"] == registration["dataset"]["sha256"]
            and training["source_manifest_sha256"] == registration["source_manifest"]["sha256"],
            "candidate or evaluation identity differs from the registered optimizer run")
        dataset, cases = prepare_cases(registration["dataset"], fingerprint=plan["regression_fingerprint"], settings=arms["zero"])
        report["arms"] = {}
        for arm in ("zero", "candidate"):
            verify_project_source(registration["source_manifest"], source_root)
            report["arms"][arm] = evaluate_arm(cases, NativeNetworkSelectorClient(arms[arm]),
                run_id=registration["run_id"], arm=arm, max_seconds=registration["max_seconds_per_arm"], record=record)
            _atomic_json(output / "RESULT.json", report)
        verify_project_source(registration["source_manifest"], source_root)
        core.verify_file(Path(registration["dataset"]["path"]).parent / dataset["regression"]["file"], dataset["regression"]["sha256"])
        report.update(compare_arms(report["arms"], plan), status="evaluated")
        if trained["status"] != "candidate":
            report.update(candidate_qualified=False,
                preferred_state="zero" if report["zero_qualified"] else None,
                candidate_disqualification="optimizer_run_did_not_complete")
    except BaseException as exc:
        report.update(status="interrupted" if isinstance(exc, (KeyboardInterrupt, SystemExit)) else "failed",
                      error_type=type(exc).__name__, error=str(exc), retained=False)
        record({"event": "evaluation_failed", "error_type": type(exc).__name__, "error": str(exc)})
        raise
    finally:
        report.update(finished_at=datetime.now(timezone.utc).isoformat(), log_sha256=core.sha256_file(log))
        _atomic_json(output / "RESULT.json", report)
    return report
