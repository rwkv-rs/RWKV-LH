"""One immutable execution authority for the complete RWKV atom lifecycle.

The strong Planner creates :class:`SupervisorAtom`.  This module binds that exact
value to its immutable parent request once, gives it a content digest, and derives
all runtime progress from the same binding.  Selector, Executor, Controller,
Harness, transaction validation, workspace commit, and outcome recovery must not
invent parallel copies of action budgets, mutation roots, or completion rules.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any

from rwkv_lh.model_io import canonical_digest
from rwkv_lh.operation_contracts import (
    PATH_MUTATION_ARGUMENTS,
    PATH_MUTATION_OPERATIONS,
)
from rwkv_lh.schema import ActionStatus, GoalState, RunState
from rwkv_lh.supervisor import AtomRole, SupervisorAtom


ATOM_EXECUTION_POLICY_KEY = "atom_execution"
ATOM_EXECUTION_BINDING_SCHEMA_VERSION = "rwkv-lh.atom-execution-binding.v1"
ATOM_EXECUTION_CONTRACT_SCHEMA_VERSION = "rwkv-lh.atom-execution-contract.v1"
ATOM_EXECUTION_DEPENDENCY_SCHEMA_VERSION = "rwkv-lh.atom-dependency-result.v1"
ATOM_CONTRACT_PROGRESS_SCHEMA_VERSION = "rwkv-lh.atom-contract-progress.v1"

_PATH_READ_OPERATIONS = frozenset(
    {
        "bind_evidence",
        "file_digest",
        "read_file",
        "read_json",
        "search_text",
    }
)


def _sha256(value: object, *, name: str) -> str:
    selected = str(value or "")
    if len(selected) != 64 or any(
        character not in "0123456789abcdef" for character in selected
    ):
        raise ValueError(f"{name} must be lowercase SHA-256")
    return selected


@dataclass(frozen=True)
class AtomExecutionContract:
    """The exact Planner atom and immutable request, bound by one digest."""

    immutable_request: str
    atom: SupervisorAtom
    contract_digest: str
    schema_version: str = ATOM_EXECUTION_CONTRACT_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        immutable_request: str,
        atom: SupervisorAtom,
    ) -> "AtomExecutionContract":
        request = str(immutable_request or "")
        if not request:
            raise ValueError("atom execution contract requires immutable_request")
        # Reparse the Planner value against the parent request.  This detects an
        # in-memory atom assembled outside the validated Supervisor boundary.
        validated_atom = SupervisorAtom.from_dict(
            atom.to_dict(),
            immutable_request=request,
        )
        payload = {
            "schema_version": ATOM_EXECUTION_CONTRACT_SCHEMA_VERSION,
            "immutable_request": request,
            "atom": validated_atom.to_dict(),
        }
        return cls(
            immutable_request=request,
            atom=validated_atom,
            contract_digest=canonical_digest(payload),
        )

    @property
    def minimum_actions(self) -> int:
        """One completion floor, including the v4 compatibility derivation."""

        if self.atom.operation_allowset_source:
            return self.atom.minimum_actions
        return 2 if len(self.atom.allowed_operations) > 1 else 1

    @property
    def atom_kind(self) -> str:
        if self.atom.atom_kind:
            return self.atom.atom_kind
        if self.atom.role is AtomRole.FINALIZER:
            return "synthesize"
        return "mutate" if self.atom.write_roots else "investigate"

    @property
    def effect_ceiling(self) -> str:
        if self.atom.effect_ceiling:
            return self.atom.effect_ceiling
        return (
            "workspace_mutation"
            if self.atom.write_roots
            else "local_read_only"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "immutable_request": self.immutable_request,
            "atom": self.atom.to_dict(),
            "contract_digest": self.contract_digest,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AtomExecutionContract":
        if not isinstance(value, Mapping):
            raise TypeError("atom execution contract must be an object")
        if str(value.get("schema_version") or "") != (
            ATOM_EXECUTION_CONTRACT_SCHEMA_VERSION
        ):
            raise ValueError("unsupported atom execution contract schema")
        raw_atom = value.get("atom")
        if not isinstance(raw_atom, Mapping):
            raise TypeError("atom execution contract atom must be an object")
        contract = cls.create(
            immutable_request=str(value.get("immutable_request") or ""),
            atom=SupervisorAtom.from_dict(
                raw_atom,
                immutable_request=str(value.get("immutable_request") or ""),
            ),
        )
        if _sha256(
            value.get("contract_digest"),
            name="contract_digest",
        ) != contract.contract_digest:
            raise ValueError("atom execution contract digest does not match its content")
        # Requiring exact canonical fields prevents a second, ignored variable
        # namespace from being smuggled into the persisted contract envelope.
        if dict(value) != contract.to_dict():
            raise ValueError("atom execution contract contains non-canonical fields")
        return contract


@dataclass(frozen=True)
class AtomDependencyResult:
    """Immutable identity/count facts from one committed predecessor outcome."""

    atom_id: str
    contract_digest: str
    action_count: int
    schema_version: str = ATOM_EXECUTION_DEPENDENCY_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if not self.atom_id.strip():
            raise ValueError("dependency atom_id must be non-empty")
        _sha256(self.contract_digest, name="dependency contract_digest")
        if isinstance(self.action_count, bool) or self.action_count < 0:
            raise ValueError("dependency action_count must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "atom_id": self.atom_id,
            "contract_digest": self.contract_digest,
            "action_count": self.action_count,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AtomDependencyResult":
        if str(value.get("schema_version") or "") != (
            ATOM_EXECUTION_DEPENDENCY_SCHEMA_VERSION
        ):
            raise ValueError("unsupported atom dependency result schema")
        result = cls(
            atom_id=str(value.get("atom_id") or ""),
            contract_digest=str(value.get("contract_digest") or ""),
            action_count=int(value.get("action_count", 0) or 0),
        )
        if dict(value) != result.to_dict():
            raise ValueError("atom dependency result contains non-canonical fields")
        return result


@dataclass(frozen=True)
class AtomExecutionBinding:
    """The sole persisted Planner→runtime handoff for one atom run."""

    contract: AtomExecutionContract
    completed_dependencies: tuple[AtomDependencyResult, ...] = ()
    schema_version: str = ATOM_EXECUTION_BINDING_SCHEMA_VERSION

    def __post_init__(self) -> None:
        ids = tuple(item.atom_id for item in self.completed_dependencies)
        if len(set(ids)) != len(ids):
            raise ValueError("atom execution binding contains duplicate dependencies")
        expected = self.contract.atom.depends_on
        if ids != expected:
            raise ValueError(
                "completed dependency identities differ from the Planner contract"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "contract": self.contract.to_dict(),
            "completed_dependencies": [
                item.to_dict() for item in self.completed_dependencies
            ],
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AtomExecutionBinding":
        if not isinstance(value, Mapping):
            raise TypeError("atom execution binding must be an object")
        if str(value.get("schema_version") or "") != (
            ATOM_EXECUTION_BINDING_SCHEMA_VERSION
        ):
            raise ValueError("unsupported atom execution binding schema")
        raw_contract = value.get("contract")
        if not isinstance(raw_contract, Mapping):
            raise TypeError("atom execution binding contract must be an object")
        raw_dependencies = value.get("completed_dependencies")
        if not isinstance(raw_dependencies, list):
            raise TypeError(
                "atom execution binding completed_dependencies must be an array"
            )
        binding = cls(
            contract=AtomExecutionContract.from_dict(raw_contract),
            completed_dependencies=tuple(
                AtomDependencyResult.from_dict(item)
                for item in raw_dependencies
                if isinstance(item, Mapping)
            ),
        )
        if len(binding.completed_dependencies) != len(raw_dependencies):
            raise TypeError("atom dependency results must be objects")
        if dict(value) != binding.to_dict():
            raise ValueError("atom execution binding contains non-canonical fields")
        return binding

    @classmethod
    def from_goal(
        cls,
        goal: GoalState,
        *,
        required: bool = False,
    ) -> "AtomExecutionBinding | None":
        raw = goal.runtime_policy.get(ATOM_EXECUTION_POLICY_KEY)
        if raw is None:
            if required:
                raise ValueError("atom Goal is missing its execution binding")
            return None
        if not isinstance(raw, Mapping):
            raise TypeError("atom execution runtime policy must be an object")
        return cls.from_dict(raw)


def atom_execution_contract_digest(goal: GoalState) -> str:
    binding = AtomExecutionBinding.from_goal(goal)
    return binding.contract.contract_digest if binding is not None else ""


def _relative_parts(value: object) -> tuple[str, ...]:
    raw = str(value or "").strip().replace("\\", "/")
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or ".." in path.parts or "\x00" in raw:
        return ()
    return tuple(part for part in path.parts if part not in {"", "."})


def path_is_within(target: tuple[str, ...], root: str) -> bool:
    if root == ".":
        return True
    root_parts = tuple(PurePosixPath(root).parts)
    return bool(root_parts and target[: len(root_parts)] == root_parts)


def path_kind(value: str) -> str:
    selected = str(value or "").replace("\\", "/").rstrip("/")
    if not selected or selected == "." or not PurePosixPath(selected).suffix:
        return "directory_or_extensionless"
    if PurePosixPath(selected).suffix.casefold() == ".json":
        return "json_file"
    return "non_json_file"


def _action_value(action: object, *names: str) -> object:
    if isinstance(action, Mapping):
        for name in names:
            if name in action:
                return action.get(name)
        return None
    for name in names:
        if hasattr(action, name):
            return getattr(action, name)
    return None


def action_succeeded(action: object) -> bool:
    status = _action_value(action, "status")
    status_value = status.value if isinstance(status, ActionStatus) else str(status or "")
    result = dict(_action_value(action, "result") or {})
    return status_value == ActionStatus.SUCCEEDED.value and bool(result.get("success"))


def action_completion_eligible(action: object) -> bool:
    """Return whether a successful action is complete enough to advance an atom."""

    if not action_succeeded(action):
        return False
    result = dict(_action_value(action, "result") or {})
    raw_metadata = result.get("metadata")
    metadata = dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}
    return metadata.get("complete") is not False and metadata.get("truncated") is not True


def action_observes_mutation_scope(
    contract: AtomExecutionContract,
    action: object,
) -> bool:
    """Recognize the legacy post-mutation observation from one shared definition."""

    if not action_completion_eligible(action):
        return False
    operation = str(_action_value(action, "action_type", "operation") or "")
    if operation == "check_command":
        return True
    if operation not in {
        "read_file",
        "read_json",
        "file_digest",
        "bind_evidence",
        "list_directory",
    }:
        return False
    arguments = dict(_action_value(action, "arguments") or {})
    raw_path = str(arguments.get("path") or "")
    if not raw_path:
        return False
    target = _relative_parts(raw_path)
    if operation == "list_directory":
        # Listing ``.`` observes every declared root.  A more specific directory
        # observes roots nested below that directory.
        if raw_path.strip().replace("\\", "/") == ".":
            return True
        if not target:
            return False
        return any(
            tuple(PurePosixPath(root).parts)[: len(target)] == target
            for root in contract.atom.write_roots
        )
    return bool(target) and any(
        path_is_within(target, root)
        for root in contract.atom.write_roots
    )


def covered_write_root_indexes(
    contract: AtomExecutionContract,
    actions: Sequence[object],
) -> frozenset[int]:
    roots = contract.atom.write_roots
    covered: set[int] = set()
    for action in actions:
        operation = str(_action_value(action, "action_type", "operation") or "")
        if operation not in PATH_MUTATION_OPERATIONS or not action_succeeded(action):
            continue
        arguments = dict(_action_value(action, "arguments") or {})
        for argument_name in PATH_MUTATION_ARGUMENTS[operation]:
            target = _relative_parts(arguments.get(argument_name))
            if not target:
                continue
            covered.update(
                index
                for index, root in enumerate(roots)
                if path_is_within(target, root)
            )
    return frozenset(covered)


def covered_read_root_indexes(
    contract: AtomExecutionContract,
    actions: Sequence[object],
) -> frozenset[int]:
    """Return declared read roots with a complete, direct Harness observation.

    Arguments and paths remain private to the Executor.  Only the resulting root
    indexes/counts enter the Selector projection.  Directory listings count only
    when they directly list a declared directory root; listing a parent does not
    pretend to have read a child's content.
    """

    roots = contract.atom.read_roots
    covered: set[int] = set()
    for action in actions:
        if not action_completion_eligible(action):
            continue
        operation = str(_action_value(action, "action_type", "operation") or "")
        arguments = dict(_action_value(action, "arguments") or {})
        raw_path = str(arguments.get("path") or "").strip().replace("\\", "/")
        if operation == "list_directory":
            target = _relative_parts(raw_path or ".")
            for index, root in enumerate(roots):
                normalized_root = str(root).strip().replace("\\", "/")
                if normalized_root == "." and raw_path in {"", "."}:
                    covered.add(index)
                elif target and target == tuple(PurePosixPath(root).parts):
                    covered.add(index)
            continue
        if operation not in _PATH_READ_OPERATIONS:
            continue
        target = _relative_parts(raw_path or ".")
        if not target and raw_path not in {"", "."}:
            continue
        covered.update(
            index
            for index, root in enumerate(roots)
            if (root == "." and raw_path in {"", "."})
            or (bool(target) and path_is_within(target, root))
        )
    return frozenset(covered)


def action_observes_read_scope(
    contract: AtomExecutionContract,
    action: object,
) -> bool:
    """Return whether one complete action is relevant to declared read scope."""

    if not action_completion_eligible(action):
        return False
    operation = str(_action_value(action, "action_type", "operation") or "")
    if operation == "check_command":
        return True
    return bool(covered_read_root_indexes(contract, (action,)))


def _latest_action_fact(actions: Sequence[object]) -> dict[str, object] | None:
    latest = actions[-1] if actions else None
    if latest is None:
        return None
    result = dict(_action_value(latest, "result") or {})
    raw_metadata = result.get("metadata")
    metadata = dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}
    fact: dict[str, object] = {
        "sequence": int(_action_value(latest, "sequence") or 0),
        "operation": str(
            _action_value(latest, "action_type", "operation") or ""
        ),
        "success": bool(result.get("success")),
        "outcome_type": str(
            result.get("outcome_type")
            or _action_value(latest, "outcome_type")
            or "pending"
        ),
    }
    if "complete" in metadata:
        fact["complete"] = bool(metadata["complete"])
    if "truncated" in metadata:
        fact["truncated"] = bool(metadata["truncated"])
    raw_error = result.get("error")
    if isinstance(raw_error, Mapping) and str(raw_error.get("type") or ""):
        fact["error_type"] = str(raw_error["type"])
    return fact


@dataclass(frozen=True)
class AtomContractProgress:
    """One Harness-observed completion projection shared by all runtime stages."""

    contract_digest: str
    action_count: int
    successful_action_count: int
    minimum_eligible_action_count: int
    remaining_action_budget: int
    covered_read_root_indexes: tuple[int, ...]
    covered_write_root_indexes: tuple[int, ...]
    remaining_minimum_action_count: int
    read_observation_required: bool
    read_observation_satisfied: bool
    remaining_read_observation_count: int
    remaining_write_root_count: int
    post_mutation_observation_required: bool
    post_mutation_observation_satisfied: bool
    remaining_required_count: int
    completion_ready: bool
    latest_action: Mapping[str, object] | None
    schema_version: str = ATOM_CONTRACT_PROGRESS_SCHEMA_VERSION

    @property
    def covered_write_root_count(self) -> int:
        return len(self.covered_write_root_indexes)

    @property
    def covered_read_root_count(self) -> int:
        return len(self.covered_read_root_indexes)

    def selector_projection(
        self,
        binding: AtomExecutionBinding,
    ) -> dict[str, object]:
        contract = binding.contract
        read_roots = contract.atom.read_roots
        write_roots = contract.atom.write_roots
        remaining_read_indexes = tuple(
            index
            for index in range(len(read_roots))
            if index not in self.covered_read_root_indexes
        )
        remaining_write_indexes = tuple(
            index
            for index in range(len(write_roots))
            if index not in self.covered_write_root_indexes
        )
        return {
            "schema_version": self.schema_version,
            "contract": {
                "contract_digest": contract.contract_digest,
                "atom_kind": contract.atom_kind,
                "effect_ceiling": contract.effect_ceiling,
                "role": contract.atom.role.value,
                "minimum_actions": contract.minimum_actions,
                "action_budget": contract.atom.action_budget,
                "required_read_root_count": len(read_roots),
                "required_read_root_kinds": dict(
                    sorted(Counter(path_kind(item) for item in read_roots).items())
                ),
                "required_write_root_count": len(write_roots),
                "required_write_root_kinds": dict(
                    sorted(Counter(path_kind(item) for item in write_roots).items())
                ),
                "completed_dependency_count": len(
                    binding.completed_dependencies
                ),
                "dependency_evidence_action_count": sum(
                    item.action_count for item in binding.completed_dependencies
                ),
            },
            "progress": {
                "action_count": self.action_count,
                "successful_action_count": self.successful_action_count,
                "minimum_eligible_action_count": (
                    self.minimum_eligible_action_count
                ),
                "remaining_action_budget": self.remaining_action_budget,
                "covered_read_root_count": self.covered_read_root_count,
                "covered_write_root_count": self.covered_write_root_count,
                "remaining_minimum_action_count": (
                    self.remaining_minimum_action_count
                ),
                "read_observation_required": self.read_observation_required,
                "read_observation_satisfied": self.read_observation_satisfied,
                "remaining_read_observation_count": (
                    self.remaining_read_observation_count
                ),
                "remaining_write_root_count": self.remaining_write_root_count,
                "post_mutation_observation_required": (
                    self.post_mutation_observation_required
                ),
                "post_mutation_observation_satisfied": (
                    self.post_mutation_observation_satisfied
                ),
                "remaining_required_count": self.remaining_required_count,
                "unobserved_read_root_kinds": (
                    dict(
                        sorted(
                            Counter(
                                path_kind(read_roots[index])
                                for index in remaining_read_indexes
                            ).items()
                        )
                    )
                    if not self.read_observation_satisfied
                    else {}
                ),
                "remaining_write_root_kinds": dict(
                    sorted(
                        Counter(
                            path_kind(write_roots[index])
                            for index in remaining_write_indexes
                        ).items()
                    )
                ),
                "completion_ready": self.completion_ready,
                "latest_action": (
                    dict(self.latest_action) if self.latest_action is not None else None
                ),
            },
        }


def contract_progress(
    contract: AtomExecutionContract,
    actions: Sequence[object],
) -> AtomContractProgress:
    """Derive the one completion truth consumed by every atom runtime stage."""

    ordered = sorted(
        actions,
        key=lambda item: int(_action_value(item, "sequence") or 0),
    )
    drifted = [
        str(_action_value(item, "action_id") or "")
        for item in ordered
        if str(
            _action_value(
                item,
                "atom_execution_contract_digest",
                "contract_digest",
            )
            or ""
        )
        != contract.contract_digest
    ]
    if drifted:
        raise ValueError(
            "Harness action records differ from the immutable atom execution "
            f"contract: {drifted}"
        )

    covered_reads = covered_read_root_indexes(contract, ordered)
    covered_reads_before_latest = covered_read_root_indexes(contract, ordered[:-1])
    covered_writes = covered_write_root_indexes(contract, ordered)
    covered_writes_before_latest = covered_write_root_indexes(contract, ordered[:-1])
    succeeded = [item for item in ordered if action_succeeded(item)]
    complete_successes = [
        item for item in ordered if action_completion_eligible(item)
    ]
    requires_path_mutation = bool(
        contract.atom.write_roots
        and set(contract.atom.allowed_operations) & PATH_MUTATION_OPERATIONS
    )
    minimum_eligible_actions = (
        [
            item
            for item in complete_successes
            if str(_action_value(item, "action_type", "operation") or "")
            in PATH_MUTATION_OPERATIONS
        ]
        if requires_path_mutation and contract.atom.operation_allowset_source
        else complete_successes
    )
    remaining_minimum = max(
        0,
        contract.minimum_actions - len(minimum_eligible_actions),
    )
    read_observation_required = bool(contract.atom.read_roots)
    read_observation_satisfied = (
        not read_observation_required
        or any(action_observes_read_scope(contract, item) for item in ordered)
    )
    remaining_read_observations = int(not read_observation_satisfied)
    remaining_write_roots = (
        len(contract.atom.write_roots) - len(covered_writes)
        if requires_path_mutation
        else 0
    )

    # Capability-graph mutations have a dependent verifier node.  The legacy
    # graph instead required an observation after its final mutation inside the
    # same atom.  Keep that compatibility rule, but derive it here rather than
    # leaving transaction commit with a second completion state machine.
    post_observation_required = bool(
        requires_path_mutation
        and not contract.atom.operation_allowset_source
        and len(contract.atom.allowed_operations) > 1
    )
    mutation_indexes = [
        index
        for index, item in enumerate(ordered)
        if action_completion_eligible(item)
        and str(_action_value(item, "action_type", "operation") or "")
        in PATH_MUTATION_OPERATIONS
    ]
    post_observation_satisfied = not post_observation_required
    if post_observation_required and mutation_indexes:
        post_observation_satisfied = any(
            action_observes_mutation_scope(contract, item)
            for item in ordered[mutation_indexes[-1] + 1 :]
        )

    # This is a lower bound on additional direct actions, not a sum of gates:
    # one successful write can satisfy both the action floor and one root.
    remaining_required = max(
        remaining_minimum,
        remaining_read_observations,
        remaining_write_roots,
    )
    if post_observation_required and not post_observation_satisfied:
        remaining_required = (
            max(remaining_required, 1)
            if mutation_indexes
            else max(
                remaining_minimum,
                remaining_read_observations,
                remaining_write_roots + 1,
            )
        )
    completion_ready = bool(
        remaining_minimum == 0
        and read_observation_satisfied
        and remaining_write_roots == 0
        and post_observation_satisfied
    )
    latest = _latest_action_fact(ordered)
    if latest is not None:
        newly_covered_reads = len(covered_reads - covered_reads_before_latest)
        newly_covered_writes = len(covered_writes - covered_writes_before_latest)
        latest["new_read_roots_covered"] = newly_covered_reads
        latest["new_write_roots_covered"] = newly_covered_writes
        latest["advanced_contract"] = bool(
            newly_covered_reads
            or newly_covered_writes
            or (
                read_observation_required
                and read_observation_satisfied
                and action_observes_read_scope(contract, ordered[-1])
                and not any(
                    action_observes_read_scope(contract, item)
                    for item in ordered[:-1]
                )
            )
            or (
                ordered[-1] in minimum_eligible_actions
                and len(minimum_eligible_actions) <= contract.minimum_actions
            )
            or (
                post_observation_required
                and post_observation_satisfied
                and action_observes_mutation_scope(contract, ordered[-1])
                and mutation_indexes
                and mutation_indexes[-1] < len(ordered) - 1
                and not any(
                    action_observes_mutation_scope(contract, item)
                    for item in ordered[mutation_indexes[-1] + 1 : -1]
                )
            )
        )
    return AtomContractProgress(
        contract_digest=contract.contract_digest,
        action_count=len(ordered),
        successful_action_count=len(succeeded),
        minimum_eligible_action_count=len(minimum_eligible_actions),
        remaining_action_budget=max(
            0,
            contract.atom.action_budget - len(ordered),
        ),
        covered_read_root_indexes=tuple(sorted(covered_reads)),
        covered_write_root_indexes=tuple(sorted(covered_writes)),
        remaining_minimum_action_count=remaining_minimum,
        read_observation_required=read_observation_required,
        read_observation_satisfied=read_observation_satisfied,
        remaining_read_observation_count=remaining_read_observations,
        remaining_write_root_count=remaining_write_roots,
        post_mutation_observation_required=post_observation_required,
        post_mutation_observation_satisfied=post_observation_satisfied,
        remaining_required_count=remaining_required,
        completion_ready=completion_ready,
        latest_action=latest,
    )


def contract_integrity_error(
    contract: AtomExecutionContract,
    actions: Sequence[object],
) -> str:
    """Explain why the same canonical progress cannot yet be committed."""

    try:
        progress = contract_progress(contract, actions)
    except ValueError as exc:
        return f"transaction_integrity: {exc}"
    requires_path_mutation = bool(
        contract.atom.write_roots
        and set(contract.atom.allowed_operations) & PATH_MUTATION_OPERATIONS
    )
    if requires_path_mutation and not progress.covered_write_root_indexes:
        return "transaction_integrity: no successful path mutation was observed"
    if progress.remaining_write_root_count:
        uncovered_roots = [
            root
            for index, root in enumerate(contract.atom.write_roots)
            if index not in progress.covered_write_root_indexes
        ]
        return (
            "transaction_integrity: no successful path mutation covered "
            f"write_roots={uncovered_roots!r}"
        )
    if progress.remaining_read_observation_count:
        unread_roots = [
            root
            for index, root in enumerate(contract.atom.read_roots)
            if index not in progress.covered_read_root_indexes
        ]
        return (
            "transaction_integrity: no complete direct observation covered "
            f"read_roots={unread_roots!r}"
        )
    if progress.remaining_minimum_action_count:
        return (
            "transaction_integrity: immutable atom minimum_actions still requires "
            f"{progress.remaining_minimum_action_count} complete successful action(s)"
        )
    if not progress.post_mutation_observation_satisfied:
        return (
            "transaction_integrity: a successful read/digest/check observation of "
            "the mutation scope is required after the final mutation"
        )
    return ""


def atom_contract_progress(
    state: RunState,
    *,
    binding: AtomExecutionBinding | None = None,
) -> AtomContractProgress | None:
    selected_binding = binding or AtomExecutionBinding.from_goal(state.goal)
    if selected_binding is None:
        return None
    return contract_progress(
        selected_binding.contract,
        tuple(state.actions.values()),
    )


def final_answer_eligible(
    state: RunState,
    *,
    legacy_minimum_actions: int = 0,
) -> bool:
    """Use the unified contract when present; retain only a top-level fallback."""

    progress = atom_contract_progress(state)
    if progress is not None:
        return progress.completion_ready
    return len(state.actions) >= max(0, int(legacy_minimum_actions))


__all__ = [
    "ATOM_CONTRACT_PROGRESS_SCHEMA_VERSION",
    "ATOM_EXECUTION_BINDING_SCHEMA_VERSION",
    "ATOM_EXECUTION_CONTRACT_SCHEMA_VERSION",
    "ATOM_EXECUTION_DEPENDENCY_SCHEMA_VERSION",
    "ATOM_EXECUTION_POLICY_KEY",
    "AtomContractProgress",
    "AtomDependencyResult",
    "AtomExecutionBinding",
    "AtomExecutionContract",
    "action_completion_eligible",
    "action_observes_read_scope",
    "action_observes_mutation_scope",
    "action_succeeded",
    "atom_contract_progress",
    "atom_execution_contract_digest",
    "contract_integrity_error",
    "contract_progress",
    "covered_read_root_indexes",
    "covered_write_root_indexes",
    "final_answer_eligible",
    "path_is_within",
    "path_kind",
]
