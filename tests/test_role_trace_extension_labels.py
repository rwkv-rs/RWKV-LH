"""All production extensions use their real argument registry during target validation."""
import json

import pytest

from rwkv_lh.goal_state_protocols import executor_args_v7 as protocol
from rwkv_lh.model_io import ModelCommand
from rwkv_lh.role_trace_inputs import _reconstruction_harness
from rwkv_lh.role_trace_labels import validate_role_target


@pytest.mark.parametrize(("operation", "arguments"), [
    ("current_time", {"timezone": "UTC"}),
    ("calculator", {"expression": "2+2"}),
    ("date_diff", {"date_a": "2026-09-01", "date_b": "2026-09-10"}),
    ("web_search", {"query": "public fixture"}),
    ("connector_lookup", {"operation": "github_repository", "query": "fixture/project"}),
])
def test_extension_target_uses_complete_registry_without_execution(operation, arguments):
    harness = _reconstruction_harness()
    definition = harness.g1i_tool_definitions([operation])[0]
    phase = "observe" if operation in ("web_search", "connector_lookup") else "derive_evidence"
    contract = protocol.build_target_contract(phase=phase, roots=(), target_descriptors=(), operations=(operation,))
    execution = protocol.build_execution_state(
        active_step_id="EXTENSION-FIXTURE", active_step_revision=1, declared_phase=phase,
        effective_phase=phase, assigned_actions=(), mechanical_evidence={}, target_contract=contract,
    )
    requirement = "Use the provided literal values: " + json.dumps(arguments)
    source = protocol.build_prompt_source(immutable_goal=requirement, current_requirement=requirement,
        execution_state=execution, selected_operation=operation, selected_tool_contract=definition,
        committed_fact_refs=(), executor_history=())
    rebuilt = {"protocol_version": protocol.INPUT_SCHEMA_VERSION, "prompt_source": source, "bound_fact_records": []}
    target = ModelCommand(operation, arguments).canonical
    assert validate_role_target("executor_args", rebuilt, target, verifier_id="STRUCTURAL-TEST-ONLY") == target
    invalid = ModelCommand(operation, {**arguments, "invented_argument": True}).canonical
    with pytest.raises(ValueError):
        validate_role_target("executor_args", rebuilt, invalid, verifier_id="STRUCTURAL-TEST-ONLY")
