"""The sole production render contract for the G1J Selector-Intent lane."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from rwkv_lh.goal_state_protocols import selector_intent
from rwkv_lh.model_io import canonical_digest, canonical_json


@dataclass(frozen=True)
class NetworkSelectorInputProtocol:
    schema_version: str
    endpoint: str
    menu_prefix: str
    task_marker: str
    task_prefix: str
    step_prefix: str
    bootstrap_payload: Callable[[Any], dict[str, Any]]
    input_digest: Callable[[Any], str]
    menu_digest: Callable[[Any], str]
    render_bootstrap: Callable[[Any], str]
    render_step: Callable[[Any], str]


G1J_SELECTOR_INTENT_INPUT_PROTOCOL = selector_intent.INPUT_SCHEMA_VERSION
G1J_SELECTOR_INTENT_HEAD_ID = "rwkv_lh_g1j_selector_intent_head_v2"
G1J_SELECTOR_TRAINING_TRAJECTORY_MODE = "persistent-causal-sequences.v1"
G1J_SELECTOR_INTENT_MENU_SCHEMA_VERSION = (
    "rwkv-lh.g1j-per-stage-state-tuning.selector-intent-menu.v1"
)


def _g1j_values(value: Any) -> dict[str, Any]:
    source = value.to_dict() if hasattr(value, "to_dict") else dict(value)
    return {
        "stage_objective": source["stage_objective"],
        "stage_role": source["stage_role"],
        "progress": dict(source["progress"]),
        "eligible_labels": list(source["eligible_labels"]),
    }


def _g1j_menu_digest(value: Any) -> str:
    return canonical_digest(
        {
            "schema_version": G1J_SELECTOR_INTENT_MENU_SCHEMA_VERSION,
            "tools": [dict(item) for item in value.menu],
        }
    )


def _g1j_bootstrap_payload(value: Any) -> dict[str, Any]:
    _g1j_values(value)
    return {
        "menu_digest": _g1j_menu_digest(value),
        "menu_schema_version": G1J_SELECTOR_INTENT_MENU_SCHEMA_VERSION,
        "schema_version": G1J_SELECTOR_INTENT_INPUT_PROTOCOL,
        "tools": [dict(item) for item in value.menu],
    }


def _g1j_render_bootstrap(value: Any) -> str:
    payload = _g1j_bootstrap_payload(value)
    return (
        "SelectorIntentMenuV1: "
        + canonical_json(payload)
        + "\nSelectorIntentRoleV1: "
        + json.dumps(
            {"schema_version": G1J_SELECTOR_INTENT_INPUT_PROTOCOL},
            ensure_ascii=False,
            sort_keys=False,
            separators=(",", ":"),
        )
    )


def _g1j_render_step(value: Any) -> str:
    return selector_intent.render_prompt(_g1j_values(value))


def _g1j_input_digest(value: Any) -> str:
    return canonical_digest(
        {
            "bootstrap": _g1j_render_bootstrap(value),
            "step": _g1j_render_step(value),
        }
    )


_G1J_PROTOCOL = NetworkSelectorInputProtocol(
    schema_version=G1J_SELECTOR_INTENT_INPUT_PROTOCOL,
    endpoint="/selector-intent-v1/select",
    menu_prefix="SelectorIntentMenuV1: ",
    task_marker="\nSelectorIntentRoleV1: ",
    task_prefix="SelectorIntentRoleV1: ",
    step_prefix="SelectorIntentPromptV1: ",
    bootstrap_payload=_g1j_bootstrap_payload,
    input_digest=_g1j_input_digest,
    menu_digest=_g1j_menu_digest,
    render_bootstrap=_g1j_render_bootstrap,
    render_step=_g1j_render_step,
)

CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL = G1J_SELECTOR_INTENT_INPUT_PROTOCOL
SUPPORTED_NETWORK_SELECTOR_INPUT_PROTOCOLS = frozenset(
    {G1J_SELECTOR_INTENT_INPUT_PROTOCOL}
)


def network_selector_input_protocol(version: str) -> NetworkSelectorInputProtocol:
    if str(version) != G1J_SELECTOR_INTENT_INPUT_PROTOCOL:
        raise ValueError("unsupported network Selector input protocol")
    return _G1J_PROTOCOL


__all__ = [
    "CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL",
    "G1J_SELECTOR_INTENT_HEAD_ID",
    "G1J_SELECTOR_INTENT_INPUT_PROTOCOL",
    "G1J_SELECTOR_TRAINING_TRAJECTORY_MODE",
    "SUPPORTED_NETWORK_SELECTOR_INPUT_PROTOCOLS",
    "NetworkSelectorInputProtocol",
    "network_selector_input_protocol",
]
