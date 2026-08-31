"""Minimal task/progress/name/description protocol for network takeover."""

from __future__ import annotations

from dataclasses import dataclass

from rwkv_lh.exact_tool_selector.network_protocol import network_selector_tool_menu
from rwkv_lh.exact_tool_selector.protocol import canonical_digest, canonical_json
from rwkv_lh.exact_tool_selector.takeover_model_v4 import NETWORK_TAKEOVER_LABELS


NETWORK_TAKEOVER_QUERY_SCHEMA = "rwkv-lh.network-takeover-query.v1"
_MODES = frozenset({"fresh", "continuation"})
_EVIDENCE_STATES = frozenset(
    {"none", "evidence_missing", "evidence_partial", "evidence_committed"}
)
_POLICY_STATES = frozenset({"network_allowed", "network_denied"})


def network_takeover_tool_menu() -> tuple[dict[str, str], ...]:
    descriptions = {
        item["name"]: item["description"] for item in network_selector_tool_menu()
    }
    return (
        {"name": "web_search", "description": descriptions["web_search"]},
        {
            "name": "connector_lookup",
            "description": descriptions["connector_lookup"],
        },
        {
            "name": "DEFER",
            "description": (
                "Do not take over this stage; leave local, deterministic, final, "
                "ambiguous, or unsupported tool selection to the existing Executor."
            ),
        },
    )


@dataclass(frozen=True)
class NetworkTakeoverProgress:
    mode: str = "fresh"
    evidence_state: str = "none"
    policy_state: str = "network_allowed"

    def __post_init__(self) -> None:
        if self.mode not in _MODES:
            raise ValueError("network takeover mode is invalid")
        if self.evidence_state not in _EVIDENCE_STATES:
            raise ValueError("network takeover evidence state is invalid")
        if self.policy_state not in _POLICY_STATES:
            raise ValueError("network takeover policy state is invalid")
        if self.mode == "fresh" and self.evidence_state != "none":
            raise ValueError("fresh network takeover input requires evidence_state=none")

    def to_dict(self) -> dict[str, str]:
        return {
            "mode": self.mode,
            "evidence_state": self.evidence_state,
            "policy_state": self.policy_state,
        }


@dataclass(frozen=True)
class NetworkTakeoverInput:
    objective: str
    progress: NetworkTakeoverProgress = NetworkTakeoverProgress()

    def __post_init__(self) -> None:
        if not self.objective.strip():
            raise ValueError("network takeover objective must be non-empty")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": NETWORK_TAKEOVER_QUERY_SCHEMA,
            "objective": self.objective,
            "progress": self.progress.to_dict(),
            "tools": [dict(item) for item in network_takeover_tool_menu()],
        }

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def render(self) -> str:
        return "NetworkTakeoverQueryV1: " + canonical_json(self.to_dict())


def validate_takeover_label(label: str) -> str:
    value = str(label or "")
    if value not in NETWORK_TAKEOVER_LABELS:
        raise ValueError(f"unknown network takeover label: {value!r}")
    return value


__all__ = [
    "NETWORK_TAKEOVER_QUERY_SCHEMA",
    "NetworkTakeoverInput",
    "NetworkTakeoverProgress",
    "network_takeover_tool_menu",
    "validate_takeover_label",
]
