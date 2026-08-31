from __future__ import annotations

import threading

import pytest

from rwkv_lh.atom_execution import (
    ATOM_EXECUTION_POLICY_KEY,
    AtomExecutionBinding,
    AtomExecutionContract,
)
from rwkv_lh.capability_projection import (
    CAPABILITY_PROJECTION_VERSION,
    project_contract_capabilities,
)
from rwkv_lh.harness import ActionHarness, ScopeViolation
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.parallel_atoms import PATH_MUTATION_OPERATIONS, ScopedAtomHarness
from rwkv_lh.retrieval import (
    FrozenRetrievalBackend,
    NetworkPolicy,
    NetworkPolicyMode,
    build_retrieval_actions,
)
from rwkv_lh.schema import GoalState, TaskAction
from rwkv_lh.supervisor import CAPABILITY_ATOM_SCHEMA_VERSION, SupervisorAtom


REQUEST = "Inspect public evidence or update scoped result.txt and verify it."


def harness() -> ActionHarness:
    actions = build_retrieval_actions(
        backend=FrozenRetrievalBackend({}),
        network_policy=NetworkPolicy(NetworkPolicyMode.AUTO_PUBLIC),
        provenance_resolver=lambda _goal, _tool, _arguments: {},
    )
    return ActionHarness(sandbox_commands=False, actions=actions)


def catalog(selected: ActionHarness) -> tuple[dict, ...]:
    values = []
    for item in selected.g1i_tool_definitions():
        name = str(item["name"])
        definition = selected.definition(name)
        values.append(
            {
                "name": name,
                "scope_mode": (
                    "read_only"
                    if not definition.side_effect
                    else "path_mutation"
                    if name in PATH_MUTATION_OPERATIONS
                    else "exclusive_side_effect"
                ),
                "capability_class": definition.capability_class,
                "network_access": definition.network_access,
                "data_boundary": definition.data_boundary,
                "side_effect_class": definition.side_effect_class,
            }
        )
    return tuple(values)


def test_public_investigation_projects_choices_without_planner_tool_names() -> None:
    projection = project_contract_capabilities(
        atom_kind="investigate",
        effect_ceiling="public_read_only",
        role="work",
        operation_catalog=catalog(harness()),
    )

    assert set(projection.operations) == {
        "file_digest",
        "list_directory",
        "search_text",
        "read_file",
        "read_json",
        "bind_evidence",
        "web_search",
        "connector_lookup",
        "calculator",
        "date_diff",
        "current_time",
    }
    assert not set(projection.operations) & PATH_MUTATION_OPERATIONS
    assert "check_command" not in projection.operations
    assert "run_command" not in projection.operations
    assert projection.source == CAPABILITY_PROJECTION_VERSION
    assert projection.minimum_actions == 1
    assert not projection.exclusive
    assert projection.operations[:2] == ("web_search", "connector_lookup")


def test_offline_policy_removes_network_tools_from_authoritative_menu() -> None:
    actions = build_retrieval_actions(
        backend=FrozenRetrievalBackend({}),
        network_policy=NetworkPolicy(NetworkPolicyMode.OFFLINE),
        provenance_resolver=lambda _goal, _tool, _arguments: {},
    )
    selected = ActionHarness(sandbox_commands=False, actions=actions)
    names = {item["name"] for item in selected.g1i_tool_definitions()}

    assert "web_search" not in names
    assert "connector_lookup" not in names
    assert {"calculator", "date_diff", "current_time"} <= names


def test_workspace_wide_write_scope_is_mechanically_exclusive() -> None:
    projection = project_contract_capabilities(
        atom_kind="mutate",
        effect_ceiling="workspace_mutation",
        role="work",
        operation_catalog=catalog(harness()),
        write_roots=(".",),
    )

    assert projection.exclusive


def test_mutation_projection_reserves_one_action_per_write_root() -> None:
    projection = project_contract_capabilities(
        atom_kind="mutate",
        effect_ceiling="workspace_mutation",
        role="work",
        operation_catalog=catalog(harness()),
        write_roots=("result.txt", "README.md"),
    )

    assert projection.minimum_actions == 2
    with pytest.raises(ValueError, match="minimum_actions"):
        SupervisorAtom.create(
            immutable_request=REQUEST,
            atom_id="infeasible-two-root-writer",
            role="work",
            objective="Update result.txt and README.md.",
            request_clauses=(REQUEST,),
            write_roots=("result.txt", "README.md"),
            exclusive=projection.exclusive,
            allowed_operations=projection.operations,
            action_budget=1,
            completion_checks=("Both declared roots are complete.",),
            atom_kind=projection.atom_kind,
            effect_ceiling=projection.effect_ceiling,
            evidence_kinds=("artifacts",),
            freshness="current_workspace",
            source_preferences=("workspace",),
            operation_allowset_source=projection.source,
            minimum_actions=projection.minimum_actions,
        )


