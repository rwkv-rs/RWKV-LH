from __future__ import annotations

import json
import threading
from dataclasses import dataclass, replace
from pathlib import Path

import pytest

from rwkv_lh.atom_execution import (
    ATOM_EXECUTION_POLICY_KEY,
    AtomExecutionBinding,
    AtomExecutionContract,
)
from rwkv_lh.capability_projection import CAPABILITY_PROJECTION_VERSION
from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionHarness, ScopeViolation
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import ModelSession
from rwkv_lh.parallel_atoms import (
    AtomExecutionOutcome,
    AtomExecutionStatus,
    ScopedAtomHarness,
    ThreadedRWKVAtomPool,
)
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import RunStatus, TaskAction
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.supervisor import (
    AtomRole,
    StageDisposition,
    SupervisorAtom,
    SupervisorPolicy,
    SupervisorStage,
    SupervisorStageRequest,
)


REQUEST = "Create left.txt containing left and right.txt containing right."
OPERATION_CATALOG = (
    {
        "name": "read_file",
        "description": "Read a file.",
        "scope_mode": "read_only",
    },
    {
        "name": "write_file",
        "description": "Write a file.",
        "scope_mode": "path_mutation",
    },
    {
        "name": "run_command",
        "description": "Run a command.",
        "scope_mode": "exclusive_side_effect",
    },
)


def stage_request(
    *,
    stage_index: int = 1,
    completed_atoms=(),
) -> SupervisorStageRequest:
    return SupervisorStageRequest(
        run_id="RUN",
        request=REQUEST,
        request_digest="request-digest",
        constraints=("Stay inside the workspace.",),
        stage_index=stage_index,
        max_parallel_atoms=4,
        previous_stage_id="",
        completed_atoms=tuple(completed_atoms),
        available_operations=OPERATION_CATALOG,
        workspace_manifest={"entries": []},
    )


def atom(
    atom_id: str,
    *,
    role: str = "work",
    depends_on=(),
    write_roots=(),
    exclusive: bool = False,
) -> SupervisorAtom:
    return SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id=atom_id,
        role=role,
        objective=f"Complete {atom_id}.",
        request_clauses=(REQUEST,),
        depends_on=depends_on,
        read_roots=(),
        write_roots=write_roots,
        exclusive=exclusive,
        allowed_operations=(
            ("read_file",)
            if role == "finalizer" or not write_roots
            else ("write_file",)
        ),
        action_budget=(1 if write_roots else 4),
        completion_checks=(f"{atom_id} is observably complete.",),
    )


def outcome(stage: SupervisorStage, selected: SupervisorAtom, text: str):
    execution_contract = AtomExecutionContract.create(
        immutable_request=REQUEST,
        atom=selected,
    )
    return AtomExecutionOutcome(
        stage_id=stage.stage_id,
        atom_id=selected.atom_id,
        contract_digest=execution_contract.contract_digest,
        role=selected.role,
        status=AtomExecutionStatus.COMPLETED,
        candidate_output=text,
        candidate_decision_id=f"D-{selected.atom_id}",
        action_count=1,
        model_request_count=2,
        protocol_rejections=0,
        actions=(),
        artifacts=(),
        write_roots=selected.write_roots,
        error="",
        started_at="2026-08-22T00:00:00+00:00",
        ended_at="2026-08-22T00:00:01+00:00",
    )


