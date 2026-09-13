"""Single semantic validator for Planner-authored contract graph patches.

The OpenAI-compatible Planner adapter and the durable Controller must accept the
same patch language.  Keeping the complete validation here lets the adapter feed
every semantic failure back through its bounded repair loop without weakening the
Controller's fail-closed replay boundary.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from rwkv_lh.capability_projection import (
    CAPABILITY_PROJECTION_VERSION,
    project_contract_capabilities,
)
from rwkv_lh.contract_graph import (
    ContractGraphNode,
    ContractGraphPatch,
    ContractObligation,
    ObligationPhase,
    ResultCapsule,
    validate_content_mutation_dependencies,
)
from rwkv_lh.supervisor import AtomRole


def contract_scopes_overlap(
    left_roots: Sequence[str],
    right_roots: Sequence[str],
) -> bool:
    """Return whether two workspace-relative scope sets overlap."""

    for left in left_roots:
        for right in right_roots:
            if left == "." or right == ".":
                return True
            left_parts = tuple(part for part in left.split("/") if part)
            right_parts = tuple(part for part in right.split("/") if part)
            shared = min(len(left_parts), len(right_parts))
            if left_parts[:shared] == right_parts[:shared]:
                return True
    return False


def contract_scope_covers(read_root: str, write_root: str) -> bool:
    """Return whether one read root covers the complete write-root subtree."""

    if read_root == ".":
        return True
    if write_root == ".":
        return False
    read_parts = tuple(part for part in read_root.split("/") if part and part != ".")
    write_parts = tuple(
        part for part in write_root.split("/") if part and part != "."
    )
    return (
        len(read_parts) <= len(write_parts)
        and write_parts[: len(read_parts)] == read_parts
    )


def validate_contract_patch_semantics(
    patch: ContractGraphPatch,
    *,
    existing_obligations: Mapping[str, ContractObligation],
    existing_nodes: Mapping[str, ContractGraphNode],
    operation_catalog: Sequence[Mapping[str, Any]],
    capsules: Sequence[ResultCapsule],
    finalizer_required: bool,
    workspace_manifest: Mapping[str, Any],
    existing_node_statuses: Mapping[str, str] | None = None,
) -> None:
    """Validate the complete shared Planner/Controller patch contract."""

    if not patch.new_nodes:
        raise ValueError("every contract planner patch must add executable nodes")
    if patch.base_revision > 0 and patch.new_obligations:
        raise ValueError(
            "immutable obligations are frozen after the initial contract patch"
        )
    catalog = {
        str(item.get("name") or ""): str(item.get("scope_mode") or "")
        for item in operation_catalog
    }
    for node in patch.new_nodes:
        if node.atom.operation_allowset_source != CAPABILITY_PROJECTION_VERSION:
            raise ValueError(
                "new contract graph nodes require Controller capability projection"
            )
        projection = project_contract_capabilities(
            atom_kind=node.atom.atom_kind,
            effect_ceiling=node.atom.effect_ceiling,
            role=node.atom.role.value,
            operation_catalog=operation_catalog,
            write_roots=node.atom.write_roots,
            evidence_kinds=node.atom.evidence_kinds,
            source_preferences=node.atom.source_preferences,
        )
        if node.atom.allowed_operations != projection.operations:
            raise ValueError(
                f"contract node {node.node_id} operation allowset was not "
                "mechanically projected"
            )
        if node.atom.exclusive != projection.exclusive:
            raise ValueError(
                f"contract node {node.node_id} changed projected exclusivity"
            )
        if node.atom.minimum_actions != projection.minimum_actions:
            raise ValueError(
                f"contract node {node.node_id} changed projected minimum actions"
            )
        unknown = set(node.atom.allowed_operations) - set(catalog)
        if unknown:
            raise ValueError(
                f"contract node selected unavailable operations: {sorted(unknown)}"
            )
        modes = [catalog[operation] for operation in node.atom.allowed_operations]
        if node.atom.role == AtomRole.FINALIZER and any(
            mode != "read_only" for mode in modes
        ):
            raise ValueError("contract finalizer must use a read-only operation")
        if "path_mutation" in modes and not 1 <= len(node.atom.write_roots) <= 8:
            raise ValueError("contract path mutation requires one to eight roots")
        if "path_mutation" in modes and not (
            node.atom.minimum_actions <= node.atom.action_budget <= 12
        ):
            raise ValueError(
                "contract mutation transaction has an invalid action budget"
            )
        if "exclusive_side_effect" in modes and not node.atom.exclusive:
            raise ValueError(
                "contract external side effect requires projected exclusivity"
            )

    mutations = [
        node for node in patch.new_nodes if node.atom.atom_kind == "mutate"
    ]
    verifiers = [
        node for node in patch.new_nodes if node.atom.atom_kind == "verify"
    ]
    node_by_id = {
        **existing_nodes,
        **{node.node_id: node for node in patch.new_nodes},
    }
    statuses = {node_id: "pending" for node_id in existing_nodes}
    capsule_statuses: dict[str, str] = {}
    for capsule in capsules:
        if capsule.node_id not in existing_nodes:
            continue
        previous = capsule_statuses.get(capsule.node_id)
        if previous is not None and previous != capsule.node_status:
            raise ValueError(
                "result capsules disagree on an existing node status"
            )
        capsule_statuses[capsule.node_id] = capsule.node_status
    statuses.update(capsule_statuses)
    if existing_node_statuses is not None:
        supplied = {
            str(node_id): str(status)
            for node_id, status in existing_node_statuses.items()
        }
        unknown_statuses = set(supplied) - set(existing_nodes)
        if unknown_statuses:
            raise ValueError(
                "existing node statuses reference unknown nodes: "
                f"{sorted(unknown_statuses)}"
            )
        invalid_statuses = {
            node_id: status
            for node_id, status in supplied.items()
            if status not in {"pending", "completed", "failed", "interrupted"}
        }
        if invalid_statuses:
            raise ValueError(
                f"existing node statuses are invalid: {invalid_statuses}"
            )
        capsule_mismatches = {
            node_id: {
                "status": supplied[node_id],
                "capsule_status": capsule_status,
            }
            for node_id, capsule_status in capsule_statuses.items()
            if node_id in supplied and supplied[node_id] != capsule_status
        }
        if capsule_mismatches:
            raise ValueError(
                "existing node status differs from its result capsule: "
                f"{capsule_mismatches}"
            )
        statuses.update(supplied)

    if patch.base_revision > 0:
        blocked_dependencies = {
            node.node_id: {
                dependency: statuses[dependency]
                for dependency in node.atom.depends_on
                if dependency in existing_nodes
                and statuses[dependency] != "completed"
            }
            for node in patch.new_nodes
        }
        blocked_dependencies = {
            node_id: dependencies
            for node_id, dependencies in blocked_dependencies.items()
            if dependencies
        }
        if blocked_dependencies:
            raise ValueError(
                "correction nodes depend on non-completed existing nodes and "
                f"can never become ready: {blocked_dependencies}"
            )

    def descends_from(node_id: str, ancestor_id: str) -> bool:
        pending = [node_id]
        visited: set[str] = set()
        while pending:
            current = pending.pop()
            if current in visited:
                continue
            visited.add(current)
            node = node_by_id.get(current)
            if node is None:
                continue
            if ancestor_id in node.atom.depends_on:
                return True
            pending.extend(node.atom.depends_on)
        return False

    for mutation in mutations:
        if not any(
            descends_from(verifier.node_id, mutation.node_id)
            and (
                not mutation.atom.write_roots
                or all(
                    any(
                        contract_scope_covers(read_root, write_root)
                        for read_root in verifier.atom.read_roots
                    )
                    for write_root in mutation.atom.write_roots
                )
            )
            for verifier in verifiers
        ):
            raise ValueError(
                f"contract mutation {mutation.node_id} requires a downstream "
                "verify node over its write scope"
            )

    validate_content_mutation_dependencies(
        patch,
        existing_nodes=existing_nodes,
        result_capsules=capsules,
        visible_paths=tuple(
            str(item.get("path") or "")
            for item in workspace_manifest.get("entries") or ()
            if isinstance(item, Mapping) and str(item.get("path") or "")
        ),
    )

    finalizers = [
        node for node in patch.new_nodes if node.atom.role == AtomRole.FINALIZER
    ]
    work = [node for node in patch.new_nodes if node.atom.role == AtomRole.WORK]
    all_obligations = {
        **existing_obligations,
        **{item.obligation_id: item for item in patch.new_obligations},
    }
    required_ids = set(all_obligations)
    presentation_ids = {
        obligation_id
        for obligation_id, obligation in all_obligations.items()
        if obligation.phase == ObligationPhase.FINAL_PRESENTATION
    }
    invalid_work_bindings = {
        node.node_id: sorted(set(node.obligation_ids) & presentation_ids)
        for node in work
        if set(node.obligation_ids) & presentation_ids
    }
    if invalid_work_bindings:
        raise ValueError(
            "work nodes cannot bind final-presentation obligations: "
            f"{invalid_work_bindings}"
        )
    if patch.base_revision == 0:
        if not patch.new_obligations:
            raise ValueError("initial contract patch requires immutable obligations")
        if not work or len(finalizers) != 1:
            raise ValueError(
                "initial contract patch requires work and one frozen finalizer"
            )
        finalizer = finalizers[0]
        if not required_ids <= set(finalizer.obligation_ids):
            raise ValueError("initial finalizer must bind every obligation")
        initial_work_ids = {node.node_id for node in work}
        if not initial_work_ids <= set(finalizer.atom.depends_on):
            raise ValueError(
                "initial finalizer must depend on every initial work node"
            )
    elif finalizer_required:
        if work or len(finalizers) != 1:
            raise ValueError(
                "replacement finalizer patch must contain one finalizer only"
            )
        finalizer = finalizers[0]
        if not required_ids <= set(finalizer.obligation_ids):
            raise ValueError("replacement finalizer must bind every obligation")
        completed_work_ids = {
            node_id
            for node_id, node in existing_nodes.items()
            if node.atom.role == AtomRole.WORK
            and statuses.get(node_id) == "completed"
        }
        if not completed_work_ids <= set(finalizer.atom.depends_on):
            raise ValueError(
                "replacement finalizer must depend on every completed work node"
            )
    elif finalizers:
        raise ValueError(
            "correction patch cannot add a finalizer before evidence passes"
        )

    all_work_ids = {
        node_id
        for node_id, node in node_by_id.items()
        if node.atom.role == AtomRole.WORK
    }
    invalid_finalizer_dependencies = {
        node.node_id: sorted(set(node.atom.depends_on) - all_work_ids)
        for node in finalizers
        if set(node.atom.depends_on) - all_work_ids
    }
    if invalid_finalizer_dependencies:
        raise ValueError(
            "finalizers may depend only on work nodes: "
            f"{invalid_finalizer_dependencies}"
        )


__all__ = [
    "contract_scope_covers",
    "contract_scopes_overlap",
    "validate_contract_patch_semantics",
]