def test_capability_atoms_allow_twelve_actions_but_legacy_atoms_remain_at_four() -> None:
    projection = project_contract_capabilities(
        atom_kind="mutate",
        effect_ceiling="workspace_mutation",
        role="work",
        operation_catalog=catalog(harness()),
        write_roots=("result.txt",),
    )
    capability = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="bounded-capability",
        role="work",
        objective="Update scoped result.txt and verify it.",
        request_clauses=(REQUEST,),
        write_roots=("result.txt",),
        exclusive=projection.exclusive,
        allowed_operations=projection.operations,
        action_budget=12,
        completion_checks=("result.txt is complete.",),
        atom_kind=projection.atom_kind,
        effect_ceiling=projection.effect_ceiling,
        evidence_kinds=("artifact",),
        freshness="current_workspace",
        source_preferences=("workspace",),
        operation_allowset_source=projection.source,
        minimum_actions=projection.minimum_actions,
    )

    assert capability.action_budget == 12
    with pytest.raises(ValueError, match="between 1 and 12"):
        SupervisorAtom.create(
            immutable_request=REQUEST,
            atom_id="oversized-capability",
            role="work",
            objective="Update scoped result.txt and verify it.",
            request_clauses=(REQUEST,),
            write_roots=("result.txt",),
            exclusive=projection.exclusive,
            allowed_operations=projection.operations,
            action_budget=13,
            completion_checks=("result.txt is complete.",),
            atom_kind=projection.atom_kind,
            effect_ceiling=projection.effect_ceiling,
            evidence_kinds=("artifact",),
            freshness="current_workspace",
            source_preferences=("workspace",),
            operation_allowset_source=projection.source,
            minimum_actions=projection.minimum_actions,
        )
    with pytest.raises(ValueError, match="between 1 and 4"):
        SupervisorAtom.create(
            immutable_request=REQUEST,
            atom_id="oversized-legacy",
            role="work",
            objective="Update scoped result.txt and verify it.",
            request_clauses=(REQUEST,),
            write_roots=("result.txt",),
            allowed_operations=("write_file",),
            action_budget=5,
            completion_checks=("result.txt is complete.",),
        )


def test_read_only_source_choice_belongs_to_rwkv_not_planner_ceiling() -> None:
    selected = catalog(harness())
    local = project_contract_capabilities(
        atom_kind="verify",
        effect_ceiling="local_read_only",
        role="work",
        operation_catalog=selected,
    )
    mutation = project_contract_capabilities(
        atom_kind="mutate",
        effect_ceiling="workspace_mutation",
        role="work",
        operation_catalog=selected,
    )
    process = project_contract_capabilities(
        atom_kind="mutate",
        effect_ceiling="local_process_mutation",
        role="work",
        operation_catalog=selected,
    )
    finalizer = project_contract_capabilities(
        atom_kind="synthesize",
        effect_ceiling="local_read_only",
        role="finalizer",
        operation_catalog=selected,
    )

    assert "web_search" in local.operations
    assert "connector_lookup" in local.operations
    assert "write_file" not in local.operations
    assert "write_file" in mutation.operations
    assert "run_command" not in mutation.operations
    assert "run_command" in process.operations
    assert process.exclusive
    assert set(finalizer.operations) == {
        "file_digest",
        "list_directory",
        "search_text",
        "read_file",
        "read_json",
        "bind_evidence",
    }
    assert finalizer.minimum_actions == 1


@pytest.mark.parametrize(
    "projection_source",
    (
        "controller_capability_projection.v1",
        "controller_capability_projection.v2",
    ),
)
def test_legacy_projection_source_remains_readable(projection_source: str) -> None:
    atom = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="legacy-v1-projection",
        role="work",
        objective="Inspect evidence under the historical projection contract.",
        request_clauses=(REQUEST,),
        allowed_operations=("read_file",),
        action_budget=1,
        completion_checks=("Evidence is observed.",),
        atom_kind="investigate",
        effect_ceiling="local_read_only",
        evidence_kinds=("file",),
        freshness="current_workspace",
        source_preferences=("workspace",),
        operation_allowset_source=projection_source,
        minimum_actions=1,
    )

    assert SupervisorAtom.from_dict(atom.to_dict(), immutable_request=REQUEST) == atom


def test_frozen_v2_two_root_budget_one_atom_remains_recoverable() -> None:
    atom = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="frozen-v2-two-root",
        role="work",
        objective="Update result.txt and README.md.",
        request_clauses=(REQUEST,),
        write_roots=("result.txt", "README.md"),
        allowed_operations=("write_file",),
        action_budget=1,
        completion_checks=("The historical atom is recoverable.",),
        atom_kind="mutate",
        effect_ceiling="workspace_mutation",
        evidence_kinds=("artifacts",),
        freshness="current_workspace",
        source_preferences=("workspace",),
        operation_allowset_source="controller_capability_projection.v2",
        minimum_actions=1,
    )

    assert SupervisorAtom.from_dict(atom.to_dict(), immutable_request=REQUEST) == atom