def test_child_action_projection_resumes_after_started_half_commit(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = ActionHarness()
    model = LongHorizonModel(harness=harness)
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    state = store.create_run(
        model.create_literal_goal(REQUEST, str(workspace)),
        "RUN-PROJECTION-RECOVERY",
    )
    selected = atom("child")
    stage = SupervisorStage.create(
        stage_request(),
        disposition="dispatch",
        review_summary="Project one child action.",
        atoms=(selected,),
    )
    action_id = "A00001"
    selected_outcome = replace(
        outcome(stage, selected, "done"),
        actions=(
            {
                "action_id": action_id,
                "sequence": 1,
                "operation": "read_file",
                "arguments": {"path": "left.txt"},
                "status": "succeeded",
                "result": {"success": True, "output": "left"},
                "artifact_refs": [],
                "workspace_changed": False,
            },
        ),
    )
    attempt_id = f"{stage.stage_id}:{selected.atom_id}:{action_id}"
    controller = LongHorizonController(store, model=model, harness=harness)
    controller._persist(
        state,
        "attempt_started",
        {
            "attempt_id": attempt_id,
            "stage_id": stage.stage_id,
            "atom_id": selected.atom_id,
            "contract_digest": selected_outcome.contract_digest,
            "action_id": action_id,
            "operation": "read_file",
            "arguments": {"path": "left.txt"},
            "action_sequence": 1,
            "rwkv_action_authority": True,
            "supervisor_action_executed": False,
            "at": selected_outcome.started_at,
        },
        subject_id=attempt_id,
    )

    assert controller._project_parallel_atom_actions(
        state,
        {selected.atom_id: selected_outcome},
    ) is True
    assert controller._project_parallel_atom_actions(
        state,
        {selected.atom_id: selected_outcome},
    ) is False
    events = [state.causal_records[item] for item in state.causal_order]
    assert sum(
        event.event_type == "attempt_started"
        and event.payload.get("attempt_id") == attempt_id
        for event in events
    ) == 1
    assert sum(
        event.event_type == "action_returned"
        and event.payload.get("attempt_id") == attempt_id
        for event in events
    ) == 1


class StageSupervisor:
    provider_name = "test-provider"
    model_name = "test-strong-model"

    def __init__(self):
        self.requests: list[SupervisorStageRequest] = []

    def next_stage(self, request: SupervisorStageRequest) -> SupervisorStage:
        self.requests.append(request)
        if request.stage_index == 1:
            return SupervisorStage.create(
                request,
                disposition="dispatch",
                review_summary="Dispatch two independent file atoms.",
                atoms=(
                    atom("left", write_roots=("left.txt",)),
                    atom("right", write_roots=("right.txt",)),
                ),
            )
        if request.stage_index == 2:
            return SupervisorStage.create(
                request,
                disposition="dispatch",
                review_summary="Material work is done; dispatch one finalizer.",
                atoms=(
                    atom(
                        "final",
                        role="finalizer",
                        depends_on=("left", "right"),
                    ),
                ),
            )
        return SupervisorStage.create(
            request,
            disposition="accept_final",
            review_summary="The RWKV finalizer candidate is supported.",
            accepted_candidate_atom_id="final",
        )


class RecordingPool:
    def __init__(self):
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
        del parent_goal, max_transitions, completed_outcomes
        self.batches.append(tuple(item.atom_id for item in atoms))
        assert max_workers == len(atoms)
        return tuple(
            outcome(
                stage,
                item,
                (
                    "Created and verified both requested files."
                    if item.role == AtomRole.FINALIZER
                    else f"Completed atom {item.atom_id}."
                ),
            )
            for item in atoms
        )


class ContractDriftPool:
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
        del parent_goal, max_workers, max_transitions, completed_outcomes
        return tuple(
            replace(
                outcome(stage, item, "tampered"),
                contract_digest="f" * 64,
            )
            for item in atoms
        )


def test_parallel_stage_requires_verbatim_request_clauses_and_disjoint_writes():
    with pytest.raises(ValueError, match="verbatim substrings"):
        SupervisorAtom.create(
            immutable_request=REQUEST,
            atom_id="bad",
            role="work",
            objective="Rewrite the request.",
            request_clauses=("Create two files.",),
            allowed_operations=("read_file",),
            action_budget=2,
            completion_checks=("Done.",),
        )

    request = stage_request()
    with pytest.raises(ValueError, match="overlapping write roots"):
        SupervisorStage.create(
            request,
            disposition="dispatch",
            review_summary="Invalid concurrent writes.",
            atoms=(
                atom("one", write_roots=("left.txt",)),
                atom("two", write_roots=("left.txt",)),
            ),
        )

    invented = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="invented",
        role="work",
        objective="Write 2026/source.txt.",
        request_clauses=(REQUEST,),
        write_roots=("2026/source.txt",),
        allowed_operations=("write_file",),
        action_budget=1,
        completion_checks=("2026/source.txt exists.",),
    )
    with pytest.raises(ValueError, match="introduced scope roots"):
        SupervisorStage.create(
            request,
            disposition="dispatch",
            review_summary="Reject invented path rewriting.",
            atoms=(invented,),
        )


def test_supervisor_rejects_flattened_outcome_drift_from_execution_contract():
    selected = atom("left", write_roots=("left.txt",))
    first_stage = SupervisorStage.create(
        stage_request(),
        disposition="dispatch",
        review_summary="Create the requested file.",
        atoms=(selected,),
    )
    completed = outcome(first_stage, selected, "done").to_supervisor_dict()
    completed["execution_contract"] = AtomExecutionContract.create(
        immutable_request=REQUEST,
        atom=selected,
    ).to_dict()
    completed["write_roots"] = ["right.txt"]

    with pytest.raises(ValueError, match="changed write roots"):
        SupervisorStage.create(
            stage_request(stage_index=2, completed_atoms=(completed,)),
            disposition="dispatch",
            review_summary="Continue only from the exact completed contract.",
            atoms=(atom("verify", depends_on=("left",)),),
        )

def test_parallel_stage_does_not_treat_technical_prose_as_path_authority():
    request = stage_request()
    technical = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="technical",
        role="work",
        objective="Compare before/after and inspect TaskQueue.pop.",
        request_clauses=(REQUEST,),
        read_roots=("left.txt",),
        allowed_operations=("read_file",),
        action_budget=1,
        completion_checks=("Report path/line_count/byte_count fields.",),
    )

    stage = SupervisorStage.create(
        request,
        disposition="dispatch",
        review_summary="Technical prose is not a filesystem scope declaration.",
        atoms=(technical,),
    )

    assert stage.atoms == (technical,)


def test_parallel_stage_allows_descendants_of_user_authorized_root():
    recursive_request = "Recursively inspect docs and update every discovered file."
    request = SupervisorStageRequest(
        run_id="RUN-DESCENDANT",
        request=recursive_request,
        request_digest="request-descendant",
        constraints=(),
        stage_index=2,
        max_parallel_atoms=4,
        previous_stage_id="STAGE-1",
        completed_atoms=(),
        available_operations=OPERATION_CATALOG,
        workspace_manifest={"entries": [{"path": "docs"}]},
    )
    descendant = SupervisorAtom.create(
        immutable_request=recursive_request,
        atom_id="descendant",
        role="work",
        objective="Update the discovered docs/nested/config.json artifact.",
        request_clauses=(recursive_request,),
        read_roots=("docs/nested/config.json",),
        write_roots=("docs/nested/config.json",),
        allowed_operations=("read_file", "write_file"),
        action_budget=3,
        completion_checks=("The discovered descendant is updated and verified.",),
    )

    stage = SupervisorStage.create(
        request,
        disposition="dispatch",
        review_summary="Continue within the explicitly authorized recursive root.",
        atoms=(descendant,),
    )

    assert stage.atoms == (descendant,)


