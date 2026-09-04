"""Project exactly one Planner-owned current subtask into the Selector lane."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from rwkv_lh.exact_tool_selector.network_protocol import NetworkSelectorInput


SELECTOR_CURRENT_SUBTASK_PROJECTION_VERSION = (
    "rwkv-lh.selector-current-subtask.v1"
)
_PHASES = {"observe", "mutate", "execute", "derive_evidence"}


@dataclass(frozen=True)
class SelectorStageContext:
    """The complete semantic input for one independent Selector evaluation."""

    current_subtask: Mapping[str, object]

    def __post_init__(self) -> None:
        normalized = dict(self.current_subtask)
        # Share the production validator with serving and StateTune data.
        validated = NetworkSelectorInput.create(current_subtask=normalized)
        object.__setattr__(self, "current_subtask", validated.current_subtask)


def goal_frontier_selector_context(
    frontier: Mapping[str, object],
) -> SelectorStageContext:
    """Reduce one Controller frontier to the six Planner-owned subtask fields.

    Action results, audit transcripts, previous choices, counters, and WKV state
    are intentionally absent. If execution changes the required next action,
    the Controller/Planner must first publish a revised frontier.
    """

    objective = str(frontier.get("objective") or "").strip()
    phase = str(
        frontier.get("effective_phase") or frontier.get("phase") or ""
    ).strip()
    if not objective:
        raise ValueError("Goal frontier Selector context requires an objective")
    if phase not in _PHASES:
        raise ValueError("Goal frontier Selector context has an invalid phase")

    def strings(name: str) -> list[str]:
        raw = frontier.get(name) or ()
        if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
            raise ValueError(f"Goal frontier {name} must be a string sequence")
        values = [str(item).strip() for item in raw]
        if any(not item for item in values):
            raise ValueError(f"Goal frontier {name} contains an empty value")
        return values

    current_subtask = {
        "objective": objective,
        "phase": phase,
        "read_roots": strings("read_roots"),
        "write_roots": strings("write_roots"),
        "success_evidence": strings("success_evidence"),
        "constraints": strings("constraints"),
    }
    if not current_subtask["success_evidence"]:
        raise ValueError("Goal frontier Selector context requires success evidence")
    return SelectorStageContext(current_subtask=current_subtask)


def build_network_selector_input(
    stage_context: SelectorStageContext,
    *,
    eligible_labels: Sequence[str] | None = None,
    menu_order_id: str = "canonical",
) -> NetworkSelectorInput:
    """Build a fresh request; there is deliberately no parent-state argument."""

    values: dict[str, object] = {
        "current_subtask": dict(stage_context.current_subtask),
        "menu_order_id": menu_order_id,
    }
    if eligible_labels is not None:
        values["eligible_labels"] = tuple(str(item) for item in eligible_labels)
    return NetworkSelectorInput.create(**values)


__all__ = [
    "SELECTOR_CURRENT_SUBTASK_PROJECTION_VERSION",
    "SelectorStageContext",
    "build_network_selector_input",
    "goal_frontier_selector_context",
]
