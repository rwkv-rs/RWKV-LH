from __future__ import annotations

import hashlib
import json
from dataclasses import replace

import pytest

from rwkv_lh.atom_execution import AtomExecutionContract
from rwkv_lh.contract_graph import (
    ContractAssertion,
    ContractExecutionBatch,
    ContractGraphNode,
    ContractGraphPatch,
    ContractGraphReview,
    ContractObligation,
    ContractPlanRequest,
    ContractReviewRequest,
    ObligationVerdict,
    ObligationVerdictStatus,
    ObligationPhase,
    ResultCapsule,
    extract_request_paths,
    validate_contract_assertion_coverage,
    validate_content_mutation_dependencies,
)
from rwkv_lh.capability_projection import project_contract_capabilities
from rwkv_lh.contract_validation import validate_contract_patch_semantics
from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionDefinition, ActionHarness, ActionResult
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.parallel_atoms import (
    AtomExecutionOutcome,
    AtomExecutionStatus,
    ThreadedRWKVAtomPool,
)
from rwkv_lh.schema import RunStatus
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.supervisor import AtomRole, SupervisorAtom, SupervisorPolicy
from rwkv_lh.trace_projection import project_run_activity


REQUEST = "Create left.txt containing left and right.txt containing right."


def execution_contract(atom: SupervisorAtom) -> AtomExecutionContract:
    return AtomExecutionContract.create(
        immutable_request=REQUEST,
        atom=atom,
    )


def obligation(identifier: str, clause: str = REQUEST) -> ContractObligation:
    return ContractObligation.create(
        REQUEST,
        obligation_id=identifier,
        request_clause=clause,
        predicate=f"The public state proves {identifier}.",
        evidence_kinds=("file", "digest"),
    )


def node(identifier: str, obligation_id: str, *, depends_on=()) -> ContractGraphNode:
    atom = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id=identifier,
        role="work",
        objective=f"Establish {obligation_id}.",
        request_clauses=(REQUEST,),
        depends_on=depends_on,
        read_roots=(),
        write_roots=("left.txt",),
        exclusive=False,
        allowed_operations=("write_file",),
        action_budget=1,
        completion_checks=(f"Evidence exists for {obligation_id}.",),
    )
    return ContractGraphNode.create(
        node_id=identifier,
        obligation_ids=(obligation_id,),
        atom=atom,
    )


def capsule(node_id: str = "NODE-1") -> ResultCapsule:
    return ResultCapsule.create(
        node_id=node_id,
        node_status="completed",
        operation="write_file",
        result={"success": True, "path": "left.txt"},
        artifacts=(
            {
                "path": "left.txt",
                "sha256": "a" * 64,
                "size_bytes": 4,
            },
        ),
        workspace_revision="revision-1",
    )


def test_semantic_assertion_can_target_a_non_file_route_outcome() -> None:
    assertion = ContractAssertion.create(
        assertion_id="ASSERT-route",
        kind="semantic_review",
        target_path="",
    )
    assert assertion.target_path == ""
    assert assertion.local_evaluation_issue().startswith("assertion explicitly")


def test_command_succeeded_can_bind_a_named_deterministic_action() -> None:
    assertion = ContractAssertion.create(
        assertion_id="ASSERT-calculate",
        kind="command_succeeded",
        expected="calculator",
    )
    observed = ResultCapsule.create(
        node_id="NODE-calculate",
        node_status="completed",
        operation="calculator",
        result={"success": True, "output": '{"value":42}'},
        artifacts=(),
        workspace_revision="revision-1",
    )

    passed, refs, reason = LongHorizonController._evaluate_typed_assertion(
        assertion,
        (observed,),
    )

    assert passed is True
    assert refs == (observed.evidence_id,)
    assert reason == "command result succeeded"


def test_obligation_clause_must_be_verbatim_request_text() -> None:
    with pytest.raises(ValueError, match="verbatim"):
        obligation("OBL-1", "Create a file that was never requested.")


def test_contract_obligation_cannot_be_downgraded_to_optional() -> None:
    with pytest.raises(ValueError, match="must be required"):
        ContractObligation.create(
            REQUEST,
            obligation_id="OBL-optional",
            request_clause=REQUEST,
            predicate="Create both requested files.",
            evidence_kinds=("file_write",),
            required=False,
        )


def test_contract_obligation_rejects_invented_explicit_json_key() -> None:
    with pytest.raises(ValueError, match="explicit JSON keys"):
        ContractObligation.create(
            "Create result.json containing the source path and requirements.",
            obligation_id="OBL-json-key",
            request_clause=(
                "Create result.json containing the source path and requirements."
            ),
            predicate=(
                "result.json contains explicit key `authoritative_source_path` "
                "and key `requirements`."
            ),
            evidence_kinds=("json_observation",),
        )


def test_typed_contract_assertion_round_trips_and_resolves_public_text() -> None:
    assertion = ContractAssertion.create(
        assertion_id="ASSERT-left-exact",
        kind="text_exact",
        target_path="left.txt",
        expected="left\n",
    )
    contract = ContractObligation.create(
        REQUEST,
        obligation_id="OBL-left-exact",
        request_clause=REQUEST,
        predicate="left.txt contains the exact requested content.",
        evidence_kinds=("read_file",),
        assertions=(assertion,),
    )
    restored = ContractObligation.from_dict(
        contract.to_dict(), immutable_request=REQUEST
    )
    observation = ResultCapsule.create(
        node_id="NODE-read-left",
        node_status="completed",
        operation="read_file",
        result={"success": True, "output": "left\n", "metadata": {"complete": True}},
        artifacts=({"path": "left.txt", "sha256": "a" * 64},),
        workspace_revision="revision-left",
    )

    verdicts = LongHorizonController._evaluate_typed_contract(
        {restored.obligation_id: restored}, (observation,)
    )

    assert verdicts[restored.obligation_id].status == ObligationVerdictStatus.SATISFIED
    assert verdicts[restored.obligation_id].evidence_refs == (
        observation.evidence_id,
    )


def test_typed_contract_coverage_rejects_weak_artifact_only_contract() -> None:
    request = (
        "Read metrics.json and create STATUS.md containing `# Service Status` "
        "with services sorted by name."
    )
    weak = ContractObligation.create(
        request,
        obligation_id="OBL-weak",
        request_clause=request,
        predicate="STATUS.md exists.",
        evidence_kinds=("artifact",),
        assertions=(
            ContractAssertion.create(
                assertion_id="ASSERT-only-exists",
                kind="artifact_exists",
                target_path="STATUS.md",
            ),
        ),
    )

    with pytest.raises(ValueError, match="exact request literals"):
        validate_contract_assertion_coverage(request, (weak,))


def test_request_path_extraction_splits_sibling_file_shorthand_only() -> None:
    request = (
        "Repair storage.py/service.py and index.html/styles.css/app.js, then "
        "update src/evidence_demo/cli.py."
    )

    assert extract_request_paths(request) == (
        "storage.py",
        "service.py",
        "index.html",
        "styles.css",
        "app.js",
        "src/evidence_demo/cli.py",
    )


def test_narrow_transaction_can_read_mutate_and_verify_same_target() -> None:
    contract = obligation("OBL-transaction")
    atom = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="NODE-transaction",
        role="work",
        objective="Inspect left.txt, update it, and verify the result.",
        request_clauses=(REQUEST,),
        read_roots=("left.txt",),
        write_roots=("left.txt",),
        allowed_operations=("read_file", "write_file"),
        action_budget=3,
        completion_checks=("The current target is read before and after mutation.",),
    )
    transaction = ContractGraphNode.create(
        node_id=atom.atom_id,
        obligation_ids=(contract.obligation_id,),
        atom=atom,
    )
    patch = ContractGraphPatch.create(
        request_digest="request-digest",
        base_revision=0,
        summary="Use one scoped RWKV transaction.",
        new_obligations=(contract,),
        new_nodes=(transaction,),
    )

    validate_content_mutation_dependencies(
        patch,
        existing_nodes={},
        result_capsules=(),
        visible_paths=("left.txt",),
    )
    assert transaction.atom.action_budget == 3
    assert transaction.atom.allowed_operations == ("read_file", "write_file")


def test_result_capsule_boundary_keeps_latest_artifact_observation(tmp_path) -> None:
    harness = ActionHarness(sandbox_commands=False)
    model = LongHorizonModel(harness=harness)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    store.create_run(model.create_literal_goal(REQUEST, str(workspace)), "RUN-LATEST")
    state = store.load("RUN-LATEST")
    controller = LongHorizonController(store, model=model, harness=harness)
    contract = obligation("OBL-latest")

    def reader(identifier: str) -> ContractGraphNode:
        selected = SupervisorAtom.create(
            immutable_request=REQUEST,
            atom_id=identifier,
            role="work",
            objective="Read the current left.txt contents.",
            request_clauses=(REQUEST,),
            read_roots=("left.txt",),
            allowed_operations=("read_file",),
            action_budget=1,
            completion_checks=("The complete current text is observed.",),
        )
        return ContractGraphNode.create(
            node_id=identifier,
            obligation_ids=(contract.obligation_id,),
            atom=selected,
        )

    old_node = reader("NODE-read-old")
    new_node = reader("NODE-read-new")

    def read_outcome(selected: ContractGraphNode, output: str, sha: str):
        return AtomExecutionOutcome(
            stage_id=f"STAGE-{selected.node_id}",
            atom_id=selected.node_id,
            contract_digest=execution_contract(selected.atom).contract_digest,
            role=AtomRole.WORK,
            status=AtomExecutionStatus.COMPLETED,
            candidate_output="private summary",
            candidate_decision_id=f"D-{selected.node_id}",
            action_count=1,
            model_request_count=2,
            protocol_rejections=0,
            actions=(
                {
                    "action_id": "A00001",
                    "sequence": 1,
                    "operation": "read_file",
                    "arguments": {"path": "left.txt"},
                    "status": "succeeded",
                    "result": {
                        "success": True,
                        "output": output,
                        "metadata": {"complete": True},
                    },
                    "artifact_refs": [],
                    "workspace_changed": False,
                },
            ),
            artifacts=(
                {
                    "action_id": "A00001",
                    "path": "left.txt",
                    "sha256": sha,
                    "size_bytes": len(output),
                    "media_type": "text/plain",
                },
            ),
            write_roots=(),
            error="",
            started_at="2026-08-23T00:00:00+00:00",
            ended_at="2026-08-23T00:00:01+00:00",
        )

    capsules = controller._contract_result_capsules(
        state,
        {old_node.node_id: old_node, new_node.node_id: new_node},
        {
            old_node.node_id: read_outcome(old_node, "old", "a" * 64),
            new_node.node_id: read_outcome(new_node, "new", "b" * 64),
        },
    )

    assert len(capsules) == 1
    assert capsules[0].node_id == new_node.node_id
    assert capsules[0].result["output"] == "new"