def test_scoped_atom_harness_rejects_undeclared_mutation(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    model = LongHorizonModel(harness=ActionHarness(sandbox_commands=False))
    execution_contract = AtomExecutionContract.create(
        immutable_request=REQUEST,
        atom=atom("left", write_roots=("left.txt",)),
    )
    goal = model.create_literal_goal(
        REQUEST,
        str(workspace),
        runtime_policy={
            ATOM_EXECUTION_POLICY_KEY: AtomExecutionBinding(
                contract=execution_contract
            ).to_dict()
        },
    )
    base = ActionHarness(sandbox_commands=False)
    scoped = ScopedAtomHarness(
        base,
        execution_contract,
        threading.RLock(),
    )

    with scoped.action_transaction(goal):
        result = scoped.execute(
            TaskAction("write_file", {"path": "left.txt", "content": "left"}),
            goal,
        )
    assert result.success is True
    with pytest.raises(ScopeViolation, match="outside write_roots"):
        with scoped.action_transaction(goal):
            scoped.execute(
                TaskAction(
                    "write_file",
                    {"path": "right.txt", "content": "right"},
                ),
                goal,
            )


def test_scoped_atom_harness_discloses_only_scope_compatible_tools():
    base = ActionHarness(sandbox_commands=False)
    finalizer = ScopedAtomHarness(
        base,
        AtomExecutionContract.create(
            immutable_request=REQUEST,
            atom=atom("final", role="finalizer"),
        ),
        threading.RLock(),
    )
    finalizer_names = {
        item["name"] for item in finalizer.g1i_tool_definitions()
    }
    assert "read_file" in finalizer_names
    assert "write_file" not in finalizer_names
    assert "run_command" not in finalizer_names

    writer = ScopedAtomHarness(
        base,
        AtomExecutionContract.create(
            immutable_request=REQUEST,
            atom=atom("left", write_roots=("left.txt",)),
        ),
        threading.RLock(),
    )
    writer_names = {item["name"] for item in writer.g1i_tool_definitions()}
    assert "write_file" in writer_names
    assert "read_file" not in writer_names
    assert "run_command" not in writer_names


def test_path_and_external_side_effect_scopes_use_distinct_contracts(
    tmp_path: Path,
):
    operation_catalog = (
        *OPERATION_CATALOG,
        {
            "name": "move_file",
            "description": "Move one file.",
            "scope_mode": "path_mutation",
        },
    )
    request = replace(
        stage_request(),
        available_operations=operation_catalog,
    )
    mover = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="move",
        role="work",
        objective="Move left.txt to right.txt.",
        request_clauses=(REQUEST,),
        write_roots=("left.txt", "right.txt"),
        allowed_operations=("move_file",),
        action_budget=1,
        completion_checks=("right.txt contains the moved file.",),
    )
    external = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="external",
        role="work",
        objective="Run one exclusive external operation.",
        request_clauses=(REQUEST,),
        exclusive=True,
        allowed_operations=("run_command",),
        action_budget=1,
        completion_checks=("The exclusive operation returned.",),
    )

    move_stage = SupervisorStage.create(
        request,
        disposition="dispatch",
        review_summary="Move with source and destination scopes.",
        atoms=(mover,),
    )
    external_stage = SupervisorStage.create(
        request,
        disposition="dispatch",
        review_summary="External effects do not invent path roots.",
        atoms=(external,),
    )

    assert move_stage.atoms[0].write_roots == ("left.txt", "right.txt")
    assert external_stage.atoms[0].write_roots == ()

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "left.txt").write_text("left", encoding="utf-8")
    base = ActionHarness(sandbox_commands=False)
    execution_contract = AtomExecutionContract.create(
        immutable_request=REQUEST,
        atom=mover,
    )
    goal = LongHorizonModel(harness=base).create_literal_goal(
        REQUEST,
        str(workspace),
        runtime_policy={
            ATOM_EXECUTION_POLICY_KEY: AtomExecutionBinding(
                contract=execution_contract
            ).to_dict()
        },
    )
    scoped = ScopedAtomHarness(
        base,
        execution_contract,
        threading.RLock(),
    )
    result = scoped.execute(
        TaskAction(
            "move_file",
            {"source": "left.txt", "destination": "right.txt"},
        ),
        goal,
    )
    assert result.success is True


def test_finalizer_requires_completed_work_and_no_unrecovered_failure():
    completed = {
        "atom_id": "left",
        "role": "work",
        "status": "completed",
        "candidate_output": "left complete",
        "write_roots": ["left.txt"],
    }
    failed = {
        "atom_id": "right_failed",
        "role": "work",
        "status": "interrupted",
        "candidate_output": "",
        "write_roots": ["right.txt"],
    }
    request = stage_request(stage_index=2, completed_atoms=(completed, failed))
    with pytest.raises(ValueError, match="failed work remains unrecovered"):
        SupervisorStage.create(
            request,
            disposition="dispatch",
            review_summary="Finalization is premature.",
            atoms=(
                atom("final", role="finalizer", depends_on=("left",)),
            ),
        )

    repaired = {
        "atom_id": "right_repair",
        "role": "work",
        "status": "completed",
        "candidate_output": "right complete",
        "write_roots": ["right.txt"],
    }
    repaired_request = stage_request(
        stage_index=3,
        completed_atoms=(completed, failed, repaired),
    )
    stage = SupervisorStage.create(
        repaired_request,
        disposition="dispatch",
        review_summary="All material work is committed.",
        atoms=(
            atom(
                "final",
                role="finalizer",
                depends_on=("left", "right_repair"),
            ),
        ),
    )
    assert stage.atoms[0].role == AtomRole.FINALIZER

    with pytest.raises(ValueError, match="scope-incompatible operations"):
        SupervisorStage.create(
            repaired_request,
            disposition="dispatch",
            review_summary="A finalizer cannot receive write tools.",
            atoms=(
                SupervisorAtom.create(
                    immutable_request=REQUEST,
                    atom_id="bad_final",
                    role="finalizer",
                    objective="Review completion.",
                    request_clauses=(REQUEST,),
                    depends_on=("left", "right_repair"),
                    allowed_operations=("write_file",),
                    action_budget=2,
                    completion_checks=("Reviewed.",),
                ),
            ),
        )


