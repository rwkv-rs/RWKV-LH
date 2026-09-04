#!/usr/bin/env python3
"""Freeze source authorities for the five new G1J StateTune datasets.

This is a source-curation command, not a dataset generator.  The five formal
dataset generators remain the only commands allowed to render prompt/target
training rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable, Iterable

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.goal_state_protocols.dataset_contract import (
    ROOT,
    SOURCE_FIELDS,
    STAGE_SPECS,
    canonical_json_line,
    split_for_family,
)
from rwkv_lh.goal_state_protocols.dataset_verifiers import operation_contract


AUTHORITY_SCHEMA_VERSION = "rwkv-lh.g1j-per-stage-state-source-authority.v1"
EXPERIMENT_ID = "G1J_PER_STAGE_STATE_TUNING_V1_20260902"

SELECTOR_OBJECTIVES = {
    "list_directory": "inventory bounded path, type, and size metadata without opening file contents",
    "search_text": "locate exact matching UTF-8 lines inside the workspace without using the public web",
    "read_file": "observe one tokenizer-bounded byte range from a known plain-text workspace artifact",
    "read_json": "parse a known JSON artifact and observe its canonical structured byte range",
    "file_digest": "measure the SHA-256 digest and byte size of one existing workspace artifact",
    "write_file": "atomically create a complete UTF-8 text artifact from already committed content",
    "write_json": "atomically replace one complete JSON value while preserving no unspecified fields",
    "patch_json": "update explicit top-level keys in an existing JSON object and preserve the other keys",
    "replace_text": "replace one exact occurrence in an existing UTF-8 artifact",
    "remove_line": "remove one complete known text line from an existing artifact",
    "append_file": "append committed UTF-8 content to an existing workspace artifact",
    "make_directory": "create one scoped directory needed by the active frontier",
    "copy_file": "duplicate one existing artifact's exact bytes to a destination",
    "move_file": "rename one existing artifact so the source disappears and the destination remains",
    "delete_file": "delete one explicitly scoped obsolete workspace path",
    "bind_evidence": "retain an exact line span with its source locator as completion evidence",
    "check_command": "run a read-only test or inspection process with argv and shell disabled",
    "run_command": "run a potentially mutating local process with argv and shell disabled",
    "web_search": "search the public web for a current exact record and preserve content-addressed evidence",
    "connector_lookup": "query a structured public source for an exact repository record",
    "calculator": "evaluate one complete arithmetic expression using already known operands",
    "date_diff": "calculate the absolute calendar-day distance between two observed ISO dates",
    "current_time": "observe the current clock reading for one specified IANA timezone",
    "final_answer": "return the evidence-complete result now that every planned step is committed",
    "ABSTAIN": "resolve an ambiguous frontier with conflicting and insufficient facts before choosing any operation",
}


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _signature(*values: str) -> str:
    seed = "\0".join(values).encode("utf-8")
    # A long, content-addressed fixture context keeps identical production tool
    # contracts from dominating the preregistered byte-5gram comparison.
    return "".join(
        hashlib.sha256(f"g1j-{index}\0".encode("ascii") + seed).hexdigest()
        for index in range(8)
    )


def _families(stage: str, namespace: str, split: str, count: int) -> list[str]:
    selected: list[str] = []
    candidate = 0
    while len(selected) < count:
        family = f"g1j-{stage}-{namespace}-family-{candidate:05d}"
        if split_for_family(family)[0] == split:
            selected.append(family)
        candidate += 1
    return selected


def _eligible(selected: str, variant: int) -> list[str]:
    if selected == "final_answer":
        return ["final_answer"]
    nonterminal = list(NETWORK_EXACT_TOOL_LABELS[:-2])
    if selected == "ABSTAIN":
        candidates = {
            nonterminal[(variant * 3 + 2) % len(nonterminal)],
            nonterminal[(variant * 7 + 9) % len(nonterminal)],
            "ABSTAIN",
        }
    else:
        index = nonterminal.index(selected)
        candidates = {
            selected,
            nonterminal[(index + 5 + variant) % len(nonterminal)],
            nonterminal[(index + 11 + 2 * variant) % len(nonterminal)],
        }
    return [label for label in NETWORK_EXACT_TOOL_LABELS if label in candidates]


def _selector_sources() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    split_counts = {"train": 12, "dev": 4, "sealed": 4}
    for label_index, label in enumerate(NETWORK_EXACT_TOOL_LABELS):
        variant = 0
        for split, count in split_counts.items():
            for family in _families("selector", f"label-{label_index:02d}", split, count):
                signature = _signature("selector", label, family)
                objective = (
                    f"Fixture context {signature}: the only current frontier is to "
                    f"{SELECTOR_OBJECTIVES[label]}. No later plan step may be advanced."
                )
                competitors = _eligible(label, variant)
                prior = NETWORK_EXACT_TOOL_LABELS[(label_index - 1) % 23]
                payload = {
                    "stage_objective": objective,
                    "stage_role": "route exactly one operation for the isolated current frontier",
                    "progress": {
                        "completed_stage_count": variant % 4,
                        "action_index": variant % 7,
                        "succeeded_operations": [] if variant % 3 else [prior],
                        "failed_operations": [] if variant % 5 else [prior],
                        "protocol_rejection_count": variant % 2,
                    },
                    "eligible_labels": competitors,
                    "selected_operation": label,
                    "selection_authority": "planner_contract",
                    "selection_verifier_id": "g1j-selector-operation-policy.v1",
                }
                rows.append(
                    {
                        "source_id": f"g1j-selector-{label_index:02d}-{variant:03d}",
                        "stage": "selector_intent",
                        "project_family": family,
                        "source_kind": "executable_fixture",
                        "parent_source_ids": [],
                        "payload": payload,
                    }
                )
                variant += 1
    return rows


def _executor_params(operation: str, variant: int) -> dict[str, Any]:
    suffix = f"{variant:03d}"
    commands: dict[str, Callable[[], dict[str, Any]]] = {
        "write_file": lambda: {
            "path": f"written-{suffix}.txt",
            "content": f"committed fixture payload {suffix}\n",
            "overwrite": True,
            "create_parents": True,
        },
        "write_json": lambda: {
            "path": f"written-{suffix}.json",
            "value": {"fixture": suffix, "ready": True},
            "overwrite": True,
            "create_parents": True,
        },
        "patch_json": lambda: {
            "path": "fixture.json",
            "updates": {"alpha": variant + 10, "fixture": suffix},
        },
        "replace_text": lambda: {
            "path": "fixture.txt",
            "old": "beta",
            "new": f"delta-{suffix}",
            "count": 1,
            "all": False,
        },
        "remove_line": lambda: {"path": "fixture.txt", "text": "beta", "all": False},
        "append_file": lambda: {"path": "fixture.txt", "content": f"append-{suffix}\n"},
        "delete_file": lambda: {"path": "delete-me.txt", "missing_ok": False, "recursive": False},
        "make_directory": lambda: {"path": f"created-{suffix}", "parents": True},
        "copy_file": lambda: {"source": "source.bin", "destination": f"copied-{suffix}.bin"},
        "move_file": lambda: {"source": "source.bin", "destination": f"moved-{suffix}.bin"},
        "file_digest": lambda: {"path": "fixture.txt"},
        "list_directory": lambda: {
            "path": ".",
            "recursive": False,
            "max_entries": 64,
            "start_after": "",
            "max_tokens": 1024,
        },
        "search_text": lambda: {
            "pattern": "alpha",
            "path": ".",
            "mode": "literal",
            "case_sensitive": True,
            "recursive": True,
            "max_results": 25,
            "start_after": "",
            "max_tokens": 1024,
            "max_file_bytes": 100000,
            "max_line_chars": 400,
        },
        "read_file": lambda: {"path": "fixture.txt", "start_byte": 0, "max_tokens": 1024},
        "read_json": lambda: {"path": "fixture.json", "start_byte": 0, "max_tokens": 1024},
        "bind_evidence": lambda: {
            "path": "fixture.txt",
            "start_line": 1,
            "end_line": 2,
            "source": f"fixture-{suffix}",
            "max_tokens": 1024,
        },
        "check_command": lambda: {
            "argv": [
                sys.executable,
                "-c",
                "from pathlib import Path; assert Path('fixture.txt').read_text() == 'alpha\\nbeta\\ngamma\\n'",
            ],
            "cwd": ".",
            "timeout": 30.0,
            "env": {},
            "expected_exit_code": 0,
        },
        "run_command": lambda: {
            "argv": [
                sys.executable,
                "-c",
                f"from pathlib import Path; Path('process-{suffix}.txt').write_text('ok')",
            ],
            "cwd": ".",
            "timeout": 30.0,
            "env": {},
            "expected_exit_code": 0,
        },
        "web_search": lambda: {"query": f"G1J frozen public record {suffix}", "max_results": 5},
        "connector_lookup": lambda: {"operation": "github_repository", "query": f"RWKV-LH fixture {suffix}"},
        "calculator": lambda: {"expression": f"({variant + 17} * 3) + 5"},
        "date_diff": lambda: {
            "date_a": "2026-09-02",
            "date_b": f"2026-08-{(variant % 20) + 1:02d}",
            "source_a": f"fixture-a-{suffix}",
            "source_b": f"fixture-b-{suffix}",
        },
        "current_time": lambda: {"timezone": "Asia/Shanghai"},
    }
    return commands[operation]()


def _executor_sources() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    operations = list(NETWORK_EXACT_TOOL_LABELS[:-2])
    split_counts = {"train": 8, "dev": 3, "sealed": 3}
    for operation_index, operation in enumerate(operations):
        variant = 0
        for split, count in split_counts.items():
            for family in _families("executor", f"operation-{operation_index:02d}", split, count):
                signature = _signature("executor", operation, family)
                requirement = (
                    f"Executable context {signature}: satisfy only the committed {operation_index:02d} "
                    "frontier using its disclosed production contract and the isolated fixture."
                )
                payload = {
                    "current_requirement": requirement,
                    "selected_operation": operation,
                    "selected_tool_contract": operation_contract(operation),
                    "committed_fact_refs": [f"fact:{signature[:24]}"],
                    "executor_history": [],
                    "command": {"function": operation, "params": _executor_params(operation, variant)},
                    "fixture_id": f"g1j-executor-fixture-{operation_index:02d}-{variant:03d}",
                    "execution_verifier_id": "g1j-executor-isolated-workspace.v1",
                }
                rows.append(
                    {
                        "source_id": f"g1j-executor-{operation_index:02d}-{variant:03d}",
                        "stage": "executor_args",
                        "project_family": family,
                        "source_kind": "executable_fixture",
                        "parent_source_ids": [],
                        "payload": payload,
                    }
                )
                variant += 1
    return rows


STEP_FIELDS = (
    "step_id",
    "objective",
    "stage",
    "depends_on",
    "success_evidence",
    "obligation_ids",
    "read_roots",
    "write_roots",
    "allowed_operations",
    "constraints",
)


def _step_sources() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mutations = (
        ("complete", "committed", "rwkv-lh.evidence.v1", True, "observation_complete"),
        ("missing", "missing", "rwkv-lh.evidence.v1", False, "stagnation"),
        ("conflict", "conflicting", "rwkv-lh.evidence.v1", True, "observation_complete"),
        ("failure", "failed", "rwkv-lh.evidence.v1", True, "tool_failure"),
        ("truncated", "committed", "rwkv-lh.evidence.v1", False, "observation_complete"),
        ("version", "committed", "rwkv-lh.evidence.v0", True, "mutation_transaction_complete"),
    )
    family_counter = 0
    for split, family_count in {"train": 10, "dev": 3, "sealed": 3}.items():
        for family in _families("auditor-step", "trajectory", split, family_count):
            signature = _signature("auditor-step", family)
            step_id = f"S-{signature[:12]}"
            base_source_id = f"g1j-auditor-step-{family_counter:03d}-00"
            for mutation_index, (name, status, version, complete, boundary) in enumerate(mutations):
                evidence_ref = f"evidence:{signature[12:36]}"
                active_step = dict(
                    zip(
                        STEP_FIELDS,
                        (
                            step_id,
                            f"Verify artifact constellation {signature} and commit its exact bounded result.",
                            "verification",
                            [],
                            ["artifact digest and completion observation"],
                            [f"obligation:{signature[36:52]}"],
                            ["fixture/input"],
                            [],
                            ["file_digest", "bind_evidence"],
                            ["no mutation", "evidence required"],
                        ),
                    )
                )
                is_complete = name == "complete"
                payload = {
                    "boundary": boundary,
                    "active_step": active_step,
                    "available_evidence_refs": [evidence_ref],
                    "evidence_records": [
                        {
                            "evidence_ref": evidence_ref,
                            "status": status,
                            "version": version,
                            "complete": complete,
                            "quote": f"Observed constellation {signature[52:]} at immutable locator {signature[:20]}.",
                        }
                    ],
                    "decision": {
                        "verdict": "continue" if is_complete else "repair",
                        "step_id": step_id,
                        "step_complete": is_complete,
                        "evidence_refs": [evidence_ref] if is_complete else [],
                        "gaps": [] if is_complete else [f"completion evidence is {status} or invalid"],
                        "reason": "all required evidence is committed" if is_complete else "the active step remains unverified",
                    },
                    "completion_verifier_id": "g1j-step-completion-verifier.v1",
                }
                rows.append(
                    {
                        "source_id": f"g1j-auditor-step-{family_counter:03d}-{mutation_index:02d}",
                        "stage": "auditor_step",
                        "project_family": family,
                        "source_kind": "executable_fixture" if is_complete else "deterministic_counterfactual",
                        "parent_source_ids": [] if is_complete else [base_source_id],
                        "payload": payload,
                    }
                )
            family_counter += 1
    return rows


def _evidence_complete_fixture(signature: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    evidence_a = f"evidence:{signature[:24]}"
    evidence_b = f"evidence:{signature[24:48]}"
    path = f"artifacts/{signature[48:60]}/result.json"
    count = int(signature[60:64], 16) % 700 + 100
    steps = [
        {"step_id": f"S-{signature[:10]}", "complete": True, "evidence_refs": [evidence_a]},
        {"step_id": f"S-{signature[10:20]}", "complete": True, "evidence_refs": [evidence_b]},
    ]
    facts = [
        {"fact_id": f"fact:{signature[:12]}", "value": f"build-{count}", "evidence_refs": [evidence_a]},
        {"fact_id": f"fact:{signature[12:24]}", "value": path, "evidence_refs": [evidence_b]},
    ]
    evidence = [
        {
            "evidence_ref": evidence_a,
            "status": "committed",
            "quote": f"Verified build-{count} with signature {signature[64:96]}.",
        },
        {
            "evidence_ref": evidence_b,
            "status": "committed",
            "quote": f"Verified {path} with signature {signature[96:]}.",
        },
    ]
    return steps, facts, evidence


def _final_text(facts: list[dict[str, Any]], signature: str) -> str:
    return (
        "## Result\n"
        f"The verified result is {facts[0]['value']} at {facts[1]['value']}.\n\n"
        "## Evidence\n"
        f"Both committed evidence records were checked under fixture signature {signature[:32]}."
    )


def _finalizer_sources() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    counter = 0
    for split, count in {"train": 40, "dev": 12, "sealed": 12}.items():
        for family in _families("finalizer", "complete-goal", split, count):
            signature = _signature("finalizer", family)
            steps, facts, evidence = _evidence_complete_fixture(signature)
            payload = {
                "immutable_goal": f"Report the verified build and exact artifact path for goal signature {signature}.",
                "completed_steps": steps,
                "committed_facts": facts,
                "evidence_records": evidence,
                "format_contract": {
                    "format_id": "g1j-result-evidence-sections.v1",
                    "language": "English",
                    "required_sections": ["Result", "Evidence"],
                },
                "final_text": _final_text(facts, signature),
                "fact_verifier_id": "g1j-finalizer-fact-verifier.v1",
            }
            rows.append(
                {
                    "source_id": f"g1j-finalizer-{counter:03d}",
                    "stage": "finalizer_answer",
                    "project_family": family,
                    "source_kind": "executable_fixture",
                    "parent_source_ids": [],
                    "payload": payload,
                }
            )
            counter += 1
    return rows


def _mutate_final_candidate(
    name: str,
    steps: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    evidence: list[dict[str, Any]],
    text: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], str]:
    steps = json.loads(json.dumps(steps))
    facts = json.loads(json.dumps(facts))
    evidence = json.loads(json.dumps(evidence))
    if name == "delete_fact":
        text = text.replace(f" at {facts[1]['value']}", "")
    elif name == "replace_numeric":
        text = text.replace(str(facts[0]["value"]), "build-99999")
    elif name == "replace_path":
        text = text.replace(str(facts[1]["value"]), "artifacts/unverified/result.json")
    elif name == "unsupported_fact":
        text += "\nUNSUPPORTED: deployment has already completed."
    elif name == "evidence_binding":
        evidence[1]["status"] = "unbound"
    elif name == "format":
        text = text.replace("## Result", "Result").replace("## Evidence", "Evidence")
    elif name == "plan_incomplete":
        steps[1]["complete"] = False
    return steps, facts, evidence, text


def _final_auditor_sources() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mutations = (
        "ready",
        "delete_fact",
        "replace_numeric",
        "replace_path",
        "unsupported_fact",
        "evidence_binding",
        "format",
        "plan_incomplete",
    )
    family_counter = 0
    for split, count in {"train": 8, "dev": 2, "sealed": 2}.items():
        for family in _families("auditor-final", "candidate", split, count):
            signature = _signature("auditor-final", family)
            base_steps, base_facts, base_evidence = _evidence_complete_fixture(signature)
            base_text = _final_text(base_facts, signature)
            base_source_id = f"g1j-auditor-final-{family_counter:03d}-00"
            for mutation_index, mutation in enumerate(mutations):
                steps, facts, evidence, text = _mutate_final_candidate(
                    mutation, base_steps, base_facts, base_evidence, base_text
                )
                ready = mutation == "ready"
                available = sorted(record["evidence_ref"] for record in evidence)
                payload = {
                    "immutable_goal": f"Approve only the fully grounded final candidate for goal signature {signature}.",
                    "completed_steps": steps,
                    "committed_facts": facts,
                    "available_evidence_refs": available,
                    "evidence_records": evidence,
                    "final_candidate": {"function": "final_answer", "params": {"text": text}},
                    "decision": {
                        "verdict": "ready_for_final" if ready else "repair",
                        "step_id": "",
                        "step_complete": False,
                        "evidence_refs": available if ready else [],
                        "gaps": [] if ready else ["candidate differs from committed plan, facts, evidence, or format"],
                        "reason": "candidate is fully evidence-bound" if ready else "candidate must return to the Goal loop for repair",
                    },
                    "final_verifier_id": "g1j-final-candidate-verifier.v1",
                }
                rows.append(
                    {
                        "source_id": f"g1j-auditor-final-{family_counter:03d}-{mutation_index:02d}",
                        "stage": "auditor_final",
                        "project_family": family,
                        "source_kind": "executable_fixture" if ready else "deterministic_counterfactual",
                        "parent_source_ids": [] if ready else [base_source_id],
                        "payload": payload,
                    }
                )
            family_counter += 1
    return rows


def _source_sets() -> dict[str, list[dict[str, Any]]]:
    return {
        "selector_intent": _selector_sources(),
        "executor_args": _executor_sources(),
        "auditor_step": _step_sources(),
        "finalizer_answer": _finalizer_sources(),
        "auditor_final": _final_auditor_sources(),
    }


def _registry_row(
    record: dict[str, Any], authority_path: Path, authority_sha: str, locator: int
) -> dict[str, Any]:
    spec = STAGE_SPECS[record["stage"]]
    row = {
        "schema_version": spec.source_schema_version,
        "source_id": record["source_id"],
        "stage": spec.role_state_id,
        "project_family": record["project_family"],
        "source_kind": record["source_kind"],
        "source_path": str(authority_path.relative_to(ROOT)),
        "source_sha256": authority_sha,
        "record_locator": f"#/records/{locator}",
        "parent_source_ids": record["parent_source_ids"],
        "payload": record["payload"],
    }
    if tuple(row) != SOURCE_FIELDS:
        raise RuntimeError("source registry row order differs from frozen contract")
    return row


def freeze(experiment_root: Path) -> None:
    experiment_root = experiment_root.resolve()
    expected = ROOT / "data" / "experiments" / EXPERIMENT_ID
    if experiment_root != expected:
        raise ValueError(f"source freeze output must be the preregistered experiment: {expected}")
    if not experiment_root.is_dir():
        raise FileNotFoundError(f"experiment root does not exist: {experiment_root}")
    authority_directory = experiment_root / "source_authority"
    authority_path = authority_directory / "fixtures.json"
    source_sets = _source_sets()
    targets = [authority_directory, *(experiment_root / stage for stage in source_sets)]
    if any(path.exists() for path in targets):
        raise FileExistsError("source freeze refuses to overwrite an authority or stage directory")

    records = [record for stage in STAGE_SPECS for record in source_sets[stage]]
    authority = {
        "schema_version": AUTHORITY_SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "purpose": "Frozen executable and deterministic label authority for zero-State and later StateTune comparison.",
        "generation": str(Path(__file__).resolve().relative_to(ROOT)),
        "records": records,
    }
    authority_bytes = json.dumps(
        authority, ensure_ascii=False, sort_keys=False, separators=(",", ":")
    ).encode("utf-8") + b"\n"
    authority_sha = _sha256_bytes(authority_bytes)

    authority_directory.mkdir()
    authority_path.write_bytes(authority_bytes)
    locator_by_source = {record["source_id"]: index for index, record in enumerate(records)}
    for stage, stage_records in source_sets.items():
        stage_directory = experiment_root / stage
        stage_directory.mkdir()
        registry = [
            _registry_row(
                record,
                authority_path,
                authority_sha,
                locator_by_source[record["source_id"]],
            )
            for record in stage_records
        ]
        registry.sort(key=lambda row: row["source_id"].encode("utf-8"))
        (stage_directory / "source_registry.full.jsonl").write_bytes(
            b"".join(canonical_json_line(row) for row in registry)
        )

    summary = {
        "schema_version": "rwkv-lh.g1j-per-stage-state-source-freeze-summary.v1",
        "experiment_id": EXPERIMENT_ID,
        "authority_path": str(authority_path.relative_to(ROOT)),
        "authority_sha256": authority_sha,
        "stages": {
            stage: {
                "rows": len(rows),
                "source_registry_path": str(
                    (experiment_root / stage / "source_registry.full.jsonl").relative_to(ROOT)
                ),
            }
            for stage, rows in source_sets.items()
        },
        "status": "frozen",
    }
    (authority_directory / "freeze_summary.json").write_bytes(canonical_json_line(summary))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-experiment", required=True, type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    freeze(parse_args().output_experiment)
