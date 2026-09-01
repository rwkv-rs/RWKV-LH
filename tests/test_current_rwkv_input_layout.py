from __future__ import annotations

import json
from pathlib import Path

import pytest

from rwkv_lh.atom_execution import (
    ATOM_EXECUTION_POLICY_KEY,
    AtomDependencyResult,
    AtomExecutionBinding,
    AtomExecutionContract,
    contract_integrity_error,
)
from rwkv_lh.capability_projection import CAPABILITY_PROJECTION_VERSION
from rwkv_lh.exact_tool_selector.compact_protocol_v6 import (
    SELECTOR_CURRENT_QUESTION,
    render_compact_selector_bootstrap,
    render_compact_selector_step,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NetworkSelectorInput,
    NetworkSelectorProgress,
)
from rwkv_lh.exact_tool_selector.runtime_projection import (
    build_network_selector_input,
    selector_contract_progress,
    selector_final_answer_eligible,
)
from rwkv_lh.harness import ActionHarness
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_io import render_independent_executor_tool_disclosure
from rwkv_lh.model_io import (
    ModelIOError,
    validate_independent_executor_generation_input,
)
from rwkv_lh.schema import ActionRecord, ActionStatus, RunState, TaskAction
from rwkv_lh.supervisor import SupervisorAtom


def _selector_input() -> NetworkSelectorInput:
    return NetworkSelectorInput.create(
        task_request="Inspect the project and fix the registered defect.",
        stage_objective="Read the exact failing source file before editing it.",
        stage_role="evidence",
        progress=NetworkSelectorProgress(
            completed_stage_count=0,
            action_index=0,
            succeeded_operations=(),
            failed_operations=(),
            protocol_rejection_count=0,
        ),
    )


def test_current_selector_keeps_context_first_and_each_question_at_the_tail() -> None:
    value = _selector_input()
    bootstrap = render_compact_selector_bootstrap(value)
    step = render_compact_selector_step(value)

    assert bootstrap.index("SelectorMenuV6:") < bootstrap.index(
        "SelectorTaskIdentityV6:"
    )
    assert value.task_request not in bootstrap
    step_payload = json.loads(step.removeprefix("SelectorStepV6: "))
    assert list(step_payload)[-1] == "current_question"
    assert list(step_payload["current_question"])[-1] == "question"
    assert step_payload["current_question"] == {
        "complete_requirement": value.task_request,
        "current_stage": value.stage_objective,
        "question": SELECTOR_CURRENT_QUESTION,
    }
    assert step.count(value.task_request) == 1
    assert step.count(value.stage_objective) == 1
    assert step.endswith(json.dumps(SELECTOR_CURRENT_QUESTION) + "}}")


def test_current_executor_sampling_matches_the_registered_runtime() -> None:
    assert LongHorizonModel._SAMPLING.temperature == 0.1
    assert LongHorizonModel._SAMPLING.top_p == 1.0
    assert LongHorizonModel._SAMPLING.top_k == 0


def _closed_loop_action(
    *,
    action_id: str,
    sequence: int,
    operation: str,
    arguments: dict[str, object],
    contract_digest: str,
    success: bool = True,
) -> ActionRecord:
    return ActionRecord(
        action_id=action_id,
        sequence=sequence,
        status=ActionStatus.SUCCEEDED if success else ActionStatus.FAILED,
        action_type=operation,
        arguments=dict(arguments),
        wire_arguments=dict(arguments),
        action_fingerprint=f"fingerprint-{action_id}",
        idempotency_key=f"idempotency-{action_id}",
        decision_id=f"decision-{action_id}",
        request_id=f"request-{action_id}",
        started_at="2026-08-30T00:00:00+00:00",
        ended_at="2026-08-30T00:00:01+00:00",
        result={
            "success": success,
            "outcome_type": "success" if success else "error",
            "metadata": {},
        },
        outcome_type="success" if success else "error",
        atom_execution_contract_digest=contract_digest,
    )