def test_multi_action_capsules_bind_artifacts_to_exact_action_and_keep_typed_views(
    tmp_path,
) -> None:
    harness = ActionHarness(sandbox_commands=False)
    model = LongHorizonModel(harness=harness)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    store.create_run(model.create_literal_goal(REQUEST, str(workspace)), "RUN-VIEWS")
    state = store.load("RUN-VIEWS")
    controller = LongHorizonController(store, model=model, harness=harness)
    contract = obligation("OBL-views")
    atom = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="NODE-views",
        role="work",
        objective="Read left.txt, then check it.",
        request_clauses=(REQUEST,),
        read_roots=("left.txt",),
        allowed_operations=("read_file", "check_command"),
        action_budget=2,
        completion_checks=("The content and check result are public.",),
    )
    graph_node = ContractGraphNode.create(
        node_id=atom.atom_id,
        obligation_ids=(contract.obligation_id,),
        atom=atom,
    )
    outcome = AtomExecutionOutcome(
        stage_id="STAGE-views",
        atom_id=atom.atom_id,
        contract_digest=execution_contract(atom).contract_digest,
        role=AtomRole.WORK,
        status=AtomExecutionStatus.COMPLETED,
        candidate_output="done",
        candidate_decision_id="D-views",
        action_count=2,
        model_request_count=2,
        protocol_rejections=0,
        actions=(
            {
                "action_id": "A-read",
                "operation": "read_file",
                "result": {
                    "success": True,
                    "output": "left\n",
                    "metadata": {"complete": True},
                },
            },
            {
                "action_id": "A-check",
                "operation": "check_command",
                "result": {"success": True, "output": "tests passed", "exit_code": 0},
            },
        ),
        artifacts=(
            {
                "action_id": "A-read",
                "path": "left.txt",
                "sha256": "a" * 64,
                "size_bytes": 5,
                "media_type": "text/plain",
            },
        ),
        write_roots=(),
        error="",
        started_at="2026-08-24T00:00:00+00:00",
        ended_at="2026-08-24T00:00:01+00:00",
    )

    capsules = controller._contract_result_capsules(
        state, {graph_node.node_id: graph_node}, {graph_node.node_id: outcome}
    )

    by_operation = {item.operation: item for item in capsules}
    assert by_operation["read_file"].artifacts[0]["path"] == "left.txt"
    assert by_operation["check_command"].artifacts == ()
    assertion = ContractAssertion.create(
        assertion_id="ASSERT-view-content",
        kind="text_exact",
        target_path="left.txt",
        expected="left\n",
    )
    assert LongHorizonController._evaluate_typed_assertion(assertion, capsules)[0] is True


def test_contract_capsules_include_controller_authoritative_network_audit(
    tmp_path,
) -> None:
    network_definition = ActionDefinition(
        "web_probe",
        "Synthetic registered network probe.",
        True,
        False,
        True,
        5.0,
        {"query": {"type": "string"}},
        required_arguments=("query",),
        capability_class="network.public_web",
        network_access="public_web",
        data_boundary="public_external",
        side_effect_class="external_read_only",
    )
    harness = ActionHarness(
        sandbox_commands=False,
        actions={
            "web_probe": (
                network_definition,
                lambda _goal, _arguments: ActionResult("web_probe", True),
            )
        },
    )
    model = LongHorizonModel(harness=harness)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    store.create_run(model.create_literal_goal(REQUEST, str(workspace)), "RUN-AUDIT")
    state = store.load("RUN-AUDIT")
    controller = LongHorizonController(store, model=model, harness=harness)

    no_attempt = controller._contract_result_capsules(state, {}, {})
    audit = next(item for item in no_attempt if item.operation == "network_audit")
    assert audit.result["no_network_action_attempted"] is True
    assert audit.result["network_backend_invocation_count"] == 0
    assert audit.workspace_revision.startswith("network-audit-")
    assert (
        next(
            item
            for item in controller._contract_result_capsules(state, {}, {})
            if item.operation == "network_audit"
        ).evidence_id
        == audit.evidence_id
    )

    contract = obligation("OBL-network-audit")
    atom = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="NODE-network-audit",
        role="work",
        objective="Exercise the registered public network route.",
        request_clauses=(REQUEST,),
        allowed_operations=("web_probe",),
        action_budget=1,
        completion_checks=("The exact operation result is public.",),
    )
    graph_node = ContractGraphNode.create(
        node_id=atom.atom_id,
        obligation_ids=(contract.obligation_id,),
        atom=atom,
    )
    outcome = AtomExecutionOutcome(
        stage_id="STAGE-network-audit",
        atom_id=atom.atom_id,
        contract_digest=execution_contract(atom).contract_digest,
        role=AtomRole.WORK,
        status=AtomExecutionStatus.COMPLETED,
        candidate_output="done",
        candidate_decision_id="D-network-audit",
        action_count=1,
        model_request_count=1,
        protocol_rejections=0,
        actions=(
            {
                "action_id": "A-network",
                "operation": "web_probe",
                "result": {
                    "success": False,
                    "outcome_type": "policy_rejected",
                    "metadata": {
                        "network_policy": {
                            "allowed": False,
                            "reason": "sensitive_egress_forbidden",
                        }
                    },
                },
            },
        ),
        artifacts=(),
        write_roots=(),
        error="",
        started_at="2026-08-25T00:00:00+00:00",
        ended_at="2026-08-25T00:00:01+00:00",
    )

    attempted = controller._contract_result_capsules(
        state,
        {graph_node.node_id: graph_node},
        {graph_node.node_id: outcome},
    )
    audit = next(item for item in attempted if item.operation == "network_audit")
    assert audit.result["network_action_count"] == 1
    assert audit.result["network_policy_rejection_count"] == 1
    assert audit.result["network_backend_invocation_count"] == 0


def test_contract_capsule_keeps_bounded_external_evidence_for_reviewer(
    tmp_path,
) -> None:
    definition = ActionDefinition(
        "web_probe",
        "Synthetic registered network probe.",
        True,
        False,
        True,
        5.0,
        {"query": {"type": "string"}},
        required_arguments=("query",),
        capability_class="network.public_web",
        network_access="public_web",
        data_boundary="public_external",
        side_effect_class="external_read_only",
    )
    harness = ActionHarness(
        sandbox_commands=False,
        actions={
            "web_probe": (
                definition,
                lambda _goal, _arguments: ActionResult("web_probe", True),
            )
        },
    )
    model = LongHorizonModel(harness=harness)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    store.create_run(model.create_literal_goal(REQUEST, str(workspace)), "RUN-EVIDENCE")
    state = store.load("RUN-EVIDENCE")
    controller = LongHorizonController(store, model=model, harness=harness)
    graph_atom = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="NODE-evidence",
        role="work",
        objective="Find official RWKV evidence.",
        request_clauses=(REQUEST,),
        allowed_operations=("web_probe",),
        action_budget=1,
        completion_checks=("The exact public source is preserved.",),
    )
    node = ContractGraphNode.create(
        node_id=graph_atom.atom_id,
        obligation_ids=(obligation("OBL-evidence").obligation_id,),
        atom=graph_atom,
    )
    source_text = "RWKV official source " + ("x" * 30_000)
    durable_result = {
        "success": True,
        "action_type": "web_probe",
        "outcome_type": "success",
        "output": source_text,
        "evidence": [
            {
                "evidence_record_id": "E-official",
                "source_object": {
                    "source_object_id": "public_web_page:official",
                    "source_object_type": "public_web_page",
                },
                "snapshot_digest": "a" * 64,
                "url": "https://example.test/official-rwkv",
                "title": "RWKV official source",
                "structured_fields": {"description": source_text},
                "exact_spans": [
                    {
                        "span_id": "SPAN-official",
                        "text": source_text,
                        "locator": {"start_char": 0, "end_char": len(source_text)},
                    }
                ],
            }
        ],
        "metadata": {
            "external_evidence": {
                "route_id": "ROUTE-official",
                "request_digest": "request-digest",
                "status": "evidence_committed",
            },
            "network_policy": {"allowed": True},
        },
    }
    original = json.dumps(durable_result, ensure_ascii=False, sort_keys=True)
    selected = AtomExecutionOutcome(
        stage_id="STAGE-evidence",
        atom_id=graph_atom.atom_id,
        contract_digest=execution_contract(graph_atom).contract_digest,
        role=AtomRole.WORK,
        status=AtomExecutionStatus.COMPLETED,
        candidate_output="done",
        candidate_decision_id="D-evidence",
        action_count=1,
        model_request_count=1,
        protocol_rejections=0,
        actions=(
            {
                "action_id": "A-evidence",
                "operation": "web_probe",
                "arguments": {"query": "RWKV official source"},
                "result": durable_result,
            },
        ),
        artifacts=(),
        write_roots=(),
        error="",
        started_at="2026-08-30T00:00:00+00:00",
        ended_at="2026-08-30T00:00:01+00:00",
    )

    capsules = controller._contract_result_capsules(
        state, {node.node_id: node}, {node.node_id: selected}
    )
    projected = next(item for item in capsules if item.operation == "web_probe")

    assert len(json.dumps(projected.to_dict(), ensure_ascii=False)) < 8_000
    assert projected.result["evidence"][0]["url"] == (
        "https://example.test/official-rwkv"
    )
    assert "RWKV official source" in (
        projected.result["evidence"][0]["exact_spans"][0]["text"]
    )
    assert projected.result["durable_result_persisted"] is True
    assert json.dumps(durable_result, ensure_ascii=False, sort_keys=True) == original


