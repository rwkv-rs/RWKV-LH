"""Versioned render registry for independent Selector inputs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from rwkv_lh.exact_tool_selector import (
    compact_protocol_v3,
    compact_protocol_v4,
    compact_protocol_v5,
    compact_protocol_v6,
    compact_protocol_v7,
    compact_protocol_v8,
)
from rwkv_lh.exact_tool_selector.compact_protocol_v3 import (
    compact_selector_tool_menu,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest, canonical_json
from rwkv_lh.goal_state_protocols import selector_intent


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
    menu_digest: Callable[[], str]
    render_bootstrap: Callable[[Any], str]
    render_step: Callable[[Any], str]
    current_requirement_in_step: bool = False
    current_question_in_step: bool = False
    frontier_only_in_step: bool = False
    g1j_selector_intent: bool = False


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


def _g1j_menu_digest() -> str:
    return canonical_digest(
        {
            "schema_version": G1J_SELECTOR_INTENT_MENU_SCHEMA_VERSION,
            "tools": [dict(item) for item in compact_selector_tool_menu()],
        }
    )


def _g1j_bootstrap_payload(value: Any) -> dict[str, Any]:
    _g1j_values(value)
    return {
        "menu_digest": _g1j_menu_digest(),
        "menu_schema_version": G1J_SELECTOR_INTENT_MENU_SCHEMA_VERSION,
        "schema_version": G1J_SELECTOR_INTENT_INPUT_PROTOCOL,
        "tools": [dict(item) for item in compact_selector_tool_menu()],
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


_PROTOCOLS = {
    G1J_SELECTOR_INTENT_INPUT_PROTOCOL: NetworkSelectorInputProtocol(
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
        frontier_only_in_step=True,
        g1j_selector_intent=True,
    ),
    compact_protocol_v3.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION: NetworkSelectorInputProtocol(
        schema_version=compact_protocol_v3.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        endpoint="/v3/select",
        menu_prefix="SelectorMenuV3: ",
        task_marker="\nSelectorTaskV3: ",
        task_prefix="SelectorTaskV3: ",
        step_prefix="SelectorStepV3: ",
        bootstrap_payload=compact_protocol_v3.compact_selector_bootstrap_payload,
        input_digest=compact_protocol_v3.compact_selector_input_digest,
        menu_digest=compact_protocol_v3.compact_selector_menu_digest,
        render_bootstrap=compact_protocol_v3.render_compact_selector_bootstrap,
        render_step=compact_protocol_v3.render_compact_selector_step,
    ),
    compact_protocol_v4.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION: NetworkSelectorInputProtocol(
        schema_version=compact_protocol_v4.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        endpoint="/v4/select",
        menu_prefix="SelectorMenuV4: ",
        task_marker="\nSelectorTaskV4: ",
        task_prefix="SelectorTaskV4: ",
        step_prefix="SelectorStepV4: ",
        bootstrap_payload=compact_protocol_v4.compact_selector_bootstrap_payload,
        input_digest=compact_protocol_v4.compact_selector_input_digest,
        menu_digest=compact_protocol_v4.compact_selector_menu_digest,
        render_bootstrap=compact_protocol_v4.render_compact_selector_bootstrap,
        render_step=compact_protocol_v4.render_compact_selector_step,
    ),
    compact_protocol_v5.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION: NetworkSelectorInputProtocol(
        schema_version=compact_protocol_v5.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        endpoint="/v5/select",
        menu_prefix="SelectorMenuV5: ",
        task_marker="\nSelectorTaskIdentityV5: ",
        task_prefix="SelectorTaskIdentityV5: ",
        step_prefix="SelectorStepV5: ",
        bootstrap_payload=compact_protocol_v5.compact_selector_bootstrap_payload,
        input_digest=compact_protocol_v5.compact_selector_input_digest,
        menu_digest=compact_protocol_v5.compact_selector_menu_digest,
        render_bootstrap=compact_protocol_v5.render_compact_selector_bootstrap,
        render_step=compact_protocol_v5.render_compact_selector_step,
        current_requirement_in_step=True,
    ),
    compact_protocol_v6.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION: NetworkSelectorInputProtocol(
        schema_version=compact_protocol_v6.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        endpoint="/v6/select",
        menu_prefix="SelectorMenuV6: ",
        task_marker="\nSelectorTaskIdentityV6: ",
        task_prefix="SelectorTaskIdentityV6: ",
        step_prefix="SelectorStepV6: ",
        bootstrap_payload=compact_protocol_v6.compact_selector_bootstrap_payload,
        input_digest=compact_protocol_v6.compact_selector_input_digest,
        menu_digest=compact_protocol_v6.compact_selector_menu_digest,
        render_bootstrap=compact_protocol_v6.render_compact_selector_bootstrap,
        render_step=compact_protocol_v6.render_compact_selector_step,
        current_question_in_step=True,
    ),
    compact_protocol_v7.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION: NetworkSelectorInputProtocol(
        schema_version=compact_protocol_v7.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        endpoint="/v7/select",
        menu_prefix="SelectorMenuV7: ",
        task_marker="\nSelectorTaskIdentityV7: ",
        task_prefix="SelectorTaskIdentityV7: ",
        step_prefix="SelectorStepV7: ",
        bootstrap_payload=compact_protocol_v7.compact_selector_bootstrap_payload,
        input_digest=compact_protocol_v7.compact_selector_input_digest,
        menu_digest=compact_protocol_v7.compact_selector_menu_digest,
        render_bootstrap=compact_protocol_v7.render_compact_selector_bootstrap,
        render_step=compact_protocol_v7.render_compact_selector_step,
        current_question_in_step=True,
    ),
    compact_protocol_v8.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION: NetworkSelectorInputProtocol(
        schema_version=compact_protocol_v8.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        endpoint="/v8/select",
        menu_prefix="SelectorMenuV8: ",
        task_marker="\nSelectorRoleV8: ",
        task_prefix="SelectorRoleV8: ",
        step_prefix="SelectorStepV8: ",
        bootstrap_payload=compact_protocol_v8.compact_selector_bootstrap_payload,
        input_digest=compact_protocol_v8.compact_selector_input_digest,
        menu_digest=compact_protocol_v8.compact_selector_menu_digest,
        render_bootstrap=compact_protocol_v8.render_compact_selector_bootstrap,
        render_step=compact_protocol_v8.render_compact_selector_step,
        frontier_only_in_step=True,
    ),
}

DEFAULT_NETWORK_SELECTOR_INPUT_PROTOCOL = (
    compact_protocol_v3.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION
)
REQUEST_LAST_NETWORK_SELECTOR_INPUT_PROTOCOL = (
    compact_protocol_v4.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION
)
FULL_REQUEST_LAST_NETWORK_SELECTOR_INPUT_PROTOCOL = (
    compact_protocol_v5.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION
)
CURRENT_QUESTION_LAST_NETWORK_SELECTOR_INPUT_PROTOCOL = (
    compact_protocol_v6.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION
)
REQUIREMENT_BYTE_TAIL_NETWORK_SELECTOR_INPUT_PROTOCOL = (
    compact_protocol_v7.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION
)
FRONTIER_QUESTION_TAIL_NETWORK_SELECTOR_INPUT_PROTOCOL = (
    compact_protocol_v8.COMPACT_SELECTOR_INPUT_SCHEMA_VERSION
)
CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL = G1J_SELECTOR_INTENT_INPUT_PROTOCOL
SUPPORTED_NETWORK_SELECTOR_INPUT_PROTOCOLS = frozenset(_PROTOCOLS)


def network_selector_input_protocol(version: str) -> NetworkSelectorInputProtocol:
    try:
        return _PROTOCOLS[str(version)]
    except KeyError as exc:
        raise ValueError("unsupported network Selector input protocol") from exc


__all__ = [
    "DEFAULT_NETWORK_SELECTOR_INPUT_PROTOCOL",
    "CURRENT_QUESTION_LAST_NETWORK_SELECTOR_INPUT_PROTOCOL",
    "CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL",
    "FULL_REQUEST_LAST_NETWORK_SELECTOR_INPUT_PROTOCOL",
    "G1J_SELECTOR_INTENT_HEAD_ID",
    "G1J_SELECTOR_TRAINING_TRAJECTORY_MODE",
    "FRONTIER_QUESTION_TAIL_NETWORK_SELECTOR_INPUT_PROTOCOL",
    "REQUEST_LAST_NETWORK_SELECTOR_INPUT_PROTOCOL",
    "REQUIREMENT_BYTE_TAIL_NETWORK_SELECTOR_INPUT_PROTOCOL",
    "SUPPORTED_NETWORK_SELECTOR_INPUT_PROTOCOLS",
    "NetworkSelectorInputProtocol",
    "network_selector_input_protocol",
]
