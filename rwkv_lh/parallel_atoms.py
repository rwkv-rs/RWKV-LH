"""Parallel RWKV atom execution with explicit workspace mutation scopes."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Mapping, Protocol, Sequence

from rwkv_lh.atom_execution import (
    ATOM_EXECUTION_POLICY_KEY,
    AtomDependencyResult,
    AtomExecutionBinding,
    AtomExecutionContract,
    contract_integrity_error,
    path_is_within,
)
from rwkv_lh.harness import ActionHarness, ScopeViolation
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_io import canonical_digest
from rwkv_lh.operation_contracts import (
    PATH_MUTATION_ARGUMENTS,
    PATH_MUTATION_OPERATIONS,
)
from rwkv_lh.schema import (
    GoalState,
    RunState,
    RunStatus,
    TaskAction,
    ToolSelectionRecord,
    utc_now,
)
from rwkv_lh.store import LongHorizonStore, StateRecoveryError
from rwkv_lh.supervisor import AtomRole, SupervisorAtom


class AtomExecutionStatus(str, Enum):
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    FAILED = "failed"


@dataclass(frozen=True)
class AtomExecutionOutcome:
    stage_id: str
    atom_id: str
    contract_digest: str
    role: AtomRole
    status: AtomExecutionStatus
    candidate_output: str
    candidate_decision_id: str
    action_count: int
    model_request_count: int
    protocol_rejections: int
    actions: tuple[Mapping[str, Any], ...]
    artifacts: tuple[Mapping[str, Any], ...]
    write_roots: tuple[str, ...]
    error: str
    started_at: str
    ended_at: str
    tool_selection_handoffs: tuple[Mapping[str, Any], ...] = ()
    tool_selection_decision_bindings: tuple[Mapping[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "atom_id": self.atom_id,
            "contract_digest": self.contract_digest,
            "role": self.role.value,
            "status": self.status.value,
            "candidate_output": self.candidate_output,
            "candidate_output_sha256": hashlib.sha256(
                self.candidate_output.encode("utf-8")
            ).hexdigest(),
            "candidate_decision_id": self.candidate_decision_id,
            "action_count": self.action_count,
            "model_request_count": self.model_request_count,
            "protocol_rejections": self.protocol_rejections,
            "actions": [dict(item) for item in self.actions],
            "artifacts": [dict(item) for item in self.artifacts],
            "write_roots": list(self.write_roots),
            "error": self.error,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "tool_selection_handoffs": [
                dict(item) for item in self.tool_selection_handoffs
            ],
            "tool_selection_decision_bindings": [
                dict(item) for item in self.tool_selection_decision_bindings
            ],
        }

    def to_supervisor_dict(self) -> dict[str, Any]:
        projected_actions: list[dict[str, Any]] = []
        operation_counts: dict[str, int] = {}
        for item in self.actions:
            operation = str(item.get("operation") or "")
            operation_counts[operation] = operation_counts.get(operation, 0) + 1
        for item in self.actions[-4:]:
            result = dict(item.get("result") or {})
            output = str(result.get("output") or "")
            output_limit = 2400 if self.role == AtomRole.FINALIZER else 800
            if len(output) > output_limit:
                result["output"] = output[:output_limit]
                result["output_truncated"] = True
            projected_actions.append(
                {
                    "action_id": str(item.get("action_id") or ""),
                    "operation": str(item.get("operation") or ""),
                    "arguments": dict(item.get("arguments") or {}),
                    "status": str(item.get("status") or ""),
                    "result": result,
                    "workspace_changed": bool(item.get("workspace_changed")),
                }
            )
        candidate = (
            self.candidate_output if self.role == AtomRole.FINALIZER else ""
        )
        return {
            "stage_id": self.stage_id,
            "atom_id": self.atom_id,
            "contract_digest": self.contract_digest,
            "role": self.role.value,
            "status": self.status.value,
            "candidate_output": candidate[:3000],
            "candidate_output_sha256": hashlib.sha256(
                candidate.encode("utf-8")
            ).hexdigest(),
            "action_count": self.action_count,
            "model_request_count": self.model_request_count,
            "protocol_rejections": self.protocol_rejections,
            "tool_selection_handoff_count": len(self.tool_selection_handoffs),
            "tool_selection_decision_binding_count": len(
                self.tool_selection_decision_bindings
            ),
            "operation_counts": operation_counts,
            "recent_actions": projected_actions,
            "artifacts": [dict(item) for item in self.artifacts[-32:]],
            "write_roots": list(self.write_roots),
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AtomExecutionOutcome":
        raw_handoffs = value.get("tool_selection_handoffs") or ()
        if not isinstance(raw_handoffs, (list, tuple)) or any(
            not isinstance(item, Mapping) for item in raw_handoffs
        ):
            raise TypeError("tool_selection_handoffs must contain objects")
        raw_bindings = value.get("tool_selection_decision_bindings") or ()
        if not isinstance(raw_bindings, (list, tuple)) or any(
            not isinstance(item, Mapping) for item in raw_bindings
        ):
            raise TypeError(
                "tool_selection_decision_bindings must contain objects"
            )
        return cls(
            stage_id=str(value.get("stage_id") or ""),
            atom_id=str(value.get("atom_id") or ""),
            contract_digest=str(value.get("contract_digest") or ""),
            role=AtomRole(str(value.get("role") or "")),
            status=AtomExecutionStatus(str(value.get("status") or "")),
            candidate_output=str(value.get("candidate_output") or ""),
            candidate_decision_id=str(value.get("candidate_decision_id") or ""),
            action_count=int(value.get("action_count", 0) or 0),
            model_request_count=int(value.get("model_request_count", 0) or 0),
            protocol_rejections=int(value.get("protocol_rejections", 0) or 0),
            actions=tuple(
                dict(item)
                for item in value.get("actions") or ()
                if isinstance(item, Mapping)
            ),
            artifacts=tuple(
                dict(item)
                for item in value.get("artifacts") or ()
                if isinstance(item, Mapping)
            ),
            write_roots=tuple(str(item) for item in value.get("write_roots") or ()),
            error=str(value.get("error") or ""),
            started_at=str(value.get("started_at") or ""),
            ended_at=str(value.get("ended_at") or ""),
            tool_selection_handoffs=tuple(
                ToolSelectionRecord.from_dict(item).to_dict()
                for item in raw_handoffs
            ),
            tool_selection_decision_bindings=tuple(
                dict(item) for item in raw_bindings
            ),
        )


def _decision_selection_id(state: RunState, decision_id: str) -> str:
    decision = state.decisions.get(decision_id)
    if decision is None:
        raise StateRecoveryError("action references a missing Executor decision")
    candidates = {decision.tool_selection_id} if decision.tool_selection_id else set()
    for checkpoint_id in (
        decision.input_checkpoint_id,
        decision.output_checkpoint_id,
    ):
        checkpoint = state.model_states.get(checkpoint_id)
        metadata = checkpoint.native_state_metadata if checkpoint else None
        selection_id = str((metadata or {}).get("tool_selection_id") or "")
        if selection_id:
            candidates.add(selection_id)
    candidates.update(
        selection.selection_id
        for selection in state.tool_selections.values()
        if selection.consumed_decision_id == decision_id
    )
    if len(candidates) > 1:
        raise StateRecoveryError(
            "Executor decision carries conflicting exact tool selection identities"
        )
    return next(iter(candidates), "")


def _project_atom_actions(state: RunState) -> tuple[Mapping[str, Any], ...]:
    """Project actions without losing the Selector→Executor decision binding."""

    projected: list[Mapping[str, Any]] = []
    for action in sorted(state.actions.values(), key=lambda item: item.sequence):
        decision = state.decisions.get(action.decision_id)
        if decision is None or not decision.accepted:
            raise StateRecoveryError(
                "executed action has no accepted Executor decision"
            )
        selection_id = _decision_selection_id(state, action.decision_id)
        selection = state.tool_selections.get(selection_id)
        if state.tool_selections and selection is None:
            raise StateRecoveryError(
                "executed action has no exact Selector decision binding"
            )
        if selection is not None and (
            selection.selected_operation != action.action_type
            or selection.atom_execution_contract_digest
            != action.atom_execution_contract_digest
            or (
                decision.selected_operation
                and decision.selected_operation != selection.selected_operation
            )
            or (
                decision.atom_execution_contract_digest
                and decision.atom_execution_contract_digest
                != selection.atom_execution_contract_digest
            )
        ):
            raise StateRecoveryError(
                "executed action differs from its exact Selector binding"
            )
        projected.append(
            {
                "action_id": action.action_id,
                "sequence": action.sequence,
                "operation": action.action_type,
                "arguments": dict(action.arguments),
                "status": action.status.value,
                "result": dict(action.result or {}),
                "decision_id": action.decision_id,
                "request_id": action.request_id,
                "selection_id": selection.selection_id if selection else "",
                "selected_operation": (
                    selection.selected_operation if selection else ""
                ),
                "contract_digest": action.atom_execution_contract_digest,
                "artifact_refs": list(action.artifact_refs),
                "workspace_changed": bool(
                    action.workspace_digest_before
                    and action.workspace_digest_after
                    and action.workspace_digest_before
                    != action.workspace_digest_after
                ),
            }
        )
    return tuple(projected)


def _project_tool_selection_decision_bindings(
    state: RunState,
) -> tuple[Mapping[str, Any], ...]:
    """Bind every consumed Selector result to its exact Executor decision."""

    actions_by_decision = {action.decision_id: action for action in state.actions.values()}
    decisions_by_selection: dict[str, list[Any]] = {}
    for decision in state.decisions.values():
        selection_id = _decision_selection_id(state, decision.decision_id)
        if selection_id:
            decisions_by_selection.setdefault(selection_id, []).append(decision)
    projected: list[Mapping[str, Any]] = []
    for selection in sorted(
        state.tool_selections.values(),
        key=lambda item: (item.created_at, item.selection_id),
    ):
        decisions = sorted(
            decisions_by_selection.get(selection.selection_id, ()),
            key=lambda item: (item.created_at, item.decision_id),
        )
        if (
            not selection.consumed_decision_id
            or selection.consumed_decision_id
            not in {item.decision_id for item in decisions}
        ):
            raise StateRecoveryError(
                "consumed exact tool selection has no Executor decision"
            )
        for attempt_index, decision in enumerate(decisions, start=1):
            action = actions_by_decision.get(decision.decision_id)
            action_expected = bool(
                decision.accepted
                and selection.selected_operation != "final_answer"
            )
            if bool(action) != action_expected:
                raise StateRecoveryError(
                    "exact tool selection decision/action lifecycle is incomplete"
                )
            if (
                decision.selected_operation
                and decision.selected_operation != selection.selected_operation
            ) or (
                decision.atom_execution_contract_digest
                and decision.atom_execution_contract_digest
                != selection.atom_execution_contract_digest
            ):
                raise StateRecoveryError(
                    "Executor decision differs from its exact Selector binding"
                )
            if action is not None and (
                action.request_id != decision.request_id
                or action.action_type != selection.selected_operation
                or action.atom_execution_contract_digest
                != selection.atom_execution_contract_digest
            ):
                raise StateRecoveryError(
                    "exact tool selection decision/action identity differs"
                )
            projected.append(
                {
                    "selection_id": selection.selection_id,
                    "selected_operation": selection.selected_operation,
                    "attempt_index": attempt_index,
                    "consumed_decision_id": decision.decision_id,
                    "selection_consumption_decision": (
                        decision.decision_id
                        == selection.consumed_decision_id
                    ),
                    "decision_request_id": decision.request_id,
                    "decision_accepted": decision.accepted,
                    "decision_command_digest": decision.command_digest,
                    "decision_raw_output_sha256": hashlib.sha256(
                        decision.raw_output.encode("utf-8")
                    ).hexdigest(),
                    "action_id": action.action_id if action is not None else "",
                    "contract_digest": selection.atom_execution_contract_digest,
                }
            )
    return tuple(projected)


class AtomWorkerPool(Protocol):
    def run_stage(
        self,
        parent_goal: GoalState,
        stage: "AtomBatch",
        atoms: Sequence[SupervisorAtom],
        *,
        max_workers: int,
        max_transitions: int,
        completed_outcomes: Mapping[str, AtomExecutionOutcome],
    ) -> tuple[AtomExecutionOutcome, ...]: ...


class AtomBatch(Protocol):
    """Only the stable identity needed by an RWKV worker pool."""

    stage_id: str
    stage_index: int


def _relative_parts(value: Any) -> tuple[str, ...]:
    raw = str(value or "").strip().replace("\\", "/")
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or ".." in path.parts or "\x00" in raw:
        raise ScopeViolation(f"atom action path is not workspace-relative: {value}")
    return tuple(part for part in path.parts if part not in {"", "."})


class ScopedAtomHarness:
    """Delegate Harness operations while enforcing one atom's declared writes."""

    operation_order_authority = "controller_capability_projection"

    def __init__(
        self,
        base: ActionHarness,
        contract: AtomExecutionContract,
        action_lock: threading.RLock,
    ) -> None:
        self.base = base
        self.contract = contract
        self._action_lock = action_lock

    def __getattr__(self, name: str) -> Any:
        return getattr(self.base, name)

    def g1i_tool_definitions(
        self,
        action_types: tuple[str, ...] | list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Expose only operations compatible with the committed atom scope."""

        requested = (
            [str(item) for item in action_types]
            if action_types is not None
            else list(self.contract.atom.allowed_operations)
        )
        allowed: list[str] = []
        for name in requested:
            if name not in self.contract.atom.allowed_operations:
                continue
            definition = self.base.definition(name)
            if not definition.side_effect:
                allowed.append(name)
                continue
            if self.contract.atom.exclusive or (
                self.contract.atom.write_roots and name in PATH_MUTATION_ARGUMENTS
            ):
                allowed.append(name)
        return self.base.g1i_tool_definitions(allowed)

    @contextmanager
    def action_transaction(self, goal: GoalState):
        self._validate_goal_binding(goal)
        with self._action_lock:
            yield

    def execute(self, action: TaskAction, goal: GoalState):
        self._validate_goal_binding(goal)
        if action.action_type not in self.contract.atom.allowed_operations:
            raise ScopeViolation(
                f"atom {self.contract.atom.atom_id} attempted operation "
                f"{action.action_type!r} outside its Planner allowset"
            )
        definition = self.base.definition(action.action_type)
        if definition.side_effect:
            self._validate_mutation(action)
        return self.base.execute(action, goal)

    def _validate_mutation(self, action: TaskAction) -> None:
        argument_names = PATH_MUTATION_ARGUMENTS.get(action.action_type)
        if not argument_names:
            if self.contract.atom.exclusive:
                return
            raise ScopeViolation(
                f"atom {self.contract.atom.atom_id} must be exclusive for side-effecting "
                f"operation {action.action_type}"
            )
        if not self.contract.atom.write_roots:
            raise ScopeViolation(
                f"read-only atom {self.contract.atom.atom_id} attempted "
                f"{action.action_type}"
            )
        for argument_name in argument_names:
            target = _relative_parts(action.arguments.get(argument_name))
            allowed = any(
                path_is_within(target, root)
                for root in self.contract.atom.write_roots
            )
            if (
                not allowed
                and action.action_type == "make_directory"
                and target
            ):
                allowed = any(
                    tuple(PurePosixPath(root).parts)[: len(target)] == target
                    for root in self.contract.atom.write_roots
                    if root != "."
                )
            if not allowed:
                raise ScopeViolation(
                    f"atom {self.contract.atom.atom_id} attempted to mutate "
                    f"{argument_name}={action.arguments.get(argument_name)!r} outside "
                    f"write_roots={list(self.contract.atom.write_roots)!r}"
                )

    def _validate_goal_binding(self, goal: GoalState) -> None:
        binding = AtomExecutionBinding.from_goal(goal, required=True)
        if binding is None or (
            binding.contract.contract_digest != self.contract.contract_digest
        ):
            raise ScopeViolation(
                "Harness Goal execution contract differs from its scoped atom contract"
            )


ModelFactory = Callable[[AtomExecutionContract, ScopedAtomHarness], LongHorizonModel]


class ThreadedRWKVAtomPool:
    """Run ready atoms in isolated workspaces and commit only completed writes."""

    def __init__(
        self,
        root: str | Path,
        *,
        harness: ActionHarness,
        model_factory: ModelFactory,
    ) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.harness = harness
        self.model_factory = model_factory
        self._workspace_lock = threading.RLock()

    def run_stage(
        self,
        parent_goal: GoalState,
        stage: AtomBatch,
        atoms: Sequence[SupervisorAtom],
        *,
        max_workers: int,
        max_transitions: int,
        completed_outcomes: Mapping[str, AtomExecutionOutcome],
    ) -> tuple[AtomExecutionOutcome, ...]:
        selected = tuple(atoms)
        if not selected:
            return ()
        workers = min(max(1, int(max_workers)), len(selected))
        outcomes: dict[str, AtomExecutionOutcome] = {}
        contracts = {
            atom.atom_id: AtomExecutionContract.create(
                immutable_request=parent_goal.request,
                atom=atom,
            )
            for atom in selected
        }
        atom_workspaces = {
            atom.atom_id: self._prepare_atom_workspace(
                parent_goal,
                stage,
                contracts[atom.atom_id],
            )
            for atom in selected
        }
        with ThreadPoolExecutor(
            max_workers=workers,
            thread_name_prefix=f"rwkv-atom-{stage.stage_index}",
        ) as executor:
            futures = {
                executor.submit(
                    self._run_atom,
                    parent_goal,
                    stage,
                    contracts[atom.atom_id],
                    atom_workspaces[atom.atom_id],
                    completed_outcomes,
                    max_transitions=max_transitions,
                ): atom
                for atom in selected
            }
            for future in as_completed(futures):
                atom = futures[future]
                try:
                    outcome = future.result()
                except BaseException as exc:
                    if getattr(exc, "rwkv_lh_process_loss", False):
                        raise
                    now = utc_now()
                    outcome = AtomExecutionOutcome(
                        stage_id=stage.stage_id,
                        atom_id=atom.atom_id,
                        contract_digest=(
                            contracts[atom.atom_id].contract_digest
                        ),
                        role=atom.role,
                        status=AtomExecutionStatus.FAILED,
                        candidate_output="",
                        candidate_decision_id="",
                        action_count=0,
                        model_request_count=0,
                        protocol_rejections=0,
                        actions=(),
                        artifacts=(),
                        write_roots=atom.write_roots,
                        error=f"{type(exc).__name__}: {exc}"[:2000],
                        started_at=now,
                        ended_at=now,
                    )
                outcomes[atom.atom_id] = outcome
        return tuple(outcomes[atom.atom_id] for atom in selected)

    def _run_atom(
        self,
        parent_goal: GoalState,
        stage: AtomBatch,
        contract: AtomExecutionContract,
        atom_workspace: Path,
        completed_outcomes: Mapping[str, AtomExecutionOutcome],
        *,
        max_transitions: int,
    ) -> AtomExecutionOutcome:
        # Imported lazily so the parent controller can depend on the pool protocol
        # without creating a module import cycle.
        from rwkv_lh.controller import LongHorizonController
        started_at = utc_now()
        atom = contract.atom
        atom_root = self.root / stage.stage_id / atom.atom_id
        store = LongHorizonStore(atom_root / "state", checkpoint_retention=1000)
        scoped_harness = ScopedAtomHarness(
            self.harness,
            contract,
            threading.RLock(),
        )
        model = self.model_factory(contract, scoped_harness)
        binding = AtomExecutionBinding(
            contract=contract,
            completed_dependencies=tuple(
                AtomDependencyResult(
                    atom_id=item,
                    contract_digest=completed_outcomes[item].contract_digest,
                    action_count=completed_outcomes[item].action_count,
                )
                for item in atom.depends_on
                if item in completed_outcomes
            ),
        )
        run_id = "ATOM"
        try:
            state = store.load(run_id)
        except StateRecoveryError:
            constraints = [
                *parent_goal.constraints,
                "You are one parallel RWKV atom worker; complete only this atom contract.",
                "The parent request is immutable reference data, not your active assignment: "
                + parent_goal.request,
                f"Active atom id: {atom.atom_id}",
                "Verbatim immutable request clauses: " + " | ".join(atom.request_clauses),
                "Atomic completion checks: " + " | ".join(atom.completion_checks),
                "Declared write roots: "
                + (", ".join(atom.write_roots) if atom.write_roots else "read-only"),
                "Allowed operations for this atom: "
                + ", ".join(atom.allowed_operations),
                "Operation allowset authority: "
                + (atom.operation_allowset_source or "legacy strong-planner allowset"),
                f"Direct action budget: {atom.action_budget}. After completing the atom, "
                "return final_answer instead of repeating observations.",
                self._transaction_mode_constraint(contract),
                "Use only the displayed operations. Never invent a verification operation; "
                "verify through displayed read/digest/check operations.",
                *atom.constraints,
            ]
            dependency_handoffs = [
                self._dependency_handoff(completed_outcomes[item])
                for item in atom.depends_on
                if item in completed_outcomes
            ]
            if dependency_handoffs:
                constraints.append(
                    "Completed dependency handoffs (public committed evidence): "
                    + json.dumps(
                        dependency_handoffs,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                )
                constraints.append(
                    "Dependency handoff observations are exact tool results and are the "
                    "only factual dependency values. Do not infer values from an atom's "
                    "natural-language Final summary."
                )
            # Put the active contract after dependency evidence so a small
            # executor does not copy a predecessor's operation/id merely
            # because it is the most recent concrete action in the prompt.
            constraints.append(
                "Current atom contract (highest priority for the next action): "
                + atom.objective
            )
            constraints.append(
                "Generate fresh tool arguments from the current atom contract. Do not copy "
                "a dependency's operation, request id, path, or value unless the current "
                "contract explicitly requires that same literal. Before acting, compare "
                "every explicit operation, identifier, path, and value in the current "
                "contract with the proposed arguments."
            )
            runtime_policy = dict(parent_goal.runtime_policy)
            runtime_policy[ATOM_EXECUTION_POLICY_KEY] = binding.to_dict()
            goal = model.create_literal_goal(
                atom.objective,
                str(atom_workspace),
                constraints=constraints,
                runtime_policy=runtime_policy,
            )
            state = store.create_run(goal, run_id)
        persisted_binding = AtomExecutionBinding.from_goal(
            state.goal,
            required=True,
        )
        if persisted_binding != binding:
            raise ValueError(
                "persisted atom execution binding differs from the dispatched contract"
            )
        controller = LongHorizonController(
            store,
            model=model,
            harness=scoped_harness,
            max_transitions=max_transitions,
        )
        result = controller.run(run_id)
        state = result.state
        status = (
            AtomExecutionStatus.COMPLETED
            if state.status == RunStatus.COMPLETED
            else AtomExecutionStatus.FAILED
            if state.status == RunStatus.FAILED
            else AtomExecutionStatus.INTERRUPTED
        )
        actions = _project_atom_actions(state)
        transaction_error = self._transaction_integrity_error(contract, actions)
        if status == AtomExecutionStatus.COMPLETED and transaction_error:
            status = AtomExecutionStatus.INTERRUPTED
        artifacts = tuple(
            {
                "artifact_id": artifact.artifact_id,
                "action_id": artifact.action_id,
                "path": artifact.path,
                "sha256": artifact.sha256,
                "media_type": artifact.media_type,
                "size_bytes": artifact.size_bytes,
                "summary": artifact.summary,
            }
            for artifact in state.artifacts.values()
        )
        error = ""
        if transaction_error:
            error = transaction_error
        elif status != AtomExecutionStatus.COMPLETED:
            error = str((state.errors[-1] if state.errors else {}).get("message") or "")
        elif atom.write_roots or atom.exclusive:
            self._commit_atom_workspace(
                Path(parent_goal.workspace_root).resolve(),
                atom_workspace,
                contract,
            )
        return AtomExecutionOutcome(
            stage_id=stage.stage_id,
            atom_id=atom.atom_id,
            contract_digest=contract.contract_digest,
            role=atom.role,
            status=status,
            candidate_output=result.final_output,
            candidate_decision_id=state.final_decision_id,
            action_count=len(actions),
            model_request_count=len(state.temp_decisions),
            protocol_rejections=state.protocol_rejections,
            actions=actions,
            artifacts=artifacts,
            write_roots=contract.atom.write_roots,
            error=error,
            started_at=started_at,
            ended_at=utc_now(),
            tool_selection_handoffs=tuple(
                selection.to_dict()
                for selection in sorted(
                    state.tool_selections.values(),
                    key=lambda item: (item.created_at, item.selection_id),
                )
            ),
            tool_selection_decision_bindings=(
                _project_tool_selection_decision_bindings(state)
            ),
        )

    @staticmethod
    def _transaction_mode_constraint(contract: AtomExecutionContract) -> str:
        if contract.atom.action_budget == 1:
            mode = (
                "Transaction mode: single action. Complete the one direct action, then "
                "return final_answer."
            )
        else:
            mode = (
                "Transaction mode: bounded multi-operation. Keep one RWKV state; "
                f"complete {contract.minimum_actions}-"
                f"{contract.atom.action_budget} direct actions and continue "
                "until the completion checks pass or the action budget is exhausted."
            )
        if contract.atom.write_roots and (
            set(contract.atom.allowed_operations) & PATH_MUTATION_OPERATIONS
        ):
            mode += (
                " Before final_answer, successful path mutations must cover every "
                "declared write root."
            )
        return mode

    @staticmethod
    def _transaction_integrity_error(
        contract: AtomExecutionContract,
        actions: tuple[Mapping[str, Any], ...],
    ) -> str:
        """Compatibility surface backed by the one canonical progress function."""

        return contract_integrity_error(contract, actions)

    def _prepare_atom_workspace(
        self,
        parent_goal: GoalState,
        stage: AtomBatch,
        contract: AtomExecutionContract,
    ) -> Path:
        parent_workspace = Path(parent_goal.workspace_root).resolve()
        atom_workspace = (
            self.root / stage.stage_id / contract.atom.atom_id / "workspace"
        ).resolve()
        if atom_workspace == parent_workspace or atom_workspace.is_relative_to(
            parent_workspace
        ) or parent_workspace.is_relative_to(atom_workspace):
            raise ValueError(
                "atom snapshot and authoritative workspace must not overlap"
            )
        with self._workspace_lock:
            if atom_workspace.exists():
                return atom_workspace
            atom_workspace.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(
                parent_workspace,
                atom_workspace,
            )
        return atom_workspace

    @staticmethod
    def _dependency_handoff(outcome: AtomExecutionOutcome) -> dict[str, Any]:
        """Project committed dependency facts without replaying action choices.

        A dependent worker needs the predecessor's observed values and artifact
        identities, not the concrete operation/argument envelope that produced
        them.  Replaying that envelope creates a recency prior which can make a
        small persistent executor copy the predecessor's tool instead of acting
        on its own atom contract.
        """

        # Use the same durable-result→RWKV projection authority as the direct
        # Controller observation path.  In particular, raw external EvidenceRecord
        # values may contain whole fetched pages and must never be copied verbatim
        # into a dependent atom's initial prompt.  The full result stays untouched
        # in the predecessor outcome and is bound here by digest.
        from rwkv_lh.controller import LongHorizonController

        observations: list[dict[str, Any]] = []
        for item in outcome.actions[-4:]:
            result = dict(item.get("result") or {})
            output = str(result.get("output") or "")
            projected = LongHorizonController._model_action_result(
                result,
                arguments=(
                    item.get("arguments")
                    if isinstance(item.get("arguments"), Mapping)
                    else {}
                ),
                evidence_source_limit=1,
                evidence_span_chars=256,
                structured_field_budget=400,
            )
            result_artifacts = [
                {
                    "path": str(artifact.get("path") or ""),
                    "sha256": str(artifact.get("sha256") or ""),
                    "size_bytes": int(artifact.get("size_bytes", 0) or 0),
                    "media_type": str(artifact.get("media_type") or ""),
                }
                for artifact in result.get("artifacts") or ()
                if isinstance(artifact, Mapping)
            ]
            observations.append(
                {
                    "success": bool(result.get("success")),
                    "observed_content": output[:800],
                    "observed_content_sha256": hashlib.sha256(
                        output.encode("utf-8")
                    ).hexdigest(),
                    "observed_content_chars": len(output),
                    "observed_content_complete": len(output) <= 800,
                    "evidence": [
                        dict(evidence)
                        for evidence in projected.get("evidence") or ()
                        if isinstance(evidence, Mapping)
                    ],
                    "evidence_projection": dict(
                        projected.get("evidence_projection") or {}
                    ),
                    "source_artifacts": result_artifacts[:8],
                    "error": LongHorizonController._bounded_model_value(
                        result.get("error") or {}
                    ),
                    "full_result_digest": canonical_digest(result),
                    "full_result_persisted": True,
                }
            )
        return {
            "atom_id": outcome.atom_id,
            "status": outcome.status.value,
            "observations": observations,
            "artifacts": [
                {
                    "path": str(item.get("path") or ""),
                    "sha256": str(item.get("sha256") or ""),
                    "size_bytes": int(item.get("size_bytes", 0) or 0),
                    "media_type": str(item.get("media_type") or ""),
                }
                for item in outcome.artifacts[-8:]
            ],
        }

    def _commit_atom_workspace(
        self,
        parent_workspace: Path,
        atom_workspace: Path,
        contract: AtomExecutionContract,
    ) -> None:
        parent_workspace = parent_workspace.resolve()
        atom_workspace = atom_workspace.resolve()
        if parent_workspace == atom_workspace:
            raise ValueError(
                "an atom snapshot cannot be the authoritative workspace"
            )
        if contract.atom.exclusive:
            self._commit_exclusive_snapshot(parent_workspace, atom_workspace)
            return
        with self._workspace_lock:
            for root in contract.atom.write_roots:
                if root == ".":
                    for child in list(parent_workspace.iterdir()):
                        self._remove_path(child)
                    for child in atom_workspace.iterdir():
                        self._copy_path(child, parent_workspace / child.name)
                    continue
                parts = _relative_parts(root)
                source = atom_workspace.joinpath(*parts)
                target = parent_workspace.joinpath(*parts)
                self._remove_path(target)
                if source.exists() or source.is_symlink():
                    self._copy_path(source, target)

    def _commit_exclusive_snapshot(
        self,
        parent_workspace: Path,
        atom_workspace: Path,
    ) -> None:
        """Replace the authoritative workspace only after an exclusive success.

        Exclusive operations such as ``run_command`` can mutate undeclared paths.
        They therefore run in a complete snapshot.  A successful snapshot is
        staged beside the parent and swapped in with a recoverable backup; failed
        or interrupted snapshots never reach this method.
        """

        if not parent_workspace.is_dir() or not atom_workspace.is_dir():
            raise ValueError("exclusive commit requires two existing directories")
        if atom_workspace.is_relative_to(
            parent_workspace
        ) or parent_workspace.is_relative_to(atom_workspace):
            raise ValueError(
                "exclusive snapshot and authoritative workspace must not overlap"
            )
        with self._workspace_lock:
            transaction_root = Path(
                tempfile.mkdtemp(
                    prefix=".rwkv-lh-exclusive-commit-",
                    dir=str(parent_workspace.parent),
                )
            )
            replacement = transaction_root / "replacement"
            backup = transaction_root / "backup"
            try:
                shutil.copytree(atom_workspace, replacement)
                parent_workspace.rename(backup)
                try:
                    replacement.rename(parent_workspace)
                except BaseException:
                    backup.rename(parent_workspace)
                    raise
            finally:
                # If restoration itself failed, preserve the transaction directory
                # and its backup for manual recovery instead of deleting evidence.
                if parent_workspace.exists():
                    shutil.rmtree(transaction_root, ignore_errors=True)

    @staticmethod
    def _remove_path(path: Path) -> None:
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path)

    @staticmethod
    def _copy_path(source: Path, target: Path) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir() and not source.is_symlink():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target, follow_symlinks=False)


__all__ = [
    "AtomBatch",
    "AtomExecutionOutcome",
    "AtomExecutionStatus",
    "AtomWorkerPool",
    "PATH_MUTATION_OPERATIONS",
    "ScopedAtomHarness",
    "ThreadedRWKVAtomPool",
]