def test_controller_dispatches_parallel_batches_and_accepts_only_raw_finalizer(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = ActionHarness(sandbox_commands=False)
    model = LongHorizonModel(harness=harness)
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    goal = model.create_literal_goal(
        REQUEST,
        str(workspace),
        constraints=["Stay inside the workspace."],
    )
    store.create_run(goal, "RUN")
    supervisor = StageSupervisor()
    pool = RecordingPool()
    controller = LongHorizonController(
        store,
        model=model,
        harness=harness,
        supervisor=supervisor,
        supervisor_policy=SupervisorPolicy(
            mode="parallel_atoms",
            max_parallel_stages=6,
            max_parallel_atoms=4,
            atom_max_transitions=20,
        ),
        atom_worker_pool=pool,
    )

    result = controller.run("RUN")

    assert result.state.status == RunStatus.COMPLETED
    assert result.final_output == "Created and verified both requested files."
    assert pool.batches == [("left", "right"), ("final",)]
    assert len(supervisor.requests) == 3
    event_types = [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ]
    assert event_types.count("supervisor_stage_committed") == 3
    assert event_types.count("atom_attempt_started") == 3
    assert event_types.count("atom_outcome_committed") == 3
    terminal = [
        event
        for event in result.state.causal_records.values()
        if event.event_type == "run_completed"
    ][0]
    assert terminal.payload["output_source"] == (
        "rwkv_parallel_finalizer_exact_candidate"
    )
    assert terminal.payload["controller_rewritten"] is False


def test_parent_controller_rejects_worker_contract_digest_drift(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = ActionHarness(sandbox_commands=False)
    model = LongHorizonModel(harness=harness)
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    store.create_run(model.create_literal_goal(REQUEST, str(workspace)), "RUN")
    controller = LongHorizonController(
        store,
        model=model,
        harness=harness,
        supervisor=StageSupervisor(),
        supervisor_policy=SupervisorPolicy(
            mode="parallel_atoms",
            max_parallel_stages=6,
            max_parallel_atoms=4,
            atom_max_transitions=20,
        ),
        atom_worker_pool=ContractDriftPool(),
    )

    with pytest.raises(ValueError, match="changed committed atom identity"):
        controller.run("RUN")


@dataclass
class Response:
    content: str
    finish_reason: str = "stop"


class AtomQueueClient:
    model_name = "test-rwkv"

    def __init__(self, calls, *, barrier: threading.Barrier | None = None):
        self.outputs = [json.dumps(item, separators=(",", ":")) for item in calls]
        self.barrier = barrier
        self.calls = 0
        self.prompts: list[str] = []

    def text_completion(self, prompt: str, max_tokens: int = 768, stop=None):
        del max_tokens, stop
        self.prompts.append(prompt)
        self.calls += 1
        if self.barrier is not None and self.calls == 1:
            self.barrier.wait(timeout=5)
        return Response(self.outputs.pop(0))


def test_real_atom_pool_runs_two_rwkv_lanes_concurrently_and_finalizes(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = ActionHarness(sandbox_commands=False)
    parent_model = LongHorizonModel(harness=harness)
    store = LongHorizonStore(tmp_path / "parent-state", checkpoint_retention=1000)
    goal = parent_model.create_literal_goal(REQUEST, str(workspace))
    store.create_run(goal, "RUN")
    barrier = threading.Barrier(2)
    scripted = {
        "left": [
            {"function": "write_file", "params": {"path": "left.txt", "content": "left"}},
            {"function": "final_answer", "params": {"text": "left atom complete"}},
        ],
        "right": [
            {"function": "write_file", "params": {"path": "right.txt", "content": "right"}},
            {"function": "final_answer", "params": {"text": "right atom complete"}},
        ],
        "final": [
            {"function": "read_file", "params": {"path": "left.txt"}},
            {"function": "read_file", "params": {"path": "right.txt"}},
            {
                "function": "final_answer",
                "params": {"text": "Created and verified both requested files."},
            },
        ],
    }
    settings = RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
        tool_disclosure_mode="full",
    )
    clients: dict[str, AtomQueueClient] = {}

    def model_factory(selected, scoped_harness):
        client = AtomQueueClient(
            scripted[selected.atom.atom_id],
            barrier=(
                barrier
                if selected.atom.atom_id in {"left", "right"}
                else None
            ),
        )
        clients[selected.atom.atom_id] = client
        return LongHorizonModel(
            ModelSession(
                client,
                settings=settings,
            ),
            harness=scoped_harness,
        )

    pool = ThreadedRWKVAtomPool(
        tmp_path / "atom-workers",
        harness=harness,
        model_factory=model_factory,
    )
    controller = LongHorizonController(
        store,
        model=parent_model,
        harness=harness,
        supervisor=StageSupervisor(),
        supervisor_policy=SupervisorPolicy(
            mode="parallel_atoms",
            max_parallel_stages=6,
            max_parallel_atoms=4,
            atom_max_transitions=20,
        ),
        atom_worker_pool=pool,
    )

    result = controller.run("RUN")

    assert result.state.status == RunStatus.COMPLETED
    assert result.final_output == "Created and verified both requested files."
    assert (workspace / "left.txt").read_text(encoding="utf-8") == "left"
    assert (workspace / "right.txt").read_text(encoding="utf-8") == "right"
    committed = [
        event.payload["outcome"]
        for event in result.state.causal_records.values()
        if event.event_type == "atom_outcome_committed"
    ]
    assert {item["atom_id"] for item in committed} == {"left", "right", "final"}
    assert sum(int(item["action_count"]) for item in committed) == 4
    event_types = [
        event.event_type for event in result.state.causal_records.values()
    ]
    assert event_types.count("attempt_started") == 4
    assert event_types.count("action_returned") == 4
    assert '"immutable_request": "Complete left."' in clients["left"].prompts[0]
    assert "Completed dependency handoffs" in clients["final"].prompts[0]
    assert '\\"observations\\"' in clients["final"].prompts[0]
    assert '\\"observed_content\\"' in clients["final"].prompts[0]
    assert '\\"operation\\"' not in clients["final"].prompts[0]
    assert '\\"arguments\\"' not in clients["final"].prompts[0]
    assert '\\"candidate_output\\"' not in clients["final"].prompts[0]
    left_state_root = next((tmp_path / "atom-workers").glob("*/left/state"))
    left_state = LongHorizonStore(
        left_state_root,
        checkpoint_retention=1000,
    ).load("ATOM")
    binding = AtomExecutionBinding.from_dict(
        left_state.goal.runtime_policy[ATOM_EXECUTION_POLICY_KEY]
    )
    assert binding.contract.atom_kind == "mutate"
    assert binding.contract.effect_ceiling == "workspace_mutation"
    assert binding.contract.atom.write_roots == ("left.txt",)
    assert binding.completed_dependencies == ()


def test_failed_atom_workspace_is_not_committed(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = ActionHarness(sandbox_commands=False)
    parent_model = LongHorizonModel(harness=harness)
    goal = parent_model.create_literal_goal(REQUEST, str(workspace))
    selected = atom("left", write_roots=("left.txt",))
    stage = SupervisorStage.create(
        stage_request(),
        disposition="dispatch",
        review_summary="Run one isolated writer.",
        atoms=(selected,),
    )
    settings = RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
        tool_disclosure_mode="full",
    )

    def model_factory(_selected, scoped_harness):
        client = AtomQueueClient(
            [
                {
                    "function": "write_file",
                    "params": {"path": "left.txt", "content": "uncommitted"},
                },
                {"function": "unknown_operation", "params": {}},
            ]
        )
        return LongHorizonModel(
            ModelSession(client, settings=settings),
            harness=scoped_harness,
        )

    pool = ThreadedRWKVAtomPool(
        tmp_path / "atom-workers",
        harness=harness,
        model_factory=model_factory,
    )
    outcomes = pool.run_stage(
        goal,
        stage,
        (selected,),
        max_workers=1,
        max_transitions=5,
        completed_outcomes={},
    )

    assert outcomes[0].status == AtomExecutionStatus.FAILED
    assert not (workspace / "left.txt").exists()
    assert (
        tmp_path
        / "atom-workers"
        / stage.stage_id
        / selected.atom_id
        / "workspace"
        / "left.txt"
    ).read_text(encoding="utf-8") == "uncommitted"


def test_dependency_handoff_bounds_full_external_evidence_without_mutation() -> None:
    source_text = "RWKV official evidence " + ("x" * 30_000)
    evidence = {
        "evidence_record_id": "E-1",
        "source_object": {
            "source_object_id": "public_web_page:1",
            "source_object_type": "public_web_page",
        },
        "snapshot_digest": "a" * 64,
        "url": "https://example.test/rwkv",
        "title": "RWKV official evidence",
        "published": "2026-08-30",
        "structured_fields": {"description": source_text},
        "exact_spans": [
            {
                "span_id": "SPAN-1",
                "text": source_text,
                "locator": {"start_char": 0, "end_char": len(source_text)},
            }
        ],
    }
    result = {
        "success": True,
        "action_type": "web_search",
        "outcome_type": "success",
        "output": source_text,
        "evidence": [evidence, {**evidence, "evidence_record_id": "E-2"}],
        "metadata": {
            "external_evidence": {
                "route_id": "ROUTE-1",
                "request_digest": "request-digest",
                "status": "evidence_committed",
            },
            "network_policy": {"allowed": True},
        },
    }
    actions = tuple(
        {
            "action_id": f"A{index:05d}",
            "operation": "web_search",
            "arguments": {"query": "RWKV official evidence"},
            "result": result,
        }
        for index in range(1, 7)
    )
    selected = AtomExecutionOutcome(
        stage_id="STAGE-1",
        atom_id="network-discovery",
        contract_digest="b" * 64,
        role=AtomRole.WORK,
        status=AtomExecutionStatus.COMPLETED,
        candidate_output="done",
        candidate_decision_id="D-final",
        action_count=len(actions),
        model_request_count=7,
        protocol_rejections=0,
        actions=actions,
        artifacts=(),
        write_roots=(),
        error="",
        started_at="2026-08-30T00:00:00+00:00",
        ended_at="2026-08-30T00:00:01+00:00",
    )
    original = json.dumps(selected.to_dict(), ensure_ascii=False, sort_keys=True)

    handoff = ThreadedRWKVAtomPool._dependency_handoff(selected)
    encoded = json.dumps(handoff, ensure_ascii=False, sort_keys=True)

    assert len(encoded) < 12_000
    assert len(handoff["observations"]) == 4
    assert all(len(item["observed_content"]) == 800 for item in handoff["observations"])
    assert all(len(item["evidence"]) == 1 for item in handoff["observations"])
    projected_span = handoff["observations"][0]["evidence"][0]["exact_spans"][0]
    assert len(projected_span["text"]) == 256
    assert projected_span["source_text_chars"] == len(source_text)
    assert handoff["observations"][0]["full_result_persisted"] is True
    assert json.dumps(selected.to_dict(), ensure_ascii=False, sort_keys=True) == original


def test_exclusive_command_commits_complete_isolated_snapshot_on_success(
    tmp_path: Path,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "before.txt").write_text("before", encoding="utf-8")
    harness = ActionHarness(sandbox_commands=False)
    goal = LongHorizonModel(harness=harness).create_literal_goal(
        REQUEST, str(workspace)
    )
    selected = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="exclusive-command",
        role="work",
        objective="Create left.txt through one exclusive command.",
        request_clauses=(REQUEST,),
        exclusive=True,
        allowed_operations=("run_command",),
        action_budget=1,
        completion_checks=("left.txt exists in the parent workspace.",),
    )
    stage = SupervisorStage.create(
        stage_request(),
        disposition="dispatch",
        review_summary="Run one exclusive workspace command.",
        atoms=(selected,),
    )
    settings = RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
        tool_disclosure_mode="full",
    )

    def model_factory(_selected, scoped_harness):
        return LongHorizonModel(
            ModelSession(
                AtomQueueClient(
                    [
                        {
                            "function": "run_command",
                            "params": {
                                "argv": [
                                    "python",
                                    "-c",
                                    "from pathlib import Path; Path('left.txt').write_text('external')",
                                ]
                            },
                        },
                        {
                            "function": "final_answer",
                            "params": {"text": "exclusive command complete"},
                        },
                    ]
                ),
                settings=settings,
            ),
            harness=scoped_harness,
        )

    pool = ThreadedRWKVAtomPool(
        tmp_path / "atom-workers",
        harness=harness,
        model_factory=model_factory,
    )
    outcomes = pool.run_stage(
        goal,
        stage,
        (selected,),
        max_workers=1,
        max_transitions=5,
        completed_outcomes={},
    )

    assert outcomes[0].status == AtomExecutionStatus.COMPLETED
    assert (workspace / "left.txt").read_text(encoding="utf-8") == "external"
    assert (workspace / "before.txt").read_text(encoding="utf-8") == "before"
    assert (
        tmp_path
        / "atom-workers"
        / stage.stage_id
        / selected.atom_id
        / "workspace"
        / "left.txt"
    ).read_text(encoding="utf-8") == "external"