def test_mutation_receipt_invalidates_stale_content_without_becoming_content(tmp_path) -> None:
    harness = ActionHarness(sandbox_commands=False)
    model = LongHorizonModel(harness=harness)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    store.create_run(model.create_literal_goal(REQUEST, str(workspace)), "RUN-TOMBSTONE")
    state = store.load("RUN-TOMBSTONE")
    controller = LongHorizonController(store, model=model, harness=harness)
    contract = obligation("OBL-tombstone")

    def selected_node(identifier: str, operation: str) -> ContractGraphNode:
        atom = SupervisorAtom.create(
            immutable_request=REQUEST,
            atom_id=identifier,
            role="work",
            objective=f"Use {operation} on left.txt.",
            request_clauses=(REQUEST,),
            read_roots=(("left.txt",) if operation == "read_file" else ()),
            write_roots=(("left.txt",) if operation == "write_file" else ()),
            allowed_operations=(operation,),
            action_budget=1,
            completion_checks=("The exact operation result is public.",),
        )
        return ContractGraphNode.create(
            node_id=identifier,
            obligation_ids=(contract.obligation_id,),
            atom=atom,
        )

    reader = selected_node("NODE-old-content", "read_file")
    writer = selected_node("NODE-new-mutation", "write_file")

    def selected_outcome(node: ContractGraphNode, output: str, digest: str):
        return AtomExecutionOutcome(
            stage_id=f"STAGE-{node.node_id}",
            atom_id=node.node_id,
            contract_digest=execution_contract(node.atom).contract_digest,
            role=AtomRole.WORK,
            status=AtomExecutionStatus.COMPLETED,
            candidate_output="done",
            candidate_decision_id=f"D-{node.node_id}",
            action_count=1,
            model_request_count=1,
            protocol_rejections=0,
            actions=(
                {
                    "action_id": "A-one",
                    "operation": node.atom.allowed_operations[0],
                    "result": {"success": True, "output": output},
                },
            ),
            artifacts=(
                {
                    "action_id": "A-one",
                    "path": "left.txt",
                    "sha256": digest,
                    "size_bytes": len(output),
                },
            ),
            write_roots=node.atom.write_roots,
            error="",
            started_at="2026-08-24T00:00:00+00:00",
            ended_at="2026-08-24T00:00:01+00:00",
        )

    capsules = controller._contract_result_capsules(
        state,
        {reader.node_id: reader, writer.node_id: writer},
        {
            reader.node_id: selected_outcome(reader, "old", "a" * 64),
            writer.node_id: selected_outcome(writer, "wrote left.txt", "b" * 64),
        },
    )
    assertion = ContractAssertion.create(
        assertion_id="ASSERT-current-content",
        kind="text_exact",
        target_path="left.txt",
        expected="wrote left.txt",
    )

    passed, _, reason = LongHorizonController._evaluate_typed_assertion(
        assertion, capsules
    )
    assert passed is None
    assert "no complete public observation" in reason


def test_pre_mutation_baseline_supports_deterministic_preservation_checks() -> None:
    before_json = ResultCapsule.create(
        node_id="NODE-before-json",
        observation_id="A-before-json",
        node_status="completed",
        operation="read_json",
        result={
            "success": True,
            "output": json.dumps(
                {
                    "name": "alpha",
                    "feature": {"enabled": False, "mode": "legacy"},
                    "retries": 4,
                }
            ),
            "metadata": {"complete": True},
        },
        artifacts=({"path": "config.json", "sha256": "a" * 64},),
        workspace_revision="revision-before-json",
    )
    mutation = ResultCapsule.create(
        node_id="NODE-write-json",
        observation_id="A-write-json",
        node_status="completed",
        operation="write_json",
        result={"success": True, "output": "wrote config.json"},
        artifacts=({"path": "config.json", "sha256": "b" * 64},),
        workspace_revision="revision-write-json",
    )
    after_json = ResultCapsule.create(
        node_id="NODE-after-json",
        observation_id="A-after-json",
        node_status="completed",
        operation="read_json",
        result={
            "success": True,
            "output": json.dumps(
                {
                    "name": "alpha",
                    "feature": {"enabled": True, "mode": "safe"},
                    "retries": 4,
                }
            ),
            "metadata": {"complete": True},
        },
        artifacts=({"path": "config.json", "sha256": "b" * 64},),
        workspace_revision="revision-after-json",
    )

    selected = LongHorizonController._latest_contract_result_capsules(
        (before_json, mutation, after_json)
    )

    baseline = next(
        item for item in selected if item.operation == "pre_mutation_snapshot"
    )
    assert baseline.result["source_evidence_id"] == before_json.evidence_id
    assertion = ContractAssertion.create(
        assertion_id="ASSERT-preserve-unrelated",
        kind="json_preserve",
        target_path="config.json",
        sources=({"path": "config.json"},),
        keys=("/feature/enabled", "/feature/mode"),
    )
    passed, refs, reason = LongHorizonController._evaluate_typed_assertion(
        assertion, selected
    )
    assert passed is True
    assert after_json.evidence_id in refs
    assert baseline.evidence_id in refs
    assert reason == "typed JSON relation passed"


def test_text_remove_only_compares_current_bytes_with_baseline() -> None:
    before = ResultCapsule.create(
        node_id="NODE-before-text",
        observation_id="A-before-text",
        node_status="completed",
        operation="read_file",
        result={
            "success": True,
            "output": "name=demo\ndeprecated=true\nmode=prod\n",
            "metadata": {"complete": True},
        },
        artifacts=({"path": "app.env", "sha256": "a" * 64},),
        workspace_revision="revision-before-text",
    )
    mutation = ResultCapsule.create(
        node_id="NODE-remove-text",
        observation_id="A-remove-text",
        node_status="completed",
        operation="remove_line",
        result={"success": True, "output": "removed line"},
        artifacts=({"path": "app.env", "sha256": "b" * 64},),
        workspace_revision="revision-remove-text",
    )
    after = ResultCapsule.create(
        node_id="NODE-after-text",
        observation_id="A-after-text",
        node_status="completed",
        operation="read_file",
        result={
            "success": True,
            "output": "name=demo\nmode=prod\n",
            "metadata": {"complete": True},
        },
        artifacts=({"path": "app.env", "sha256": "b" * 64},),
        workspace_revision="revision-after-text",
    )
    selected = LongHorizonController._latest_contract_result_capsules(
        (before, mutation, after)
    )
    assertion = ContractAssertion.create(
        assertion_id="ASSERT-remove-only",
        kind="text_remove_only",
        target_path="app.env",
        sources=({"path": "app.env"},),
        expected="deprecated=true",
    )

    passed, _, reason = LongHorizonController._evaluate_typed_assertion(
        assertion, selected
    )

    assert passed is True
    assert reason == "typed text relation passed"


def test_truncated_contract_output_cannot_prove_complete_text_relation() -> None:
    bounded = LongHorizonController._bounded_contract_result(
        {
            "success": True,
            "action_type": "read_file",
            "output": "a" * 8000 + "forbidden-tail",
            "metadata": {"complete": True},
        }
    )
    observed = ResultCapsule.create(
        node_id="NODE-long-read",
        node_status="completed",
        operation="read_file",
        result=bounded,
        artifacts=({"path": "long.txt", "sha256": "a" * 64},),
        workspace_revision="revision-long-read",
    )
    assertion = ContractAssertion.create(
        assertion_id="ASSERT-no-forbidden-tail",
        kind="text_excludes",
        target_path="long.txt",
        expected="forbidden-tail",
    )

    passed, _, reason = LongHorizonController._evaluate_typed_assertion(
        assertion, (observed,)
    )

    assert bounded["metadata"]["complete"] is False
    assert bounded["output_projection"]["truncated"] is True
    assert passed is None
    assert "no complete public observation" in reason


def test_text_template_sorts_expected_rows_before_non_overlapping_match() -> None:
    source = ResultCapsule.create(
        node_id="NODE-template-source",
        node_status="completed",
        operation="read_json",
        result={
            "success": True,
            "output": json.dumps([{"name": "b"}, {"name": "a"}]),
            "metadata": {"complete": True},
        },
        artifacts=({"path": "rows.json", "sha256": "a" * 64},),
        workspace_revision="revision-template",
    )
    target = ResultCapsule.create(
        node_id="NODE-template-target",
        node_status="completed",
        operation="read_file",
        result={
            "success": True,
            "output": "a\nb\n",
            "metadata": {"complete": True},
        },
        artifacts=({"path": "report.txt", "sha256": "b" * 64},),
        workspace_revision="revision-template",
    )
    assertion = ContractAssertion.create(
        assertion_id="ASSERT-template-order",
        kind="text_template",
        target_path="report.txt",
        sources=({"path": "rows.json"},),
        expected="{name}\n",
        keys=("name",),
        order="ascending",
    )

    passed, _, reason = LongHorizonController._evaluate_typed_assertion(
        assertion, (source, target)
    )

    assert passed is True
    assert reason == "typed text relation passed"


def test_text_template_duplicate_rows_require_duplicate_output_occurrences() -> None:
    source = ResultCapsule.create(
        node_id="NODE-template-duplicates",
        node_status="completed",
        operation="read_json",
        result={
            "success": True,
            "output": json.dumps([{"name": "same"}, {"name": "same"}]),
            "metadata": {"complete": True},
        },
        artifacts=({"path": "rows.json", "sha256": "a" * 64},),
        workspace_revision="revision-template-duplicates",
    )
    target = ResultCapsule.create(
        node_id="NODE-template-one-line",
        node_status="completed",
        operation="read_file",
        result={
            "success": True,
            "output": "same\n",
            "metadata": {"complete": True},
        },
        artifacts=({"path": "report.txt", "sha256": "b" * 64},),
        workspace_revision="revision-template-duplicates",
    )
    assertion = ContractAssertion.create(
        assertion_id="ASSERT-template-count",
        kind="text_template",
        target_path="report.txt",
        sources=({"path": "rows.json"},),
        expected="{name}\n",
    )

    passed, _, reason = LongHorizonController._evaluate_typed_assertion(
        assertion, (source, target)
    )

    assert passed is False
    assert reason == "typed text relation failed"


