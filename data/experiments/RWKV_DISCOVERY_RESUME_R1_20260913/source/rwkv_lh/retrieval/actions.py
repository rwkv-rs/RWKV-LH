"""Optional retrieval and deterministic tool extensions for ActionHarness.

The extensions are not installed into the default Harness implicitly.  A
caller must provide a backend, a network policy and an explicit provenance
resolver, then pass the returned mapping to ``ActionHarness(actions=...)``.
"""

from __future__ import annotations

import ast
import math
import operator
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Callable, Mapping, Protocol, Sequence
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from rwkv_lh.harness import ActionDefinition, ActionResult
from rwkv_lh.model_io import canonical_digest, canonical_json
from rwkv_lh.retrieval.contracts import (
    ExternalEvidenceEnvelope,
    ExternalEvidenceRequestMismatch,
    external_evidence_request_digest,
    validate_external_evidence_request,
)
from rwkv_lh.retrieval.policy import (
    EgressProvenance,
    NetworkPolicy,
)
from rwkv_lh.schema import GoalState


class RetrievalBackend(Protocol):
    """Execute one already-selected retrieval operation."""

    provider_name: str

    def execute(
        self,
        tool: str,
        arguments: Mapping[str, Any],
    ) -> ExternalEvidenceEnvelope: ...

    def recover(
        self,
        tool: str,
        arguments: Mapping[str, Any],
    ) -> ExternalEvidenceEnvelope | None: ...


ProvenanceResolver = Callable[
    [GoalState, str, Mapping[str, Any]],
    Mapping[str, EgressProvenance | str],
]
NetworkPolicyResolver = Callable[[GoalState], NetworkPolicy]


@dataclass
class FrozenRetrievalBackend:
    """A deterministic, network-free backend used before live integration."""

    responses: Mapping[str, ExternalEvidenceEnvelope]
    provider_name: str = "frozen-fixture"

    @staticmethod
    def request_key(tool: str, arguments: Mapping[str, Any]) -> str:
        return external_evidence_request_digest(tool, arguments)

    def execute(
        self,
        tool: str,
        arguments: Mapping[str, Any],
    ) -> ExternalEvidenceEnvelope:
        key = self.request_key(tool, arguments)
        envelope = self.responses.get(key)
        if envelope is None:
            raise KeyError(f"frozen retrieval fixture has no request {key}")
        return validate_external_evidence_request(
            envelope,
            tool=tool,
            arguments=arguments,
        )

    def recover(
        self,
        tool: str,
        arguments: Mapping[str, Any],
    ) -> ExternalEvidenceEnvelope | None:
        key = self.request_key(tool, arguments)
        envelope = self.responses.get(key)
        if envelope is None:
            return None
        return validate_external_evidence_request(
            envelope,
            tool=tool,
            arguments=arguments,
        )


_BINARY_OPERATORS: dict[type[ast.operator], Callable[[Any, Any], Any]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[Any], Any]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _safe_number(value: Any) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("calculator accepts only real numeric literals")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("calculator result must be finite")
    if abs(value) > 10**100:
        raise ValueError("calculator magnitude exceeds the fixed bound")
    return value


def _evaluate_expression(expression: str) -> int | float:
    text = str(expression or "").strip()
    if not text or len(text) > 256:
        raise ValueError("calculator expression must contain 1-256 characters")
    parsed = ast.parse(text, mode="eval")

    def evaluate(node: ast.AST, *, depth: int = 0) -> int | float:
        if depth > 32:
            raise ValueError("calculator expression is too deeply nested")
        if isinstance(node, ast.Expression):
            return evaluate(node.body, depth=depth + 1)
        if isinstance(node, ast.Constant):
            return _safe_number(node.value)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
            return _safe_number(
                _UNARY_OPERATORS[type(node.op)](
                    evaluate(node.operand, depth=depth + 1)
                )
            )
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
            left = evaluate(node.left, depth=depth + 1)
            right = evaluate(node.right, depth=depth + 1)
            if isinstance(node.op, ast.Pow) and abs(right) > 1000:
                raise ValueError("calculator exponent exceeds the fixed bound")
            return _safe_number(_BINARY_OPERATORS[type(node.op)](left, right))
        raise ValueError("calculator expression contains an unsupported operation")

    return evaluate(parsed)