def test_failed_exclusive_command_never_mutates_parent_workspace(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "before.txt").write_text("authoritative", encoding="utf-8")
    harness = ActionHarness(sandbox_commands=False)
    goal = LongHorizonModel(harness=harness).create_literal_goal(
        REQUEST, str(workspace)
    )
    selected = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="failed-exclusive-command",
        role="work",
        objective="Run one failing exclusive command.",
        request_clauses=(REQUEST,),
        exclusive=True,
        allowed_operations=("run_command",),
        action_budget=1,
        completion_checks=("The command succeeds.",),
    )
    stage = SupervisorStage.create(
        stage_request(),
        disposition="dispatch",
        review_summary="Inject a failed exclusive workspace command.",
        atoms=(selected,),
    )
    settings = RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
        tool_disclosure_mode="full",
    )

    def model_factory(_selected, scoped_harness):
        return LongHorizonModel(
            ModelSession(
                AtomQueueClient(
                    [
                        {
                            "function": "run_command",
                            "params": {
                                "argv": [
                                    "python",
                                    "-c",
                                    "from pathlib import Path; "
                                    "Path('leaked.txt').write_text('must-not-commit'); "
                                    "raise SystemExit(7)",
                                ]
                            },
                        },
                        {
                            "function": "final_answer",
                            "params": {"text": "must not be accepted"},
                        },
                    ]
                ),
                settings=settings,
            ),
            harness=scoped_harness,
        )

    pool = ThreadedRWKVAtomPool(
        tmp_path / "atom-workers",
        harness=harness,
        model_factory=model_factory,
    )
    outcomes = pool.run_stage(
        goal,
        stage,
        (selected,),
        max_workers=1,
        max_transitions=5,
        completed_outcomes={},
    )

    assert outcomes[0].status != AtomExecutionStatus.COMPLETED
    assert not (workspace / "leaked.txt").exists()
    assert (workspace / "before.txt").read_text(encoding="utf-8") == "authoritative"
    snapshot = (
        tmp_path
        / "atom-workers"
        / stage.stage_id
        / selected.atom_id
        / "workspace"
    )
    assert (snapshot / "leaked.txt").read_text(encoding="utf-8") == "must-not-commit"