def test_unordered_text_template_backtracks_across_substring_candidates() -> None:
    source = ResultCapsule.create(
        node_id="NODE-template-substrings",
        node_status="completed",
        operation="read_json",
        result={
            "success": True,
            "output": json.dumps([{"value": "a"}, {"value": "ab"}]),
            "metadata": {"complete": True},
        },
        artifacts=({"path": "rows.json", "sha256": "a" * 64},),
        workspace_revision="revision-template-substrings",
    )
    target = ResultCapsule.create(
        node_id="NODE-template-substring-target",
        node_status="completed",
        operation="read_file",
        result={
            "success": True,
            "output": "ab a",
            "metadata": {"complete": True},
        },
        artifacts=({"path": "report.txt", "sha256": "b" * 64},),
        workspace_revision="revision-template-substrings",
    )
    assertion = ContractAssertion.create(
        assertion_id="ASSERT-template-substrings",
        kind="text_template",
        target_path="report.txt",
        sources=({"path": "rows.json"},),
        expected="{value}",
    )

    passed, _, reason = LongHorizonController._evaluate_typed_assertion(
        assertion,
        (source, target),
    )

    assert passed is True
    assert reason == "typed text relation passed"


@pytest.mark.parametrize("keys", [(), ("name", "priority")])
def test_ordered_text_template_requires_exactly_one_sort_key(keys: tuple[str, ...]) -> None:
    with pytest.raises(ValueError, match="exactly one sort key"):
        ContractAssertion.create(
            assertion_id="ASSERT-template-ambiguous-order",
            kind="text_template",
            target_path="report.txt",
            sources=({"path": "rows.json"},),
            expected="{name}",
            keys=keys,
            order="ascending",
        )


def test_unordered_text_template_rejects_unused_sort_keys() -> None:
    with pytest.raises(ValueError, match="require an explicit order"):
        ContractAssertion.create(
            assertion_id="ASSERT-template-unused-key",
            kind="text_template",
            target_path="report.txt",
            sources=({"path": "rows.json"},),
            expected="{name}",
            keys=("name",),
        )


@pytest.mark.parametrize("algorithm", ["minimum", "maximum"])
def test_empty_numeric_aggregate_is_unresolved_not_an_exception(algorithm: str) -> None:
    source = ResultCapsule.create(
        node_id="NODE-empty-values",
        node_status="completed",
        operation="read_json",
        result={
            "success": True,
            "output": "[]",
            "metadata": {"complete": True},
        },
        artifacts=({"path": "values.json", "sha256": "a" * 64},),
        workspace_revision="revision-empty-values",
    )
    target = ResultCapsule.create(
        node_id="NODE-empty-result",
        node_status="completed",
        operation="read_json",
        result={
            "success": True,
            "output": json.dumps({"value": None}),
            "metadata": {"complete": True},
        },
        artifacts=({"path": "result.json", "sha256": "b" * 64},),
        workspace_revision="revision-empty-values",
    )
    assertion = ContractAssertion.create(
        assertion_id=f"ASSERT-empty-{algorithm}",
        kind="numeric_aggregate",
        target_path="result.json",
        target_pointer="/value",
        sources=({"path": "values.json"},),
        algorithm=algorithm,
    )

    passed, _, reason = LongHorizonController._evaluate_typed_assertion(
        assertion, (source, target)
    )

    assert passed is None
    assert reason == "aggregate source collection is empty"


def test_non_executable_source_transformation_routes_to_semantic_reviewer() -> None:
    assertion = ContractAssertion.create(
        assertion_id="ASSERT-derived-prose",
        kind="json_value_from_source",
        target_path="summary.json",
        target_pointer="/total",
        sources=(
            {"path": "a.json", "pointer": "/value"},
            {"path": "b.json", "pointer": "/value"},
        ),
        expected="add both values and round to two decimals",
    )

    passed, refs, reason = LongHorizonController._evaluate_typed_assertion(
        assertion, ()
    )

    assert passed is None
    assert refs == ()
    assert reason.startswith("semantic exception:")


def test_digest_equal_reads_target_json_pointer_instead_of_container_digest() -> None:
    payload_digest = hashlib.sha256(b"payload bytes").hexdigest()
    manifest_digest = hashlib.sha256(
        json.dumps({"sha256": payload_digest}).encode("utf-8")
    ).hexdigest()
    payload = ResultCapsule.create(
        node_id="NODE-payload",
        node_status="completed",
        operation="file_digest",
        result={"success": True},
        artifacts=({"path": "payload.bin", "sha256": payload_digest},),
        workspace_revision="revision-digest",
    )
    manifest = ResultCapsule.create(
        node_id="NODE-manifest",
        node_status="completed",
        operation="read_json",
        result={
            "success": True,
            "output": json.dumps({"sha256": payload_digest}),
            "metadata": {"complete": True},
        },
        artifacts=({"path": "manifest.json", "sha256": manifest_digest},),
        workspace_revision="revision-digest",
    )
    assertion = ContractAssertion.create(
        assertion_id="ASSERT-manifest-payload-digest",
        kind="digest_equal",
        target_path="manifest.json",
        target_pointer="/sha256",
        sources=({"path": "payload.bin"},),
        algorithm="sha256",
    )

    passed, refs, reason = LongHorizonController._evaluate_typed_assertion(
        assertion, (payload, manifest)
    )

    assert passed is True
    assert refs == (manifest.evidence_id, payload.evidence_id)
    assert reason == "digest relation passed"


def test_correction_work_invalidates_frozen_finalizer_until_replacement() -> None:
    contract = obligation("OBL-review-gated-finalizer")

    def graph_node(identifier: str, *, role: str, depends_on=()) -> ContractGraphNode:
        atom = SupervisorAtom.create(
            immutable_request=REQUEST,
            atom_id=identifier,
            role=role,
            objective=(
                "Report the accepted current workspace."
                if role == "finalizer"
                else "Complete one workspace correction."
            ),
            request_clauses=(REQUEST,),
            depends_on=depends_on,
            read_roots=(("left.txt",) if role == "finalizer" else ()),
            write_roots=(("left.txt",) if role == "work" else ()),
            allowed_operations=(("read_file",) if role == "finalizer" else ("write_file",)),
            action_budget=1,
            completion_checks=("The current result is public.",),
        )
        return ContractGraphNode.create(
            node_id=identifier,
            obligation_ids=(contract.obligation_id,),
            atom=atom,
        )

    initial = graph_node("NODE-initial", role="work")
    correction = graph_node("NODE-correction", role="work", depends_on=(initial.node_id,))
    frozen = graph_node(
        "NODE-frozen-finalizer",
        role="finalizer",
        depends_on=(initial.node_id,),
    )
    replacement = graph_node(
        "NODE-replacement-finalizer",
        role="finalizer",
        depends_on=(initial.node_id, correction.node_id),
    )
    nodes = {
        item.node_id: item
        for item in (initial, correction, frozen, replacement)
    }

    def completed(item: ContractGraphNode) -> AtomExecutionOutcome:
        return AtomExecutionOutcome(
            stage_id=f"BATCH-{item.node_id}",
            atom_id=item.node_id,
            contract_digest=execution_contract(item.atom).contract_digest,
            role=item.atom.role,
            status=AtomExecutionStatus.COMPLETED,
            candidate_output="done",
            candidate_decision_id=f"D-{item.node_id}",
            action_count=1,
            model_request_count=1,
            protocol_rejections=0,
            actions=(),
            artifacts=(),
            write_roots=item.atom.write_roots,
            error="",
            started_at="2026-08-24T00:00:00+00:00",
            ended_at="2026-08-24T00:00:01+00:00",
        )

    ready = LongHorizonController._contract_ready_nodes(
        nodes,
        {
            initial.node_id: completed(initial),
            correction.node_id: completed(correction),
        },
        allow_finalizer=True,
        finalizers_only=True,
    )

    assert [item.node_id for item in ready] == [replacement.node_id]


def test_correction_patch_cannot_depend_on_noncompleted_existing_node() -> None:
    selected_harness = ActionHarness()
    operation_catalog = tuple(
        {
            "name": str(item["name"]),
            "scope_mode": (
                "read_only"
                if not selected_harness.definition(str(item["name"])).side_effect
                else "exclusive_side_effect"
            ),
            "capability_class": selected_harness.definition(
                str(item["name"])
            ).capability_class,
            "network_access": selected_harness.definition(
                str(item["name"])
            ).network_access,
            "side_effect_class": selected_harness.definition(
                str(item["name"])
            ).side_effect_class,
        }
        for item in selected_harness.g1i_tool_definitions()
    )
    selected_obligation = obligation("OBL-correction-ready")
    projection = project_contract_capabilities(
        atom_kind="investigate",
        effect_ceiling="local_read_only",
        role="work",
        operation_catalog=operation_catalog,
        evidence_kinds=("workspace_file",),
        source_preferences=("workspace_file",),
    )

    def read_node(identifier: str, *, depends_on=()) -> ContractGraphNode:
        return ContractGraphNode.create(
            node_id=identifier,
            obligation_ids=(selected_obligation.obligation_id,),
            atom=SupervisorAtom.create(
                immutable_request=REQUEST,
                atom_id=identifier,
                role="work",
                objective="Read current workspace evidence for the correction.",
                request_clauses=(REQUEST,),
                depends_on=depends_on,
                read_roots=("left.txt",),
                allowed_operations=projection.operations,
                action_budget=1,
                completion_checks=("Current evidence is observed.",),
                atom_kind=projection.atom_kind,
                effect_ceiling=projection.effect_ceiling,
                evidence_kinds=("workspace_file",),
                freshness="current_workspace",
                source_preferences=("workspace_file",),
                operation_allowset_source=projection.source,
                minimum_actions=projection.minimum_actions,
            ),
        )

    prior = read_node("NODE-prior")
    correction = read_node("NODE-correction", depends_on=(prior.node_id,))
    patch = ContractGraphPatch.create(
        request_digest=hashlib.sha256(REQUEST.encode()).hexdigest(),
        base_revision=1,
        summary="Retry with a schedulable correction.",
        new_obligations=(),
        new_nodes=(correction,),
        existing_obligation_ids=(selected_obligation.obligation_id,),
        existing_node_ids=(prior.node_id,),
    )

    def validate(status: str) -> None:
        evidence = ResultCapsule.create(
            node_id=prior.node_id,
            node_status=status,
            operation="read_file",
            result={"success": status == "completed"},
            workspace_revision="revision-prior",
        )
        validate_contract_patch_semantics(
            patch,
            existing_obligations={
                selected_obligation.obligation_id: selected_obligation
            },
            existing_nodes={prior.node_id: prior},
            operation_catalog=operation_catalog,
            capsules=(evidence,),
            finalizer_required=False,
            workspace_manifest={"entries": []},
            existing_node_statuses={prior.node_id: status},
        )

    with pytest.raises(ValueError, match="can never become ready"):
        validate("interrupted")
    validate("completed")