def test_abstract_source_preferences_rank_without_deleting_rwkv_choices() -> None:
    selected = catalog(harness())
    structured = project_contract_capabilities(
        atom_kind="investigate",
        effect_ceiling="public_read_only",
        role="work",
        operation_catalog=selected,
        source_preferences=("structured_registry",),
    )
    workspace_file = project_contract_capabilities(
        atom_kind="investigate",
        effect_ceiling="local_read_only",
        role="work",
        operation_catalog=selected,
        source_preferences=("workspace_file",),
    )

    assert structured.operations[0] == "connector_lookup"
    assert workspace_file.operations[0] == "read_file"
    assert set(structured.operations) == set(workspace_file.operations)

    atom = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="ranked-structured",
        role="work",
        objective="Inspect the current structured public record.",
        request_clauses=(REQUEST,),
        allowed_operations=structured.operations,
        action_budget=1,
        completion_checks=("The current record is observed.",),
        atom_kind=structured.atom_kind,
        effect_ceiling=structured.effect_ceiling,
        evidence_kinds=("current_record",),
        freshness="current_at_run_time",
        source_preferences=("structured_registry",),
        operation_allowset_source=structured.source,
        minimum_actions=structured.minimum_actions,
    )
    scoped = ScopedAtomHarness(
        harness(),
        AtomExecutionContract.create(
            immutable_request=REQUEST,
            atom=atom,
        ),
        threading.RLock(),
    )
    model = LongHorizonModel(harness=scoped)

    assert [item["name"] for item in model.action_definitions()] == list(
        structured.operations
    )


@pytest.mark.parametrize(
    ("kind", "ceiling", "role"),
    [
        ("investigate", "workspace_mutation", "work"),
        ("mutate", "public_read_only", "work"),
        ("synthesize", "public_read_only", "finalizer"),
        ("investigate", "local_read_only", "finalizer"),
    ],
)
def test_invalid_planner_kind_effect_combinations_fail_closed(
    kind: str,
    ceiling: str,
    role: str,
) -> None:
    with pytest.raises(ValueError):
        project_contract_capabilities(
            atom_kind=kind,
            effect_ceiling=ceiling,
            role=role,
            operation_catalog=catalog(harness()),
        )


def test_v2_atom_round_trip_records_controller_allowset_authority() -> None:
    projection = project_contract_capabilities(
        atom_kind="investigate",
        effect_ceiling="public_read_only",
        role="work",
        operation_catalog=catalog(harness()),
    )
    atom = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="research",
        role="work",
        objective="Inspect current public evidence and retain exact evidence.",
        request_clauses=(REQUEST,),
        read_roots=(".",),
        allowed_operations=projection.operations,
        action_budget=3,
        completion_checks=("Exact current evidence is observed.",),
        atom_kind=projection.atom_kind,
        effect_ceiling=projection.effect_ceiling,
        evidence_kinds=("exact_span", "source_object"),
        freshness="current_at_run_time",
        source_preferences=("primary", "structured"),
        operation_allowset_source=projection.source,
        minimum_actions=projection.minimum_actions,
    )

    assert atom.schema_version == CAPABILITY_ATOM_SCHEMA_VERSION
    assert len(atom.allowed_operations) > 4
    assert SupervisorAtom.from_dict(atom.to_dict(), immutable_request=REQUEST) == atom
    assert atom.to_dict()["operation_allowset_source"] == (
        CAPABILITY_PROJECTION_VERSION
    )


def test_exclusive_process_atom_still_enforces_declared_path_roots(
    tmp_path,
) -> None:
    selected_harness = harness()
    projection = project_contract_capabilities(
        atom_kind="mutate",
        effect_ceiling="local_process_mutation",
        role="work",
        operation_catalog=catalog(selected_harness),
    )
    atom = SupervisorAtom.create(
        immutable_request=REQUEST,
        atom_id="process",
        role="work",
        objective="Update scoped result.txt and verify it.",
        request_clauses=(REQUEST,),
        write_roots=("result.txt",),
        exclusive=projection.exclusive,
        allowed_operations=projection.operations,
        action_budget=2,
        completion_checks=("result.txt is verified.",),
        atom_kind=projection.atom_kind,
        effect_ceiling=projection.effect_ceiling,
        evidence_kinds=("artifact",),
        freshness="current_workspace",
        source_preferences=("workspace",),
        operation_allowset_source=projection.source,
        minimum_actions=projection.minimum_actions,
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    contract = AtomExecutionContract.create(
        immutable_request=REQUEST,
        atom=atom,
    )
    goal = GoalState.create(
        request=atom.objective,
        constraints=(),
        workspace_root=workspace,
        runtime_policy={
            ATOM_EXECUTION_POLICY_KEY: AtomExecutionBinding(
                contract=contract
            ).to_dict()
        },
    )
    scoped = ScopedAtomHarness(
        selected_harness,
        contract,
        threading.RLock(),
    )

    with pytest.raises(ScopeViolation, match="outside write_roots"):
        scoped.execute(
            TaskAction(
                "write_file",
                {"path": "outside.txt", "content": "forbidden"},
            ),
            goal,
        )
