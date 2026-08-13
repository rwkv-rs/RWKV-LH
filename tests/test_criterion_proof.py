import hashlib
import json
from pathlib import Path

import pytest

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionHarness
from rwkv_lh.memory import WorkingMemoryBuilder
from rwkv_lh.model import (
    CrossValidationDecision,
    LongHorizonModel,
    ModelInvoker,
    ModelProtocolError,
)
from rwkv_lh.proof import (
    ACTUAL_READ_OPERATORS,
    EXPECTED_READ_OPERATORS,
    CriterionProofEngine,
    READ_OPERATOR_ARGUMENTS,
)
from rwkv_lh.schema import (
    ArtifactRecord,
    Attempt,
    AttemptStatus,
    CriterionClaimStatus,
    GoalCriterion,
    GoalState,
    MemoryEntry,
    RunState,
    RunStatus,
    TaskAction,
    TaskNode,
    TaskStatus,
    ValidationSpec,
    action_fingerprint,
    utc_now,
)
from rwkv_lh.store import LongHorizonStore


def make_proof_state(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    goal = GoalState.create(
        objective="Produce the exact requested result",
        original_request="The required text is good and totals are exact.",
        constraints=["Stay in the workspace"],
        success_criteria=[GoalCriterion("GC1", "The requested result is exact")],
        workspace_root=root,
    )
    task = TaskNode(
        "T1",
        "Prove result",
        "Prove the exact result",
        satisfies_criteria=["GC1"],
        action=TaskAction("read_file", {"path": "result.txt"}),
        attempt_ids=["T1-A1"],
    )
    attempt = Attempt(
        "T1-A1",
        "T1",
        AttemptStatus.SUCCEEDED,
        action_fingerprint(task.action),
        "proof-key",
        utc_now(),
        ended_at=utc_now(),
        tool_result={
            "action_type": "read_file",
            "success": True,
            "output": "good",
        },
    )
    state = RunState("PROOF", goal)
    state.tasks = {task.task_id: task}
    state.attempts = {attempt.attempt_id: attempt}
    return state, task, attempt


def valid_text_claim():
    return {
        "criterion_id": "GC1",
        "subject_task_id": "T1",
        "producer_task_id": "T1",
        "comparison": "exact_equals",
        "actual": {
            "op": "ref",
            "source": "workspace",
            "path": "result.txt",
            "selector": {"kind": "text"},
        },
        "expected": {
            "op": "literal",
            "goal_quote": "good",
            "value": "good",
        },
    }


def valid_text_assertion():
    return {
        "criterion_id": "GC1",
        "subject_task_id": "T1",
        "producer_task_id": "T1",
        "comparison": "exact_equals",
        "actual": {
            "source": "workspace",
            "path": "result.txt",
            "selector": {"kind": "text"},
            "transforms": [],
        },
        "expected": {
            "source": "goal_literal",
            "goal_quote": "good",
            "value": "good",
            "transforms": [],
        },
    }


def test_exact_workspace_claim_is_verified_with_distinct_provenance(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    (tmp_path / "result.txt").write_text("good", encoding="utf-8")

    claim = CriterionProofEngine().evaluate_claim(
        state,
        task,
        attempt,
        valid_text_claim(),
        claim_id="CC-1",
        rwkv_reason="semantic pass",
    )

    assert claim.status == CriterionClaimStatus.VERIFIED
    assert claim.passed is True
    assert [ref.source_type for ref in claim.proof_refs] == [
        "workspace",
        "goal_literal",
    ]
    assert len({ref.evidence_ref_id for ref in claim.proof_refs}) == 2


def test_expected_side_cannot_read_mutable_workspace_or_action_result(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    (tmp_path / "result.txt").write_text("good", encoding="utf-8")
    engine = CriterionProofEngine()
    for source in ["workspace", "action_result"]:
        raw = valid_text_claim()
        raw["expected"] = {
            "op": "ref",
            "source": source,
            "path": "result.txt",
            "selector": {"kind": "text" if source == "workspace" else "output_text"},
        }
        claim = engine.evaluate_claim(
            state,
            task,
            attempt,
            raw,
            claim_id=f"CC-{source}",
            rwkv_reason="semantic pass",
        )
        assert claim.status == CriterionClaimStatus.REJECTED
        assert "expected proof cannot reference" in claim.reason


def test_unknown_expression_or_selector_fields_fail_closed(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    (tmp_path / "result.txt").write_text("good", encoding="utf-8")
    for location in ["expression", "selector"]:
        raw = valid_text_claim()
        if location == "expression":
            raw["actual"]["invented_answer"] = "good"
        else:
            raw["actual"]["selector"]["fallback"] = "accept"
        claim = CriterionProofEngine().evaluate_claim(
            state,
            task,
            attempt,
            raw,
            claim_id=f"CC-{location}",
            rwkv_reason="semantic pass",
        )
        assert claim.status == CriterionClaimStatus.REJECTED
        assert "unsupported fields" in claim.reason


def test_same_path_cannot_be_presented_as_independent_dependency_evidence(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    path = tmp_path / "result.txt"
    path.write_text("good", encoding="utf-8")
    dependency = TaskNode(
        "T0",
        "Producer",
        "Produce result",
        status=TaskStatus.COMPLETED,
    )
    task.dependencies = [dependency.task_id]
    state.tasks[dependency.task_id] = dependency
    state.artifacts["A0"] = ArtifactRecord(
        "A0",
        "T0",
        "result.txt",
        hashlib.sha256(path.read_bytes()).hexdigest(),
        "text/plain",
    )
    raw = valid_text_claim()
    raw["expected"] = {
        "op": "ref",
        "source": "dependency_artifact",
        "task_id": "T0",
        "artifact_id": "A0",
        "selector": {"kind": "text"},
    }

    claim = CriterionProofEngine().evaluate_claim(
        state,
        task,
        attempt,
        raw,
        claim_id="CC-overlap",
        rwkv_reason="semantic pass",
    )

    assert claim.status == CriterionClaimStatus.REJECTED
    assert "same evidence source" in claim.reason


def action_output_vs_dependency_claim(task_id: str, artifact_id: str):
    return {
        "criterion_id": "GC1",
        "subject_task_id": "T1",
        "producer_task_id": "T1",
        "comparison": "exact_equals",
        "actual": {
            "op": "ref",
            "source": "action_result",
            "selector": {"kind": "output_text"},
        },
        "expected": {
            "op": "ref",
            "source": "dependency_artifact",
            "task_id": task_id,
            "artifact_id": artifact_id,
            "selector": {"kind": "text"},
        },
    }


@pytest.mark.parametrize(
    ("action_type", "arguments"),
    [
        ("write_file", {"path": "result.txt", "content": "good"}),
        ("write_json", {"path": "result.txt", "value": "good"}),
        ("append_file", {"path": "result.txt", "content": "good"}),
        ("copy_file", {"source": "source.txt", "destination": "result.txt"}),
    ],
)
def test_action_output_cannot_use_model_written_same_target_as_expected(
    tmp_path, action_type, arguments
):
    state, task, attempt = make_proof_state(tmp_path)
    path = tmp_path / "result.txt"
    path.write_text("good", encoding="utf-8")
    dependency = TaskNode(
        "T0",
        "Write target",
        "Model-selected producer writes the target",
        status=TaskStatus.COMPLETED,
        action=TaskAction(action_type, arguments),
    )
    task.dependencies = [dependency.task_id]
    state.tasks[dependency.task_id] = dependency
    state.artifacts["A0"] = ArtifactRecord(
        "A0",
        "T0",
        "result.txt",
        hashlib.sha256(path.read_bytes()).hexdigest(),
        "text/plain",
    )

    claim = CriterionProofEngine().evaluate_claim(
        state,
        task,
        attempt,
        action_output_vs_dependency_claim("T0", "A0"),
        claim_id="CC-model-write-lineage",
        rwkv_reason="semantic pass",
    )

    assert claim.status == CriterionClaimStatus.REJECTED
    assert "model-written workspace target lineage" in claim.reason


def test_action_output_cannot_use_same_target_write_memory_as_expected(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    (tmp_path / "result.txt").write_text("good", encoding="utf-8")
    dependency = TaskNode(
        "T0",
        "Write target",
        "Model-selected producer writes the target",
        status=TaskStatus.COMPLETED,
        action=TaskAction("write_file", {"path": "result.txt", "content": "good"}),
    )
    task.dependencies = [dependency.task_id]
    state.tasks[dependency.task_id] = dependency
    state.memory_index["M0"] = MemoryEntry(
        "M0", "action_result", "T0", "write result", "good"
    )
    raw = action_output_vs_dependency_claim("T0", "A0")
    raw["expected"] = {
        "op": "ref",
        "source": "dependency_memory",
        "task_id": "T0",
        "memory_id": "M0",
        "selector": {"kind": "text"},
    }

    claim = CriterionProofEngine().evaluate_claim(
        state,
        task,
        attempt,
        raw,
        claim_id="CC-model-write-memory-lineage",
        rwkv_reason="semantic pass",
    )

    assert claim.status == CriterionClaimStatus.REJECTED
    assert "model-written workspace target lineage" in claim.reason


def test_action_output_can_use_read_only_same_target_snapshot_as_expected(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    path = tmp_path / "result.txt"
    path.write_text("good", encoding="utf-8")
    dependency = TaskNode(
        "T0",
        "Read target",
        "Read-only snapshot of the target",
        status=TaskStatus.COMPLETED,
        action=TaskAction("read_file", {"path": "result.txt"}),
    )
    task.dependencies = [dependency.task_id]
    state.tasks[dependency.task_id] = dependency
    state.artifacts["A0"] = ArtifactRecord(
        "A0",
        "T0",
        "result.txt",
        hashlib.sha256(path.read_bytes()).hexdigest(),
        "text/plain",
    )

    claim = CriterionProofEngine().evaluate_claim(
        state,
        task,
        attempt,
        action_output_vs_dependency_claim("T0", "A0"),
        claim_id="CC-read-snapshot",
        rwkv_reason="semantic pass",
    )

    assert claim.status == CriterionClaimStatus.VERIFIED


@pytest.mark.parametrize("source_kind", ["artifact", "memory"])
def test_read_snapshot_after_model_write_keeps_transitive_model_lineage(
    tmp_path, source_kind
):
    state, task, attempt = make_proof_state(tmp_path)
    path = tmp_path / "result.txt"
    path.write_text("good", encoding="utf-8")
    writer = TaskNode(
        "TW",
        "Write target",
        "Model-selected producer writes the target",
        status=TaskStatus.COMPLETED,
        action=TaskAction("write_file", {"path": "result.txt", "content": "good"}),
        attempt_ids=["TW-A1"],
    )
    reader = TaskNode(
        "T0",
        "Read target",
        "Read-only snapshot after the write",
        status=TaskStatus.COMPLETED,
        action=TaskAction("read_file", {"path": "result.txt"}),
        attempt_ids=["T0-A1"],
    )
    writer_attempt = Attempt(
        "TW-A1",
        "TW",
        AttemptStatus.SUCCEEDED,
        action_fingerprint(writer.action),
        "writer-key",
        "2026-08-13T00:00:00+00:00",
        ended_at="2026-08-13T00:00:01+00:00",
    )
    reader_attempt = Attempt(
        "T0-A1",
        "T0",
        AttemptStatus.SUCCEEDED,
        action_fingerprint(reader.action),
        "reader-key",
        "2026-08-13T00:00:02+00:00",
        ended_at="2026-08-13T00:00:03+00:00",
        artifact_refs=["A0"],
    )
    task.dependencies = [reader.task_id]
    state.tasks.update({writer.task_id: writer, reader.task_id: reader})
    state.attempts.update(
        {
            writer_attempt.attempt_id: writer_attempt,
            reader_attempt.attempt_id: reader_attempt,
        }
    )
    raw = action_output_vs_dependency_claim("T0", "A0")
    if source_kind == "artifact":
        state.artifacts["A0"] = ArtifactRecord(
            "A0",
            "T0",
            "result.txt",
            hashlib.sha256(path.read_bytes()).hexdigest(),
            "text/plain",
        )
    else:
        state.memory_index["M-T0-A1"] = MemoryEntry(
            "M-T0-A1", "action_result", "T0", "good", "good"
        )
        raw["expected"] = {
            "op": "ref",
            "source": "dependency_memory",
            "task_id": "T0",
            "memory_id": "M-T0-A1",
            "selector": {"kind": "text"},
        }

    claim = CriterionProofEngine().evaluate_claim(
        state,
        task,
        attempt,
        raw,
        claim_id=f"CC-transitive-{source_kind}",
        rwkv_reason="semantic pass",
    )

    assert claim.status == CriterionClaimStatus.REJECTED
    assert "model-written workspace target lineage" in claim.reason


def test_read_snapshot_before_later_model_write_remains_eligible(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    path = tmp_path / "result.txt"
    path.write_text("good", encoding="utf-8")
    reader = TaskNode(
        "T0",
        "Read initial target",
        "Read-only snapshot before a later write",
        status=TaskStatus.COMPLETED,
        action=TaskAction("read_file", {"path": "result.txt"}),
        attempt_ids=["T0-A1"],
    )
    later_writer = TaskNode(
        "TW",
        "Later write",
        "Mutation occurs after the snapshot",
        status=TaskStatus.COMPLETED,
        action=TaskAction("write_file", {"path": "result.txt", "content": "good"}),
        attempt_ids=["TW-A1"],
    )
    state.tasks.update({reader.task_id: reader, later_writer.task_id: later_writer})
    state.attempts.update(
        {
            "T0-A1": Attempt(
                "T0-A1",
                "T0",
                AttemptStatus.SUCCEEDED,
                action_fingerprint(reader.action),
                "reader-key",
                "2026-08-13T00:00:00+00:00",
                ended_at="2026-08-13T00:00:01+00:00",
                artifact_refs=["A0"],
            ),
            "TW-A1": Attempt(
                "TW-A1",
                "TW",
                AttemptStatus.SUCCEEDED,
                action_fingerprint(later_writer.action),
                "writer-key",
                "2026-08-13T00:00:02+00:00",
                ended_at="2026-08-13T00:00:03+00:00",
            ),
        }
    )
    task.dependencies = [reader.task_id]
    state.artifacts["A0"] = ArtifactRecord(
        "A0",
        "T0",
        "result.txt",
        hashlib.sha256(path.read_bytes()).hexdigest(),
        "text/plain",
    )

    claim = CriterionProofEngine().evaluate_claim(
        state,
        task,
        attempt,
        action_output_vs_dependency_claim("T0", "A0"),
        claim_id="CC-snapshot-before-write",
        rwkv_reason="semantic pass",
    )

    assert claim.status == CriterionClaimStatus.VERIFIED


def test_read_snapshot_without_auditable_attempt_does_not_infer_lineage(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    path = tmp_path / "result.txt"
    path.write_text("good", encoding="utf-8")
    writer = TaskNode(
        "TW",
        "Write target",
        "Writer lacks a completed attempt",
        status=TaskStatus.COMPLETED,
        action=TaskAction("write_file", {"path": "result.txt", "content": "good"}),
    )
    reader = TaskNode(
        "T0",
        "Read target",
        "Read snapshot has no auditable attempt",
        status=TaskStatus.COMPLETED,
        action=TaskAction("read_file", {"path": "result.txt"}),
    )
    task.dependencies = [reader.task_id]
    state.tasks.update({writer.task_id: writer, reader.task_id: reader})
    state.artifacts["A0"] = ArtifactRecord(
        "A0",
        "T0",
        "result.txt",
        hashlib.sha256(path.read_bytes()).hexdigest(),
        "text/plain",
    )

    claim = CriterionProofEngine().evaluate_claim(
        state,
        task,
        attempt,
        action_output_vs_dependency_claim("T0", "A0"),
        claim_id="CC-no-inferred-order",
        rwkv_reason="semantic pass",
    )

    assert claim.status == CriterionClaimStatus.VERIFIED


@pytest.mark.parametrize("unsafe_kind", ["symlink", "parent_traversal"])
def test_dependency_snapshot_path_normalization_fails_closed(tmp_path, unsafe_kind):
    state, task, attempt = make_proof_state(tmp_path)
    (tmp_path / "result.txt").write_text("good", encoding="utf-8")
    outside = tmp_path.parent / f"{tmp_path.name}-outside.txt"
    outside.write_text("good", encoding="utf-8")
    if unsafe_kind == "symlink":
        (tmp_path / "unsafe.txt").symlink_to(outside)
        unsafe_path = "unsafe.txt"
    else:
        unsafe_path = f"../{outside.name}"
    dependency = TaskNode(
        "T0",
        "Unsafe snapshot",
        "Dependency path cannot be trusted",
        status=TaskStatus.COMPLETED,
        action=TaskAction("read_file", {"path": unsafe_path}),
    )
    task.dependencies = [dependency.task_id]
    state.tasks[dependency.task_id] = dependency
    state.artifacts["A0"] = ArtifactRecord(
        "A0",
        "T0",
        unsafe_path,
        hashlib.sha256(outside.read_bytes()).hexdigest(),
        "text/plain",
    )

    claim = CriterionProofEngine().evaluate_claim(
        state,
        task,
        attempt,
        action_output_vs_dependency_claim("T0", "A0"),
        claim_id=f"CC-unsafe-{unsafe_kind}",
        rwkv_reason="semantic pass",
    )

    assert claim.status == CriterionClaimStatus.REJECTED
    assert claim.passed is False


def test_action_output_can_use_model_written_different_target_as_expected(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    (tmp_path / "result.txt").write_text("good", encoding="utf-8")
    expected_path = tmp_path / "expected.txt"
    expected_path.write_text("good", encoding="utf-8")
    dependency = TaskNode(
        "T0",
        "Write independent target",
        "Model-selected producer writes a different target",
        status=TaskStatus.COMPLETED,
        action=TaskAction(
            "write_file", {"path": "expected.txt", "content": "good"}
        ),
    )
    task.dependencies = [dependency.task_id]
    state.tasks[dependency.task_id] = dependency
    state.artifacts["A0"] = ArtifactRecord(
        "A0",
        "T0",
        "expected.txt",
        hashlib.sha256(expected_path.read_bytes()).hexdigest(),
        "text/plain",
    )

    claim = CriterionProofEngine().evaluate_claim(
        state,
        task,
        attempt,
        action_output_vs_dependency_claim("T0", "A0"),
        claim_id="CC-different-target",
        rwkv_reason="semantic pass",
    )

    assert claim.status == CriterionClaimStatus.VERIFIED


def test_changed_dependency_artifact_hash_is_rejected(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    (tmp_path / "result.txt").write_text("good", encoding="utf-8")
    expected_path = tmp_path / "expected.txt"
    expected_path.write_text("old", encoding="utf-8")
    dependency = TaskNode("T0", "Producer", "Produce expected", status=TaskStatus.COMPLETED)
    task.dependencies = [dependency.task_id]
    state.tasks[dependency.task_id] = dependency
    state.artifacts["A0"] = ArtifactRecord(
        "A0",
        "T0",
        "expected.txt",
        hashlib.sha256(expected_path.read_bytes()).hexdigest(),
        "text/plain",
    )
    expected_path.write_text("good", encoding="utf-8")
    raw = valid_text_claim()
    raw["expected"] = {
        "op": "ref",
        "source": "dependency_artifact",
        "task_id": "T0",
        "artifact_id": "A0",
        "selector": {"kind": "text"},
    }

    claim = CriterionProofEngine().evaluate_claim(
        state,
        task,
        attempt,
        raw,
        claim_id="CC-changed",
        rwkv_reason="semantic pass",
    )

    assert claim.status == CriterionClaimStatus.REJECTED
    assert "artifact hash changed" in claim.reason


def test_group_sum_executes_only_the_rwkv_proposed_transform(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    (tmp_path / "records.json").write_text(
        '[{"group":"a","value":1},{"group":"a","value":2},{"group":"b","value":4}]',
        encoding="utf-8",
    )
    raw = valid_text_claim()
    raw["actual"] = {
        "op": "group_sum",
        "group_pointer": "/group",
        "value_pointer": "/value",
        "arg": {
            "op": "ref",
            "source": "workspace",
            "path": "records.json",
            "selector": {"kind": "json"},
        },
    }
    raw["expected"] = {
        "op": "literal",
        "goal_quote": "totals are exact",
        "value": {"a": 3, "b": 4},
    }

    claim = CriterionProofEngine().evaluate_claim(
        state,
        task,
        attempt,
        raw,
        claim_id="CC-group",
        rwkv_reason="semantic pass",
    )

    assert claim.status == CriterionClaimStatus.VERIFIED


def test_missing_json_pointer_and_depth_overflow_fail_closed(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    (tmp_path / "value.json").write_text('{"present": 1}', encoding="utf-8")
    raw = valid_text_claim()
    raw["actual"] = {
        "op": "ref",
        "source": "workspace",
        "path": "value.json",
        "selector": {"kind": "json_pointer", "pointer": "/missing"},
    }
    missing = CriterionProofEngine().evaluate_claim(
        state,
        task,
        attempt,
        raw,
        claim_id="CC-missing",
        rwkv_reason="semantic pass",
    )
    assert missing.status == CriterionClaimStatus.REJECTED
    assert "json_pointer key is missing" in missing.reason

    raw = valid_text_claim()
    expression = raw["actual"]
    for _ in range(4):
        expression = {"op": "sha256", "arg": expression}
    raw["actual"] = expression
    deep = CriterionProofEngine(max_depth=2).evaluate_claim(
        state,
        task,
        attempt,
        raw,
        claim_id="CC-deep",
        rwkv_reason="semantic pass",
    )
    assert deep.status == CriterionClaimStatus.REJECTED
    assert "depth limit" in deep.reason


def test_linear_assertion_normalizes_without_adding_semantic_fields(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    (tmp_path / "result.txt").write_text("good", encoding="utf-8")
    raw_assertion = valid_text_assertion()

    claim = CriterionProofEngine().evaluate_linear_assertion(
        state,
        task,
        attempt,
        raw_assertion,
        claim_id="CC-linear",
        rwkv_reason="semantic pass",
    )

    assert claim.status == CriterionClaimStatus.VERIFIED
    assert claim.raw_claim == raw_assertion
    assert claim.claim_protocol == "linear_typed_assertion.v1"
    assert [item["operation"] for item in claim.normalization_trace] == [
        "source_to_ref",
        "source_to_literal",
    ]
    assert claim.actual.op == "ref"
    assert claim.expected.op == "literal"


def test_linear_assertion_rejects_incompatible_or_dropped_fields(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    (tmp_path / "result.txt").write_text("good", encoding="utf-8")
    engine = CriterionProofEngine()
    cases = []
    reason = valid_text_assertion()
    reason["reason"] = "silently ignored"
    cases.append(reason)
    incompatible = valid_text_assertion()
    incompatible["actual"]["value"] = "silently ignored"
    cases.append(incompatible)
    missing = valid_text_assertion()
    missing["actual"].pop("path")
    cases.append(missing)

    for index, raw_assertion in enumerate(cases, start=1):
        claim = engine.evaluate_linear_assertion(
            state,
            task,
            attempt,
            raw_assertion,
            claim_id=f"CC-linear-reject-{index}",
            rwkv_reason="semantic pass",
        )
        assert claim.status == CriterionClaimStatus.REJECTED
        assert claim.normalization_trace == []


def test_linear_transform_order_is_preserved(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    (tmp_path / "records.json").write_text('[3,1,2]', encoding="utf-8")
    raw_assertion = valid_text_assertion()
    raw_assertion["actual"] = {
        "source": "workspace",
        "path": "records.json",
        "selector": {"kind": "json"},
        "transforms": [{"op": "sort"}, {"op": "sha256"}],
    }
    raw_assertion["expected"] = {
        "source": "goal_literal",
        "goal_quote": "totals are exact",
        "value": "a615eeaee21de5179de080de8c3052c8da901138406ba71c38c032845f7d54f4",
        "transforms": [],
    }

    normalized, trace = CriterionProofEngine.normalize_linear_assertion(
        raw_assertion
    )

    assert normalized["actual"]["op"] == "sha256"
    assert normalized["actual"]["arg"]["op"] == "sort"
    assert [item.get("op") for item in trace if item["operation"] == "wrap_transform"] == [
        "sort",
        "sha256",
    ]


def test_linear_path_exists_uses_only_rwkv_selected_path_and_type(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    (tmp_path / "created").mkdir()
    raw_assertion = valid_text_assertion()
    raw_assertion["actual"] = {
        "source": "workspace",
        "path": "created",
        "selector": {"kind": "path_exists", "path_type": "directory"},
        "transforms": [],
    }
    raw_assertion["expected"] = {
        "source": "goal_literal",
        "goal_quote": "required",
        "value": True,
        "transforms": [],
    }

    verified = CriterionProofEngine().evaluate_linear_assertion(
        state,
        task,
        attempt,
        raw_assertion,
        claim_id="CC-path-exists",
        rwkv_reason="semantic pass",
    )
    assert verified.status == CriterionClaimStatus.VERIFIED

    raw_assertion["actual"]["selector"]["path_type"] = "file"
    rejected = CriterionProofEngine().evaluate_linear_assertion(
        state,
        task,
        attempt,
        raw_assertion,
        claim_id="CC-path-type",
        rwkv_reason="semantic pass",
    )
    assert rejected.status == CriterionClaimStatus.REJECTED
    assert "exact typed proof values are unequal" in rejected.reason


def valid_operator_assertion():
    return {
        "criterion_id": "GC1",
        "subject_task_id": "T1",
        "producer_task_id": "T1",
        "comparison": "exact_equals",
        "actual": {
            "read_op": "workspace_text",
            "arguments": {"path": "result.txt"},
            "transforms": [],
        },
        "expected": {
            "read_op": "goal_literal",
            "arguments": {"goal_quote": "good", "value": "good"},
            "transforms": [],
        },
    }


def test_operator_assertion_exact_mapping_is_auditable(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    (tmp_path / "result.txt").write_text("good", encoding="utf-8")
    raw_assertion = valid_operator_assertion()

    claim = CriterionProofEngine().evaluate_operator_assertion(
        state,
        task,
        attempt,
        raw_assertion,
        claim_id="CC-operator",
        rwkv_reason="semantic pass",
    )

    assert claim.status == CriterionClaimStatus.VERIFIED
    assert claim.claim_protocol == "read_operator_assertion.v1"
    assert claim.raw_claim == raw_assertion
    assert claim.actual.to_dict() == {
        "op": "ref",
        "source": "workspace",
        "path": "result.txt",
        "selector": {"kind": "text"},
    }
    assert [item["read_op"] for item in claim.normalization_trace] == [
        "workspace_text",
        "goal_literal",
    ]


def test_operator_assertion_rejects_unknown_operator_and_extra_argument(tmp_path):
    state, task, attempt = make_proof_state(tmp_path)
    (tmp_path / "result.txt").write_text("good", encoding="utf-8")
    cases = []
    unknown = valid_operator_assertion()
    unknown["actual"]["read_op"] = "workspace_text|action_output_text"
    cases.append(unknown)
    extra = valid_operator_assertion()
    extra["actual"]["arguments"]["task_id"] = "T1"
    cases.append(extra)

    for index, raw_assertion in enumerate(cases, start=1):
        claim = CriterionProofEngine().evaluate_operator_assertion(
            state,
            task,
            attempt,
            raw_assertion,
            claim_id=f"CC-operator-reject-{index}",
            rwkv_reason="semantic pass",
        )
        assert claim.status == CriterionClaimStatus.REJECTED
        assert claim.normalization_trace == []


def operator_arguments(read_op):
    values = {
        "path": "result.txt",
        "pointer": "/value",
        "recursive": True,
        "path_type": "file",
        "task_id": "T0",
        "artifact_id": "A0",
        "memory_id": "M0",
        "goal_quote": "good",
        "value": "good",
    }
    return {name: values[name] for name in READ_OPERATOR_ARGUMENTS[read_op]}


@pytest.mark.parametrize("read_op", sorted(ACTUAL_READ_OPERATORS))
def test_every_actual_read_operator_has_one_exact_parameter_contract(read_op):
    raw = valid_operator_assertion()
    raw["actual"] = {
        "read_op": read_op,
        "arguments": operator_arguments(read_op),
        "transforms": [],
    }

    normalized, trace = CriterionProofEngine.normalize_operator_assertion(raw)

    assert normalized["actual"]["op"] == "ref"
    assert trace[0]["read_op"] == read_op


@pytest.mark.parametrize("read_op", sorted(EXPECTED_READ_OPERATORS))
def test_every_expected_read_operator_has_one_exact_parameter_contract(read_op):
    raw = valid_operator_assertion()
    raw["expected"] = {
        "read_op": read_op,
        "arguments": operator_arguments(read_op),
        "transforms": [],
    }

    normalized, trace = CriterionProofEngine.normalize_operator_assertion(raw)

    assert normalized["expected"]["op"] in {"ref", "literal"}
    assert trace[1]["read_op"] == read_op


def test_binding_contract_rejects_reordered_or_extra_fields():
    intents = [
        {
            "criterion_id": "GC1",
            "subject_task_id": "T1",
            "producer_task_id": "T1",
            "comparison": "exact_equals",
            "actual_read_op": "workspace_text",
            "expected_read_op": "goal_literal",
        }
    ]
    binding = {
        "schema_version": "long-horizon.assertion-binding.v1",
        "criterion_assertion_bindings": [
            {
                "criterion_id": "GC2",
                "actual_arguments": {"path": "result.txt"},
                "actual_transforms": [],
                "expected_arguments": {"goal_quote": "good", "value": "good"},
                "expected_transforms": [],
            }
        ],
    }
    with pytest.raises(ModelProtocolError, match="criterion/order mismatch"):
        LongHorizonModel._parse_assertion_bindings(binding, intents)

    binding["criterion_assertion_bindings"][0]["criterion_id"] = "GC1"
    binding["criterion_assertion_bindings"][0]["actual_arguments"]["task_id"] = "T1"
    with pytest.raises(ModelProtocolError, match="argument fields"):
        LongHorizonModel._parse_assertion_bindings(binding, intents)


def test_intent_coverage_rejects_missing_duplicate_and_replan_intents():
    intent = {
        "criterion_id": "GC1",
        "subject_task_id": "T1",
        "producer_task_id": "T1",
        "comparison": "exact_equals",
        "actual_read_op": "workspace_text",
        "expected_read_op": "goal_literal",
    }
    with pytest.raises(ModelProtocolError, match="exactly one intent"):
        LongHorizonModel._validate_intent_coverage(
            "pass", [intent, dict(intent)], ["GC1"]
        )
    with pytest.raises(ModelProtocolError, match="exactly one intent"):
        LongHorizonModel._validate_intent_coverage("pass", [], ["GC1"])
    with pytest.raises(ModelProtocolError, match="replan validation"):
        LongHorizonModel._validate_intent_coverage("replan", [intent], ["GC1"])


def test_rwkv_validation_v4_progressively_binds_selected_operators(tmp_path):
    state, task, _ = make_proof_state(tmp_path)
    intent_payload = {
        "schema_version": "long-horizon.validation.v4",
        "decision": "pass",
        "reason": "semantic pass",
        "criterion_assertion_intents": [
            {
                "criterion_id": "GC1",
                "subject_task_id": "T1",
                "producer_task_id": "T1",
                "comparison": "exact_equals",
                "actual_read_op": "workspace_text",
                "expected_read_op": "goal_literal",
            }
        ],
    }
    binding_payload = {
        "name": "bind_criterion_assertion",
        "arguments": {
                "actual_arguments": {"path": "result.txt"},
                "actual_transforms": [],
                "expected_arguments": {
                    "goal_quote": "good",
                    "value": "good",
                },
                "expected_transforms": [],
        },
    }

    class ValidationClient:
        def __init__(self):
            self.prompts = []
            self.outputs = [intent_payload, binding_payload]

        def text_completion(self, prompt, max_tokens=768, stop=None):
            self.prompts.append(prompt)
            payload = self.outputs.pop(0)
            return type("Response", (), {"content": json.dumps(payload)})()

    client = ValidationClient()
    model = LongHorizonModel(ModelInvoker(client=client))
    context = WorkingMemoryBuilder().build_task_validation(state, task)

    decision = model.cross_validate(
        state,
        task,
        context,
        lambda *_args: None,
        action_result={"output": "good"},
        validation_results=[],
    )

    assert decision.passed is True
    assert decision.reason == "semantic pass"
    assert decision.criterion_assertion_intents == intent_payload[
        "criterion_assertion_intents"
    ]
    assert decision.assertion_binding_protocol_valid is True
    assert decision.criterion_assertions == [
        {
            "criterion_id": "GC1",
            "subject_task_id": "T1",
            "producer_task_id": "T1",
            "comparison": "exact_equals",
            "actual": {
                "read_op": "workspace_text",
                "arguments": {"path": "result.txt"},
                "transforms": [],
            },
            "expected": {
                "read_op": "goal_literal",
                "arguments": {"goal_quote": "good", "value": "good"},
                "transforms": [],
            },
        }
    ]
    assert len(client.prompts) == 2
    assert "workspace_text" in client.prompts[0]
    assert "System: Tools:" in client.prompts[1]
    assert '"name":"bind_criterion_assertion"' in client.prompts[1]
    assert "function-call shape {name, arguments}" in client.prompts[1]
    assert "exactly those two top-level keys" in client.prompts[1]
    assert "FIXED ACTUAL OPERATOR: workspace_text" in client.prompts[1]
    assert "FIXED EXPECTED OPERATOR: goal_literal" in client.prompts[1]
    for input_only_key in (
        "actual_read_op",
        "expected_read_op",
        "actual_required_argument_keys",
        "expected_required_argument_keys",
    ):
        assert input_only_key not in client.prompts[1]
    assert "workspace_json_pointer" not in client.prompts[1]
    assert "ORIGINAL GOAL REQUEST (quote source only)" in client.prompts[0]


def test_binding_failure_does_not_change_rwkv_semantic_pass(tmp_path):
    state, task, _ = make_proof_state(tmp_path)
    intent_payload = {
        "schema_version": "long-horizon.validation.v4",
        "decision": "pass",
        "reason": "semantic pass",
        "criterion_assertion_intents": [
            {
                "criterion_id": "GC1",
                "subject_task_id": "T1",
                "producer_task_id": "T1",
                "comparison": "exact_equals",
                "actual_read_op": "workspace_text",
                "expected_read_op": "goal_literal",
            }
        ],
    }
    malformed_binding = {"name": "bind_criterion_assertion", "arguments": {}}

    class ValidationClient:
        def __init__(self):
            self.outputs = [
                intent_payload,
                malformed_binding,
                malformed_binding,
            ]

        def text_completion(self, prompt, max_tokens=768, stop=None):
            return type(
                "Response",
                (),
                {"content": json.dumps(self.outputs.pop(0))},
            )()

    model = LongHorizonModel(ModelInvoker(client=ValidationClient()))
    decision = model.cross_validate(
        state,
        task,
        WorkingMemoryBuilder().build_task_validation(state, task),
        lambda *_args: None,
        action_result={"output": "good"},
        validation_results=[],
    )

    assert decision.passed is True
    assert decision.criterion_assertions == []
    assert decision.criterion_assertion_intents == intent_payload[
        "criterion_assertion_intents"
    ]
    assert decision.assertion_binding_protocol_valid is False
    assert "fields must be exactly" in decision.assertion_binding_error


def test_g1i_binding_uses_one_fixed_tool_scope_per_claim_in_intent_order(tmp_path):
    state, task, _ = make_proof_state(tmp_path)
    state.goal = GoalState.create(
        objective=state.goal.objective,
        original_request=state.goal.original_request,
        constraints=list(state.goal.constraints),
        success_criteria=[
            *state.goal.success_criteria,
            GoalCriterion("GC2", "A second exact result"),
        ],
        workspace_root=tmp_path,
    )
    task.satisfies_criteria = ["GC1", "GC2"]
    intents = [
        {
            "criterion_id": criterion_id,
            "subject_task_id": "T1",
            "producer_task_id": "T1",
            "comparison": "exact_equals",
            "actual_read_op": "workspace_text",
            "expected_read_op": "goal_literal",
        }
        for criterion_id in task.satisfies_criteria
    ]
    intent_payload = {
        "schema_version": "long-horizon.validation.v4",
        "decision": "pass",
        "reason": "both criteria pass",
        "criterion_assertion_intents": intents,
    }

    class MultiClaimClient:
        def __init__(self):
            self.prompts = []
            self.outputs = [
                intent_payload,
                {
                    "name": "bind_criterion_assertion",
                    "arguments": {
                        "actual_arguments": {"path": "first.txt"},
                        "actual_transforms": [],
                        "expected_arguments": {"goal_quote": "good", "value": "one"},
                        "expected_transforms": [],
                    },
                },
                {
                    "name": "bind_criterion_assertion",
                    "arguments": {
                        "actual_arguments": {"path": "second.txt"},
                        "actual_transforms": [],
                        "expected_arguments": {"goal_quote": "good", "value": "two"},
                        "expected_transforms": [],
                    },
                },
            ]

        def text_completion(self, prompt, max_tokens=768, stop=None):
            self.prompts.append(prompt)
            return type(
                "Response", (), {"content": json.dumps(self.outputs.pop(0))}
            )()

    client = MultiClaimClient()
    decision = LongHorizonModel(ModelInvoker(client=client)).cross_validate(
        state,
        task,
        WorkingMemoryBuilder().build_task_validation(state, task),
        lambda *_args: None,
        action_result={"output": "good"},
        validation_results=[],
    )

    assert [item["criterion_id"] for item in decision.criterion_assertions] == [
        "GC1",
        "GC2",
    ]
    assert [
        item["actual"]["arguments"]["path"]
        for item in decision.criterion_assertions
    ] == ["first.txt", "second.txt"]
    assert len(client.prompts) == 3
    assert "CLAIM POSITION: 1 of 2" in client.prompts[1]
    assert "CLAIM POSITION: 2 of 2" in client.prompts[2]
    assert all(prompt.count('"name":"bind_criterion_assertion"') == 1 for prompt in client.prompts[1:])


def test_g1i_binding_tool_schema_contains_only_selected_operator_arguments():
    tool = LongHorizonModel._assertion_binding_tool_definition(
        {
            "criterion_id": "GC1",
            "subject_task_id": "T1",
            "producer_task_id": "T1",
            "comparison": "exact_equals",
            "actual_read_op": "action_output_text",
            "expected_read_op": "goal_literal",
        }
    )

    properties = tool["parameters"]["properties"]
    assert tool["name"] == "bind_criterion_assertion"
    assert properties["actual_arguments"]["properties"] == {}
    assert properties["expected_arguments"]["required"] == ["goal_quote", "value"]
    assert tool["parameters"]["additionalProperties"] is False


def test_semantic_replan_does_not_issue_binding_request(tmp_path):
    state, task, _ = make_proof_state(tmp_path)
    payload = {
        "schema_version": "long-horizon.validation.v4",
        "decision": "replan",
        "reason": "evidence is insufficient",
        "criterion_assertion_intents": [],
    }

    class ValidationClient:
        def __init__(self):
            self.calls = 0

        def text_completion(self, prompt, max_tokens=768, stop=None):
            self.calls += 1
            return type("Response", (), {"content": json.dumps(payload)})()

    client = ValidationClient()
    decision = LongHorizonModel(ModelInvoker(client=client)).cross_validate(
        state,
        task,
        WorkingMemoryBuilder().build_task_validation(state, task),
        lambda *_args: None,
        action_result={"output": "good"},
        validation_results=[],
    )

    assert decision.passed is False
    assert client.calls == 1


class ScriptedProofModel:
    def __init__(self, decision_factory):
        self.decision_factory = decision_factory
        self.cross_calls = 0
        self.commit_calls = 0
        self.final_calls = 0

    def cross_validate(
        self,
        state,
        task,
        context,
        persist,
        *,
        action_result=None,
        validation_results=None,
    ):
        self.cross_calls += 1
        return self.decision_factory(state, task, action_result or {})

    def commit_criterion_evidence(
        self,
        state,
        context,
        persist,
        *,
        criterion_ids,
        source_catalog,
    ):
        del context, persist
        self.commit_calls += 1
        actual_sources = source_catalog["causal_actual_sources"]
        producer = state.tasks[actual_sources[-1]["owner_task_id"]]
        decision = self.decision_factory(
            state,
            producer,
            {"output": str(producer.action.arguments.get("content") or "")},
        )
        claims = decision.criterion_assertions
        exact_coverage = (
            decision.passed
            and len(claims) == len(criterion_ids)
            and sorted(str(item.get("criterion_id") or "") for item in claims)
            == sorted(criterion_ids)
            and len({str(item.get("criterion_id") or "") for item in claims})
            == len(claims)
            and decision.assertion_binding_protocol_valid
        )
        expected_values = [
            str(
                ((item.get("expected") or {}).get("arguments") or {}).get(
                    "value"
                )
                or ""
            )
            for item in claims
        ]
        if not exact_coverage or any(value != "good" for value in expected_values):
            return {"decision": "replan", "bindings": []}
        return {
            "decision": "pass",
            "bindings": [
                {
                    "criterion_id": criterion_id,
                    "actual_ref": actual_sources[0]["ref"],
                    "expected_ref": "GOAL",
                    "reason": decision.reason,
                }
                for criterion_id in criterion_ids
            ],
        }

    def final_answer(self, state, context, persist):
        self.final_calls += 1
        return "verified final"


def controller_goal(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    return GoalState.create(
        objective="Write good",
        original_request="Write exactly good to result.txt.",
        constraints=["Stay in workspace"],
        success_criteria=[GoalCriterion("GC1", "result.txt is exactly good")],
        workspace_root=root,
    )


def scripted_claim(task, *, expected="good"):
    return {
        "criterion_id": "GC1",
        "subject_task_id": task.task_id,
        "producer_task_id": task.task_id,
        "comparison": "exact_equals",
        "actual": {
            "read_op": "workspace_text",
            "arguments": {"path": "result.txt"},
            "transforms": [],
        },
        "expected": {
            "read_op": "goal_literal",
            "arguments": {"goal_quote": "good", "value": expected},
            "transforms": [],
        },
    }


def run_single_claim_case(tmp_path, decision_factory):
    workspace = tmp_path / "workspace"
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(controller_goal(workspace), "CLAIM-RUN")
    task = TaskNode(
        "T1",
        "Write exact result",
        "Write and prove result.txt",
        satisfies_criteria=["GC1"],
        action=TaskAction("write_file", {"path": "result.txt", "content": "good"}),
        completion_criteria=[
            ValidationSpec(
                "file_content",
                {"path": "result.txt", "expected_content": "good"},
            )
        ],
    )
    state.tasks = {task.task_id: task}
    state.status = RunStatus.RUNNING
    state = store.save(state, event_type="plan_saved")
    model = ScriptedProofModel(decision_factory)
    return store, model, LongHorizonController(store, model=model).run(state.run_id)


def test_valid_rwkv_claim_creates_goal_evidence_and_completes(tmp_path):
    def decide(state, task, action_result):
        return CrossValidationDecision(True, "semantic pass", [scripted_claim(task)])

    _, model, result = run_single_claim_case(tmp_path, decide)

    assert result.state.status == RunStatus.COMPLETED
    assert model.final_calls == 1
    evidence = next(iter(result.state.criterion_evidence.values()))
    claim = result.state.criterion_claims[evidence.claim_id]
    assert evidence.owner_task_id == "T1"
    assert claim.status == CriterionClaimStatus.VERIFIED
    assert claim.claim_protocol == "rwkv_goal_provenance_commit.v1"


def test_explicit_model_cross_check_is_reused_for_criterion_assertion(tmp_path):
    workspace = tmp_path / "workspace"
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(controller_goal(workspace), "ONE-CROSS-CHECK")
    task = TaskNode(
        "T1",
        "Write exact result",
        "Write and prove result.txt",
        satisfies_criteria=["GC1"],
        action=TaskAction(
            "write_file", {"path": "result.txt", "content": "good"}
        ),
        completion_criteria=[
            ValidationSpec(
                "file_content",
                {"path": "result.txt", "expected_content": "good"},
            ),
            ValidationSpec("model_cross_check", {}, required=True),
        ],
    )
    state.tasks = {task.task_id: task}
    state.status = RunStatus.RUNNING
    state = store.save(state, event_type="plan_saved")

    def decide(current, active_task, action_result):
        return CrossValidationDecision(
            True,
            "semantic pass",
            [scripted_claim(active_task)],
        )

    model = ScriptedProofModel(decide)
    result = LongHorizonController(store, model=model).run(state.run_id)

    assert result.state.status == RunStatus.COMPLETED
    assert model.cross_calls == 1
    assert model.commit_calls == 1
    attempt = result.state.attempts["T1-A1"]
    assert [item.kind for item in attempt.validation_results] == [
        "file_content",
        "model_cross_check",
    ]
    cross_result = attempt.validation_results[-1]
    assert cross_result.evidence["criterion_assertion_evaluated"] is False
    committed = next(
        item
        for item in store.event_records(result.state.run_id)
        if item["type"] == "goal_criterion_provenance_committed"
    )
    assert committed["data"]["protocol"] == "rwkv_goal_provenance_commit.v1"


def test_unequal_or_missing_claim_does_not_fail_task_but_blocks_goal(tmp_path):
    for name, claims in [
        ("unequal", lambda task: [scripted_claim(task, expected="wrong")]),
        ("missing", lambda task: []),
    ]:
        case_root = tmp_path / name

        def decide(state, task, action_result, make_claims=claims):
            return CrossValidationDecision(True, "semantic pass", make_claims(task))

        store, model, result = run_single_claim_case(case_root, decide)
        assert result.state.tasks["T1"].status == TaskStatus.COMPLETED
        assert result.state.status == RunStatus.BLOCKED
        assert result.state.criterion_evidence == {}
        assert model.final_calls == 0
        assert store.event_records(result.state.run_id)[-1]["data"]["reason"] == (
            "required_goal_evidence_missing"
        )


def test_invalid_old_binding_shape_requests_replan_without_overriding_task_pass(tmp_path):
    intent = {
        "criterion_id": "GC1",
        "subject_task_id": "T1",
        "producer_task_id": "T1",
        "comparison": "exact_equals",
        "actual_read_op": "workspace_text",
        "expected_read_op": "goal_literal",
    }

    def decide(state, task, action_result):
        return CrossValidationDecision(
            True,
            "semantic pass",
            [],
            [intent],
            False,
            "binding contract rejected",
        )

    store, _, result = run_single_claim_case(tmp_path, decide)

    assert result.state.tasks["T1"].status == TaskStatus.COMPLETED
    assert result.state.status == RunStatus.BLOCKED
    assert result.state.criterion_evidence == {}
    replan_event = next(
        item
        for item in store.event_records(result.state.run_id)
        if item["type"] == "goal_criterion_provenance_replan_requested"
    )
    assert replan_event["data"]["protocol"] == "rwkv_goal_provenance_commit.v1"
    assert replan_event["data"]["controller_semantic_fields_generated"] is False


def test_duplicate_criterion_proposals_create_no_evidence(tmp_path):
    def decide(state, task, action_result):
        claim = scripted_claim(task)
        return CrossValidationDecision(True, "semantic pass", [claim, dict(claim)])

    _, _, result = run_single_claim_case(tmp_path, decide)

    assert result.state.status == RunStatus.BLOCKED
    assert result.state.criterion_evidence == {}
    assert result.state.criterion_claims == {}


def test_rwkv_replan_is_never_overridden_by_available_provenance(tmp_path):
    def decide(state, task, action_result):
        return CrossValidationDecision(False, "semantic replan", [scripted_claim(task)])

    _, _, result = run_single_claim_case(tmp_path, decide)

    assert result.state.tasks["T1"].status == TaskStatus.COMPLETED
    assert result.state.status == RunStatus.BLOCKED
    assert result.state.criterion_claims == {}


def test_final_revalidation_invalidates_evidence_changed_by_later_task(tmp_path):
    workspace = tmp_path / "workspace"
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(controller_goal(workspace), "STALE-PROOF")
    first = TaskNode(
        "T1",
        "Write good",
        "Create the claimed result",
        satisfies_criteria=["GC1"],
        action=TaskAction("write_file", {"path": "result.txt", "content": "good"}),
        completion_criteria=[
            ValidationSpec(
                "file_content",
                {"path": "result.txt", "expected_content": "good"},
            )
        ],
    )
    state.tasks = {"T1": first}
    state.status = RunStatus.RUNNING
    state = store.save(state, event_type="plan_saved")

    def decide(current, task, action_result):
        return CrossValidationDecision(True, "semantic pass", [scripted_claim(task)])

    model = ScriptedProofModel(decide)
    controller = LongHorizonController(store, model=model)
    result = controller.run(state.run_id)

    assert result.state.status == RunStatus.COMPLETED
    assert model.final_calls == 1
    evidence = next(iter(result.state.criterion_evidence.values()))
    claim = result.state.criterion_claims[evidence.claim_id]
    (workspace / "result.txt").write_text("bad", encoding="utf-8")

    invalidated = controller._revalidate_goal_proofs(result.state)

    assert invalidated == [claim.claim_id]
    assert evidence.status.value == "invalidated"
    assert claim.status == CriterionClaimStatus.INVALIDATED