def test_explicit_semantic_review_assertion_is_frozen_but_never_local() -> None:
    assertion = ContractAssertion.create(
        assertion_id="ASSERT-semantic",
        kind="semantic_review",
        target_path="summary.json",
        sources=({"path": "source.json", "pointer": "/records"},),
        expected="Apply the request's conditional business rule exactly.",
    )
    restored = ContractAssertion.from_dict(assertion.to_dict())

    passed, _, reason = LongHorizonController._evaluate_typed_assertion(restored, ())

    assert restored == assertion
    assert passed is None
    assert "semantic Reviewer" in reason


def test_correction_signature_ignores_replan_identity_and_error_text() -> None:
    evidence = ResultCapsule.create(
        node_id="NODE-evidence",
        node_status="interrupted",
        operation="read_file",
        result={"success": False},
        artifacts=(),
        workspace_revision="same",
        error_type="RWKVAtomInterrupted",
        error_message="correction NODE-1 did not finish",
    )
    review = ContractGraphReview.create(
        graph_revision=1,
        summary="Evidence is incomplete.",
        verdicts=(
            ObligationVerdict.create(
                obligation_id="OBL-stagnant",
                status="insufficient",
                evidence_refs=(),
                reason="No public content is available.",
            ),
        ),
        obligation_ids=("OBL-stagnant",),
        evidence_ids=(evidence.evidence_id,),
    )

    def replan(identifier: str, revision: int) -> ResultCapsule:
        return ResultCapsule.create(
            node_id=identifier,
            observation_id=f"EVENT-{revision}",
            node_status="completed",
            operation="replan_applied",
            result={
                "success": True,
                "fact_type": "replan_applied",
                "patch_id": identifier,
                "to_graph_revision": revision,
            },
            artifacts=(),
            workspace_revision=f"graph-{revision}",
        )

    first = LongHorizonController._contract_correction_signature(
        review, (evidence, replan("PATCH-1", 2))
    )
    second_evidence = ResultCapsule.create(
        node_id="NODE-correction-2",
        node_status="interrupted",
        operation="read_file",
        result={"success": False},
        artifacts=(),
        workspace_revision="same",
        error_type="RWKVAtomInterrupted",
        error_message="correction NODE-2 did not finish for another wording",
    )
    second = LongHorizonController._contract_correction_signature(
        review, (second_evidence, replan("PATCH-2", 3))
    )

    assert first == second
    assert first[2] == "execution_failure"


def test_multi_operation_mutation_requires_post_mutation_observation() -> None:
    atom = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="NODE-transaction-integrity",
        role="work",
        objective="Write left.txt and read it back.",
        request_clauses=(REQUEST,),
        read_roots=("left.txt",),
        write_roots=("left.txt",),
        allowed_operations=("write_file", "read_file"),
        action_budget=2,
        completion_checks=("The committed target is observed after mutation.",),
    )
    write = {
        "operation": "write_file",
        "arguments": {"path": "left.txt", "content": "left"},
        "status": "succeeded",
        "result": {"success": True},
    }
    read = {
        "operation": "read_file",
        "status": "succeeded",
        "arguments": {"path": "left.txt"},
        "result": {"success": True, "output": "left"},
    }
    contract = execution_contract(atom)
    for action_id, action in enumerate((write, read), start=1):
        action["action_id"] = f"A{action_id}"
        action["contract_digest"] = contract.contract_digest

    assert "required after" in ThreadedRWKVAtomPool._transaction_integrity_error(
        contract, (read, write)
    )
    assert (
        ThreadedRWKVAtomPool._transaction_integrity_error(
            contract,
            (write, read),
        )
        == ""
    )


def test_contract_batch_contains_only_durable_execution_identity(
    tmp_path,
) -> None:
    harness = ActionHarness(sandbox_commands=False)
    model = LongHorizonModel(harness=harness)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    store.create_run(model.create_literal_goal(REQUEST, str(workspace)), "RUN-FINALIZER")
    state = store.load("RUN-FINALIZER")
    controller = LongHorizonController(store, model=model, harness=harness)
    contract = obligation("OBL-finalizer")

    def selected_node(
        identifier: str,
        *,
        role: str = "work",
        depends_on=(),
    ) -> ContractGraphNode:
        atom = SupervisorAtom.create(
            immutable_request=REQUEST,
            atom_id=identifier,
            role=role,
            objective=(
                "Read the final artifacts and report completion."
                if role == "finalizer"
                else "Establish the requested artifact."
            ),
            request_clauses=(REQUEST,),
            depends_on=depends_on,
            read_roots=(("left.txt",) if role == "finalizer" else ()),
            write_roots=(("left.txt",) if role == "work" else ()),
            allowed_operations=(("read_file",) if role == "finalizer" else ("write_file",)),
            action_budget=1,
            completion_checks=("The exact operation result is public.",),
        )
        return ContractGraphNode.create(
            node_id=identifier,
            obligation_ids=(contract.obligation_id,),
            atom=atom,
        )

    recovered = selected_node("NODE-current-success")
    finalizer = selected_node(
        "NODE-current-finalizer",
        role="finalizer",
        depends_on=(recovered.node_id,),
    )

    stage = controller._create_contract_batch(
        state,
        (finalizer,),
        [],
        graph_revision=1,
    )

    assert stage.node_ids == (finalizer.node_id,)
    assert set(stage.to_dict()) == {
        "schema_version",
        "stage_id",
        "stage_index",
        "graph_revision",
        "node_ids",
        "request_digest",
    }
    assert ContractExecutionBatch.restore(stage.to_dict()) == stage
    legacy = ContractExecutionBatch.from_legacy_stage(
        stage_id="STAGE-legacy",
        stage_index=stage.stage_index,
        graph_revision=stage.graph_revision,
        node_ids=stage.node_ids,
        request_digest=stage.request_digest,
    )
    assert legacy.stage_id == "STAGE-legacy"
    assert legacy.node_ids == stage.node_ids


def test_existing_content_mutation_requires_latest_read_dependency() -> None:
    contract = obligation("OBL-existing")
    reader_atom = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="NODE-read-existing",
        role="work",
        objective="Observe left.txt before changing it.",
        request_clauses=(REQUEST,),
        read_roots=("left.txt",),
        allowed_operations=("read_file",),
        action_budget=1,
        completion_checks=("left.txt contents are observed.",),
    )
    reader = ContractGraphNode.create(
        node_id=reader_atom.atom_id,
        obligation_ids=(contract.obligation_id,),
        atom=reader_atom,
    )
    observed = ResultCapsule.create(
        node_id=reader.node_id,
        node_status="completed",
        operation="read_file",
        result={"success": True, "output": "old"},
        artifacts=({"path": "left.txt", "sha256": "a" * 64},),
        workspace_revision="old-revision",
    )

    blind = node("NODE-blind", contract.obligation_id)
    blind_patch = ContractGraphPatch.create(
        request_digest="request-digest",
        base_revision=1,
        summary="Blind rewrite must be rejected.",
        new_obligations=(),
        new_nodes=(blind,),
        existing_obligation_ids=(contract.obligation_id,),
        existing_node_ids=(reader.node_id,),
    )
    with pytest.raises(ValueError, match="latest content observation"):
        validate_content_mutation_dependencies(
            blind_patch,
            existing_nodes={reader.node_id: reader},
            result_capsules=(observed,),
            visible_paths=("left.txt",),
        )

    informed = node(
        "NODE-informed",
        contract.obligation_id,
        depends_on=(reader.node_id,),
    )
    informed_patch = ContractGraphPatch.create(
        request_digest="request-digest",
        base_revision=1,
        summary="Rewrite consumes the exact current content.",
        new_obligations=(),
        new_nodes=(informed,),
        existing_obligation_ids=(contract.obligation_id,),
        existing_node_ids=(reader.node_id,),
    )
    validate_content_mutation_dependencies(
        informed_patch,
        existing_nodes={reader.node_id: reader},
        result_capsules=(observed,),
        visible_paths=("left.txt",),
    )