class AtomProcessLoss(RuntimeError):
    rwkv_lh_process_loss = True


class CrashAtomHarness(ActionHarness):
    def __init__(self):
        super().__init__(sandbox_commands=False)
        self.crashed = False

    def execute(self, action: TaskAction, goal):
        result = super().execute(action, goal)
        if action.action_type == "write_file" and not self.crashed:
            self.crashed = True
            raise AtomProcessLoss("atom process lost after durable child effect")
        return result


def test_process_loss_propagates_then_resumes_same_atom_snapshot(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = CrashAtomHarness()
    goal = LongHorizonModel(harness=harness).create_literal_goal(
        REQUEST, str(workspace)
    )
    selected = atom("left", write_roots=("left.txt",))
    stage = SupervisorStage.create(
        stage_request(),
        disposition="dispatch",
        review_summary="Run recoverable isolated writer.",
        atoms=(selected,),
    )
    runtime = RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
        tool_disclosure_mode="full",
    )
    factory_calls = 0

    def model_factory(_selected, scoped_harness):
        nonlocal factory_calls
        factory_calls += 1
        calls = (
            [
                {
                    "function": "write_file",
                    "params": {"path": "left.txt", "content": "left"},
                },
                {"function": "final_answer", "params": {"text": "recovered"}},
            ]
            if factory_calls == 1
            else [
                {"function": "final_answer", "params": {"text": "recovered"}}
            ]
        )
        return LongHorizonModel(
            ModelSession(AtomQueueClient(calls), settings=runtime),
            harness=scoped_harness,
        )

    pool = ThreadedRWKVAtomPool(
        tmp_path / "atom-workers",
        harness=harness,
        model_factory=model_factory,
    )

    with pytest.raises(AtomProcessLoss):
        pool.run_stage(
            goal,
            stage,
            (selected,),
            max_workers=1,
            max_transitions=10,
            completed_outcomes={},
        )
    assert not (workspace / "left.txt").exists()

    outcomes = pool.run_stage(
        goal,
        stage,
        (selected,),
        max_workers=1,
        max_transitions=10,
        completed_outcomes={},
    )

    assert outcomes[0].status == AtomExecutionStatus.COMPLETED
    assert (workspace / "left.txt").read_text(encoding="utf-8") == "left"


