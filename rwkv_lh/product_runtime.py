"""Construct one product Controller from immutable persisted run policy."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Callable, Mapping

from rwkv_lh.exact_tool_selector.network_client import (
    NetworkExactToolSelectorClient,
    NetworkExactToolSelectorSettings,
)
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import create_model_session
from rwkv_lh.retrieval import build_product_harness, retrieval_policy_from_goal
from rwkv_lh.runtime.executor_profiles import executor_profile_binding_for_run
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.run_lifecycle import goal_self_termination_only
from rwkv_lh.schema import RunState
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.stateful_goal_loop import StatefulGoalLoopController
from rwkv_lh.supervisor_openai import (
    OpenAICompatibleSupervisorClient,
    supervisor_policy_from_env,
)
from rwkv_lh.trace_projection import projected_tool_outputs


AuditHook = Callable[[Mapping[str, Any]], None]


def _product_tool_selector() -> NetworkExactToolSelectorClient | None:
    from rwkv_lh.runtime.settings import load_local_env

    load_local_env()
    settings = NetworkExactToolSelectorSettings.from_env()
    return (
        NetworkExactToolSelectorClient(settings)
        if settings is not None
        else None
    )


def _prior_tool_outputs(store: LongHorizonStore, run_id: str) -> tuple[str, ...]:
    """Return prior action outputs as untrusted provenance, not as authority."""
    current = store.load(run_id)
    outputs: list[str] = list(projected_tool_outputs(current))
    for action in current.actions.values():
        result = action.result
        if not isinstance(result, Mapping):
            continue
        evidence = result.get("evidence")
        if isinstance(evidence, list):
            for item in evidence:
                if not isinstance(item, Mapping):
                    continue
                for span in item.get("exact_spans") or ():
                    if isinstance(span, Mapping) and str(span.get("text") or "").strip():
                        outputs.append(str(span["text"]))
    return tuple(outputs)


def supervisor_mode_from_policy(value: Mapping[str, Any]) -> str:
    raw = value.get("supervisor")
    selected = raw if isinstance(raw, Mapping) else {}
    mode = str(selected.get("mode") or "stateful_goal").strip()
    if mode != "stateful_goal":
        raise ValueError(
            "the product runtime supports only the latest stateful_goal architecture"
        )
    raw_router = value.get("state_router")
    selected_router = raw_router if isinstance(raw_router, Mapping) else {}
    router_mode = str(selected_router.get("mode") or "disabled").strip()
    if router_mode != "disabled":
        raise ValueError(
            "state_router shadow is retired from the product architecture"
        )
    return mode


def build_product_controller(
    store: LongHorizonStore,
    state: RunState,
    *,
    state_root: str | Path,
    max_transitions: int = 200,
    model_audit_hook: AuditHook | None = None,
    supervisor_audit_hook: AuditHook | None = None,
) -> Any:
    root = Path(state_root).expanduser().resolve()
    config = retrieval_policy_from_goal(state.goal)
    executor_binding = executor_profile_binding_for_run(state)
    executor_settings = executor_binding.settings
    if goal_self_termination_only(state.goal):
        # Goal mode is an unbounded state+delta workflow. Prompt replay is an
        # explicit bounded ablation only, never a silent production fallback.
        executor_settings = replace(
            executor_settings,
            state_transport="native_required",
        )
    supervisor_mode_from_policy(state.goal.runtime_policy)
    tool_selector = _product_tool_selector()
    if tool_selector is None:
        raise ValueError(
            "stateful_goal requires complete RWKV_LH_SELECTOR_* configuration; "
            "the Executor cannot replace the independent Selector"
        )
    harness = build_product_harness(
        config=config,
        snapshot_root=root / "retrieval_snapshots" / state.run_id,
        stable_network_menu=tool_selector is not None,
        untrusted_text_provider=lambda: _prior_tool_outputs(store, state.run_id),
    )
    def role_audit(role: str) -> AuditHook | None:
        if model_audit_hook is None:
            return None

        def emit(event: Mapping[str, Any]) -> None:
            model_audit_hook({**dict(event), "model_role": role})

        return emit

    # Deployment defaults may inherit from Executor.  Sessions and recurrent
    # States remain separate, and Executor's State profile is never inherited.
    # A 7.2B Auditor is therefore one .env change.
    auditor_settings = RuntimeSettings.for_role(
        "auditor",
        fallback=executor_settings,
    )
    executor_session = create_model_session(
        settings=executor_settings,
        audit_hook=role_audit("executor"),
    )
    auditor_session = create_model_session(
        settings=auditor_settings,
        audit_hook=role_audit("auditor"),
    )
    model = LongHorizonModel(
        executor_session,
        harness=harness,
        tool_selector=tool_selector,
        auditor_session=auditor_session,
    )
    supervisor = OpenAICompatibleSupervisorClient(audit_hook=supervisor_audit_hook)
    policy = supervisor_policy_from_env(mode="static")
    return StatefulGoalLoopController(
        store,
        model=model,
        harness=harness,
        supervisor=supervisor,
        supervisor_policy=policy,
        max_transitions=max_transitions,
    )


__all__ = ["build_product_controller", "supervisor_mode_from_policy"]