def test_deterministic_review_kernel_vetoes_wrong_relative_paths_and_counts() -> None:
    request_text = (
        "Recursively inspect docs/. Create docs/index.json with files sorted by relative "
        "path; each entry must contain path, line_count, and byte_count. Add total_files "
        "and total_bytes. Verify the index."
    )
    contract = ContractObligation.create(
        request_text,
        obligation_id="OBL-index",
        request_clause=request_text,
        predicate=(
            "docs/index.json uses relative path with exact line_count, byte_count, "
            "total_files, and total_bytes, then verify it."
        ),
        evidence_kinds=("json_observation", "file_observation"),
    )
    source = ResultCapsule.create(
        node_id="NODE-source",
        node_status="completed",
        operation="read_file",
        result={"success": True, "output": "# C\ncontent\n"},
        artifacts=({"path": "docs/c.md", "sha256": "a" * 64},),
        workspace_revision="source",
    )
    index = ResultCapsule.create(
        node_id="NODE-index",
        node_status="completed",
        operation="read_json",
        result={
            "success": True,
            "output": json.dumps(
                {
                    "files": [
                        {
                            "path": "docs/c.md",
                            "line_count": 1,
                            "byte_count": 12,
                        }
                    ],
                    "total_files": 1,
                    "total_bytes": 12,
                }
            ),
        },
        artifacts=({"path": "docs/index.json", "sha256": "b" * 64},),
        workspace_revision="index",
    )
    review = ContractGraphReview.create(
        graph_revision=1,
        summary="The strong Reviewer incorrectly accepted the mechanical values.",
        verdicts=(
            ObligationVerdict.create(
                obligation_id=contract.obligation_id,
                status="satisfied",
                evidence_refs=(source.evidence_id, index.evidence_id),
                reason="The index appears complete.",
            ),
        ),
        obligation_ids=(contract.obligation_id,),
        evidence_ids=(source.evidence_id, index.evidence_id),
    )
    request = ContractReviewRequest(
        run_id="RUN-MECHANICAL",
        request=request_text,
        request_digest="digest-mechanical",
        graph_revision=1,
        obligations=(contract.to_dict(),),
        nodes=(),
        result_capsules=(source, index),
        workspace_manifest={"entries": []},
    )

    revised, vetoes = LongHorizonController._apply_deterministic_review_vetoes(
        request,
        review,
    )

    assert vetoes == (contract.obligation_id,)
    assert revised.verdicts[0].status == ObligationVerdictStatus.CONTRADICTED
    assert "retains relative root prefix" in revised.verdicts[0].reason
    assert "line_count=1" in revised.verdicts[0].reason

    current = ResultCapsule.create(
        node_id="NODE-index-current",
        node_status="completed",
        operation="read_json",
        result={
            "success": True,
            "output": json.dumps(
                {
                    "files": [
                        {
                            "path": "c.md",
                            "line_count": 2,
                            "byte_count": 12,
                        }
                    ],
                    "total_files": 1,
                    "total_bytes": 12,
                }
            ),
        },
        artifacts=({"path": "docs/index.json", "sha256": "c" * 64},),
        workspace_revision="current-index",
    )
    current_request = ContractReviewRequest(
        run_id=request.run_id,
        request=request.request,
        request_digest=request.request_digest,
        graph_revision=request.graph_revision,
        obligations=request.obligations,
        nodes=(),
        result_capsules=(source, index, current),
        workspace_manifest=request.workspace_manifest,
    )
    current_review = ContractGraphReview.create(
        graph_revision=1,
        summary="The current revision has mechanically correct values.",
        verdicts=(
            ObligationVerdict.create(
                obligation_id=contract.obligation_id,
                status="satisfied",
                evidence_refs=(source.evidence_id, current.evidence_id),
                reason="The current index is exact.",
            ),
        ),
        obligation_ids=(contract.obligation_id,),
        evidence_ids=(source.evidence_id, current.evidence_id),
    )

    retained, current_vetoes = (
        LongHorizonController._apply_deterministic_review_vetoes(
            current_request,
            current_review,
        )
    )

    assert current_vetoes == ()
    assert retained.verdicts[0].status == ObligationVerdictStatus.SATISFIED


def test_patch_is_append_only_and_rejects_unknown_references_and_cycles() -> None:
    first_obligation = obligation("OBL-1")
    first_node = node("NODE-1", "OBL-1")
    first = ContractGraphPatch.create(
        request_digest="request-digest",
        base_revision=0,
        summary="Initial immutable contract graph.",
        new_obligations=(first_obligation,),
        new_nodes=(first_node,),
    )
    assert first.base_revision == 0

    with pytest.raises(ValueError, match="redefine"):
        ContractGraphPatch.create(
            request_digest="request-digest",
            base_revision=1,
            summary="Illegal replacement.",
            new_obligations=(first_obligation,),
            new_nodes=(),
            existing_obligation_ids=("OBL-1",),
            existing_node_ids=("NODE-1",),
        )
    with pytest.raises(ValueError, match="unknown obligations"):
        ContractGraphPatch.create(
            request_digest="request-digest",
            base_revision=1,
            summary="Unknown obligation.",
            new_obligations=(),
            new_nodes=(node("NODE-2", "OBL-MISSING"),),
            existing_obligation_ids=("OBL-1",),
            existing_node_ids=("NODE-1",),
        )


def test_incremental_patch_freezes_one_shot_existing_id_iterables() -> None:
    repair = node("NODE-2", "OBL-1", depends_on=("NODE-1",))
    patch = ContractGraphPatch.create(
        request_digest="request-digest",
        base_revision=1,
        summary="Append one repair node against existing graph identities.",
        new_obligations=(),
        new_nodes=(repair,),
        existing_obligation_ids=(item for item in ("OBL-1",)),
        existing_node_ids=(item for item in ("NODE-1",)),
    )

    assert patch.new_nodes == (repair,)

    cycle_left = node("NODE-2", "OBL-1", depends_on=("NODE-3",))
    cycle_right = node("NODE-3", "OBL-1", depends_on=("NODE-2",))
    with pytest.raises(ValueError, match="cycle"):
        ContractGraphPatch.create(
            request_digest="request-digest",
            base_revision=1,
            summary="Cyclic graph.",
            new_obligations=(),
            new_nodes=(cycle_left, cycle_right),
            existing_obligation_ids=("OBL-1",),
            existing_node_ids=("NODE-1",),
        )


def test_review_covers_every_obligation_and_only_registered_evidence() -> None:
    evidence = capsule()
    satisfied = ObligationVerdict.create(
        obligation_id="OBL-1",
        status="satisfied",
        evidence_refs=(evidence.evidence_id,),
        reason="The exact write result and artifact digest establish the predicate.",
    )
    review = ContractGraphReview.create(
        graph_revision=1,
        summary="All required evidence is present.",
        verdicts=(satisfied,),
        obligation_ids=("OBL-1",),
        evidence_ids=(evidence.evidence_id,),
    )
    assert review.verdicts == (satisfied,)

    with pytest.raises(ValueError, match="exactly one verdict"):
        ContractGraphReview.create(
            graph_revision=1,
            summary="Incomplete coverage.",
            verdicts=(satisfied,),
            obligation_ids=("OBL-1", "OBL-2"),
            evidence_ids=(evidence.evidence_id,),
        )

    unknown = ObligationVerdict.create(
        obligation_id="OBL-1",
        status="satisfied",
        evidence_refs=("EVID-unknown",),
        reason="Invalid evidence reference.",
    )
    with pytest.raises(ValueError, match="unknown evidence"):
        ContractGraphReview.create(
            graph_revision=1,
            summary="Invalid evidence.",
            verdicts=(unknown,),
            obligation_ids=("OBL-1",),
            evidence_ids=(evidence.evidence_id,),
        )


def test_strong_model_requests_expose_results_but_no_rwkv_process_fields() -> None:
    result = capsule()
    common = {
        "run_id": "RUN-1",
        "request": REQUEST,
        "request_digest": "request-digest",
        "graph_revision": 1,
        "obligations": (obligation("OBL-1").to_dict(),),
        "nodes": (node("NODE-1", "OBL-1").to_dict(),),
        "result_capsules": (result,),
        "workspace_manifest": {"entries": []},
    }
    plan_payload = ContractPlanRequest(
        **common,
        latest_review={
            "verdicts": [
                {"obligation_id": "OBL-1", "status": "insufficient"}
            ]
        },
        available_operations=(
            {"name": "write_file", "scope_mode": "path_mutation"},
        ),
        node_statuses={"NODE-1": "completed"},
    ).to_dict()
    review_payload = ContractReviewRequest(**common).to_dict()

    assert "nodes" not in review_payload
    assert "atom" not in plan_payload["nodes"][0]
    assert set(plan_payload["nodes"][0]) == {
        "node_id",
        "status",
        "obligation_ids",
        "role",
        "depends_on",
        "read_roots",
        "write_roots",
        "atom_kind",
        "effect_ceiling",
        "operation_allowset_source",
    }
    assert plan_payload["nodes"][0]["status"] == "completed"
    assert "available_operations" not in plan_payload
    assert "available_capabilities" in plan_payload

    forbidden = {
        "prompt",
        "transcript",
        "candidate_output",
        "candidate_decision_id",
        "recent_actions",
        "completed_atoms",
        "model_request_count",
        "protocol_rejections",
        "started_at",
        "ended_at",
    }
    for payload in (plan_payload, review_payload):
        encoded = json.dumps(payload, ensure_ascii=False)
        assert payload["result_capsules"][0]["result"]["success"] is True
        assert not any(f'"{name}"' in encoded for name in forbidden)


def test_contract_plan_request_rejects_invalid_node_status_projection() -> None:
    common = {
        "run_id": "RUN-STATUS-PROJECTION",
        "request": REQUEST,
        "request_digest": "request-digest",
        "graph_revision": 1,
        "obligations": (obligation("OBL-1").to_dict(),),
        "nodes": (node("NODE-1", "OBL-1").to_dict(),),
        "latest_review": {
            "verdicts": [
                {"obligation_id": "OBL-1", "status": "insufficient"}
            ]
        },
        "result_capsules": (),
        "available_operations": (
            {"name": "write_file", "scope_mode": "path_mutation"},
        ),
        "workspace_manifest": {"entries": []},
    }

    with pytest.raises(ValueError, match="unknown nodes"):
        ContractPlanRequest(
            **common,
            node_statuses={"NODE-missing": "completed"},
        ).to_dict()
    with pytest.raises(ValueError, match="statuses are invalid"):
        ContractPlanRequest(
            **common,
            node_statuses={"NODE-1": "running"},
        ).to_dict()


def test_result_capsule_identity_is_content_addressed() -> None:
    original = capsule()
    restored = ResultCapsule.from_dict(original.to_dict())
    assert restored == original

    altered = original.to_dict()
    altered["result"]["path"] = "right.txt"
    with pytest.raises(ValueError, match="evidence id"):
        ResultCapsule.from_dict(altered)


