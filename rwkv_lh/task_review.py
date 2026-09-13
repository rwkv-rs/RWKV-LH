"""External, outcome-first review. Never imported by the model input builders.

Humans or independently recorded reviewers judge meaning. This module checks
the frozen contract, original delivery and evidence, then derives outcomes.
It does not infer answers, grade by tool routes, or manufacture causal claims.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

CONTRACT_SCHEMA = "rwkv-lh.task-review-contract.v1"
RUN_SCHEMA = "rwkv-lh.task-review-run.v1"
REVIEW_SCHEMA = "rwkv-lh.task-review-judgment.v1"
ASSESSMENT_SCHEMA = "rwkv-lh.task-review-assessment.v1"
IDENTITY_KEYS = ("model", "protocol", "source", "sampling", "state", "budget")
OUTCOMES = ("met", "partially_met", "not_met", "no_delivery", "invalid", "unreviewable")
ASSISTANCE = ("rwkv_independent", "strong_advised", "strong_takeover")
CAUSES = ("model_behavior", "harness_input", "tool_execution", "state_transport",
          "evaluation_design", "infrastructure", "unknown")


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def file_digest(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def _fields(value: Mapping, fields: str) -> None:
    _require(isinstance(value, dict) and set(value) == set(fields.split()), "review fields differ")


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _identity(value: Mapping) -> None:
    _fields(value, " ".join(IDENTITY_KEYS))
    _require(all(_sha(v) for v in value.values()), "execution identity requires SHA256 digests")


def validate_contract(contract: dict) -> None:
    _fields(contract, "schema task_id user_request kind protocol_error_policy execution_identity requirements")
    _require(contract["schema"] == CONTRACT_SCHEMA, "unsupported contract schema")
    _require(_text(contract["task_id"]) and _text(contract["user_request"]), "missing task or user request")
    _require(contract["kind"] in ("task_trial", "boundary_probe", "retrospective"), "invalid review kind")
    _require(contract["protocol_error_policy"] in ("feedback", "stop"), "unknown protocol error policy")
    _require(contract["kind"] != "task_trial" or contract["protocol_error_policy"] == "feedback",
             "first-error stop must be a boundary_probe, not a full task_trial")
    _identity(contract["execution_identity"])
    requirements = contract["requirements"]
    _require(isinstance(requirements, list) and bool(requirements), "empty outcome requirements")
    ids = []
    for requirement in requirements:
        _fields(requirement, "id user_quote outcome level missing_effect acceptance omission_policy")
        _require(all(_text(v) for v in requirement.values()), "requirement fields must be non-empty text")
        _require(requirement["user_quote"] in contract["user_request"], "requirement not grounded in user request")
        _require(requirement["level"] in ("essential", "detail"), "unknown importance")
        ids.append(requirement["id"])
    _require(len(set(ids)) == len(ids), "duplicate requirement")
    _require(any(r["level"] == "essential" for r in requirements), "no essential user outcome")


def write_once(path: Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def freeze_contract(contract: dict, path: Path) -> None:
    validate_contract(contract)
    write_once(path, {"contract": contract, "sha256": digest(contract)})


def load_contract(path: Path) -> dict:
    frozen = json.loads(Path(path).read_text())
    _fields(frozen, "contract sha256")
    _require(digest(frozen["contract"]) == frozen["sha256"], "frozen contract digest mismatch")
    validate_contract(frozen["contract"])
    return frozen["contract"]


def _validate_run(run: dict, contract: dict, root: Path) -> set[str]:
    _fields(run, "schema run_id task_id arm repeat protocol_error_policy execution_identity termination answer artifact_ids assistance historical evidence diagnostics")
    _require(run["schema"] == RUN_SCHEMA, "unsupported run schema")
    _require(run["task_id"] == contract["task_id"], "task identity mismatch")
    _require(_text(run["run_id"]) and _text(run["arm"]), "missing run identity")
    _require(type(run["repeat"]) is int and run["repeat"] > 0, "invalid repetition")
    _require(run["protocol_error_policy"] == contract["protocol_error_policy"], "execution policy mismatch")
    _identity(run["execution_identity"])
    _require(run["execution_identity"] == contract["execution_identity"], "execution identity mismatch")
    _require(run["answer"] is None or _text(run["answer"]), "invalid original answer")
    _require(_text(run["termination"]), "missing termination reason")
    _require(run["assistance"] in ASSISTANCE, "unknown assistance attribution")
    _require(type(run["historical"]) is bool, "historical status must be explicit")
    _require(not run["historical"] or contract["kind"] == "retrospective", "historical records require retrospective review")
    _require(isinstance(run["diagnostics"], dict) and all(type(n) is int and n >= 0 for n in run["diagnostics"].values()), "invalid diagnostic counts")
    _require(isinstance(run["evidence"], list) and bool(run["evidence"]), "missing evidence")
    ids: set[str] = set()
    artifacts: set[str] = set()
    root = root.resolve(strict=True)
    for item in run["evidence"]:
        _fields(item, "id path sha256 kind")
        _require(_text(item["id"]) and item["id"] not in ids, "duplicate or empty evidence id")
        _require(item["kind"] in ("source", "trace", "artifact", "check", "identity", "review_log"), "unknown evidence kind")
        _require(_text(item["path"]), "invalid evidence path")
        relative = Path(item["path"])
        path = root / relative
        _require(not relative.is_absolute() and ".." not in relative.parts
            and path.resolve().is_relative_to(root) and not path.is_symlink(), "unsafe evidence path")
        _require(path.is_file() and _sha(item["sha256"]) and file_digest(path) == item["sha256"], "evidence checksum mismatch")
        ids.add(item["id"])
        if item["kind"] == "artifact":
            artifacts.add(item["id"])
    _require(isinstance(run["artifact_ids"], list) and len(set(run["artifact_ids"])) == len(run["artifact_ids"])
        and set(run["artifact_ids"]) <= artifacts, "delivery artifacts require artifact evidence")
    return ids


def review_packet(contract: dict, run: dict, *, evidence_root: Path) -> dict:
    validate_contract(contract)
    _validate_run(run, contract, evidence_root)
    return {"contract": deepcopy(contract), "contract_sha256": digest(contract),
        "run": deepcopy(run), "run_sha256": digest(run),
        "review_instruction": "Judge delivered outcomes against the user-bound requirements. Record omissions separately; do not require tool routes or exact wording. Do not infer root cause from failure. Original evidence must be inspected."}


def assess(contract: dict, run: dict, judgment: dict, *, evidence_root: Path) -> dict:
    validate_contract(contract)
    ids = _validate_run(run, contract, evidence_root)
    _fields(judgment, "schema contract_sha256 run_sha256 reviewer validity validity_reason validity_evidence_ids requirements findings causes")
    _require(judgment["schema"] == REVIEW_SCHEMA, "unsupported judgment schema")
    _require(judgment["contract_sha256"] == digest(contract) and judgment["run_sha256"] == digest(run), "review binding digest mismatch")
    _require(_text(judgment["reviewer"]), "missing reviewer identity")
    _require(judgment["validity"] in ("valid", "invalid", "unreviewable") and _text(judgment["validity_reason"]), "review validity requires reason")
    for key in ("requirements", "findings", "causes"):
        _require(isinstance(judgment[key], list), "review assessments must be lists")

    def evidence(item: dict) -> None:
        refs = item["evidence_ids"]
        _require(isinstance(refs, list) and bool(refs) and all(isinstance(ref, str) and ref in ids for ref in refs), "assessment requires registered evidence")
        _require(_text(item["reason"]), "assessment requires explanation")

    evidence({"evidence_ids": judgment["validity_evidence_ids"], "reason": judgment["validity_reason"]})
    expected = {r["id"]: r for r in contract["requirements"]}
    assessments = {}
    for item in judgment["requirements"]:
        _fields(item, "id status reason evidence_ids")
        _require(item["id"] in expected and item["id"] not in assessments, "unknown or duplicate requirement review")
        _require(item["status"] in ("met", "partial", "unmet", "not_assessed"), "unknown requirement outcome")
        evidence(item)
        assessments[item["id"]] = item
    for item in judgment["findings"]:
        _fields(item, "kind severity quote reason impact evidence_ids")
        _require(item["kind"] in ("unsupported", "contradiction", "false_work_claim"), "omissions belong in requirement review, not factuality findings")
        _require(item["severity"] in ("minor", "material") and _text(item["impact"]), "finding needs severity and user impact")
        _require(_text(item["quote"]) and run["answer"] is not None and item["quote"] in run["answer"], "finding quote is not in delivered answer")
        evidence(item)
    for item in judgment["causes"]:
        _fields(item, "category certainty reason evidence_ids")
        _require(item["category"] in CAUSES and item["certainty"] in ("observed", "hypothesis", "confirmed"), "invalid causal attribution")
        evidence(item)

    delivered = run["answer"] is not None or bool(run["artifact_ids"])
    essential = [r for r in contract["requirements"] if r["level"] == "essential"]
    material = any(f["severity"] == "material" for f in judgment["findings"])
    if judgment["validity"] != "valid":
        outcome = judgment["validity"]
    elif not delivered:
        _require(not assessments and not judgment["findings"], "no delivery has no answer-quality assessment")
        outcome = "no_delivery"
    elif any(r["id"] not in assessments or assessments[r["id"]]["status"] == "not_assessed" for r in essential):
        outcome = "unreviewable"
    elif material:
        outcome = "not_met"
    elif all(assessments[r["id"]]["status"] == "met" for r in essential):
        outcome = "met"
    elif any(assessments[r["id"]]["status"] in ("met", "partial") for r in essential):
        outcome = "partially_met"
    else:
        outcome = "not_met"
    return {"schema": ASSESSMENT_SCHEMA, "run_id": run["run_id"], "task_id": run["task_id"],
        "arm": run["arm"], "repeat": run["repeat"], "scope": contract["kind"],
        "contract_sha256": digest(contract), "run_sha256": digest(run), "review_sha256": digest(judgment),
        "execution_identity_sha256": digest(run["execution_identity"]),
        "outcome": outcome, "delivered": delivered, "termination": run["termination"],
        "assistance": run["assistance"], "requirement_results": deepcopy(judgment["requirements"]),
        "findings": deepcopy(judgment["findings"]), "validity_reason": judgment["validity_reason"],
        "factuality": "not_applicable" if not delivered or outcome in ("invalid", "unreviewable") else "material_issue" if material else "minor_issue" if judgment["findings"] else "no_issue_reported",
        "false_work_claims": sum(f["kind"] == "false_work_claim" for f in judgment["findings"]),
        "causes": deepcopy(judgment["causes"]),
        "confirmed_root_causes": [deepcopy(c) for c in judgment["causes"] if c["certainty"] == "confirmed" and c["category"] not in ("model_behavior", "unknown")],
        "diagnostics": deepcopy(run["diagnostics"]),
        "eligible_for_gain": contract["kind"] != "retrospective" and not run["historical"]
            and outcome not in ("invalid", "unreviewable")}


def aggregate(assessments: Sequence[dict]) -> dict:
    seen = set()
    arms = defaultdict(list)
    for item in assessments:
        _require(item.get("schema") == ASSESSMENT_SCHEMA and item.get("outcome") in OUTCOMES, "invalid assessment")
        _require(item["run_id"] not in seen, "duplicate run in aggregate")
        seen.add(item["run_id"])
        arms[item["arm"]].append(item)
    result = {}
    for arm, items in arms.items():
        counts = Counter(i["outcome"] for i in items)
        valid = len(items) - counts["invalid"] - counts["unreviewable"]
        attribution = {name: dict(Counter(i["outcome"] for i in items if i["assistance"] == name)) for name in ASSISTANCE}
        result[arm] = {"total": len(items), "valid": valid, **{k: counts[k] for k in OUTCOMES},
            "quality_rate": {"numerator": counts["met"], "denominator": valid},
            "delivered": sum(i["delivered"] for i in items), "attribution": attribution,
            "terminations": dict(Counter(i["termination"] for i in items)),
            "diagnostics": dict(sum((Counter(i["diagnostics"]) for i in items), Counter()))}
    return {"arms": result, "note": "Task outcomes precede diagnostic counts; invalid and unreviewable records stay visible. No project Strict inference."}


def quality_gate(assessments: Sequence[dict], *, task_ids: Sequence[str], repeats: int, arm: str) -> dict:
    aggregate(assessments)
    _require(bool(task_ids) and len(set(task_ids)) == len(task_ids) and type(repeats) is int and repeats > 0, "invalid registered grid")
    items = [r for r in assessments if r["arm"] == arm]
    keys = [(r["task_id"], r["repeat"]) for r in items]
    wanted = {(task, repeat) for task in task_ids for repeat in range(1, repeats + 1)}
    complete = len(keys) == len(set(keys)) and set(keys) == wanted
    consistent = len({r["execution_identity_sha256"] for r in items}) == 1
    contracts = defaultdict(set)
    for r in items:
        contracts[r["task_id"]].add(r["contract_sha256"])
    consistent = consistent and all(len(v) == 1 for v in contracts.values())
    return {"passed": bool(complete and consistent and all(r["outcome"] == "met" and r["eligible_for_gain"] for r in items)),
        "complete_grid": complete, "consistent_identity_and_contract": consistent,
        "scope": sorted({r["scope"] for r in items}),
        "note": "Fixed-group outcome quality only, not general ability or comparative cost benefit. Recovered protocol/tool errors remain diagnostics."}


def compare_counts(*, baseline_met: int, candidate_met: int, total: int, required_gain: int) -> dict:
    _require(type(total) is int and total > 0 and all(type(n) is int and 0 <= n <= total for n in (baseline_met, candidate_met, required_gain)), "invalid comparison counts")
    status = "ceiling_limited" if total - baseline_met < required_gain else "threshold_met" if candidate_met - baseline_met >= required_gain else "threshold_not_met"
    return {"comparison": status, "baseline_quality_met": baseline_met, "candidate_quality_met": candidate_met,
        "observed_gain": candidate_met - baseline_met, "required_gain": required_gain,
        "note": "Descriptive threshold check, not statistical significance or candidate ability failure."}


def capture_diagnostic_run(directory: Path, *, task_id: str, arm: str, repeat: int,
    protocol_error_policy: str, execution_identity: dict, historical: bool, assistance: str) -> dict:
    """Capture existing direct-run artifacts without synthesizing model input or answers."""
    from .model_io import ModelIOError, parse_model_command, validate_final_answer

    directory = Path(directory)
    trace_path = directory / "model_trace.jsonl"
    _require(trace_path.is_file(), "actual model trace is required")
    result = json.loads((directory / "RESULT.json").read_text())
    events = [json.loads(line) for line in trace_path.read_text().splitlines()]
    generations = [e["raw_generation"] for e in events if e["type"] == "model_session_generation_returned"]
    _require(assistance in ASSISTANCE, "explicit assistance attribution required")
    committed = {e["candidate_id"] for e in events if e["type"] == "model_session_candidate_committed"}
    finals = []
    for generation in generations:
        try:
            command = parse_model_command(generation["raw_output"])
        except ModelIOError:
            continue
        if command.name == "final_answer" and generation.get("candidate_id") in committed:
            validate_final_answer(command)
            finals.append(command.arguments["text"])
    answer = result.get("final")
    _require(answer == (finals[-1] if finals else None), "delivery does not match original model answer")
    evidence = []
    files = [directory / "RESULT.json", trace_path]
    if (directory / "state_snapshot.json").is_file():
        files.append(directory / "state_snapshot.json")
    files.extend(sorted(p for p in (directory / "workspace").rglob("*") if p.is_file()))
    for index, path in enumerate(files):
        _require(not path.is_symlink() and path.resolve().is_relative_to(directory.resolve()), "unsafe evidence path")
        evidence.append({"id": f"E{index + 1}", "path": path.relative_to(directory).as_posix(),
            "sha256": file_digest(path), "kind": "source" if path.is_relative_to(directory / "workspace") else "trace"})
    feedback = set()
    state_path = directory / "state_snapshot.json"
    if state_path.is_file():
        state = json.loads(state_path.read_text())
        states = state.get("model_states", {})
        rejections = {key for key, event in state.get("model_events", {}).items() if event.get("event_type") == "protocol_rejection"}
        for event in events:
            if event["type"] == "model_session_generation_started":
                feedback.update(set(states.get(event["input_checkpoint_id"], {}).get("event_ids", [])) & rejections)
    rejected = sum(e["type"] == "model_session_candidate_rolled_back" for e in events)
    return {"schema": RUN_SCHEMA, "run_id": result["id"], "task_id": task_id, "arm": arm, "repeat": repeat,
        "protocol_error_policy": protocol_error_policy, "execution_identity": deepcopy(execution_identity),
        "termination": result["termination"], "answer": answer, "artifact_ids": [],
        "assistance": assistance, "historical": historical, "evidence": evidence,
        "diagnostics": {"model_calls": len(generations), "input_tokens": sum(len(g["prompt_token_ids"]) for g in generations),
            "output_tokens": sum(len(g["raw_token_ids"]) for g in generations),
            "protocol_rejections": rejected, "feedback_consumed": len(feedback),
            "tool_errors": sum(not a["result"]["success"] for a in result.get("actions", []))}}
