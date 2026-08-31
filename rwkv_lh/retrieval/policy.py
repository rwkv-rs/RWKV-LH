"""Fail-closed network and egress policy contracts.

The policy accepts or rejects one already model-authored call.  It never
selects another tool, rewrites a query or removes sensitive values.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping


class NetworkPolicyMode(str, Enum):
    OFFLINE = "offline"
    AUTO_PUBLIC = "auto_public"
    EXPLICIT_EGRESS = "explicit_egress"


class EgressProvenance(str, Enum):
    USER_PUBLIC_LITERAL = "user_public_literal"
    MODEL_PUBLIC_QUERY = "model_public_query"
    WORKSPACE_PUBLIC = "workspace_public"
    WORKSPACE_SENSITIVE = "workspace_sensitive"
    SECRET = "secret"
    TOOL_UNTRUSTED = "tool_untrusted"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class NetworkPolicyDecision:
    allowed: bool
    reason: str
    tool: str
    mode: NetworkPolicyMode
    rejected_fields: tuple[str, ...] = ()
    controller_rewritten: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "tool": self.tool,
            "mode": self.mode.value,
            "rejected_fields": list(self.rejected_fields),
            "controller_rewritten": self.controller_rewritten,
        }


@dataclass(frozen=True)
class NetworkPolicy:
    mode: NetworkPolicyMode = NetworkPolicyMode.OFFLINE
    explicit_approval: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.mode, NetworkPolicyMode):
            object.__setattr__(self, "mode", NetworkPolicyMode(str(self.mode)))

    def authorize(
        self,
        *,
        tool: str,
        arguments: Mapping[str, Any],
        provenance: Mapping[str, EgressProvenance | str],
    ) -> NetworkPolicyDecision:
        operation = str(tool or "").strip()
        if self.mode == NetworkPolicyMode.OFFLINE:
            return NetworkPolicyDecision(
                False,
                "network_disabled",
                operation,
                self.mode,
            )

        outbound_fields = tuple(
            key
            for key, value in arguments.items()
            if isinstance(value, str) and value.strip()
        )
        missing = tuple(key for key in outbound_fields if key not in provenance)
        if missing:
            return NetworkPolicyDecision(
                False,
                "egress_provenance_missing",
                operation,
                self.mode,
                missing,
            )

        normalized: dict[str, EgressProvenance] = {}
        invalid: list[str] = []
        for key in outbound_fields:
            try:
                raw_label = provenance[key]
                normalized[key] = (
                    raw_label
                    if isinstance(raw_label, EgressProvenance)
                    else EgressProvenance(str(raw_label))
                )
            except (TypeError, ValueError):
                invalid.append(key)
        if invalid:
            return NetworkPolicyDecision(
                False,
                "egress_provenance_invalid",
                operation,
                self.mode,
                tuple(invalid),
            )

        forbidden = tuple(
            key
            for key, label in normalized.items()
            if label
            in {
                EgressProvenance.WORKSPACE_SENSITIVE,
                EgressProvenance.SECRET,
                EgressProvenance.TOOL_UNTRUSTED,
                EgressProvenance.UNKNOWN,
            }
        )
        if forbidden:
            return NetworkPolicyDecision(
                False,
                "sensitive_egress_forbidden",
                operation,
                self.mode,
                forbidden,
            )

        if self.mode == NetworkPolicyMode.AUTO_PUBLIC:
            non_public = tuple(
                key
                for key, label in normalized.items()
                if label
                not in {
                    EgressProvenance.USER_PUBLIC_LITERAL,
                    EgressProvenance.MODEL_PUBLIC_QUERY,
                }
            )
            if non_public:
                return NetworkPolicyDecision(
                    False,
                    "auto_public_rejects_workspace_egress",
                    operation,
                    self.mode,
                    non_public,
                )

        if (
            self.mode == NetworkPolicyMode.EXPLICIT_EGRESS
            and any(
                label == EgressProvenance.WORKSPACE_PUBLIC
                for label in normalized.values()
            )
            and not self.explicit_approval
        ):
            return NetworkPolicyDecision(
                False,
                "explicit_egress_approval_required",
                operation,
                self.mode,
                tuple(
                    key
                    for key, label in normalized.items()
                    if label == EgressProvenance.WORKSPACE_PUBLIC
                ),
            )

        return NetworkPolicyDecision(
            True,
            "allowed",
            operation,
            self.mode,
        )


__all__ = [
    "EgressProvenance",
    "NetworkPolicy",
    "NetworkPolicyDecision",
    "NetworkPolicyMode",
]
