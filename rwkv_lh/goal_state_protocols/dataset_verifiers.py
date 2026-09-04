"""Deterministic semantic authorities for frozen G1J StateTune datasets."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.harness import ActionHarness
from rwkv_lh.model_io import ModelCommand
from rwkv_lh.retrieval import (
    EgressProvenance,
    EvidenceRecord,
    EvidenceSpan,
    ExternalEvidenceEnvelope,
    NetworkPolicy,
    NetworkPolicyMode,
    SourceObject,
    build_retrieval_actions,
)
from rwkv_lh.schema import GoalState, TaskAction


ROOT = Path(__file__).resolve().parents[2]
VERIFIER_ID = "rwkv-lh.g1j-per-stage-state-dataset-verifier.v1"


class _FixtureRetrievalBackend:
    provider_name = "g1j-frozen-executable-fixture"
    connector_operations = (
        "github_repository",
        "github_release",
        "github_commit",
        "github_code",
        "package_release",
        "scholarly_record",
        "weather",
        "weather_alerts",
    )

    @staticmethod
    def _envelope(tool: str, arguments: Mapping[str, Any]) -> ExternalEvidenceEnvelope:
        request = dict(arguments)
        snapshot = (
            "Frozen G1J executable fixture confirms record build-731 and checksum "
            "a4d239c8 for protocol-bound validation."
        )
        span = EvidenceSpan.create(
            text="record build-731 and checksum a4d239c8",
            locator={"start_char": 39, "end_char": 80},
        )
        record = EvidenceRecord.create(
            source_object=SourceObject.create(
                source_object_id="https://fixture.invalid/g1j/record-731",
                source_object_type="frozen_fixture",
                source_record_id="record-731",
            ),
            snapshot_digest=hashlib.sha256(snapshot.encode("utf-8")).hexdigest(),
            exact_spans=(span,),
            url="https://fixture.invalid/g1j/record-731",
            title="G1J frozen executable fixture",
            retrieved_at="2026-09-02T00:00:00Z",
        )
        return ExternalEvidenceEnvelope.create(
            tool=tool,
            request=request,
            status="evidence_committed",
            records=(record,),
            as_of="2026-09-02T00:00:00Z",
            provider_attempts=({"provider": "frozen", "status": "ok"},),
        )

    def execute(self, tool: str, arguments: dict[str, Any]) -> ExternalEvidenceEnvelope:
        return self._envelope(tool, arguments)

    def recover(self, tool: str, arguments: dict[str, Any]) -> ExternalEvidenceEnvelope:
        return self._envelope(tool, arguments)


def _public_provenance(_goal, _tool, arguments):
    return {
        key: EgressProvenance.MODEL_PUBLIC_QUERY
        for key, value in arguments.items()
        if isinstance(value, str) and value
    }


def _product_harness() -> ActionHarness:
    actions = build_retrieval_actions(
        backend=_FixtureRetrievalBackend(),
        network_policy=NetworkPolicy(NetworkPolicyMode.AUTO_PUBLIC),
        provenance_resolver=_public_provenance,
        connector_operations=_FixtureRetrievalBackend.connector_operations,
        include_network_actions=True,
        clock=lambda: datetime(2026, 9, 2, 12, 34, 56, tzinfo=timezone.utc),
    )
    return ActionHarness(sandbox_commands=False, actions=actions)


_HARNESS = _product_harness()
_DEFINITIONS = {
    item["name"]: item
    for item in _HARNESS.g1i_tool_definitions(
        [label for label in NETWORK_EXACT_TOOL_LABELS if label not in {"final_answer", "ABSTAIN"}]
    )
}
if tuple(_DEFINITIONS) != tuple(
    label for label in NETWORK_EXACT_TOOL_LABELS if label not in {"final_answer", "ABSTAIN"}
):
    raise RuntimeError("production operation registry differs from Selector class order")


def _registry_digest() -> str:
    value = json.dumps(
        list(_DEFINITIONS.values()),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(value).hexdigest()


OPERATION_REGISTRY_SHA256 = _registry_digest()


def operation_contract(operation: str) -> dict[str, Any]:
    if operation not in _DEFINITIONS:
        raise ValueError(f"operation has no production Executor contract: {operation}")
    return json.loads(json.dumps(_DEFINITIONS[operation], ensure_ascii=False))


def _initialize_workspace(workspace: Path, operation: str) -> None:
    (workspace / "fixture.txt").write_text("alpha\nbeta\ngamma\n", encoding="utf-8")
    (workspace / "fixture.json").write_text(
        '{"alpha":1,"beta":"two","preserve":true}\n', encoding="utf-8"
    )
    (workspace / "source.bin").write_bytes(b"frozen-source-bytes\n")
    (workspace / "delete-me.txt").write_text("delete this fixture\n", encoding="utf-8")
    if operation == "make_directory":
        # The selected destination itself must remain absent before execution.
        pass


def _verify_executor_execution(payload: Mapping[str, Any]) -> None:
    operation = str(payload["selected_operation"])
    contract = operation_contract(operation)
    if payload["selected_tool_contract"] != contract:
        raise ValueError("Executor selected_tool_contract differs from production registry")
    command = payload["command"]
    if command["function"] != operation or not isinstance(command["params"], Mapping):
        raise ValueError("Executor command does not preserve the selected operation")
    properties = contract["parameters"]["properties"]
    if set(command["params"]) != set(properties):
        raise ValueError("Executor command must explicitly supply every registered parameter")
    normalized = _HARNESS.normalize_action(TaskAction(operation, dict(command["params"])))
    if normalized.arguments != dict(command["params"]):
        raise ValueError("Executor command still depends on Controller defaults or normalization")
    temp_root = ROOT / "temp"
    temp_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="g1j-executor-fixture-", dir=temp_root) as raw:
        workspace = Path(raw)
        _initialize_workspace(workspace, operation)
        goal = GoalState.create(
            request=str(payload["current_requirement"]),
            constraints=("isolated executable fixture",),
            workspace_root=workspace,
        )
        result = _HARNESS.execute(normalized, goal)
        if not result.success:
            raise ValueError(
                f"Executor fixture failed for {operation}: "
                f"{json.dumps(result.error, ensure_ascii=False)}"
            )


def _evidence_refs(records: Any) -> set[str]:
    if not isinstance(records, list):
        raise ValueError("evidence_records must be an array")
    refs: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("evidence record must be an object")
        ref = str(record.get("evidence_ref") or "")
        if not ref or ref in refs:
            raise ValueError("evidence records require unique evidence_ref values")
        refs.add(ref)
    return refs


def _verify_selector(payload: Mapping[str, Any], prompt: str) -> None:
    selected = str(payload["selected_operation"])
    eligible = list(payload["eligible_labels"])
    if eligible != [label for label in NETWORK_EXACT_TOOL_LABELS if label in set(eligible)]:
        raise ValueError("eligible_labels must preserve production registry order")
    if selected not in eligible:
        raise ValueError("selected operation is not eligible")
    objective = str(payload["stage_objective"])
    role = str(payload["stage_role"])
    if selected not in {"final_answer", "ABSTAIN"} and selected in objective + role:
        raise ValueError("Selector label leaked outside the eligible menu")
    if selected == "final_answer" and eligible != ["final_answer"]:
        raise ValueError("completion must use the singleton final_answer menu")
    if selected == "ABSTAIN" and not any(
        marker in objective.lower() for marker in ("ambiguous", "insufficient", "conflicting")
    ):
        raise ValueError("ABSTAIN requires a genuinely ambiguous fixture")
    if selected != "ABSTAIN" and selected != "final_answer" and len(eligible) < 2:
        raise ValueError("nonterminal Selector fixtures require a real competing label")
    if str(payload["selection_verifier_id"]) != "g1j-selector-operation-policy.v1":
        raise ValueError("Selector fixture uses an unknown selection verifier")
    if "selected_operation" in prompt or "selection_authority" in prompt:
        raise ValueError("Selector authority fields crossed into the prompt")


def _verify_step_audit(payload: Mapping[str, Any]) -> None:
    refs = _evidence_refs(payload["evidence_records"])
    if refs != set(payload["available_evidence_refs"]):
        raise ValueError("Step-Auditor evidence refs are not fully projected")
    records = payload["evidence_records"]
    complete = bool(records) and all(
        record.get("status") == "committed"
        and record.get("version") == "rwkv-lh.evidence.v1"
        and record.get("complete") is True
        for record in records
    )
    decision = payload["decision"]
    if complete != (decision["verdict"] == "continue"):
        raise ValueError("Step-Auditor decision differs from deterministic completion verification")
    if complete and set(decision["evidence_refs"]) != refs:
        raise ValueError("completed Step-Auditor fixture must bind all evidence")


def _fact_text(fact: Mapping[str, Any]) -> str:
    value = fact["value"]
    return json.dumps(value, ensure_ascii=False, sort_keys=True) if not isinstance(value, str) else value


def _verify_finalizer(payload: Mapping[str, Any]) -> None:
    refs = _evidence_refs(payload["evidence_records"])
    final_text = str(payload["final_text"])
    for step in payload["completed_steps"]:
        if not set(step["evidence_refs"]) <= refs:
            raise ValueError("Finalizer step evidence is not available")
    for fact in payload["committed_facts"]:
        if not set(fact["evidence_refs"]) <= refs:
            raise ValueError("Finalizer fact evidence is not available")
        if _fact_text(fact) not in final_text:
            raise ValueError("Finalizer candidate omitted a committed fact")
    required_sections = payload["format_contract"]["required_sections"]
    if any(f"## {section}" not in final_text for section in required_sections):
        raise ValueError("Finalizer candidate violated the frozen format contract")
    if str(payload["fact_verifier_id"]) != "g1j-finalizer-fact-verifier.v1":
        raise ValueError("Finalizer fixture uses an unknown fact verifier")


def _candidate_ready(payload: Mapping[str, Any]) -> bool:
    refs = _evidence_refs(payload["evidence_records"])
    if refs != set(payload["available_evidence_refs"]):
        return False
    if any(not step.get("complete") for step in payload["completed_steps"]):
        return False
    if any(not set(step["evidence_refs"]) <= refs for step in payload["completed_steps"]):
        return False
    candidate = ModelCommand(
        str(payload["final_candidate"]["function"]),
        dict(payload["final_candidate"]["params"]),
    )
    text = str(candidate.arguments.get("text") or "")
    if "UNSUPPORTED:" in text:
        return False
    if any(not set(fact["evidence_refs"]) <= refs for fact in payload["committed_facts"]):
        return False
    if any(_fact_text(fact) not in text for fact in payload["committed_facts"]):
        return False
    if any(record.get("status") != "committed" for record in payload["evidence_records"]):
        return False
    if "## Result" not in text or "## Evidence" not in text:
        return False
    return True


def _verify_final_audit(payload: Mapping[str, Any], prompt: str) -> None:
    ready = _candidate_ready(payload)
    decision = payload["decision"]
    if ready != (decision["verdict"] == "ready_for_final"):
        raise ValueError("Final-Auditor decision differs from deterministic final verification")
    if ready and set(decision["evidence_refs"]) != set(payload["available_evidence_refs"]):
        raise ValueError("ready_for_final must bind every available evidence record")
    if "mutation" in prompt.lower():
        raise ValueError("Final-Auditor mutation identity leaked into the prompt")
    if str(payload["final_verifier_id"]) != "g1j-final-candidate-verifier.v1":
        raise ValueError("Final-Auditor fixture uses an unknown final verifier")


def verify_stage_payload(
    stage: str,
    payload: Mapping[str, Any],
    prompt: str,
    target: str,
    parsed: Any,
) -> None:
    del target, parsed
    if stage == "selector_intent":
        _verify_selector(payload, prompt)
    elif stage == "executor_args":
        _verify_executor_execution(payload)
    elif stage == "auditor_step":
        _verify_step_audit(payload)
    elif stage == "finalizer_answer":
        _verify_finalizer(payload)
    elif stage == "auditor_final":
        _verify_final_audit(payload, prompt)
    else:
        raise ValueError(f"unknown G1J dataset stage: {stage}")


__all__ = [
    "OPERATION_REGISTRY_SHA256",
    "VERIFIER_ID",
    "operation_contract",
    "verify_stage_payload",
]