def test_selector_v2_closes_final_over_harness_write_root_progress(
    tmp_path: Path,
) -> None:
    requirement = "Create hello.txt containing exactly hello."
    atom = SupervisorAtom.create(
        immutable_request=requirement,
        atom_id="write-hello",
        objective=requirement,
        request_clauses=(requirement,),
        depends_on=("dep",),
        atom_kind="mutate",
        effect_ceiling="workspace_mutation",
        role="work",
        allowed_operations=("list_directory", "write_file"),
        action_budget=4,
        minimum_actions=1,
        write_roots=("hello.txt",),
        completion_checks=("hello.txt exists with the requested content.",),
        evidence_kinds=("workspace_file",),
        freshness="current_workspace",
        source_preferences=("workspace",),
        operation_allowset_source=CAPABILITY_PROJECTION_VERSION,
    )
    contract = AtomExecutionContract.create(
        immutable_request=requirement,
        atom=atom,
    )
    binding = AtomExecutionBinding(
        contract=contract,
        completed_dependencies=(
            AtomDependencyResult(
                atom_id="dep",
                contract_digest="a" * 64,
                action_count=1,
            ),
        ),
    )
    goal = LongHorizonModel.create_literal_goal(
        requirement,
        str(tmp_path),
        runtime_policy={ATOM_EXECUTION_POLICY_KEY: binding.to_dict()},
    )
    state = RunState(run_id="RUN", goal=goal)

    initial = selector_contract_progress(state)
    assert initial is not None
    assert initial["progress"]["completion_ready"] is False
    assert initial["progress"]["remaining_required_count"] == 1
    assert selector_final_answer_eligible(state) is False

    state.actions["A1"] = _closed_loop_action(
        action_id="A1",
        sequence=1,
        operation="list_directory",
        arguments={"path": "."},
        contract_digest=contract.contract_digest,
    )
    after_read = selector_contract_progress(state)
    assert after_read is not None
    assert after_read["progress"]["completion_ready"] is False
    assert after_read["progress"]["latest_action"]["advanced_contract"] is False
    assert selector_final_answer_eligible(state) is False

    state.actions["A2"] = _closed_loop_action(
        action_id="A2",
        sequence=2,
        operation="write_file",
        arguments={"path": "hello.txt", "content": "hello"},
        contract_digest=contract.contract_digest,
    )
    complete = selector_contract_progress(state)
    assert complete is not None
    assert complete["progress"]["completion_ready"] is True
    assert complete["progress"]["covered_write_root_count"] == 1
    assert complete["progress"]["remaining_required_count"] == 0
    assert complete["progress"]["latest_action"]["advanced_contract"] is True
    assert selector_final_answer_eligible(state) is True

    selector_input = build_network_selector_input(state, None)
    assert selector_input.stage_objective.startswith("CurrentDirectStageV3: ")
    compact_stage = json.loads(
        selector_input.stage_objective.removeprefix("CurrentDirectStageV3: ")
    )
    assert list(compact_stage) == [
        "schema_version",
        "action_index",
        "completion_ready",
        "latest_action",
        "atom_objective",
    ]
    assert compact_stage["atom_objective"] == atom.objective
    assert compact_stage["action_index"] == 2
    assert compact_stage["completion_ready"] is True
    assert '"content"' not in selector_input.stage_objective
    assert selector_input.task_request == requirement


