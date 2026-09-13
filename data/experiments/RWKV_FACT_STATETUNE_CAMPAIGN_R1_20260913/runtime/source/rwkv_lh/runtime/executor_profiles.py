"""Bind one immutable Executor state profile from persisted retrieval policy."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, replace
from typing import Mapping

from rwkv_lh.retrieval import NetworkPolicyMode, retrieval_policy_from_goal
from rwkv_lh.runtime.settings import RuntimeSettings, get_runtime_settings
from rwkv_lh.schema import ModelLaneKind, RunState


EXECUTOR_PROFILE_ROUTING_DISABLED = "disabled"
EXECUTOR_PROFILE_ROUTING_V1 = "retrieval-policy-v1"
NETWORK_PROFILE_ID_ENV = "RWKV_NETWORK_EXECUTOR_STATE_PROFILE_ID"
NETWORK_PROFILE_SHA256_ENV = "RWKV_NETWORK_EXECUTOR_STATE_PROFILE_SHA256"
PROFILE_ROUTING_ENV = "RWKV_EXECUTOR_PROFILE_ROUTING"
_PROFILE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ExecutorProfileBinding:
    settings: RuntimeSettings
    routing_mode: str
    retrieval_mode: NetworkPolicyMode
    role: str
    profile_switches_within_run: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "rwkv-lh.executor-profile-binding.v1",
            "routing_mode": self.routing_mode,
            "retrieval_mode": self.retrieval_mode.value,
            "role": self.role,
            "model": self.settings.model,
            "model_sha256": self.settings.model_sha256,
            "profile_id": self.settings.state_profile_id,
            "profile_sha256": self.settings.state_profile_sha256,
            "profile_delivery": self.settings.state_profile_delivery,
            "profile_switches_within_run": self.profile_switches_within_run,
        }


def _network_profile_pair(environ: Mapping[str, str]) -> tuple[str, str]:
    profile_id = str(environ.get(NETWORK_PROFILE_ID_ENV) or "").strip()
    profile_sha256 = str(environ.get(NETWORK_PROFILE_SHA256_ENV) or "").strip().casefold()
    if bool(profile_id) != bool(profile_sha256):
        raise ValueError(
            f"{NETWORK_PROFILE_ID_ENV} and {NETWORK_PROFILE_SHA256_ENV} "
            "must be configured together"
        )
    if not profile_id:
        raise ValueError("active Executor profile routing requires a network profile")
    if not _PROFILE_ID.fullmatch(profile_id):
        raise ValueError(f"{NETWORK_PROFILE_ID_ENV} is invalid")
    if not _SHA256.fullmatch(profile_sha256):
        raise ValueError(f"{NETWORK_PROFILE_SHA256_ENV} must be lowercase SHA-256")
    return profile_id, profile_sha256


def _assert_existing_lane_identity(
    state: RunState,
    settings: RuntimeSettings,
) -> None:
    checkpoints = [
        checkpoint
        for checkpoint in state.model_states.values()
        if checkpoint.lane_kind is ModelLaneKind.ACTION
    ]
    if not checkpoints:
        return
    identities = {
        (
            checkpoint.model,
            checkpoint.state_profile_id,
            checkpoint.state_profile_sha256,
        )
        for checkpoint in checkpoints
    }
    if len(identities) != 1:
        raise ValueError("persisted Executor lane contains multiple model/state identities")
    expected = (
        settings.model,
        settings.state_profile_id,
        settings.state_profile_sha256,
    )
    if next(iter(identities)) != expected:
        raise ValueError(
            "persisted Executor lane identity differs from the task-level profile binding"
        )
    observed_model_sha256 = {
        str((checkpoint.native_state_metadata or {}).get("model_sha256") or "")
        for checkpoint in checkpoints
    }
    if observed_model_sha256 != {settings.model_sha256}:
        raise ValueError("persisted Executor lane base-model SHA-256 changed")
    observed_delivery = {
        str(
            (checkpoint.native_state_metadata or {}).get(
                "state_profile_delivery"
            )
            or ""
        )
        for checkpoint in checkpoints
    }
    if observed_delivery != {settings.state_profile_delivery}:
        raise ValueError("persisted Executor lane state-profile delivery changed")


def executor_profile_binding_for_run(
    state: RunState,
    *,
    base_settings: RuntimeSettings | None = None,
    environ: Mapping[str, str] | None = None,
) -> ExecutorProfileBinding:
    """Resolve once from immutable goal policy and reject resumed state switches."""

    selected_environment = os.environ if environ is None else environ
    settings = base_settings or get_runtime_settings()
    retrieval_mode = retrieval_policy_from_goal(state.goal).mode
    routing_mode = str(
        selected_environment.get(
            PROFILE_ROUTING_ENV,
            EXECUTOR_PROFILE_ROUTING_DISABLED,
        )
        or EXECUTOR_PROFILE_ROUTING_DISABLED
    ).strip().casefold()
    if routing_mode not in {
        EXECUTOR_PROFILE_ROUTING_DISABLED,
        EXECUTOR_PROFILE_ROUTING_V1,
    }:
        raise ValueError(f"{PROFILE_ROUTING_ENV} must be disabled or retrieval-policy-v1")

    role = "configured_default"
    if routing_mode == EXECUTOR_PROFILE_ROUTING_V1:
        if (
            not settings.state_profile_id
            or not settings.state_profile_sha256
            or settings.state_profile_delivery != "request"
        ):
            raise ValueError(
                "active Executor profile routing requires an explicit request-delivered "
                "general profile"
            )
        network_id, network_sha256 = _network_profile_pair(selected_environment)
        if (network_id, network_sha256) == (
            settings.state_profile_id,
            settings.state_profile_sha256,
        ):
            raise ValueError("general and network Executor profiles must be distinct")
        if retrieval_mode is not NetworkPolicyMode.OFFLINE:
            settings = replace(
                settings,
                state_profile_id=network_id,
                state_profile_sha256=network_sha256,
                state_profile_delivery="request",
            )
            settings.validate()
            role = "network"
        else:
            role = "general"

    _assert_existing_lane_identity(state, settings)
    return ExecutorProfileBinding(
        settings=settings,
        routing_mode=routing_mode,
        retrieval_mode=retrieval_mode,
        role=role,
    )


__all__ = [
    "EXECUTOR_PROFILE_ROUTING_DISABLED",
    "EXECUTOR_PROFILE_ROUTING_V1",
    "ExecutorProfileBinding",
    "NETWORK_PROFILE_ID_ENV",
    "NETWORK_PROFILE_SHA256_ENV",
    "PROFILE_ROUTING_ENV",
    "executor_profile_binding_for_run",
]
