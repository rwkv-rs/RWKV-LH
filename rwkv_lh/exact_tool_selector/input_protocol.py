"""Versioned render registry for independent Selector inputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from rwkv_lh.exact_tool_selector import (
    compact_protocol_v3,
    compact_protocol_v4,
    compact_protocol_v5,
    compact_protocol_v6,
    compact_protocol_v7,
)


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


_PROTOCOLS = {
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
SUPPORTED_NETWORK_SELECTOR_INPUT_PROTOCOLS = frozenset(_PROTOCOLS)


def network_selector_input_protocol(version: str) -> NetworkSelectorInputProtocol:
    try:
        return _PROTOCOLS[str(version)]
    except KeyError as exc:
        raise ValueError("unsupported network Selector input protocol") from exc


__all__ = [
    "DEFAULT_NETWORK_SELECTOR_INPUT_PROTOCOL",
    "CURRENT_QUESTION_LAST_NETWORK_SELECTOR_INPUT_PROTOCOL",
    "FULL_REQUEST_LAST_NETWORK_SELECTOR_INPUT_PROTOCOL",
    "REQUEST_LAST_NETWORK_SELECTOR_INPUT_PROTOCOL",
    "REQUIREMENT_BYTE_TAIL_NETWORK_SELECTOR_INPUT_PROTOCOL",
    "SUPPORTED_NETWORK_SELECTOR_INPUT_PROTOCOLS",
    "NetworkSelectorInputProtocol",
    "network_selector_input_protocol",
]