def _deterministic_output(tool: str, arguments: Mapping[str, Any], value: Any) -> str:
    return canonical_json(
        {
            "contract": "rwkv-lh.deterministic-result.v1",
            "tool": tool,
            "arguments_digest": canonical_digest(dict(arguments)),
            "value": value,
        }
    )


def build_retrieval_actions(
    *,
    backend: RetrievalBackend,
    network_policy: NetworkPolicy,
    provenance_resolver: ProvenanceResolver,
    network_policy_resolver: NetworkPolicyResolver | None = None,
    connector_operations: Sequence[str] | None = None,
    include_network_actions: bool = False,
    clock: Callable[[], datetime] | None = None,
) -> dict[
    str,
    tuple[
        ActionDefinition,
        Callable[[GoalState, dict[str, Any]], ActionResult],
    ]
    | tuple[
        ActionDefinition,
        Callable[[GoalState, dict[str, Any]], ActionResult],
        Callable[[GoalState, dict[str, Any]], ActionResult | None],
    ],
]:
    """Build deterministic tools and policy-gated network tools when exposed.

    ``include_network_actions`` keeps the two network definitions visible for a
    fixed full-menu Selector even when the registration policy is offline.  A
    product runtime supplies ``network_policy_resolver`` so authorization is
    derived from the immutable Goal; the registration policy then controls only
    which definitions exist and cannot become a second per-run authority.
    """

    if not callable(provenance_resolver):
        raise TypeError("retrieval actions require an explicit provenance resolver")
    if network_policy_resolver is not None and not callable(network_policy_resolver):
        raise TypeError("network policy resolver must be callable")
    now = clock or (lambda: datetime.now(timezone.utc))
    configured_connector_operations = tuple(
        dict.fromkeys(
            str(item).strip()
            for item in (
                connector_operations
                if connector_operations is not None
                else (
                    "github_repository",
                    "github_release",
                    "github_commit",
                    "github_code",
                    "package_release",
                    "scholarly_record",
                    "weather",
                    "weather_alerts",
                )
            )
            if str(item).strip()
        )
    )

    def policy_for(goal: GoalState) -> NetworkPolicy:
        selected = (
            network_policy_resolver(goal)
            if network_policy_resolver is not None
            else network_policy
        )
        if not isinstance(selected, NetworkPolicy):
            raise TypeError("network policy resolver must return NetworkPolicy")
        return selected

    def request_binding_failure(
        tool: str,
        decision,
        error: ExternalEvidenceRequestMismatch,
        *,
        recovered: bool,
    ) -> ActionResult:
        metadata = {
            "network_policy": decision.to_dict(),
            "provider": str(backend.provider_name),
            "request_binding_valid": False,
        }
        if recovered:
            metadata["committed_snapshot_recovery_attempted"] = True
        return ActionResult(
            tool,
            False,
            metadata=metadata,
            error={
                "type": type(error).__name__,
                "message": str(error),
            },
        )

    def envelope_result(
        tool: str,
        arguments: Mapping[str, Any],
        envelope: ExternalEvidenceEnvelope,
        decision,
        *,
        recovered: bool = False,
    ) -> ActionResult:
        try:
            validate_external_evidence_request(
                envelope,
                tool=tool,
                arguments=arguments,
            )
        except ExternalEvidenceRequestMismatch as exc:
            return request_binding_failure(
                tool,
                decision,
                exc,
                recovered=recovered,
            )
        external = envelope.to_dict()
        metadata = {
            "external_evidence": external,
            "network_policy": decision.to_dict(),
            "provider": str(backend.provider_name),
        }
        if recovered:
            metadata["recovered_committed_snapshot"] = True
        if envelope.status == "provider_unavailable":
            return ActionResult(
                tool,
                False,
                output=canonical_json(external),
                metadata=metadata,
                error={
                    "type": "RetrievalProviderUnavailable",
                    "message": "all selected retrieval providers were unavailable",
                },
                outcome_type="provider_unavailable",
            )
        return ActionResult(
            tool,
            True,
            output=canonical_json(external),
            evidence=[item.to_dict() for item in envelope.records],
            metadata=metadata,
        )

    def network_handler(
        tool: str,
    ) -> Callable[[GoalState, dict[str, Any]], ActionResult]:
        def execute(goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
            labels = provenance_resolver(goal, tool, arguments)
            decision = policy_for(goal).authorize(
                tool=tool,
                arguments=arguments,
                provenance=labels,
            )
            if not decision.allowed:
                return ActionResult(
                    tool,
                    False,
                    output=canonical_json(
                        {
                            "contract": "rwkv-lh.network-policy-result.v1",
                            "decision": decision.to_dict(),
                        }
                    ),
                    metadata={"network_policy": decision.to_dict()},
                    error={
                        "type": "NetworkPolicyRejected",
                        "message": decision.reason,
                        "rejected_fields": list(decision.rejected_fields),
                    },
                )
            try:
                envelope = backend.execute(tool, arguments)
            except ExternalEvidenceRequestMismatch as exc:
                return request_binding_failure(
                    tool,
                    decision,
                    exc,
                    recovered=False,
                )
            except Exception as exc:
                return ActionResult(
                    tool,
                    False,
                    metadata={
                        "network_policy": decision.to_dict(),
                        "provider": str(backend.provider_name),
                    },
                    error={
                        "type": type(exc).__name__,
                        "message": str(exc)[:2000],
                    },
                )
            return envelope_result(tool, arguments, envelope, decision)

        return execute

    def network_recovery_handler(
        tool: str,
    ) -> Callable[[GoalState, dict[str, Any]], ActionResult | None]:
        def recover(
            goal: GoalState,
            arguments: dict[str, Any],
        ) -> ActionResult | None:
            labels = provenance_resolver(goal, tool, arguments)
            decision = policy_for(goal).authorize(
                tool=tool,
                arguments=arguments,
                provenance=labels,
            )
            if not decision.allowed:
                return ActionResult(
                    tool,
                    False,
                    metadata={"network_policy": decision.to_dict()},
                    error={
                        "type": "NetworkPolicyRejected",
                        "message": decision.reason,
                        "rejected_fields": list(decision.rejected_fields),
                    },
                )
            recover_method = getattr(backend, "recover", None)
            if not callable(recover_method):
                return None
            try:
                envelope = recover_method(tool, arguments)
            except ExternalEvidenceRequestMismatch as exc:
                return request_binding_failure(
                    tool,
                    decision,
                    exc,
                    recovered=True,
                )
            if envelope is None:
                return None
            return envelope_result(
                tool,
                arguments,
                envelope,
                decision,
                recovered=True,
            )

        return recover

    def calculator_handler(
        _goal: GoalState,
        arguments: dict[str, Any],
    ) -> ActionResult:
        try:
            value = _evaluate_expression(str(arguments.get("expression") or ""))
        except Exception as exc:
            return ActionResult(
                "calculator",
                False,
                error={"type": type(exc).__name__, "message": str(exc)[:2000]},
            )
        return ActionResult(
            "calculator",
            True,
            output=_deterministic_output("calculator", arguments, value),
            metadata={"deterministic": True},
        )

    def date_diff_handler(
        _goal: GoalState,
        arguments: dict[str, Any],
    ) -> ActionResult:
        try:
            left = date.fromisoformat(str(arguments.get("date_a") or ""))
            right = date.fromisoformat(str(arguments.get("date_b") or ""))
            value = abs((right - left).days)
        except Exception as exc:
            return ActionResult(
                "date_diff",
                False,
                error={"type": type(exc).__name__, "message": str(exc)[:2000]},
            )
        return ActionResult(
            "date_diff",
            True,
            output=_deterministic_output("date_diff", arguments, value),
            metadata={"deterministic": True, "unit": "calendar_days"},
        )

    def current_time_handler(
        _goal: GoalState,
        arguments: dict[str, Any],
    ) -> ActionResult:
        timezone_name = str(arguments.get("timezone") or "UTC")
        try:
            zone = ZoneInfo(timezone_name)
            observed = now()
            if observed.tzinfo is None:
                raise ValueError("current_time clock must return an aware datetime")
            value = observed.astimezone(zone).isoformat(timespec="seconds")
        except (ValueError, ZoneInfoNotFoundError) as exc:
            return ActionResult(
                "current_time",
                False,
                error={"type": type(exc).__name__, "message": str(exc)[:2000]},
            )
        return ActionResult(
            "current_time",
            True,
            output=_deterministic_output("current_time", arguments, value),
            metadata={"deterministic": False, "observed_timezone": timezone_name},
        )

    web_search = ActionDefinition(
        "web_search",
        (
            "Search/fetch a public exact URL or the general web and return "
            "content-addressed exact evidence records."
        ),
        True,
        False,
        False,
        60.0,
        {
            "query": {"type": "string", "minLength": 1},
            "max_results": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10,
                "default": 5,
            },
        },
        required_arguments=("query",),
        capability_class="network.public_web",
        network_access="public_web",
        data_boundary="public_external",
        side_effect_class="external_read_only",
        result_schema="rwkv-lh.external-evidence.v1",
        cache_policy="per_run_immutable_snapshot",
        recovery_policy="resume_committed_snapshot_or_do_not_replay_unknown",
        evidence_output=True,
    )
    connector_lookup = ActionDefinition(
        "connector_lookup",
        (
            "Query one structured public source for an exact repository, package, "
            "scholarly record, weather observation, or alert."
        ),
        True,
        False,
        False,
        60.0,
        {
            "operation": {
                "type": "string",
                "enum": list(configured_connector_operations),
            },
            "query": {"type": "string", "minLength": 1},
        },
        required_arguments=("operation", "query"),
        capability_class="network.structured_source",
        network_access="structured_source",
        data_boundary="public_external",
        side_effect_class="external_read_only",
        result_schema="rwkv-lh.external-evidence.v1",
        cache_policy="per_run_immutable_snapshot",
        recovery_policy="resume_committed_snapshot_or_do_not_replay_unknown",
        evidence_output=True,
    )
    calculator = ActionDefinition(
        "calculator",
        "Safely evaluate one complete arithmetic expression with known operands.",
        True,
        False,
        True,
        5.0,
        {"expression": {"type": "string", "minLength": 1}},
        required_arguments=("expression",),
        capability_class="deterministic.compute",
        data_boundary="model_literal",
        side_effect_class="read_only",
        result_schema="rwkv-lh.deterministic-result.v1",
        cache_policy="content_addressed",
    )
    date_diff = ActionDefinition(
        "date_diff",
        "Calculate the absolute calendar-day distance between two known ISO dates.",
        True,
        False,
        True,
        5.0,
        {
            "date_a": {"type": "string", "minLength": 10},
            "date_b": {"type": "string", "minLength": 10},
            "source_a": {"type": "string", "default": ""},
            "source_b": {"type": "string", "default": ""},
        },
        required_arguments=("date_a", "date_b"),
        capability_class="deterministic.compute",
        data_boundary="observed_fact",
        side_effect_class="read_only",
        result_schema="rwkv-lh.deterministic-result.v1",
        cache_policy="content_addressed",
    )
    current_time = ActionDefinition(
        "current_time",
        "Observe the current clock reading for one IANA timezone.",
        True,
        False,
        False,
        5.0,
        {"timezone": {"type": "string", "default": "UTC", "minLength": 1}},
        capability_class="deterministic.clock",
        data_boundary="local_clock",
        side_effect_class="read_only_time_sensitive",
        result_schema="rwkv-lh.deterministic-result.v1",
        cache_policy="never",
        recovery_policy="do_not_replay_unknown",
    )

    actions = {
        "calculator": (calculator, calculator_handler),
        "date_diff": (date_diff, date_diff_handler),
        "current_time": (current_time, current_time_handler),
    }
    if network_policy.mode.value != "offline" or include_network_actions:
        actions = {
            "web_search": (
                web_search,
                network_handler("web_search"),
                network_recovery_handler("web_search"),
            ),
            "connector_lookup": (
                connector_lookup,
                network_handler("connector_lookup"),
                network_recovery_handler("connector_lookup"),
            ),
            **actions,
        }
    return actions


__all__ = [
    "FrozenRetrievalBackend",
    "NetworkPolicyResolver",
    "ProvenanceResolver",
    "RetrievalBackend",
    "build_retrieval_actions",
]
