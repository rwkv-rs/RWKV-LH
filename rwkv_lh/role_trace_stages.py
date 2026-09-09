"""Validate per-role collection conditions in the single production architecture.

This is evidence validation, not a scheduler or training permission mechanism.
The target role starts at zero; previously validated role States may be frozen
in the source run protocol. Model or State changes require a new registration.
"""

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from rwkv_lh.role_trace_artifacts import ROLES


ZERO_SHA = "0" * 64
LANE_ROLES = {"selector": "selector_intent", "action": "executor_args",
              "auditor_step": "auditor_step", "finalizer": "finalizer_answer",
              "auditor_final": "auditor_final"}


def _sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def validate_collection_contract(value: Any) -> dict[str, Any]:
    if (not isinstance(value, Mapping)
            or set(value) != {"mode", "stage_id", "target_role", "profiles"}
            or value.get("mode") != "role_stage"
            or not isinstance(value.get("stage_id"), str) or not value["stage_id"].strip()
            or value.get("target_role") not in ROLES):
        raise ValueError("invalid frozen role-stage collection contract")
    profiles = value["profiles"]
    if not isinstance(profiles, Mapping) or set(profiles) != set(ROLES):
        raise ValueError("stage collection must freeze every role profile")
    target_index = ROLES.index(value["target_role"])
    for index, role in enumerate(ROLES):
        profile = profiles[role]
        if (not isinstance(profile, Mapping) or set(profile) != {"profile_id", "profile_sha256", "model_sha256"}
                or not isinstance(profile["profile_id"], str) or not profile["profile_id"].strip()
                or not _sha(profile["profile_sha256"]) or not _sha(profile["model_sha256"])):
            raise ValueError("stage profile requires exact model and State identity")
        zero = profile["profile_id"] == "zero" and profile["profile_sha256"] == ZERO_SHA
        if (profile["profile_id"] == "zero") != (profile["profile_sha256"] == ZERO_SHA):
            raise ValueError("zero profile identity and SHA disagree")
        if index >= target_index and not zero:
            raise ValueError("target and later roles must start at zero in stage collection")
    return deepcopy(dict(value))


def validate_collection_states(state: Any, trace: Sequence[Mapping], contract: Mapping | None = None) -> None:
    contract = validate_collection_contract(contract) if contract is not None else None
    for checkpoint in state.model_states.values():
        metadata = checkpoint.native_state_metadata or {}
        if not checkpoint.model or not _sha(metadata.get("model_sha256")):
            raise ValueError("source checkpoint lacks model SHA identity")
        expected = {"profile_id": "zero", "profile_sha256": ZERO_SHA}
        if contract is not None:
            role = LANE_ROLES.get(checkpoint.lane_kind.value)
            if role is None:
                raise ValueError("unregistered model lane in stage collection")
            expected = contract["profiles"][role]
            if metadata["model_sha256"] != expected["model_sha256"]:
                raise ValueError("source checkpoint model SHA differs from frozen stage")
        identity = checkpoint.state_profile_id, checkpoint.state_profile_sha256
        if identity != (expected["profile_id"], expected["profile_sha256"]):
            raise ValueError("source contains a nonzero or unidentified State checkpoint for its collection contract")
        binding = metadata.get("cache_binding")
        if isinstance(binding, Mapping) and (
            binding.get("state_profile_id"), binding.get("state_profile_sha256")
        ) != identity:
            raise ValueError("native binding differs from frozen State checkpoint")
    starts = {event.get("request_id"): event for event in trace
              if event.get("type") == "model_session_generation_started"}
    for event in trace:
        raw = event.get("raw_generation")
        if not isinstance(raw, Mapping):
            continue
        expected = "zero", ZERO_SHA
        if contract is not None:
            start = starts.get(raw.get("request_id"), {})
            checkpoint = state.model_states.get(start.get("input_checkpoint_id"))
            if checkpoint is None:
                raise ValueError("stage generation lacks an identified input State")
            expected = checkpoint.state_profile_id, checkpoint.state_profile_sha256
        if (raw.get("state_profile_id"), raw.get("state_profile_sha256")) != expected:
            raise ValueError("source trace generation differs from frozen State identity")