def test_projected_multi_action_prompt_matches_the_real_budget() -> None:
    selected = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="projected-multi",
        role="work",
        objective="Create left.txt and right.txt.",
        request_clauses=(REQUEST,),
        write_roots=("left.txt", "right.txt"),
        allowed_operations=("read_file", "write_file"),
        action_budget=3,
        completion_checks=("Both files are created.",),
        atom_kind="mutate",
        effect_ceiling="workspace_mutation",
        evidence_kinds=("artifacts",),
        freshness="current_workspace",
        source_preferences=("workspace",),
        operation_allowset_source=CAPABILITY_PROJECTION_VERSION,
        minimum_actions=2,
    )

    execution_contract = AtomExecutionContract.create(
        immutable_request=REQUEST,
        atom=selected,
    )
    constraint = ThreadedRWKVAtomPool._transaction_mode_constraint(
        execution_contract
    )

    assert "bounded multi-operation" in constraint
    assert "complete 2-3 direct actions" in constraint
    assert "every declared write root" in constraint
    assert "single-operation" not in constraint


def test_projected_mutation_requires_every_write_root_to_be_covered() -> None:
    selected = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="projected-coverage",
        role="work",
        objective="Create left.txt and right.txt.",
        request_clauses=(REQUEST,),
        write_roots=("left.txt", "right.txt"),
        allowed_operations=("read_file", "write_file"),
        action_budget=2,
        completion_checks=("Both files are created.",),
        atom_kind="mutate",
        effect_ceiling="workspace_mutation",
        evidence_kinds=("artifacts",),
        freshness="current_workspace",
        source_preferences=("workspace",),
        operation_allowset_source=CAPABILITY_PROJECTION_VERSION,
        minimum_actions=2,
    )
    read = {
        "operation": "read_file",
        "arguments": {"path": "left.txt"},
        "status": "succeeded",
        "result": {"success": True},
    }
    write_left = {
        "operation": "write_file",
        "arguments": {"path": "left.txt", "content": "left"},
        "status": "succeeded",
        "result": {"success": True},
    }
    write_right = {
        "operation": "write_file",
        "arguments": {"path": "right.txt", "content": "right"},
        "status": "succeeded",
        "result": {"success": True},
    }
    execution_contract = AtomExecutionContract.create(
        immutable_request=REQUEST,
        atom=selected,
    )
    for action_id, action in enumerate((read, write_left, write_right), start=1):
        action["action_id"] = f"A{action_id}"
        action["contract_digest"] = execution_contract.contract_digest

    assert "no successful path mutation" in (
        ThreadedRWKVAtomPool._transaction_integrity_error(
            execution_contract,
            (read,),
        )
    )
    assert "right.txt" in ThreadedRWKVAtomPool._transaction_integrity_error(
        execution_contract,
        (write_left,),
    )
    assert (
        ThreadedRWKVAtomPool._transaction_integrity_error(
            execution_contract,
            (write_left, write_right),
        )
        == ""
    )


def test_one_move_can_cover_its_declared_source_and_destination() -> None:
    selected = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="move-coverage",
        role="work",
        objective="Move left.txt to right.txt.",
        request_clauses=(REQUEST,),
        write_roots=("left.txt", "right.txt"),
        allowed_operations=("move_file",),
        action_budget=1,
        completion_checks=("The source was moved to the destination.",),
    )
    move = {
        "operation": "move_file",
        "arguments": {"source": "left.txt", "destination": "right.txt"},
        "status": "succeeded",
        "result": {"success": True},
    }
    execution_contract = AtomExecutionContract.create(
        immutable_request=REQUEST,
        atom=selected,
    )
    move["action_id"] = "A1"
    move["contract_digest"] = execution_contract.contract_digest

    assert (
        ThreadedRWKVAtomPool._transaction_integrity_error(
            execution_contract,
            (move,),
        )
        == ""
    )


def test_contract_work_atom_must_produce_an_operation_result(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "left.txt").write_text("left", encoding="utf-8")
    harness = ActionHarness(sandbox_commands=False)
    goal = LongHorizonModel(harness=harness).create_literal_goal(
        REQUEST, str(workspace)
    )
    selected = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="observe-left",
        role="work",
        objective="Observe left.txt.",
        request_clauses=(REQUEST,),
        read_roots=("left.txt",),
        allowed_operations=("read_file",),
        action_budget=1,
        completion_checks=("left.txt has an exact observation.",),
    )
    stage = SupervisorStage.create(
        stage_request(),
        disposition="dispatch",
        review_summary="Require one exact read result.",
        atoms=(selected,),
    )
    settings = RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
        tool_disclosure_mode="full",
    )

    def model_factory(_selected, scoped_harness):
        return LongHorizonModel(
            ModelSession(
                AtomQueueClient(
                    [
                        {
                            "function": "final_answer",
                            "params": {"text": "premature"},
                        },
                        {
                            "function": "read_file",
                            "params": {"path": "left.txt"},
                        },
                        {
                            "function": "final_answer",
                            "params": {"text": "observed"},
                        },
                    ]
                ),
                settings=settings,
            ),
            harness=scoped_harness,
        )

    pool = ThreadedRWKVAtomPool(
        tmp_path / "atom-workers",
        harness=harness,
        model_factory=model_factory,
    )
    outcomes = pool.run_stage(
        goal,
        stage,
        (selected,),
        max_workers=1,
        max_transitions=8,
        completed_outcomes={},
    )

    assert outcomes[0].status == AtomExecutionStatus.COMPLETED
    assert outcomes[0].action_count == 1
    assert outcomes[0].protocol_rejections == 1
    assert outcomes[0].actions[0]["operation"] == "read_file"