class ContractSupervisor:
    provider_name = "test-provider"
    model_name = "test-strong-planner-reviewer"

    def __init__(self) -> None:
        self.plan_requests: list[ContractPlanRequest] = []
        self.review_requests: list[ContractReviewRequest] = []

    def plan_contract_graph(
        self,
        request: ContractPlanRequest,
    ) -> ContractGraphPatch:
        self.plan_requests.append(request)
        assert request.graph_revision == 0
        contract = ContractObligation.create(
            request.request,
            obligation_id="OBL-files",
            request_clause=request.request,
            predicate="Both requested files exist with their exact requested content.",
            evidence_kinds=("operation_result", "file"),
            assertions=(
                ContractAssertion.create(
                    assertion_id="ASSERT-left-exists",
                    kind="artifact_exists",
                    target_path="left.txt",
                ),
                ContractAssertion.create(
                    assertion_id="ASSERT-right-exists",
                    kind="artifact_exists",
                    target_path="right.txt",
                ),
                # Deliberately unresolved so this legacy integration test still
                # exercises the exception-only strong Reviewer path.
                ContractAssertion.create(
                    assertion_id="ASSERT-exception-review",
                    kind="json_value_equals",
                    target_path="left.txt",
                    target_pointer="/content",
                    expected='"left"',
                ),
            ),
        )

        def graph_node(
            identifier: str,
            *,
            role: str,
            kind: str,
            effect_ceiling: str,
            write_roots=(),
            read_roots=(),
            depends_on=(),
        ) -> ContractGraphNode:
            projection = project_contract_capabilities(
                atom_kind=kind,
                effect_ceiling=effect_ceiling,
                role=role,
                operation_catalog=request.available_operations,
                write_roots=write_roots,
            )
            atom = SupervisorAtom.create(
                immutable_request=request.request,
                atom_id=identifier,
                role=role,
                objective=(
                    "Read both requested files and report exact completion."
                    if role == "finalizer"
                    else f"Create the requested artifact for {identifier}."
                ),
                request_clauses=(request.request,),
                depends_on=depends_on,
                read_roots=read_roots,
                write_roots=write_roots,
                exclusive=projection.exclusive,
                allowed_operations=projection.operations,
                action_budget=1,
                completion_checks=(f"{identifier} has an exact operation result.",),
                atom_kind=kind,
                effect_ceiling=effect_ceiling,
                evidence_kinds=("exact_operation_result",),
                freshness="current_workspace",
                source_preferences=("workspace",),
                operation_allowset_source=projection.source,
                minimum_actions=projection.minimum_actions,
            )
            return ContractGraphNode.create(
                node_id=identifier,
                obligation_ids=(contract.obligation_id,),
                atom=atom,
            )

        left = graph_node(
            "NODE-left",
            role="work",
            kind="mutate",
            effect_ceiling="workspace_mutation",
            write_roots=("left.txt",),
        )
        right = graph_node(
            "NODE-right",
            role="work",
            kind="mutate",
            effect_ceiling="workspace_mutation",
            write_roots=("right.txt",),
        )
        verify_left = graph_node(
            "NODE-verify-left",
            role="work",
            kind="verify",
            effect_ceiling="local_read_only",
            read_roots=("left.txt",),
            depends_on=(left.node_id,),
        )
        verify_right = graph_node(
            "NODE-verify-right",
            role="work",
            kind="verify",
            effect_ceiling="local_read_only",
            read_roots=("right.txt",),
            depends_on=(right.node_id,),
        )
        finalizer = graph_node(
            "NODE-final",
            role="finalizer",
            kind="synthesize",
            effect_ceiling="local_read_only",
            read_roots=("left.txt", "right.txt"),
            depends_on=(
                left.node_id,
                right.node_id,
                verify_left.node_id,
                verify_right.node_id,
            ),
        )
        return ContractGraphPatch.create(
            request_digest=request.request_digest,
            base_revision=request.graph_revision,
            summary="One immutable obligation, two parallel workers, one frozen finalizer.",
            new_obligations=(contract,),
            new_nodes=(left, right, verify_left, verify_right, finalizer),
        )

    def review_contract_graph(
        self,
        request: ContractReviewRequest,
    ) -> ContractGraphReview:
        self.review_requests.append(request)
        assert len(request.result_capsules) >= 2
        assert all(item.node_status == "completed" for item in request.result_capsules)
        verdict = ObligationVerdict.create(
            obligation_id="OBL-files",
            status="satisfied",
            evidence_refs=tuple(
                item.evidence_id for item in request.result_capsules
            ),
            reason="Both exact RWKV operation results report success.",
        )
        return ContractGraphReview.create(
            graph_revision=request.graph_revision,
            summary="Every required obligation has exact result evidence.",
            verdicts=(verdict,),
            obligation_ids=("OBL-files",),
            evidence_ids=tuple(
                item.evidence_id for item in request.result_capsules
            ),
        )


class ContractPool:
    def __init__(self) -> None:
        self.batches: list[tuple[str, ...]] = []

    def run_stage(
        self,
        parent_goal,
        stage,
        atoms,
        *,
        max_workers,
        max_transitions,
        completed_outcomes,
    ):
        del max_transitions, completed_outcomes
        self.batches.append(tuple(atom.atom_id for atom in atoms))
        assert max_workers == len(atoms)
        returned = []
        for atom in atoms:
            finalizer = atom.role == AtomRole.FINALIZER
            returned.append(
                AtomExecutionOutcome(
                    stage_id=stage.stage_id,
                    atom_id=atom.atom_id,
                    contract_digest=AtomExecutionContract.create(
                        immutable_request=parent_goal.request,
                        atom=atom,
                    ).contract_digest,
                    role=atom.role,
                    status=AtomExecutionStatus.COMPLETED,
                    candidate_output=(
                        "Created and verified both requested files."
                        if finalizer
                        else "Worker process summary is never sent to the reviewer."
                    ),
                    candidate_decision_id=f"D-{atom.atom_id}",
                    action_count=1,
                    model_request_count=7,
                    protocol_rejections=3,
                    actions=(
                        {
                            "action_id": f"ACT-{atom.atom_id}",
                            "sequence": 1,
                            "operation": atom.allowed_operations[0],
                            "arguments": {"private_worker_parameter": "not-forwarded"},
                            "status": "succeeded",
                            "result": {
                                "success": True,
                                "output": f"exact result for {atom.atom_id}",
                            },
                            "artifact_refs": [],
                            "workspace_changed": bool(atom.write_roots),
                        },
                    ),
                    artifacts=tuple(
                        {
                            "action_id": f"ACT-{atom.atom_id}",
                            "path": path,
                            "sha256": hashlib.sha256(path.encode("utf-8")).hexdigest(),
                            "size_bytes": len(path),
                            "media_type": "text/plain",
                        }
                        for path in atom.write_roots
                    ),
                    write_roots=atom.write_roots,
                    error="",
                    started_at="2026-08-22T00:00:00+00:00",
                    ended_at="2026-08-22T00:00:01+00:00",
                )
            )
        return tuple(returned)


class TypedContractSupervisor(ContractSupervisor):
    def plan_contract_graph(self, request: ContractPlanRequest) -> ContractGraphPatch:
        patch = super().plan_contract_graph(request)
        typed = ContractObligation.create(
            request.request,
            obligation_id="OBL-files",
            request_clause=request.request,
            predicate="Both requested files exist with their exact requested content.",
            evidence_kinds=("operation_result",),
            assertions=(
                ContractAssertion.create(
                    assertion_id="ASSERT-left-exists",
                    kind="artifact_exists",
                    target_path="left.txt",
                ),
                ContractAssertion.create(
                    assertion_id="ASSERT-right-exists",
                    kind="artifact_exists",
                    target_path="right.txt",
                ),
            ),
        )
        return ContractGraphPatch.create(
            request_digest=request.request_digest,
            base_revision=request.graph_revision,
            summary=patch.summary,
            new_obligations=(typed,),
            new_nodes=patch.new_nodes,
        )

    def review_contract_graph(self, request: ContractReviewRequest) -> ContractGraphReview:
        raise AssertionError("fully typed evidence must bypass the GPT Reviewer")


class PresentationContractSupervisor(TypedContractSupervisor):
    def plan_contract_graph(self, request: ContractPlanRequest) -> ContractGraphPatch:
        patch = super().plan_contract_graph(request)
        presentation = ContractObligation.create(
            request.request,
            obligation_id="OBL-confirmation",
            request_clause=request.request,
            predicate="The final answer is a concise completion confirmation.",
            evidence_kinds=("final_answer",),
            assertions=(),
            phase=ObligationPhase.FINAL_PRESENTATION,
        )
        nodes = tuple(
            ContractGraphNode.create(
                node_id=node.node_id,
                obligation_ids=("OBL-files", "OBL-confirmation"),
                atom=node.atom,
            )
            if node.atom.role == AtomRole.FINALIZER
            else node
            for node in patch.new_nodes
        )
        return ContractGraphPatch.create(
            request_digest=request.request_digest,
            base_revision=request.graph_revision,
            summary="Typed execution contract plus one final-presentation constraint.",
            new_obligations=(*patch.new_obligations, presentation),
            new_nodes=nodes,
        )

    def review_contract_graph(self, request: ContractReviewRequest) -> ContractGraphReview:
        self.review_requests.append(request)
        assert [item["obligation_id"] for item in request.obligations] == [
            "OBL-confirmation"
        ]
        final_capsules = [
            item for item in request.result_capsules if item.operation == "final_answer"
        ]
        assert len(final_capsules) == 1
        final_capsule = final_capsules[0]
        assert final_capsule.result["output"] == (
            "Created and verified both requested files."
        )
        verdict = ObligationVerdict.create(
            obligation_id="OBL-confirmation",
            status="satisfied",
            evidence_refs=(final_capsule.evidence_id,),
            reason="The exact candidate is a concise completion confirmation.",
        )
        return ContractGraphReview.create(
            graph_revision=request.graph_revision,
            summary="The exact RWKV presentation satisfies the final obligation.",
            verdicts=(verdict,),
            obligation_ids=("OBL-confirmation",),
            evidence_ids=tuple(item.evidence_id for item in request.result_capsules),
        )


