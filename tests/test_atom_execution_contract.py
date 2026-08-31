from __future__ import annotations

import threading
from pathlib import Path

import pytest

from rwkv_lh.atom_execution import (
    ATOM_EXECUTION_POLICY_KEY,
    AtomExecutionBinding,
    AtomExecutionContract,
    atom_contract_progress,
)
from rwkv_lh.capability_projection import CAPABILITY_PROJECTION_VERSION
from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionHarness, ScopeViolation
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.parallel_atoms import ScopedAtomHarness, ThreadedRWKVAtomPool
from rwkv_lh.schema import ActionRecord, ActionStatus, RunState, TaskAction
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.supervisor import SupervisorAtom


REQUEST = "Create hello.txt containing exactly hello."


def _atom(*, atom_id: str = "write-hello", write_root: str = "hello.txt"):
    return SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id=atom_id,
        role="work",
        objective=REQUEST,
        request_clauses=(REQUEST,),
        write_roots=(write_root,),
        exclusive=write_root == ".",
        allowed_operations=("write_file",),
        action_budget=1,
        completion_checks=("The requested file mutation succeeded.",),
        atom_kind="mutate",
        effect_ceiling="workspace_mutation",
        evidence_kinds=("workspace_file",),
        freshness="current_workspace",
        source_preferences=("workspace",),
        operation_allowset_source=CAPABILITY_PROJECTION_VERSION,
        minimum_actions=1,
    )


def _contract(**kwargs) -> AtomExecutionContract:
    return AtomExecutionContract.create(
        immutable_request=REQUEST,
        atom=_atom(**kwargs),
    )


def _goal(tmp_path: Path, contract: AtomExecutionContract):
    return LongHorizonModel.create_literal_goal(
        contract.atom.objective,
        str(tmp_path),
        runtime_policy={
            ATOM_EXECUTION_POLICY_KEY: AtomExecutionBinding(
                contract=contract
            ).to_dict()
        },
    )


def _action(contract_digest: str) -> ActionRecord:
    return ActionRecord(
        action_id="A00001",
        sequence=1,
        status=ActionStatus.SUCCEEDED,
        action_type="write_file",
        arguments={"path": "hello.txt", "content": "hello"},
        wire_arguments={"path": "hello.txt", "content": "hello"},
        action_fingerprint="fingerprint",
        idempotency_key="idempotency",
        decision_id="decision",
        request_id="request",
        started_at="2026-08-30T00:00:00+00:00",
        ended_at="2026-08-30T00:00:01+00:00",
        result={"success": True, "outcome_type": "success", "metadata": {}},
        outcome_type="success",
        atom_execution_contract_digest=contract_digest,
    )


def test_execution_contract_round_trip_is_exact_and_tamper_evident() -> None:
    contract = _contract()

    assert AtomExecutionContract.from_dict(contract.to_dict()) == contract

    tampered = contract.to_dict()
    tampered["atom"]["action_budget"] = 2
    with pytest.raises(ValueError, match="digest does not match"):
        AtomExecutionContract.from_dict(tampered)

    extended = contract.to_dict()
    extended["shadow_minimum_actions"] = 99
    with pytest.raises(ValueError, match="non-canonical fields"):
        AtomExecutionContract.from_dict(extended)


def test_progress_rejects_an_action_from_another_contract(tmp_path: Path) -> None:
    contract = _contract()
    other = _contract(atom_id="other")
    state = RunState(run_id="RUN", goal=_goal(tmp_path, contract))
    state.actions["A00001"] = _action(other.contract_digest)

    with pytest.raises(ValueError, match="action records differ"):
        atom_contract_progress(state)


def test_controller_rejects_parallel_action_limit_variables(tmp_path: Path) -> None:
    contract = _contract()
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=20)
    state = store.create_run(_goal(tmp_path / "workspace", contract), "RUN")

    controller = LongHorizonController(
        store,
        harness=ActionHarness(sandbox_commands=False),
        max_actions=2,
    )

    with pytest.raises(ValueError, match="max_actions differs"):
        controller._action_limits(state)


def test_scoped_harness_rejects_a_goal_bound_to_another_contract(
    tmp_path: Path,
) -> None:
    contract = _contract()
    other = _contract(atom_id="other")
    harness = ScopedAtomHarness(
        ActionHarness(sandbox_commands=False),
        contract,
        threading.RLock(),
    )

    with pytest.raises(ScopeViolation, match="differs"):
        with harness.action_transaction(_goal(tmp_path, other)):
            harness.execute(
                TaskAction(
                    "write_file",
                    {"path": "hello.txt", "content": "hello"},
                ),
                _goal(tmp_path, other),
            )


def test_exclusive_same_workspace_commit_is_rejected(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    marker = workspace / "keep.txt"
    marker.write_text("keep", encoding="utf-8")
    contract = _contract(atom_id="exclusive", write_root=".")
    pool = ThreadedRWKVAtomPool(
        tmp_path / "workers",
        harness=ActionHarness(sandbox_commands=False),
        model_factory=lambda _contract, scoped: LongHorizonModel(harness=scoped),
    )

    with pytest.raises(
        ValueError,
        match="snapshot cannot be the authoritative workspace",
    ):
        pool._commit_atom_workspace(workspace, workspace, contract)

    assert marker.read_text(encoding="utf-8") == "keep"