def test_incomplete_atom_budget_returns_to_planner_without_premature_final_loop(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = ActionHarness(sandbox_commands=False)
    goal = LongHorizonModel(harness=harness).create_literal_goal(
        REQUEST, str(workspace)
    )
    selected = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="observe-missing",
        role="work",
        objective="Observe left.txt and report whether it exists.",
        request_clauses=(REQUEST,),
        read_roots=("left.txt",),
        allowed_operations=("read_file",),
        action_budget=1,
        completion_checks=("left.txt has a complete direct observation.",),
    )
    stage = SupervisorStage.create(
        stage_request(),
        disposition="dispatch",
        review_summary="Require one exact read result.",
        atoms=(selected,),
    )
    client = AtomQueueClient(
        [
            {"function": "read_file", "params": {"path": "left.txt"}},
            {"function": "final_answer", "params": {"text": "missing"}},
        ]
    )
    selected_settings = RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
        tool_disclosure_mode="full",
    )

    def model_factory(_selected, scoped_harness):
        return LongHorizonModel(
            ModelSession(client, settings=selected_settings),
            harness=scoped_harness,
        )

    pool = ThreadedRWKVAtomPool(
        tmp_path / "atom-workers",
        harness=harness,
        model_factory=model_factory,
    )

    outcome = pool.run_stage(
        goal,
        stage,
        (selected,),
        max_workers=1,
        max_transitions=20,
        completed_outcomes={},
    )[0]

    assert outcome.status is AtomExecutionStatus.INTERRUPTED
    assert outcome.action_count == 1
    assert outcome.protocol_rejections == 0
    assert outcome.actions[0]["result"]["outcome_type"] == "not_found"
    assert len(client.prompts) == 2
    assert "read_roots" in outcome.error


def test_contract_finalizer_must_observe_current_workspace(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "left.txt").write_text("left", encoding="utf-8")
    harness = ActionHarness(sandbox_commands=False)
    goal = LongHorizonModel(harness=harness).create_literal_goal(
        REQUEST, str(workspace)
    )
    selected = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="grounded-finalizer",
        role="finalizer",
        objective="Read left.txt and report its accepted current content.",
        request_clauses=(REQUEST,),
        read_roots=("left.txt",),
        allowed_operations=("read_file",),
        action_budget=1,
        completion_checks=("The final response is grounded in left.txt.",),
        atom_kind="synthesize",
        effect_ceiling="local_read_only",
        evidence_kinds=("current_workspace",),
        freshness="current_workspace",
        source_preferences=("workspace_file",),
        operation_allowset_source="controller_capability_projection.v2",
        minimum_actions=1,
    )
    stage = SupervisorStage.create(
        stage_request(),
        disposition="dispatch",
        review_summary="Ground the final response in the accepted workspace.",
        atoms=(selected,),
    )
    settings = RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
        tool_disclosure_mode="full",
    )

    def model_factory(_selected, scoped_harness):
        return LongHorizonModel(
            ModelSession(
                AtomQueueClient(
                    [
                        {
                            "function": "final_answer",
                            "params": {"text": "ungrounded"},
                        },
                        {
                            "function": "read_file",
                            "params": {"path": "left.txt"},
                        },
                        {
                            "function": "final_answer",
                            "params": {"text": "left"},
                        },
                    ]
                ),
                settings=settings,
            ),
            harness=scoped_harness,
        )

    pool = ThreadedRWKVAtomPool(
        tmp_path / "atom-workers",
        harness=harness,
        model_factory=model_factory,
    )
    outcomes = pool.run_stage(
        goal,
        stage,
        (selected,),
        max_workers=1,
        max_transitions=8,
        completed_outcomes={},
    )

    assert outcomes[0].status == AtomExecutionStatus.COMPLETED
    assert outcomes[0].candidate_output == "left"
    assert outcomes[0].action_count == 1
    assert outcomes[0].protocol_rejections == 1
    assert outcomes[0].actions[0]["operation"] == "read_file"


def test_action_budget_forces_final_answer_without_second_tool_action(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "left.txt").write_text("left", encoding="utf-8")
    harness = ActionHarness(sandbox_commands=False)
    client = AtomQueueClient(
        [
            {"function": "read_file", "params": {"path": "left.txt"}},
            {"function": "read_file", "params": {"path": "left.txt"}},
            {"function": "final_answer", "params": {"text": "observed left"}},
        ]
    )
    settings = RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
        tool_disclosure_mode="full",
    )
    model = LongHorizonModel(
        ModelSession(client, settings=settings),
        harness=harness,
    )
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    goal = model.create_literal_goal("Inspect left.txt.", str(workspace))
    store.create_run(goal, "RUN")
    controller = LongHorizonController(
        store,
        model=model,
        harness=harness,
        max_transitions=10,
        max_actions=1,
    )

    result = controller.run("RUN")

    assert result.state.status == RunStatus.COMPLETED
    assert result.final_output == "observed left"
    assert len(result.state.actions) == 1
    assert result.state.protocol_rejections == 1


def test_zero_action_budget_forces_finalizer_without_tool_action(tmp_path: Path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = ActionHarness(sandbox_commands=False)
    client = AtomQueueClient(
        [{"function": "final_answer", "params": {"text": "final only"}}]
    )
    settings = RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
        tool_disclosure_mode="full",
    )
    model = LongHorizonModel(
        ModelSession(client, settings=settings),
        harness=harness,
    )
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    goal = model.create_literal_goal("Synthesize accepted evidence.", str(workspace))
    store.create_run(goal, "RUN-ZERO")

    result = LongHorizonController(
        store,
        model=model,
        harness=harness,
        max_transitions=4,
        max_actions=0,
    ).run("RUN-ZERO")

    assert result.state.status == RunStatus.COMPLETED
    assert result.final_output == "final only"
    assert not result.state.actions