class RejectOncePresentationSupervisor(PresentationContractSupervisor):
    def plan_contract_graph(self, request: ContractPlanRequest) -> ContractGraphPatch:
        if request.graph_revision == 0:
            return super().plan_contract_graph(request)
        self.plan_requests.append(request)
        assert request.finalizer_required is True
        assert request.latest_review is not None
        assert request.latest_review["verdicts"][0]["status"] == "contradicted"
        assert any(
            item.operation == "final_answer" for item in request.result_capsules
        )
        obligation_ids = tuple(
            str(item["obligation_id"]) for item in request.obligations
        )
        completed_work_ids = tuple(
            str(item["node_id"])
            for item in request.nodes
            if item["atom"]["role"] == "work"
            and request.node_statuses[str(item["node_id"])] == "completed"
        )
        projection = project_contract_capabilities(
            atom_kind="synthesize",
            effect_ceiling="local_read_only",
            role="finalizer",
            operation_catalog=request.available_operations,
            write_roots=(),
        )
        atom = SupervisorAtom.create(
            immutable_request=request.request,
            atom_id="NODE-final-replacement",
            role="finalizer",
            objective="Present an evidence-consistent concise completion confirmation.",
            request_clauses=(request.request,),
            depends_on=completed_work_ids,
            read_roots=("left.txt", "right.txt"),
            write_roots=(),
            exclusive=projection.exclusive,
            allowed_operations=projection.operations,
            action_budget=1,
            completion_checks=("The final answer is concise and evidence-consistent.",),
            atom_kind="synthesize",
            effect_ceiling="local_read_only",
            evidence_kinds=("final_answer",),
            freshness="current_workspace",
            source_preferences=("workspace",),
            operation_allowset_source=projection.source,
            minimum_actions=projection.minimum_actions,
        )
        finalizer = ContractGraphNode.create(
            node_id=atom.atom_id,
            obligation_ids=obligation_ids,
            atom=atom,
        )
        return ContractGraphPatch.create(
            request_digest=request.request_digest,
            base_revision=request.graph_revision,
            summary="Replace the presentation rejected by the independent Reviewer.",
            new_obligations=(),
            new_nodes=(finalizer,),
            existing_obligation_ids=obligation_ids,
            existing_node_ids=tuple(str(item["node_id"]) for item in request.nodes),
        )

    def review_contract_graph(self, request: ContractReviewRequest) -> ContractGraphReview:
        self.review_requests.append(request)
        final_capsule = next(
            item for item in request.result_capsules if item.operation == "final_answer"
        )
        accepted = final_capsule.node_id == "NODE-final-replacement"
        verdict = ObligationVerdict.create(
            obligation_id="OBL-confirmation",
            status="satisfied" if accepted else "contradicted",
            evidence_refs=(final_capsule.evidence_id,),
            reason=(
                "The replacement is concise and evidence-consistent."
                if accepted
                else "The first candidate makes an unsupported completion claim."
            ),
        )
        return ContractGraphReview.create(
            graph_revision=request.graph_revision,
            summary="Review the exact, unmodified RWKV presentation.",
            verdicts=(verdict,),
            obligation_ids=("OBL-confirmation",),
            evidence_ids=tuple(item.evidence_id for item in request.result_capsules),
        )


class ReplacementPresentationPool(ContractPool):
    def run_stage(self, *args, **kwargs):
        outcomes = super().run_stage(*args, **kwargs)
        return tuple(
            replace(
                item,
                candidate_output=(
                    "Created and verified both requested files."
                    if item.atom_id == "NODE-final-replacement"
                    else "Unsupported completion claim."
                ),
            )
            if item.role == AtomRole.FINALIZER
            else item
            for item in outcomes
        )


class ExplodingContractPool:
    def run_stage(self, *args, **kwargs):
        del args, kwargs
        raise ValueError("synthetic committed-graph runtime failure")


def test_contract_controller_uses_two_strong_calls_and_raw_rwkv_final(
    tmp_path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = ActionHarness(sandbox_commands=False)
    model = LongHorizonModel(harness=harness)
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    goal = model.create_literal_goal(REQUEST, str(workspace))
    store.create_run(goal, "RUN-CONTRACT")
    supervisor = ContractSupervisor()
    pool = ContractPool()
    controller = LongHorizonController(
        store,
        model=model,
        harness=harness,
        supervisor=supervisor,
        supervisor_policy=SupervisorPolicy(
            mode="contract_graph",
            max_parallel_atoms=4,
            max_graph_patches=4,
            max_reviewer_rounds=4,
            max_graph_atoms=16,
        ),
        atom_worker_pool=pool,
    )

    result = controller.run("RUN-CONTRACT")

    assert result.state.status == RunStatus.COMPLETED
    assert result.final_output == "Created and verified both requested files."
    assert pool.batches == [
        ("NODE-left", "NODE-right"),
        ("NODE-verify-left", "NODE-verify-right"),
        ("NODE-final",),
    ]
    assert len(supervisor.plan_requests) == 1
    assert len(supervisor.review_requests) == 1
    review_payload = supervisor.review_requests[0].to_dict()
    encoded = json.dumps(review_payload, ensure_ascii=False)
    assert "Worker process summary" not in encoded
    assert "private_worker_parameter" not in encoded
    assert "model_request_count" not in encoded
    assert "protocol_rejections" not in encoded
    assert "exact result for NODE-left" in encoded
    event_types = [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ]
    assert event_types.count("contract_graph_patch_committed") == 1
    assert event_types.count("contract_graph_review_committed") == 1
    assert event_types.count("contract_graph_batch_committed") == 3
    terminal = next(
        event
        for event in result.state.causal_records.values()
        if event.event_type == "run_completed"
    )
    assert terminal.payload["output_source"] == (
        "rwkv_contract_finalizer_exact_candidate"
    )
    assert terminal.payload["controller_rewritten"] is False
    activity = project_run_activity(result.state)
    assert len(activity["direct_actions"]) == 0
    assert len(activity["atom_actions"]) == 5
    assert activity["atom_model_requests"] == 35
    assert all(item["origin"] == "atom" for item in activity["actions"])


def test_fully_typed_contract_uses_local_review_only(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = ActionHarness(sandbox_commands=False)
    model = LongHorizonModel(harness=harness)
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    store.create_run(model.create_literal_goal(REQUEST, str(workspace)), "RUN-TYPED")
    supervisor = TypedContractSupervisor()
    controller = LongHorizonController(
        store,
        model=model,
        harness=harness,
        supervisor=supervisor,
        supervisor_policy=SupervisorPolicy(mode="contract_graph"),
        atom_worker_pool=ContractPool(),
    )

    result = controller.run("RUN-TYPED")

    assert result.state.status == RunStatus.COMPLETED
    assert supervisor.review_requests == []
    review_event = next(
        event
        for event in result.state.causal_records.values()
        if event.event_type == "contract_graph_review_committed"
    )
    assert review_event.payload["review_source"] == "local_typed_checker"
    assert review_event.payload["exception_reviewer_obligation_ids"] == []


def test_final_presentation_constraint_requires_independent_candidate_review(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = ActionHarness(sandbox_commands=False)
    model = LongHorizonModel(harness=harness)
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    store.create_run(
        model.create_literal_goal(REQUEST, str(workspace)),
        "RUN-PRESENTATION",
    )
    supervisor = PresentationContractSupervisor()
    controller = LongHorizonController(
        store,
        model=model,
        harness=harness,
        supervisor=supervisor,
        supervisor_policy=SupervisorPolicy(mode="contract_graph"),
        atom_worker_pool=ContractPool(),
    )

    result = controller.run("RUN-PRESENTATION")

    assert result.state.status == RunStatus.COMPLETED
    assert result.final_output == "Created and verified both requested files."
    assert len(supervisor.review_requests) == 1
    assert any(
        item.operation == "final_answer"
        for item in supervisor.review_requests[0].result_capsules
    )
    review_event = next(
        event
        for event in result.state.causal_records.values()
        if event.event_type == "contract_graph_review_committed"
    )
    assert review_event.payload["typed_obligation_ids"] == ["OBL-files"]
    presentation_event = next(
        event
        for event in result.state.causal_records.values()
        if event.event_type == "contract_final_presentation_review_committed"
    )
    assert presentation_event.payload["controller_rewritten"] is False
    terminal = next(
        event
        for event in result.state.causal_records.values()
        if event.event_type == "run_completed"
    )
    assert terminal.payload["final_presentation_review_id"] == (
        presentation_event.payload["review_id"]
    )


def test_rejected_final_presentation_cannot_complete_and_gets_replacement(
    tmp_path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = ActionHarness(sandbox_commands=False)
    model = LongHorizonModel(harness=harness)
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    store.create_run(
        model.create_literal_goal(REQUEST, str(workspace)),
        "RUN-PRESENTATION-REPLACEMENT",
    )
    supervisor = RejectOncePresentationSupervisor()
    pool = ReplacementPresentationPool()
    controller = LongHorizonController(
        store,
        model=model,
        harness=harness,
        supervisor=supervisor,
        supervisor_policy=SupervisorPolicy(
            mode="contract_graph",
            max_graph_patches=4,
            max_reviewer_rounds=4,
        ),
        atom_worker_pool=pool,
    )

    result = controller.run("RUN-PRESENTATION-REPLACEMENT")

    assert result.state.status == RunStatus.COMPLETED
    assert result.final_output == "Created and verified both requested files."
    assert pool.batches[-2:] == [("NODE-final",), ("NODE-final-replacement",)]
    presentation_events = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "contract_final_presentation_review_committed"
    ]
    assert len(presentation_events) == 2
    assert presentation_events[0].payload["review"]["verdicts"][0]["status"] == (
        "contradicted"
    )
    assert presentation_events[1].payload["review"]["verdicts"][0]["status"] == (
        "satisfied"
    )
    first_review_sequence = presentation_events[0].sequence
    replacement_outcome_sequence = next(
        result.state.causal_records[event_id].sequence
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type == "atom_outcome_committed"
        and result.state.causal_records[event_id].payload.get("atom_id")
        == "NODE-final-replacement"
    )
    assert not any(
        event.event_type == "run_completed"
        and first_review_sequence < event.sequence < replacement_outcome_sequence
        for event in result.state.causal_records.values()
    )
    terminal = next(
        event
        for event in result.state.causal_records.values()
        if event.event_type == "run_completed"
    )
    assert terminal.payload["accepted_candidate_atom_id"] == (
        "NODE-final-replacement"
    )


def test_contract_runtime_exception_is_persisted_as_terminal(tmp_path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = ActionHarness(sandbox_commands=False)
    model = LongHorizonModel(harness=harness)
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    store.create_run(model.create_literal_goal(REQUEST, str(workspace)), "RUN-FAIL")
    controller = LongHorizonController(
        store,
        model=model,
        harness=harness,
        supervisor=ContractSupervisor(),
        supervisor_policy=SupervisorPolicy(mode="contract_graph"),
        atom_worker_pool=ExplodingContractPool(),
    )

    result = controller.run("RUN-FAIL")

    assert result.state.status == RunStatus.INTERRUPTED
    event_types = [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ]
    assert "contract_graph_runtime_failed" in event_types
    assert event_types[-1] == "run_interrupted"