def test_selector_and_transaction_share_minimum_actions_after_root_coverage(
    tmp_path: Path,
) -> None:
    requirement = "Move left.txt to right.txt and record the completed transaction."
    atom = SupervisorAtom.create(
        immutable_request=requirement,
        atom_id="move-and-record",
        objective=requirement,
        request_clauses=(requirement,),
        atom_kind="mutate",
        effect_ceiling="workspace_mutation",
        role="work",
        allowed_operations=("move_file", "write_file"),
        action_budget=2,
        minimum_actions=2,
        write_roots=("left.txt", "right.txt"),
        completion_checks=("The move and transaction record are complete.",),
        evidence_kinds=("workspace_file",),
        freshness="current_workspace",
        source_preferences=("workspace",),
        operation_allowset_source=CAPABILITY_PROJECTION_VERSION,
    )
    contract = AtomExecutionContract.create(
        immutable_request=requirement,
        atom=atom,
    )
    binding = AtomExecutionBinding(contract=contract)
    goal = LongHorizonModel.create_literal_goal(
        requirement,
        str(tmp_path),
        runtime_policy={ATOM_EXECUTION_POLICY_KEY: binding.to_dict()},
    )
    state = RunState(run_id="RUN-MOVE", goal=goal)
    state.actions["A1"] = _closed_loop_action(
        action_id="A1",
        sequence=1,
        operation="move_file",
        arguments={"source": "left.txt", "destination": "right.txt"},
        contract_digest=contract.contract_digest,
    )

    progress = selector_contract_progress(state)
    assert progress is not None
    assert progress["progress"]["covered_write_root_count"] == 2
    assert progress["progress"]["remaining_write_root_count"] == 0
    assert progress["progress"]["remaining_minimum_action_count"] == 1
    assert progress["progress"]["completion_ready"] is False
    assert selector_final_answer_eligible(state) is False
    assert "minimum_actions" in contract_integrity_error(
        contract,
        tuple(state.actions.values()),
    )


def test_current_executor_keeps_one_closed_requirement_as_the_last_payload_field() -> None:
    requirement = "Read inputs/example.txt and return its exact first line."
    rendered = render_independent_executor_tool_disclosure(
        {
            "name": "read_file",
            "description": "Read one bounded local UTF-8 file range.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
        requirement,
    )
    prefix = "\n\nUser: Executor continuation input: "
    suffix = "\n\nAssistant: ```json\n"
    payload = json.loads(rendered.removeprefix(prefix).removesuffix(suffix))

    assert list(payload)[-1] == "current_requirement"
    assert payload["current_requirement"] == requirement
    assert rendered.count(requirement) == 1
    assert rendered.endswith(suffix)

    transcript = (
        "System: stable Executor state without the literal requirement."
        + rendered
    )
    validate_independent_executor_generation_input(transcript, requirement)


def test_current_executor_rejects_a_requirement_moved_away_from_the_tail() -> None:
    requirement = "Read inputs/example.txt and return its exact first line."
    rendered = render_independent_executor_tool_disclosure(
        {
            "name": "read_file",
            "description": "Read one bounded local UTF-8 file range.",
            "parameters": {"type": "object", "properties": {}},
        },
        requirement,
    )
    invalid = rendered.replace(
        f'"current_requirement":"{requirement}"',
        f'"current_requirement":"{requirement}","trailing_instruction":"answer now"',
    )

    with pytest.raises(ModelIOError, match="final selected-contract field"):
        validate_independent_executor_generation_input(invalid, requirement)


def test_list_directory_exposes_explicit_bounded_completion_metadata(
    tmp_path: Path,
) -> None:
    (tmp_path / "input.txt").write_text("bounded\n", encoding="utf-8")
    (tmp_path / "second.txt").write_text("bounded too\n", encoding="utf-8")
    harness = ActionHarness(sandbox_commands=False)
    goal = LongHorizonModel.create_literal_goal("Inspect the workspace.", str(tmp_path))

    complete = harness.execute(
        TaskAction(
            "list_directory",
            {"path": ".", "recursive": False, "max_entries": 8},
        ),
        goal,
    )
    truncated = harness.execute(
        TaskAction(
            "list_directory",
            {"path": ".", "recursive": False, "max_entries": 1},
        ),
        goal,
    )

    assert complete.success is True
    assert complete.metadata["truncated"] is False
    assert complete.metadata["complete"] is True
    assert truncated.success is True
    assert truncated.metadata["truncated"] is True
    assert truncated.metadata["complete"] is False
