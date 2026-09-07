"""The sole production render contract for the G1J Selector-Intent lane.

Exactly one Selector input protocol exists: failure-aware Selector Intent v4.
Production serving, StateTune data generation, and acceptance evaluation all
render through :data:`CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL`. Any other
schema is rejected; historical protocol implementations are not retained.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from rwkv_lh.goal_state_protocols import selector_intent_v4
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


G1J_SELECTOR_INTENT_V4_INPUT_PROTOCOL = selector_intent_v4.INPUT_SCHEMA_VERSION
G1J_SELECTOR_V4_RUNTIME_TRAJECTORY_MODE = "fresh-current-subtask-failure-aware.v1"
G1J_SELECTOR_INTENT_V4_MENU_SCHEMA_VERSION = selector_intent_v4.MENU_SCHEMA_VERSION


def _g1j_v4_values(value: Any) -> dict[str, Any]:
    source = value.to_dict() if hasattr(value, "to_dict") else dict(value)
    progress = source.get("current_progress")
    if not isinstance(progress, dict):
        raise ValueError("Selector Intent v4 requires current_progress")
    return selector_intent_v4.build_prompt_source(
        current_subtask=source["current_subtask"],
        current_progress=progress,
        eligible_labels=source["eligible_labels"],
    )


def _g1j_v4_menu_digest(value: Any) -> str:
    return canonical_digest(
        {
            "schema_version": G1J_SELECTOR_INTENT_V4_MENU_SCHEMA_VERSION,
            "tools": [dict(item) for item in value.menu],
        }
    )


def _g1j_v4_bootstrap_payload(value: Any) -> dict[str, Any]:
    _g1j_v4_values(value)
    return {
        "menu_digest": _g1j_v4_menu_digest(value),
        "menu_schema_version": G1J_SELECTOR_INTENT_V4_MENU_SCHEMA_VERSION,
        "schema_version": G1J_SELECTOR_INTENT_V4_INPUT_PROTOCOL,
        "tools": [dict(item) for item in value.menu],
    }


def _g1j_v4_render_bootstrap(value: Any) -> str:
    payload = _g1j_v4_bootstrap_payload(value)
    return (
        selector_intent_v4.MENU_PREFIX
        + canonical_json(payload)
        + selector_intent_v4.ROLE_MARKER
        + json.dumps(
            {"schema_version": G1J_SELECTOR_INTENT_V4_INPUT_PROTOCOL},
            ensure_ascii=False,
            sort_keys=False,
            separators=(",", ":"),
        )
    )


def _g1j_v4_render_step(value: Any) -> str:
    return selector_intent_v4.render_prompt(_g1j_v4_values(value))


def _g1j_v4_input_digest(value: Any) -> str:
    return canonical_digest(
        {
            "bootstrap": _g1j_v4_render_bootstrap(value),
            "step": _g1j_v4_render_step(value),
        }
    )


_G1J_V4_PROTOCOL = NetworkSelectorInputProtocol(
    schema_version=G1J_SELECTOR_INTENT_V4_INPUT_PROTOCOL,
    endpoint=selector_intent_v4.ENDPOINT,
    menu_prefix=selector_intent_v4.MENU_PREFIX,
    task_marker=selector_intent_v4.ROLE_MARKER,
    task_prefix=selector_intent_v4.ROLE_PREFIX,
    step_prefix=selector_intent_v4.PROMPT_PREFIX,
    bootstrap_payload=_g1j_v4_bootstrap_payload,
    input_digest=_g1j_v4_input_digest,
    menu_digest=_g1j_v4_menu_digest,
    render_bootstrap=_g1j_v4_render_bootstrap,
    render_step=_g1j_v4_render_step,
)

CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL = G1J_SELECTOR_INTENT_V4_INPUT_PROTOCOL
SUPPORTED_NETWORK_SELECTOR_INPUT_PROTOCOLS = frozenset(
    {G1J_SELECTOR_INTENT_V4_INPUT_PROTOCOL}
)


def network_selector_input_protocol(version: str) -> NetworkSelectorInputProtocol:
    selected = str(version)
    if selected == G1J_SELECTOR_INTENT_V4_INPUT_PROTOCOL:
        return _G1J_V4_PROTOCOL
    raise ValueError(
        f"unsupported network Selector input protocol {selected!r}; "
        f"only {G1J_SELECTOR_INTENT_V4_INPUT_PROTOCOL!r} is served"
    )


__all__ = [
    "CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL",
    "G1J_SELECTOR_INTENT_V4_INPUT_PROTOCOL",
    "G1J_SELECTOR_INTENT_V4_MENU_SCHEMA_VERSION",
    "G1J_SELECTOR_V4_RUNTIME_TRAJECTORY_MODE",
    "NetworkSelectorInputProtocol",
    "SUPPORTED_NETWORK_SELECTOR_INPUT_PROTOCOLS",
    "network_selector_input_protocol",
]
