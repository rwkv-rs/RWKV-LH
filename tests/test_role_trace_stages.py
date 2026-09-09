"""Frozen stage configuration checks; no training or production data creation."""

from copy import deepcopy

import pytest

from test_role_trace_inputs import controller_role_snapshots  # noqa: F401


def _contract(state):
    roles = {"selector": "selector_intent", "action": "executor_args", "auditor_step": "auditor_step",
             "finalizer": "finalizer_answer", "auditor_final": "auditor_final"}
    profiles = {}
    for checkpoint in state.model_states.values():
        profiles[roles[checkpoint.lane_kind.value]] = {
            "profile_id": "zero", "profile_sha256": "0" * 64,
            "model_sha256": checkpoint.native_state_metadata["model_sha256"],
        }
    profiles["selector_intent"].update(profile_id="verified-selector", profile_sha256="a" * 64)
    return {"mode": "role_stage", "stage_id": "MOCK-EXECUTOR-STAGE", "target_role": "executor_args",
            "profiles": profiles}


def test_stage_contract_keeps_target_zero_and_only_freezes_earlier_roles(controller_role_snapshots):
    from rwkv_lh.role_trace_stages import validate_collection_contract
    contract = _contract(controller_role_snapshots[1])
    assert validate_collection_contract(contract) == contract
    for role in ("executor_args", "auditor_step"):
        changed = deepcopy(contract)
        changed["profiles"][role].update(profile_id="unverified", profile_sha256="b" * 64)
        with pytest.raises(ValueError, match="target and later roles.*zero"):
            validate_collection_contract(changed)


def test_stage_checkpoint_must_match_frozen_upstream_state(controller_role_snapshots):
    from rwkv_lh.role_trace_stages import validate_collection_states
    state = deepcopy(controller_role_snapshots[1])
    contract = _contract(state)
    for cp in state.model_states.values():
        cp.state_profile_id = "zero"
        cp.state_profile_sha256 = "0" * 64
    selector = next(cp for cp in state.model_states.values() if cp.lane_kind.value == "selector")
    with pytest.raises(ValueError, match="State checkpoint"):
        validate_collection_states(state, [], contract)
    for cp in state.model_states.values():
        if cp.lane_kind.value == "selector":
            cp.state_profile_id = "verified-selector"
            cp.state_profile_sha256 = "a" * 64
    validate_collection_states(state, [], contract)
    selector.native_state_metadata["model_sha256"] = "b" * 64
    with pytest.raises(ValueError, match="model SHA"):
        validate_collection_states(state, [], contract)
