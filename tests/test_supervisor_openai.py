from __future__ import annotations

import json
import hashlib
import os
import re
from dataclasses import replace

import requests
import pytest

from rwkv_lh.contract_graph import (
    ObligationPhase,
    ContractPlanRequest,
    ContractReviewRequest,
    ResultCapsule,
)
from rwkv_lh.goal_loop_protocol import GoalPlanRequest, GoalStageReviewRequest
from rwkv_lh.supervisor import (
    SupervisorDirectiveRequest,
    SupervisorPlanRequest,
    SupervisorReviewRequest,
    SupervisorStageRequest,
)
from rwkv_lh.supervisor_openai import (
    CONTRACT_PLAN_RESPONSE_SCHEMA,
    OpenAICompatibleSupervisorClient,
    SupervisorAPISettings,
    SupervisorProtocolError,
    SupervisorTransportError,
    _decode_supervisor_json_content,
    supervisor_policy_from_env,
)


class FakeResponse:
    def __init__(self, payload: dict, status_code: int = 200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    trust_env = False

    def __init__(self, responses: list[FakeResponse | BaseException]):
        self.responses = list(responses)
        self.posts: list[dict] = []
        self.closed = False

    def post(self, url, **kwargs):
        self.posts.append({"url": url, **kwargs})
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response

    def get(self, url, **kwargs):
        del url, kwargs
        return FakeResponse({"data": [{"id": "gpt-test"}]})

    def close(self):
        self.closed = True


def response(content: dict, *, model: str = "gpt-test") -> FakeResponse:
    return FakeResponse(
        {
            "model": model,
            "choices": [
                {
                    "message": {"role": "assistant", "content": json.dumps(content)},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
        }
    )


def contract_operation_catalog() -> tuple[dict, ...]:
    return (
        {
            "name": "write_file",
            "description": "Write a file.",
            "scope_mode": "path_mutation",
            "capability_class": "local.workspace_mutation",
            "network_access": "none",
            "data_boundary": "workspace",
            "side_effect_class": "workspace_mutation",
        },
        {
            "name": "read_file",
            "description": "Read a file.",
            "scope_mode": "read_only",
            "capability_class": "local.workspace_read",
            "network_access": "none",
            "data_boundary": "workspace",
            "side_effect_class": "read_only",
        },
    )


def contract_work_atom_branches(schema: dict) -> list[dict]:
    atom_schema = schema["properties"]["new_nodes"]["items"]["properties"][
        "atom"
    ]
    return atom_schema["anyOf"]


def nested_schema_keys(value) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(str(key) for key in value)
        for item in value.values():
            keys.update(nested_schema_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(nested_schema_keys(item))
    return keys


def v2_atom(
    *,
    atom_id: str,
    role: str,
    objective: str,
    depends_on: list[str],
    read_roots: list[str],
    write_roots: list[str],
    kind: str,
    effect_ceiling: str,
    action_budget: int = 1,
) -> dict:
    return {
        "atom_id": atom_id,
        "role": role,
        "kind": kind,
        "effect_ceiling": effect_ceiling,
        "objective": objective,
        "depends_on": depends_on,
        "read_roots": read_roots,
        "write_roots": write_roots,
        "evidence_requirements": {
            "kinds": ["exact_operation_result"],
            "freshness": "current_workspace",
            "source_preferences": ["workspace"],
        },
        "action_budget": action_budget,
    }


def contract_plan_value() -> dict:
    return {
        "summary": "Compile a typed result contract.",
        "new_obligations": [
            {
                "obligation_id": "OBL-result",
                "predicate": "result.txt contains exact text ok.",
                "evidence_kinds": ["read_file"],
                "assertions": [
                    {
                        "assertion_id": "ASSERT-result-text",
                        "kind": "text_exact",
                        "target_path": "result.txt",
                        "target_pointer": "",
                        "sources": [],
                        "expected": "ok",
                        "keys": [],
                        "order": "",
                        "algorithm": "",
                    }
                ],
            }
        ],
        "new_nodes": [
            {
                "obligation_ids": ["OBL-result"],
                "atom": v2_atom(
                    atom_id="NODE-write",
                    role="work",
                    objective="Create result.txt containing exact text ok.",
                    depends_on=[],
                    read_roots=[],
                    write_roots=["result.txt"],
                    kind="mutate",
                    effect_ceiling="workspace_mutation",
                ),
            },
            {
                "obligation_ids": ["OBL-result"],
                "atom": v2_atom(
                    atom_id="NODE-verify",
                    role="work",
                    objective="Read result.txt and verify its exact content.",
                    depends_on=["NODE-write"],
                    read_roots=["result.txt"],
                    write_roots=[],
                    kind="verify",
                    effect_ceiling="local_read_only",
                ),
            },
            {
                "obligation_ids": ["OBL-result"],
                "atom": v2_atom(
                    atom_id="NODE-final",
                    role="finalizer",
                    objective="Read result.txt and report completion.",
                    depends_on=["NODE-verify"],
                    read_roots=["result.txt"],
                    write_roots=[],
                    kind="synthesize",
                    effect_ceiling="local_read_only",
                ),
            },
        ],
    }


def lean_contract_plan_value() -> dict:
    """Return the production Planner payload without Controller-owned fields."""

    value = contract_plan_value()
    for obligation in value["new_obligations"]:
        obligation.pop("phase", None)
        obligation.pop("assertions", None)
    for node in value["new_nodes"]:
        atom = node["atom"]
        atom.pop("evidence_requirements", None)
        atom.pop("action_budget", None)
    return value


def test_contract_compiler_uses_assertion_structure_to_bound_presentation_phase():
    immutable_request = (
        "Create result.txt containing exact text ok, then respond concisely."
    )
    value = contract_plan_value()
    value["new_obligations"][0]["phase"] = "final_presentation"
    value["new_obligations"].append(
        {
            "obligation_id": "OBL-presentation",
            "predicate": "The final answer is concise.",
            "phase": "final_presentation",
            "evidence_kinds": [],
            "assertions": [
                {
                    "assertion_id": "ASSERT-presentation",
                    "kind": "semantic_review",
                    "target_path": "",
                    "target_pointer": "",
                    "sources": [],
                    "expected": "",
                    "keys": [],
                    "order": "",
                    "algorithm": "",
                }
            ],
        }
    )
    value["new_nodes"][-1]["obligation_ids"] = [
        "OBL-result",
        "OBL-presentation",
    ]
    request = ContractPlanRequest(
        run_id="RUN-PHASE-COMPILER",
        request=immutable_request,
        request_digest="digest-phase-compiler",
        graph_revision=0,
        obligations=(),
        nodes=(),
        latest_review=None,
        result_capsules=(),
        available_operations=contract_operation_catalog(),
        workspace_manifest={"entries": []},
    )

    patch = OpenAICompatibleSupervisorClient._contract_patch_from_value(
        request, value
    )

    by_id = {item.obligation_id: item for item in patch.new_obligations}
    assert by_id["OBL-result"].phase == ObligationPhase.EXECUTION_EVIDENCE
    assert by_id["OBL-result"].assertions
    assert by_id["OBL-presentation"].phase == ObligationPhase.FINAL_PRESENTATION
    assert by_id["OBL-presentation"].assertions == ()


def test_contract_compiler_synthesizes_missing_structural_finalizer():
    immutable_request = "Create result.txt containing exact text ok."
    value = contract_plan_value()
    value["new_nodes"] = value["new_nodes"][:-1]
    request = ContractPlanRequest(
        run_id="RUN-AUTO-FINALIZER",
        request=immutable_request,
        request_digest="digest-auto-finalizer",
        graph_revision=0,
        obligations=(),
        nodes=(),
        latest_review=None,
        result_capsules=(),
        available_operations=contract_operation_catalog(),
        workspace_manifest={"entries": []},
    )

    patch = OpenAICompatibleSupervisorClient._contract_patch_from_value(
        request, value
    )

    work = [node for node in patch.new_nodes if node.atom.role.value == "work"]
    finalizers = [
        node for node in patch.new_nodes if node.atom.role.value == "finalizer"
    ]
    assert [node.node_id for node in work] == ["NODE-write", "NODE-verify"]
    assert len(finalizers) == 1
    finalizer = finalizers[0]
    assert finalizer.node_id == "NODE-frozen-finalizer"
    assert finalizer.obligation_ids == ("OBL-result",)
    assert finalizer.atom.depends_on == ("NODE-write", "NODE-verify")
    assert finalizer.atom.write_roots == ()
    assert finalizer.atom.read_roots == (".",)
    assert finalizer.atom.allowed_operations
    assert finalizer.atom.operation_allowset_source
    assert finalizer.atom.minimum_actions == 1


def test_contract_plan_schema_assigns_finalizer_structure_to_controller():
    request = ContractPlanRequest(
        run_id="RUN-CONTROLLER-FINALIZER",
        request="Create result.txt containing exact text ok.",
        request_digest="digest-controller-finalizer",
        graph_revision=0,
        obligations=(),
        nodes=(),
        latest_review=None,
        result_capsules=(),
        available_operations=contract_operation_catalog(),
        workspace_manifest={"entries": []},
    )

    schema = OpenAICompatibleSupervisorClient._contract_plan_schema(request)
    nodes = schema["properties"]["new_nodes"]
    branches = contract_work_atom_branches(schema)
    atom_properties = [branch["properties"] for branch in branches]

    assert nodes["minItems"] == 1
    assert [item["kind"]["enum"] for item in atom_properties] == [
        ["investigate"],
        ["mutate"],
        ["verify"],
    ]
    assert all(item["role"]["enum"] == ["work"] for item in atom_properties)
    assert [item["effect_ceiling"]["enum"] for item in atom_properties] == [
        ["local_read_only", "public_read_only", "local_process_read_only"],
        ["workspace_mutation", "local_process_mutation"],
        ["local_read_only", "public_read_only", "local_process_read_only"],
    ]
    assert all(
        "latest successful read_file/read_json observation"
        in item["depends_on"]["description"]
        for item in atom_properties
    )
    assert not ({"allOf", "if", "then", "else"} & nested_schema_keys(schema))

    correction = OpenAICompatibleSupervisorClient._contract_plan_schema(
        replace(
            request,
            graph_revision=1,
            obligations=({"obligation_id": "OBL-result"},),
        )
    )
    correction_atoms = [
        branch["properties"] for branch in contract_work_atom_branches(correction)
    ]
    assert all(item["role"]["enum"] == ["work"] for item in correction_atoms)
    assert [item["kind"]["enum"] for item in correction_atoms] == [
        ["investigate"],
        ["mutate"],
        ["verify"],
    ]
    correction_pattern = correction_atoms[0]["atom_id"]["pattern"]
    assert all(
        item["atom_id"]["pattern"] == correction_pattern
        for item in correction_atoms
    )
    assert re.fullmatch(correction_pattern, "NODE-write") is None
    correction_namespace = (
        OpenAICompatibleSupervisorClient._contract_plan_atom_id_namespace(
            replace(
                request,
                graph_revision=1,
                obligations=({"obligation_id": "OBL-result"},),
            )
        )
    )
    assert re.fullmatch(correction_pattern, correction_namespace + "repair")

    next_revision = replace(
        request,
        graph_revision=2,
        obligations=({"obligation_id": "OBL-result"},),
    )
    assert (
        OpenAICompatibleSupervisorClient._contract_plan_atom_id_namespace(
            next_revision
        )
        != correction_namespace
    )

    finalizer = OpenAICompatibleSupervisorClient._contract_plan_schema(
        replace(
            request,
            graph_revision=1,
            obligations=({"obligation_id": "OBL-result"},),
            finalizer_required=True,
        )
    )
    finalizer_nodes = finalizer["properties"]["new_nodes"]
    finalizer_atom = finalizer_nodes["items"]["properties"]["atom"][
        "properties"
    ]
    assert finalizer_nodes["minItems"] == 1
    assert finalizer_nodes["maxItems"] == 1
    assert finalizer_atom["role"]["enum"] == ["finalizer"]
    assert finalizer_atom["kind"]["enum"] == ["synthesize"]
    assert finalizer_atom["effect_ceiling"]["enum"] == ["local_read_only"]


def test_contract_plan_namespace_avoids_existing_prefix_and_auto_verifier_id():
    request = ContractPlanRequest(
        run_id="RUN-FRESH-NAMESPACE",
        request="Repair result.txt and verify it.",
        request_digest="digest-fresh-namespace",
        graph_revision=1,
        obligations=({"obligation_id": "OBL-result"},),
        nodes=(),
        latest_review=None,
        result_capsules=(),
        available_operations=contract_operation_catalog(),
        workspace_manifest={"entries": [{"path": "result.txt"}]},
    )
    first_namespace = (
        OpenAICompatibleSupervisorClient._contract_plan_atom_id_namespace(request)
    )
    occupied_request = replace(
        request,
        nodes=({"node_id": first_namespace + "existing"},),
    )
    selected_namespace = (
        OpenAICompatibleSupervisorClient._contract_plan_atom_id_namespace(
            occupied_request
        )
    )
    assert selected_namespace != first_namespace
    assert not (first_namespace + "existing").startswith(selected_namespace)

    mutation_id = selected_namespace + "mutate"
    suffix = hashlib.sha256(
        f"{request.request_digest}\0{mutation_id}".encode("utf-8")
    ).hexdigest()[:12]
    auto_id = f"NODE-auto-verify-{suffix}"
    value = {
        "new_nodes": [
            {
                "obligation_ids": ["OBL-result"],
                "atom": {
                    "atom_id": mutation_id,
                    "role": "work",
                    "kind": "mutate",
                    "effect_ceiling": "workspace_mutation",
                    "objective": "Repair result.txt.",
                    "depends_on": [],
                    "read_roots": ["result.txt"],
                    "write_roots": ["result.txt"],
                },
            }
        ]
    }
    normalized = (
        OpenAICompatibleSupervisorClient._contract_nodes_with_mechanical_verification(
            replace(request, nodes=({"node_id": auto_id},)), value
        )
    )
    identifiers = [str(item["atom"]["atom_id"]) for item in normalized]
    assert auto_id not in identifiers
    assert f"{auto_id}-2" in identifiers


def test_contract_adapter_compiles_feasible_budget_for_every_write_root():
    immutable_request = "Create result.txt and README.md."
    value = lean_contract_plan_value()
    value["new_nodes"][0]["atom"]["write_roots"] = [
        "result.txt",
        "README.md",
    ]
    value["new_nodes"][1]["atom"]["read_roots"] = [
        "result.txt",
        "README.md",
    ]
    value["new_nodes"][2]["atom"]["read_roots"] = [
        "result.txt",
        "README.md",
    ]
    audit: list[dict] = []
    client = OpenAICompatibleSupervisorClient(
        settings(),
        session=FakeSession([response(value)]),
        audit_hook=audit.append,
    )

    patch = client.plan_contract_graph(
        ContractPlanRequest(
            run_id="RUN-PROJECT-BUDGET",
            request=immutable_request,
            request_digest="digest-project-budget",
            graph_revision=0,
            obligations=(),
            nodes=(),
            latest_review=None,
            result_capsules=(),
            available_operations=contract_operation_catalog(),
            workspace_manifest={"entries": []},
        )
    )

    writer = next(node for node in patch.new_nodes if node.node_id == "NODE-write")
    assert writer.atom.minimum_actions == 2
    assert writer.atom.action_budget == 4
    normalized = [
        item
        for item in audit
        if item.get("normalization")
        == "compiled_mechanical_atom_fields"
    ]
    by_id = {item["atom_id"]: item for item in normalized[0]["nodes"]}
    assert by_id["NODE-write"]["projected_action_budget"] == 4
    assert by_id["NODE-write"]["projected_minimum_actions"] == 2


def test_contract_adapter_supports_eight_distinct_project_write_roots():
    roots = tuple(f"src/module_{index}.py" for index in range(8))
    immutable_request = "Create these files: " + ", ".join(roots) + "."
    value = lean_contract_plan_value()
    value["new_obligations"][0]["predicate"] = (
        "Every requested project file exists in the workspace."
    )
    value["new_nodes"][0]["atom"].update(
        {
            "objective": "Create every requested project file.",
            "write_roots": list(roots),
        }
    )
    value["new_nodes"][1]["atom"].update(
        {
            "objective": "Verify every requested project file.",
            "read_roots": [],
        }
    )
    value["new_nodes"][2]["atom"]["read_roots"] = list(roots)

    patch = OpenAICompatibleSupervisorClient._contract_patch_from_value(
        ContractPlanRequest(
            run_id="RUN-EIGHT-ROOTS",
            request=immutable_request,
            request_digest="digest-eight-roots",
            graph_revision=0,
            obligations=(),
            nodes=(),
            latest_review=None,
            result_capsules=(),
            available_operations=contract_operation_catalog(),
            workspace_manifest={"entries": []},
        ),
        value,
    )

    writer = next(node for node in patch.new_nodes if node.node_id == "NODE-write")
    verifier = next(node for node in patch.new_nodes if node.node_id == "NODE-verify")
    assert writer.atom.write_roots == roots
    assert writer.atom.minimum_actions == 8
    assert writer.atom.action_budget == 10
    assert verifier.atom.read_roots == roots


def test_controller_synthesizes_missing_mutation_verifier_without_reprompt():
    immutable_request = "Create result.txt containing exact text ok."
    incomplete = lean_contract_plan_value()
    incomplete["new_nodes"] = [
        node
        for node in incomplete["new_nodes"]
        if node["atom"]["atom_id"] != "NODE-verify"
    ]
    incomplete["new_nodes"][-1]["atom"]["depends_on"] = ["NODE-write"]
    fake = FakeSession([response(incomplete)])
    audit: list[dict] = []
    client = OpenAICompatibleSupervisorClient(
        settings(),
        session=fake,
        audit_hook=audit.append,
    )

    patch = client.plan_contract_graph(
        ContractPlanRequest(
            run_id="RUN-VERIFY-REPAIR",
            request=immutable_request,
            request_digest="digest-verify-repair",
            graph_revision=0,
            obligations=(),
            nodes=(),
            latest_review=None,
            result_capsules=(),
            available_operations=contract_operation_catalog(),
            workspace_manifest={"entries": []},
        )
    )

    synthesized = [
        node
        for node in patch.new_nodes
        if node.node_id.startswith("NODE-auto-verify-")
    ]
    assert len(synthesized) == 1
    assert synthesized[0].atom.depends_on == ("NODE-write",)
    assert synthesized[0].atom.read_roots == ("result.txt",)
    assert len(fake.posts) == 1
    normalized = [
        item
        for item in audit
        if item.get("normalization") == "synthesized_missing_safety_verifier"
    ]
    assert normalized[0]["node_ids"] == [synthesized[0].node_id]
    assert not any(
        item.get("type") == "supervisor_semantic_response_rejected"
        for item in audit
    )


def test_contract_correction_rewires_unreachable_existing_dependency():
    immutable_request = "Create result.txt containing exact text ok."
    request_digest = "digest-unreachable-correction"
    initial_request = ContractPlanRequest(
        run_id="RUN-UNREACHABLE-CORRECTION",
        request=immutable_request,
        request_digest=request_digest,
        graph_revision=0,
        obligations=(),
        nodes=(),
        latest_review=None,
        result_capsules=(),
        available_operations=contract_operation_catalog(),
        workspace_manifest={"entries": []},
    )
    initial_patch = OpenAICompatibleSupervisorClient._contract_patch_from_value(
        initial_request,
        contract_plan_value(),
    )
    correction_request = ContractPlanRequest(
        run_id="RUN-UNREACHABLE-CORRECTION",
        request=immutable_request,
        request_digest=request_digest,
        graph_revision=1,
        obligations=tuple(
            item.to_dict() for item in initial_patch.new_obligations
        ),
        nodes=tuple(item.to_dict() for item in initial_patch.new_nodes),
        latest_review={
            "verdicts": [
                {"obligation_id": "OBL-result", "status": "insufficient"}
            ]
        },
        result_capsules=(),
        available_operations=contract_operation_catalog(),
        workspace_manifest={"entries": [{"path": "result.txt"}]},
        node_statuses={
            node.node_id: (
                "interrupted" if node.node_id == "NODE-write" else "pending"
            )
            for node in initial_patch.new_nodes
        },
    )
    namespace = OpenAICompatibleSupervisorClient._contract_plan_atom_id_namespace(
        correction_request
    )

    def correction(depends_on: list[str]) -> dict:
        return {
            "summary": "Inspect the current artifact before replanning work.",
            "new_obligations": [],
            "new_nodes": [
                {
                    "obligation_ids": ["OBL-result"],
                    "atom": {
                        "atom_id": namespace + "inspect",
                        "role": "work",
                        "kind": "investigate",
                        "effect_ceiling": "local_read_only",
                        "objective": "Inspect the current result.txt content.",
                        "depends_on": depends_on,
                        "read_roots": ["result.txt"],
                        "write_roots": [],
                    },
                }
            ],
        }

    fake = FakeSession(
        [
            response(correction(["NODE-write"])),
            response(correction([])),
        ]
    )
    audit: list[dict] = []
    client = OpenAICompatibleSupervisorClient(
        settings(),
        session=fake,
        audit_hook=audit.append,
    )

    patch = client.plan_contract_graph(correction_request)

    assert patch.new_nodes[0].atom.depends_on == ()
    assert len(fake.posts) == 1
    assert any(
        item.get("type") == "supervisor_contract_plan_normalized"
        and item.get("normalization")
        == "rewired_unreachable_correction_dependencies"
        and item.get("controller_semantic_fields_generated") is False
        for item in audit
    )


def test_controller_propagates_every_mutation_write_root_to_verifier():
    immutable_request = "Create result.txt and README.md."
    value = lean_contract_plan_value()
    value["new_nodes"][0]["atom"]["write_roots"] = [
        "result.txt",
        "README.md",
    ]
    intermediate = {
        "obligation_ids": ["OBL-result"],
        "atom": {
            "atom_id": "NODE-inspect",
            "role": "work",
            "kind": "investigate",
            "effect_ceiling": "local_read_only",
            "objective": "Inspect the generated project structure.",
            "depends_on": ["NODE-write"],
            "read_roots": ["result.txt"],
            "write_roots": [],
        },
    }
    value["new_nodes"].insert(1, intermediate)
    value["new_nodes"][2]["atom"]["depends_on"] = ["NODE-inspect"]

    patch = OpenAICompatibleSupervisorClient._contract_patch_from_value(
        ContractPlanRequest(
            run_id="RUN-VERIFY-ALL-ROOTS",
            request=immutable_request,
            request_digest="digest-verify-all-roots",
            graph_revision=0,
            obligations=(),
            nodes=(),
            latest_review=None,
            result_capsules=(),
            available_operations=contract_operation_catalog(),
            workspace_manifest={"entries": []},
        ),
        value,
    )

    verifier = next(node for node in patch.new_nodes if node.node_id == "NODE-verify")
    assert verifier.atom.depends_on == ("NODE-inspect",)
    assert verifier.atom.read_roots == ("result.txt", "README.md")


def test_controller_replaces_narrow_verifier_scope_with_full_mutation_scope():
    value = lean_contract_plan_value()
    value["new_nodes"][0]["atom"]["write_roots"] = ["src"]
    value["new_nodes"][1]["atom"]["read_roots"] = ["src/main.py"]
    request = ContractPlanRequest(
        run_id="RUN-NARROW-VERIFY",
        request="Update src and verify the complete result.",
        request_digest="digest-narrow-verify",
        graph_revision=0,
        obligations=(),
        nodes=(),
        latest_review=None,
        result_capsules=(),
        available_operations=contract_operation_catalog(),
        workspace_manifest={"entries": []},
    )

    normalized = OpenAICompatibleSupervisorClient._contract_nodes_with_mechanical_verification(
        request,
        value,
    )

    verifier = next(
        item for item in normalized if item["atom"]["atom_id"] == "NODE-verify"
    )
    assert verifier["atom"]["read_roots"] == ["src"]


def test_controller_compacts_many_converged_verifier_roots_losslessly():
    value = lean_contract_plan_value()
    mutations = []
    mutation_ids = []
    for group in range(3):
        atom_id = f"NODE-write-{group}"
        mutation_ids.append(atom_id)
        mutations.append(
            {
                "obligation_ids": ["OBL-result"],
                "atom": {
                    "atom_id": atom_id,
                    "role": "work",
                    "kind": "mutate",
                    "effect_ceiling": "workspace_mutation",
                    "objective": f"Create project file group {group}.",
                    "depends_on": [],
                    "read_roots": [],
                    "write_roots": [
                        f"group_{group}/file_{index}.txt" for index in range(6)
                    ],
                },
            }
        )
    verifier = value["new_nodes"][1]
    verifier["atom"]["depends_on"] = mutation_ids
    verifier["atom"]["read_roots"] = []
    value["new_nodes"] = [*mutations, verifier]
    request = ContractPlanRequest(
        run_id="RUN-COMPACT-VERIFY",
        request="Create and verify the complete multi-directory project.",
        request_digest="digest-compact-verify",
        graph_revision=0,
        obligations=(),
        nodes=(),
        latest_review=None,
        result_capsules=(),
        available_operations=contract_operation_catalog(),
        workspace_manifest={"entries": []},
    )

    normalized = OpenAICompatibleSupervisorClient._contract_nodes_with_mechanical_verification(
        request,
        value,
    )

    compiled_verifier = next(
        item for item in normalized if item["atom"]["atom_id"] == "NODE-verify"
    )
    assert compiled_verifier["atom"]["read_roots"] == ["."]


def settings() -> SupervisorAPISettings:
    return SupervisorAPISettings(
        base_url="https://supervisor.invalid/v1",
        api_key="test-secret-never-audited",
        model="gpt-test",
        retry_attempts=1,
        plan_cache_enabled=False,
    )


def test_goal_planner_returns_replaceable_steps_without_stealing_selector_role():
    value = {
        "add_stages": [
            {
                "stage": 1,
                "steps": [
                    {
                        "step_id": "S1",
                        "objective": "Inspect the current configuration.",
                        "depends_on": [],
                        "success_evidence": ["configuration content is observed"],
                        "read_roots": ["config.json"],
                        "write_roots": [],
                        "constraints": [],
                    }
                ],
            }
        ],
        "replace_stages": [],
        "discard_step_ids": [],
        "reason": "Start with one bounded observation.",
    }
    fake = FakeSession([response(value)])
    client = OpenAICompatibleSupervisorClient(settings(), session=fake)
    request = GoalPlanRequest(
        run_id="RUN-GOAL-PLAN",
        immutable_request="Inspect and correct config.json.",
        goal_digest="goal-digest",
        plan_revision=0,
        active_plan={"stages": []},
        latest_audit=None,
        workspace_manifest={"entries": [{"path": "config.json"}]},
    )

    patch = client.plan_goal_patch(request)

    assert patch.add_steps[0].allowed_operations == ()
    posted = fake.posts[0]["json"]
    payload = json.loads(posted["messages"][1]["content"])
    assert list(payload)[-1] == "current_requirement"
    assert payload["current_requirement"] == request.immutable_request
    step_schema = posted["response_format"]["json_schema"]["schema"][
        "properties"
    ]["add_stages"]["items"]["properties"]["steps"]["items"]
    assert "allowed_operations" not in step_schema["properties"]
    assert "stage" not in step_schema["properties"]
    assert set(step_schema["required"]) == set(step_schema["properties"])


def test_goal_planner_places_controller_semantic_repair_at_input_tail():
    value = {
        "add_stages": [
            {
                "stage": 2,
                "steps": [
                    {
                        "step_id": "S2",
                        "objective": "Read the current configuration.",
                        "depends_on": ["S1"],
                        "success_evidence": ["configuration content is observed"],
                        "read_roots": ["config.json"],
                        "write_roots": [],
                        "constraints": [],
                    }
                ],
            }
        ],
        "replace_stages": [],
        "discard_step_ids": [],
        "reason": "Use a fresh id and retain the completed dependency.",
    }
    fake = FakeSession([response(value)])
    client = OpenAICompatibleSupervisorClient(settings(), session=fake)
    request = GoalPlanRequest(
        run_id="RUN-GOAL-PLAN-REPAIR",
        immutable_request="Inspect and correct config.json.",
        goal_digest="goal-digest",
        plan_revision=1,
        active_plan={
            "stages": [
                {
                    "stage": 1,
                    "steps": [{"step_id": "S1", "status": "completed"}],
                }
            ]
        },
        latest_audit=None,
        workspace_manifest={"entries": [{"path": "config.json"}]},
        local_validation_repair={
            "attempt": 1,
            "previous_response_rejected": True,
            "error": "ValueError: Goal PlanPatch cannot reuse existing id S1",
            "instruction": "Return one fresh complete GoalPlanPatch.",
        },
    )

    client.plan_goal_patch(request)

    posted = fake.posts[0]["json"]
    payload = json.loads(posted["messages"][1]["content"])
    assert list(payload)[-1] == "local_validation_repair"
    assert payload["local_validation_repair"]["attempt"] == 1
    assert "cannot reuse existing id S1" in payload["local_validation_repair"][
        "error"
    ]
    assert "immediately preceding patch was rejected" in posted["messages"][0][
        "content"
    ]


def test_goal_stage_checker_returns_three_fields_with_kernel_bound_provenance():
    fake = FakeSession(
        [response({"verdict": "advance", "gaps": [], "reason": "coherent"})]
    )
    client = OpenAICompatibleSupervisorClient(settings(), session=fake)
    request = GoalStageReviewRequest(
        run_id="RUN-STAGE-REVIEW",
        immutable_request="Inspect and correct config.json.",
        goal_digest="goal-digest",
        stage=1,
        stage_steps=(
            {
                "step_id": "S1",
                "objective": "Inspect config.json",
                "accepted_evidence_refs": ["A00001"],
            },
        ),
        workspace_manifest={"entries": [{"path": "config.json"}]},
    )

    review = client.review_goal_stage(request)

    assert review.stage == 1
    assert review.reviewed_step_ids == ("S1",)
    assert review.evidence_refs == ("A00001",)
    posted = fake.posts[0]["json"]
    schema = posted["response_format"]["json_schema"]["schema"]
    assert set(schema["properties"]) == {"verdict", "gaps", "reason"}
    payload = json.loads(posted["messages"][1]["content"])
    assert list(payload)[-1] == "current_requirement"


def test_contract_plan_schema_requires_explicit_obligation_phase():
    obligation = CONTRACT_PLAN_RESPONSE_SCHEMA["properties"]["new_obligations"][
        "items"
    ]

    assert "phase" in obligation["required"]
    assert obligation["properties"]["phase"]["enum"] == [
        "execution_evidence",
        "final_presentation",
    ]


@pytest.mark.parametrize("tag", ("analysis", "think"))
def test_supervisor_content_accepts_known_provider_reasoning_envelope(tag):
    content = f"<{tag}>private provider reasoning</{tag}>\n" + json.dumps(
        {"summary": "valid"}
    )

    value, normalization = _decode_supervisor_json_content(content)

    assert value == {"summary": "valid"}
    assert normalization is not None
    assert normalization["normalization"] == f"provider_{tag}_prefix_removed"
    assert normalization["controller_semantic_fields_generated"] is False
    assert "private provider reasoning" not in json.dumps(normalization)


def test_supervisor_content_accepts_bare_json_without_normalization():
    value, normalization = _decode_supervisor_json_content('{"summary":"valid"}')

    assert value == {"summary": "valid"}
    assert normalization is None


@pytest.mark.parametrize(
    "content",
    (
        'provider prose\n{"summary":"valid"}',
        '<analysis>unclosed\n{"summary":"valid"}',
        '<analysis>reasoning</analysis>\n{"summary":"valid"}\ntrailing prose',
        '<analysis>reasoning</analysis>\n[]',
    ),
)
def test_supervisor_content_rejects_unknown_or_malformed_envelopes(content):
    with pytest.raises(SupervisorProtocolError):
        _decode_supervisor_json_content(content)


def test_supervisor_env_loading_does_not_pollute_rwkv_namespace(
    tmp_path,
    monkeypatch,
):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "\n".join(
            (
                "SUPERVISOR_BASE_URL=https://supervisor.invalid/v1",
                "SUPERVISOR_API_KEY=test-key",
                "SUPERVISOR_MODEL=gpt-test",
                "SUPERVISOR_MAX_REVIEW_REPAIRS=2",
                "RWKV_TOOL_DISCLOSURE_MODE=full",
            )
        ),
        encoding="utf-8",
    )
    for key in (
        "RWKV_LH_PLANNER_BASE_URL",
        "RWKV_LH_PLANNER_API_KEY",
        "RWKV_LH_PLANNER_MODEL",
        "SUPERVISOR_BASE_URL",
        "SUPERVISOR_API_KEY",
        "SUPERVISOR_MODEL",
        "SUPERVISOR_MAX_REVIEW_REPAIRS",
        "RWKV_TOOL_DISCLOSURE_MODE",
    ):
        monkeypatch.delenv(key, raising=False)

    loaded_settings = SupervisorAPISettings.from_env(env_path)
    loaded_policy = supervisor_policy_from_env(env_path)

    assert loaded_settings.model == "gpt-test"
    assert loaded_policy.max_review_repairs == 2
    assert "RWKV_TOOL_DISCLOSURE_MODE" not in os.environ


def test_openai_supervisor_builds_valid_plan_and_review_without_auditing_key():
    fake = FakeSession(
        [
            response(
                {
                    "objective": "Create and verify the requested artifact.",
                    "constraints": ["Stay inside the workspace."],
                    "steps": ["Inspect inputs.", "Write the artifact.", "Verify it."],
                    "completion_checks": ["The artifact exists with the requested content."],
                    "risks": ["Do not finish before verification."],
                }
            ),
            response(
                {
                    "disposition": "pass",
                    "summary": "The recorded write and read support completion.",
                    "issues": [],
                }
            ),
        ]
    )
    audit: list[dict] = []
    client = OpenAICompatibleSupervisorClient(
        settings(),
        session=fake,
        audit_hook=audit.append,
    )
    plan_request = SupervisorPlanRequest(
        run_id="RUN-1",
        request="Create result.txt and verify it.",
        request_digest="digest-1",
        constraints=("Stay inside the workspace.",),
        workspace_manifest={"entries": []},
    )

    plan = client.create_plan(plan_request)
    review = client.review_final(
        SupervisorReviewRequest(
            run_id="RUN-1",
            request=plan_request.request,
            request_digest=plan_request.request_digest,
            plan=plan,
            candidate_output="Created and verified result.txt.",
            candidate_decision_id="D-1",
            action_count=2,
            actions=({"operation": "write_file", "status": "succeeded"},),
            artifacts=(),
            workspace_manifest={"entries": [{"path": "result.txt"}]},
        )
    )

    assert plan.steps[-1] == "Verify it."
    assert review.disposition.value == "pass"
    assert all(
        post["json"]["response_format"]["type"] == "json_schema"
        for post in fake.posts
    )
    assert "test-secret-never-audited" not in json.dumps(audit)
    assert [item["phase"] for item in audit if item["type"] == "supervisor_request_returned"] == [
        "plan",
        "review",
    ]


def test_contract_planner_and_reviewer_receive_results_without_rwkv_process():
    immutable_request = "Create result.txt containing exact text ok."
    fake = FakeSession(
        [
            response(
                {
                    "summary": "Compile one required artifact obligation.",
                    "new_obligations": [
                        {
                            "obligation_id": "OBL-result",
                            "predicate": "result.txt contains exact text ok.",
                            "evidence_kinds": ["file", "digest"],
                            "assertions": [
                                {
                                    "assertion_id": "ASSERT-result-text",
                                    "kind": "text_exact",
                                    "target_path": "result.txt",
                                    "target_pointer": "",
                                    "sources": [],
                                    "expected": "ok",
                                    "keys": [],
                                    "order": "",
                                    "algorithm": "",
                                }
                            ],
                        }
                    ],
                    "new_nodes": [
                        {
                            "obligation_ids": ["OBL-result"],
                            "atom": {
                                    "atom_id": "NODE-write-result",
                                    "role": "work",
                                    "kind": "mutate",
                                    "effect_ceiling": "workspace_mutation",
                                    "objective": "Create result.txt containing exact text ok.",
                                "depends_on": [],
                                "read_roots": [],
                                "write_roots": ["result.txt"],
                                    "evidence_requirements": {
                                        "kinds": ["exact_operation_result"],
                                        "freshness": "current_workspace",
                                        "source_preferences": ["workspace"],
                                    },
                                "action_budget": 1,
                            },
                        },
                        {
                            "obligation_ids": ["OBL-result"],
                            "atom": {
                                    "atom_id": "NODE-verify-result",
                                    "role": "work",
                                    "kind": "verify",
                                    "effect_ceiling": "local_read_only",
                                "objective": "Read result.txt and verify exact content.",
                                "depends_on": ["NODE-write-result"],
                                "read_roots": ["result.txt"],
                                "write_roots": [],
                                    "evidence_requirements": {
                                        "kinds": ["file_observation"],
                                        "freshness": "current_workspace",
                                        "source_preferences": ["workspace_file"],
                                    },
                                "action_budget": 1,
                            },
                        },
                        {
                            "obligation_ids": ["OBL-result"],
                            "atom": {
                                    "atom_id": "NODE-final",
                                    "role": "finalizer",
                                    "kind": "synthesize",
                                    "effect_ceiling": "local_read_only",
                                "objective": "Read result.txt and report exact completion.",
                                "depends_on": ["NODE-verify-result"],
                                "read_roots": ["result.txt"],
                                "write_roots": [],
                                    "evidence_requirements": {
                                        "kinds": ["verified_ledger"],
                                        "freshness": "current_workspace",
                                        "source_preferences": ["workspace"],
                                    },
                                "action_budget": 1,
                            },
                        },
                    ],
                }
            ),
            response(
                {
                    "summary": "The exact result and artifact identify completion.",
                    "verdicts": [
                        {
                            "obligation_id": "OBL-result",
                            "status": "satisfied",
                            "evidence_refs": ["PLACEHOLDER"],
                            "reason": "The write succeeded at the requested path.",
                        }
                    ],
                }
            ),
        ]
    )
    client = OpenAICompatibleSupervisorClient(
        replace(
            settings(),
            reasoning_effort="low",
            contract_review_reasoning_effort="medium",
        ),
        session=fake,
    )
    operation_catalog = contract_operation_catalog()
    plan_request = ContractPlanRequest(
        run_id="RUN-CONTRACT",
        request=immutable_request,
        request_digest="digest-contract",
        graph_revision=0,
        obligations=(),
        nodes=(),
        latest_review=None,
        result_capsules=(),
        available_operations=operation_catalog,
        workspace_manifest={"entries": []},
    )

    patch = client.plan_contract_graph(plan_request)
    result = ResultCapsule.create(
        node_id="NODE-write-result",
        node_status="completed",
        operation="write_file",
        result={"success": True, "path": "result.txt"},
        artifacts=({"path": "result.txt", "sha256": "a" * 64},),
        workspace_revision="revision-1",
    )
    fake.responses[0].payload["choices"][0]["message"]["content"] = json.dumps(
        {
            "summary": "The exact result and artifact identify completion.",
            "verdicts": [
                {
                    "obligation_id": "OBL-result",
                    "status": "satisfied",
                    "evidence_refs": [result.evidence_id],
                    "reason": "The write succeeded at the requested path.",
                }
            ],
        }
    )
    review = client.review_contract_graph(
        ContractReviewRequest(
            run_id="RUN-CONTRACT",
            request=immutable_request,
            request_digest="digest-contract",
            graph_revision=1,
            obligations=tuple(item.to_dict() for item in patch.new_obligations),
            nodes=tuple(item.to_dict() for item in patch.new_nodes),
            result_capsules=(result,),
            workspace_manifest={"entries": [{"path": "result.txt"}]},
        )
    )

    assert review.verdicts[0].status.value == "satisfied"
    planner_schema = fake.posts[0]["json"]["response_format"]["json_schema"][
        "schema"
    ]
    assert fake.posts[0]["json"]["reasoning_effort"] == "low"
    assert fake.posts[1]["json"]["reasoning_effort"] == "medium"
    assert fake.posts[0]["json"]["response_format"]["json_schema"]["name"] == (
        "rwkv_lh_supervisor_contract_plan_v8"
    )
    atom_schema = planner_schema["properties"]["new_nodes"]["items"][
        "properties"
    ]["atom"]
    atom_branches = atom_schema["anyOf"]
    branch_properties = [item["properties"] for item in atom_branches]
    obligation_schema = planner_schema["properties"]["new_obligations"]["items"]
    assert all("operations" not in item for item in branch_properties)
    assert all("allowed_operations" not in item for item in branch_properties)
    assert all("action_budget" not in item for item in branch_properties)
    assert all("evidence_requirements" not in item for item in branch_properties)
    assert all(item["write_roots"]["maxItems"] == 8 for item in branch_properties)
    assert "assertions" not in obligation_schema["properties"]
    assert obligation_schema["properties"]["phase"]["enum"] == [
        "execution_evidence",
        "final_presentation",
    ]
    assert "phase" in obligation_schema["required"]
    assert [item["kind"]["enum"] for item in branch_properties] == [
        ["investigate"],
        ["mutate"],
        ["verify"],
    ]
    planner_payload = fake.posts[0]["json"]["messages"][1]["content"]
    assert "write_file" not in planner_payload
    assert "read_file" not in planner_payload
    assert list(json.loads(planner_payload))[-1] == "request"
    forbidden = (
        "candidate_output",
        "transcript",
        "recent_actions",
        "completed_atoms",
        "protocol_rejections",
    )
    for post in fake.posts:
        user_payload = post["json"]["messages"][1]["content"]
        assert not any(name in user_payload for name in forbidden)


def test_supervisor_health_requires_configured_model_in_catalog():
    fake = FakeSession([])
    client = OpenAICompatibleSupervisorClient(settings(), session=fake)

    health = client.health()

    assert health["available"] is True
    assert health["model_present"] is True


def test_supervisor_readiness_checks_completion_route_after_model_catalog():
    fake = FakeSession([FakeResponse({}, status_code=403)])
    audit: list[dict] = []
    client = OpenAICompatibleSupervisorClient(
        replace(
            settings(),
            retry_attempts=3,
            fallback_models=("gpt-fallback",),
        ),
        session=fake,
        audit_hook=audit.append,
    )

    readiness = client.readiness()

    assert readiness["available"] is False
    assert readiness["catalog_available"] is True
    assert readiness["completion_available"] is False
    assert readiness["http_status"] == 403
    assert readiness["retryable"] is False
    assert readiness["error_category"] == "authorization"
    assert len(fake.posts) == 1
    failed = [item for item in audit if item["type"] == "supervisor_request_failed"]
    assert failed[0]["retryable"] is False
    assert failed[0]["error_category"] == "authorization"
    assert not any(item["type"] == "supervisor_model_fallback_applied" for item in audit)


def test_non_retryable_supervisor_http_error_has_structured_contract():
    fake = FakeSession([FakeResponse({}, status_code=400)])
    client = OpenAICompatibleSupervisorClient(
        replace(settings(), retry_attempts=3),
        session=fake,
    )

    with pytest.raises(SupervisorTransportError) as captured:
        client.create_plan(
            SupervisorPlanRequest(
                run_id="RUN-BAD-REQUEST",
                request="Inspect the workspace.",
                request_digest="digest-bad-request",
                constraints=(),
                workspace_manifest={"entries": []},
            )
        )

    assert captured.value.status_code == 400
    assert captured.value.retryable is False
    assert captured.value.category == "request"
    assert len(fake.posts) == 1


def test_openai_supervisor_builds_one_online_microtask_directive():
    fake = FakeSession(
        [
            response(
                {
                    "disposition": "continue",
                    "review_status": "initial",
                    "review_summary": "Assign one observable first microtask.",
                    "issues": [],
                    "microtask_objective": "Inspect the existing input file.",
                    "completion_checks": ["The relevant input content is observed."],
                    "constraints": ["Do not modify unrelated files."],
                }
            )
        ]
    )
    audit: list[dict] = []
    client = OpenAICompatibleSupervisorClient(
        settings(), session=fake, audit_hook=audit.append
    )

    directive = client.next_directive(
        SupervisorDirectiveRequest(
            run_id="RUN-ONLINE",
            request="Transform input.txt into result.txt.",
            request_digest="digest-online",
            constraints=("Stay inside the workspace.",),
            directive_index=1,
            outcome_ref="initial",
            previous_directive=None,
            worker_outcome=None,
            action_count=0,
            actions=(),
            artifacts=(),
            workspace_manifest={"entries": [{"path": "input.txt"}]},
        )
    )

    assert directive.directive_index == 1
    assert directive.disposition.value == "continue"
    assert directive.microtask_objective == "Inspect the existing input file."
    assert fake.posts[0]["json"]["response_format"]["json_schema"]["name"] == (
        "rwkv_lh_supervisor_directive_v1"
    )
    assert [
        item["phase"]
        for item in audit
        if item["type"] == "supervisor_request_returned"
    ] == ["directive"]


def test_openai_supervisor_builds_parallel_ready_atom_stage():
    immutable_request = "Create left.txt and right.txt, then verify both."
    fake = FakeSession(
        [
            response(
                {
                    "disposition": "dispatch",
                    "review_summary": "Dispatch two disjoint file atoms.",
                    "issues": [],
                    "atoms": [
                        {
                            "atom_id": "left",
                            "role": "work",
                            "objective": "Create and verify left.txt.",
                            "request_clauses": [immutable_request],
                            "depends_on": [],
                            "read_roots": [],
                            "write_roots": ["left.txt"],
                            "exclusive": False,
                            "allowed_operations": ["write_file"],
                            "action_budget": 1,
                            "completion_checks": ["left.txt is verified."],
                            "constraints": [],
                        },
                        {
                            "atom_id": "right",
                            "role": "work",
                            "objective": "Create and verify right.txt.",
                            "request_clauses": [immutable_request],
                            "depends_on": [],
                            "read_roots": [],
                            "write_roots": ["right.txt"],
                            "exclusive": False,
                            "allowed_operations": ["write_file"],
                            "action_budget": 1,
                            "completion_checks": ["right.txt is verified."],
                            "constraints": [],
                        },
                    ],
                    "accepted_candidate_atom_id": "",
                }
            )
        ]
    )
    client = OpenAICompatibleSupervisorClient(settings(), session=fake)

    stage = client.next_stage(
        SupervisorStageRequest(
            run_id="RUN-PARALLEL",
            request=immutable_request,
            request_digest="digest-parallel",
            constraints=("Stay inside the workspace.",),
            stage_index=1,
            max_parallel_atoms=4,
                previous_stage_id="",
                completed_atoms=(),
                available_operations=(
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
                ),
                workspace_manifest={"entries": []},
        )
    )

    assert [item.atom_id for item in stage.atoms] == ["left", "right"]
    assert stage.request_digest == "digest-parallel"
    assert fake.posts[0]["json"]["response_format"]["json_schema"]["name"] == (
        "rwkv_lh_supervisor_stage_v1"
    )
    stage_schema = fake.posts[0]["json"]["response_format"]["json_schema"][
        "schema"
    ]
    assert "allOf" not in stage_schema
    assert stage_schema["additionalProperties"] is False
    depends_on_schema = stage_schema["properties"]["atoms"]["items"][
        "properties"
    ]["depends_on"]
    assert depends_on_schema["maxItems"] == 0
    assert stage_schema["properties"]["accepted_candidate_atom_id"]["enum"] == [
        ""
    ]
    assert stage_schema["properties"]["atoms"]["items"]["properties"][
        "allowed_operations"
    ]["items"]["enum"] == ["read_file", "write_file"]


def test_parallel_stage_locally_repairs_provider_schema_violation():
    immutable_request = "Create result.txt and verify it."

    def stage_content(clause: str):
        return {
            "disposition": "dispatch",
            "review_summary": "Dispatch one bounded atom.",
            "issues": [],
            "atoms": [
                {
                    "atom_id": "result",
                    "role": "work",
                    "objective": "Create and verify result.txt.",
                    "request_clauses": [clause],
                    "depends_on": [],
                    "read_roots": [],
                    "write_roots": ["result.txt"],
                    "exclusive": False,
                    "allowed_operations": ["write_file"],
                    "action_budget": 1,
                    "completion_checks": ["result.txt is verified."],
                    "constraints": [],
                }
            ],
            "accepted_candidate_atom_id": "",
        }

    fake = FakeSession(
        [
            response(stage_content("Invented replacement request.")),
            response(stage_content(immutable_request)),
        ]
    )
    audit: list[dict] = []
    client = OpenAICompatibleSupervisorClient(
        settings(),
        session=fake,
        audit_hook=audit.append,
    )
    request = SupervisorStageRequest(
        run_id="RUN-REPAIR",
        request=immutable_request,
        request_digest="digest-repair",
        constraints=(),
        stage_index=1,
        max_parallel_atoms=4,
        previous_stage_id="",
        completed_atoms=(),
        available_operations=(
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
        ),
        workspace_manifest={"entries": []},
    )

    stage = client.next_stage(request)

    assert stage.atoms[0].request_clauses == (immutable_request,)
    assert len(fake.posts) == 2
    repair = fake.posts[1]["json"]["messages"][1]["content"]
    assert "local_validation_repair" in repair
    assert list(json.loads(repair))[-1] == "local_validation_repair"
    assert any(
        item["type"] == "supervisor_semantic_response_rejected"
        for item in audit
    )


def test_parallel_acceptance_requires_independent_evidence_review():
    immutable_request = "Create result.txt with exact content ok and verify it."
    accepted = {
        "disposition": "accept_final",
        "review_summary": "Planner proposes acceptance.",
        "issues": [],
        "atoms": [],
        "accepted_candidate_atom_id": "final",
    }
    correction = {
        "disposition": "dispatch",
        "review_summary": "Exact evidence contradicts the request.",
        "issues": ["result.txt contains wrong instead of ok."],
        "atoms": [
            {
                "atom_id": "repair_result",
                "role": "work",
                "objective": "Write result.txt with exact content ok.",
                "request_clauses": [immutable_request],
                "depends_on": ["final"],
                "read_roots": [],
                "write_roots": ["result.txt"],
                "exclusive": False,
                "allowed_operations": ["write_file"],
                "action_budget": 1,
                "completion_checks": ["result.txt contains exact content ok."],
                "constraints": [],
            }
        ],
        "accepted_candidate_atom_id": "",
    }
    fake = FakeSession([response(accepted), response(correction)])
    audit: list[dict] = []
    client = OpenAICompatibleSupervisorClient(
        settings(), session=fake, audit_hook=audit.append
    )
    request = SupervisorStageRequest(
        run_id="RUN-INDEPENDENT-REVIEW",
        request=immutable_request,
        request_digest="digest-independent-review",
        constraints=(),
        stage_index=4,
        max_parallel_atoms=4,
        previous_stage_id="STAGE-3",
        completed_atoms=(
            {
                "stage_id": "STAGE-3",
                "atom_id": "final",
                "role": "finalizer",
                "status": "completed",
                "candidate_output": "result.txt is correct.",
                "recent_actions": [
                    {
                        "operation": "read_file",
                        "result": {"success": True, "output": "wrong"},
                    }
                ],
            },
        ),
        available_operations=(
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
        ),
        workspace_manifest={"entries": [{"path": "result.txt"}]},
    )

    stage = client.next_stage(request)

    assert stage.disposition.value == "dispatch"
    assert stage.atoms[0].atom_id == "repair_result"
    assert len(fake.posts) == 2
    assert [
        item["phase"]
        for item in audit
        if item["type"] == "supervisor_request_returned"
    ] == ["stage", "stage_acceptance_review"]
    reviewer_payload = fake.posts[1]["json"]["messages"][1]["content"]
    assert "proposed_acceptance" in reviewer_payload


def test_supervisor_read_timeout_retries_safe_control_plane_request():
    fake = FakeSession(
        [
            requests.ReadTimeout("first attempt timed out"),
            response(
                {
                    "objective": "Inspect and complete the request.",
                    "constraints": [],
                    "steps": ["Inspect the workspace."],
                    "completion_checks": ["The requested result is verified."],
                    "risks": [],
                }
            ),
        ]
    )
    client = OpenAICompatibleSupervisorClient(
        replace(settings(), retry_attempts=2, retry_backoff_seconds=0),
        session=fake,
    )

    plan = client.create_plan(
        SupervisorPlanRequest(
            run_id="RUN-TIMEOUT",
            request="Inspect the workspace.",
            request_digest="digest-timeout",
            constraints=(),
            workspace_manifest={"entries": []},
        )
    )

    assert plan.steps == ("Inspect the workspace.",)
    assert len(fake.posts) == 2


def test_contract_plan_http_500_falls_back_from_medium_to_low_reasoning():
    immutable_request = "Create result.txt containing exact text ok."
    fake = FakeSession(
        [
            FakeResponse({}, status_code=500),
            response(
                {
                    "summary": "Compile one mandatory result obligation.",
                    "new_obligations": [
                        {
                            "obligation_id": "OBL-result",
                            "predicate": "result.txt contains exact text ok.",
                            "evidence_kinds": ["file_observation"],
                            "assertions": [
                                {
                                    "assertion_id": "ASSERT-result-text",
                                    "kind": "text_exact",
                                    "target_path": "result.txt",
                                    "target_pointer": "",
                                    "sources": [],
                                    "expected": "ok",
                                    "keys": [],
                                    "order": "",
                                    "algorithm": "",
                                }
                            ],
                        }
                    ],
                    "new_nodes": [
                        {
                            "obligation_ids": ["OBL-result"],
                            "atom": {
                                    "atom_id": "NODE-write",
                                    "role": "work",
                                    "kind": "mutate",
                                    "effect_ceiling": "workspace_mutation",
                                "objective": "Create result.txt containing exact text ok.",
                                "depends_on": [],
                                "read_roots": [],
                                "write_roots": ["result.txt"],
                                    "evidence_requirements": {
                                        "kinds": ["exact_operation_result"],
                                        "freshness": "current_workspace",
                                        "source_preferences": ["workspace"],
                                    },
                                "action_budget": 1,
                            },
                        },
                        {
                            "obligation_ids": ["OBL-result"],
                            "atom": {
                                    "atom_id": "NODE-verify",
                                    "role": "work",
                                    "kind": "verify",
                                    "effect_ceiling": "local_read_only",
                                "objective": "Read result.txt and verify exact content.",
                                "depends_on": ["NODE-write"],
                                "read_roots": ["result.txt"],
                                "write_roots": [],
                                    "evidence_requirements": {
                                        "kinds": ["file_observation"],
                                        "freshness": "current_workspace",
                                        "source_preferences": ["workspace_file"],
                                    },
                                "action_budget": 1,
                            },
                        },
                        {
                            "obligation_ids": ["OBL-result"],
                            "atom": {
                                    "atom_id": "NODE-final",
                                    "role": "finalizer",
                                    "kind": "synthesize",
                                    "effect_ceiling": "local_read_only",
                                "objective": "Read result.txt and report completion.",
                                "depends_on": ["NODE-verify"],
                                "read_roots": ["result.txt"],
                                "write_roots": [],
                                    "evidence_requirements": {
                                        "kinds": ["verified_ledger"],
                                        "freshness": "current_workspace",
                                        "source_preferences": ["workspace"],
                                    },
                                "action_budget": 1,
                            },
                        },
                    ],
                }
            ),
        ]
    )
    audit: list[dict] = []
    client = OpenAICompatibleSupervisorClient(
        replace(
            settings(),
            retry_attempts=2,
            retry_backoff_seconds=0,
            contract_plan_reasoning_effort="medium",
        ),
        session=fake,
        audit_hook=audit.append,
    )

    patch = client.plan_contract_graph(
        ContractPlanRequest(
            run_id="RUN-FALLBACK",
            request=immutable_request,
            request_digest="digest-fallback",
            graph_revision=0,
            obligations=(),
            nodes=(),
            latest_review=None,
            result_capsules=(),
            available_operations=contract_operation_catalog(),
            workspace_manifest={"entries": []},
        )
    )

    assert patch.new_obligations[0].required is True
    assert [post["json"]["reasoning_effort"] for post in fake.posts] == [
        "medium",
        "low",
    ]
    assert [
        item for item in audit
        if item["type"] == "supervisor_reasoning_fallback_applied"
    ][0]["http_status"] == 500


def test_contract_plan_http_500_preserves_none_reasoning_on_retry():
    fake = FakeSession(
        [
            FakeResponse({}, status_code=500),
            response(contract_plan_value()),
        ]
    )
    audit: list[dict] = []
    client = OpenAICompatibleSupervisorClient(
        replace(
            settings(),
            retry_attempts=2,
            retry_backoff_seconds=0,
            contract_plan_reasoning_effort="none",
        ),
        session=fake,
        audit_hook=audit.append,
    )

    patch = client.plan_contract_graph(
        ContractPlanRequest(
            run_id="RUN-NONE-RETRY",
            request="Create result.txt containing exact text ok.",
            request_digest="digest-none-retry",
            graph_revision=0,
            obligations=(),
            nodes=(),
            latest_review=None,
            result_capsules=(),
            available_operations=contract_operation_catalog(),
            workspace_manifest={"entries": []},
        )
    )

    assert patch.new_obligations[0].required is True
    assert [post["json"]["reasoning_effort"] for post in fake.posts] == [
        "none",
        "none",
    ]
    assert not any(
        item["type"] == "supervisor_reasoning_fallback_applied" for item in audit
    )


def test_model_route_falls_back_and_circuit_skips_repeated_primary_failure():
    valid_plan = {
        "objective": "Inspect the workspace.",
        "constraints": [],
        "steps": ["Inspect the workspace."],
        "completion_checks": ["Inspection is complete."],
        "risks": [],
    }
    fake = FakeSession(
        [
            FakeResponse({}, status_code=503),
            response(valid_plan, model="gpt-fallback"),
            response(valid_plan, model="gpt-fallback"),
        ]
    )
    audit: list[dict] = []
    client = OpenAICompatibleSupervisorClient(
        replace(
            settings(),
            fallback_models=("gpt-fallback",),
            circuit_breaker_failures=1,
            circuit_breaker_cooldown_seconds=3600,
        ),
        session=fake,
        audit_hook=audit.append,
    )
    request = SupervisorPlanRequest(
        run_id="RUN-ROUTE",
        request="Inspect the workspace.",
        request_digest="digest-route",
        constraints=(),
        workspace_manifest={"entries": []},
    )

    client.create_plan(request)
    client.create_plan(request)

    assert [post["json"]["model"] for post in fake.posts] == [
        "gpt-test",
        "gpt-fallback",
        "gpt-fallback",
    ]
    assert any(item["type"] == "supervisor_model_fallback_applied" for item in audit)
    assert any(item["type"] == "supervisor_route_skipped" for item in audit)


def test_validated_contract_plan_cache_avoids_second_api_call(tmp_path):
    cache_dir = tmp_path / "plan-cache"
    configured = replace(
        settings(),
        plan_cache_enabled=True,
        plan_cache_dir=str(cache_dir.resolve()),
    )
    request = ContractPlanRequest(
        run_id="RUN-CACHE",
        request="Create result.txt containing exact text ok.",
        request_digest="digest-cache",
        graph_revision=0,
        obligations=(),
        nodes=(),
        latest_review=None,
        result_capsules=(),
        available_operations=contract_operation_catalog(),
        workspace_manifest={"entries": []},
    )
    first_session = FakeSession([response(contract_plan_value())])
    first = OpenAICompatibleSupervisorClient(configured, session=first_session)
    first_patch = first.plan_contract_graph(request)
    audit: list[dict] = []
    second_session = FakeSession([])
    second = OpenAICompatibleSupervisorClient(
        configured, session=second_session, audit_hook=audit.append
    )

    second_patch = second.plan_contract_graph(request)

    assert second_patch.patch_id == first_patch.patch_id
    assert second_session.posts == []
    assert any(item["type"] == "supervisor_plan_cache_hit" for item in audit)
