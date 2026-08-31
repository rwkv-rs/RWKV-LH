"""Construct one product Controller from immutable persisted run policy."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.exact_tool_selector.network_client import (
    NetworkExactToolSelectorClient,
    NetworkExactToolSelectorSettings,
)
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import create_model_session
from rwkv_lh.parallel_atoms import ThreadedRWKVAtomPool
from rwkv_lh.retrieval import build_product_harness, retrieval_policy_from_goal
from rwkv_lh.runtime.executor_profiles import executor_profile_binding_for_run
from rwkv_lh.schema import RunState
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.state_router.shadow import wrap_controller_for_shadow
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
    mode = str(selected.get("mode") or "none").strip()
    if mode not in {"none", "contract_graph"}:
        raise ValueError("product supervisor mode must be none or contract_graph")
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
    tool_selector = _product_tool_selector()
    harness = build_product_harness(
        config=config,
        snapshot_root=root / "retrieval_snapshots" / state.run_id,
        stable_network_menu=tool_selector is not None,
        untrusted_text_provider=lambda: _prior_tool_outputs(store, state.run_id),
    )
    model = LongHorizonModel(
        create_model_session(
            settings=executor_binding.settings,
            audit_hook=model_audit_hook,
        ),
        harness=harness,
        tool_selector=tool_selector,
    )
    supervisor = None
    policy = None
    atom_pool = None
    mode = supervisor_mode_from_policy(state.goal.runtime_policy)
    if mode == "contract_graph":
        supervisor = OpenAICompatibleSupervisorClient(audit_hook=supervisor_audit_hook)
        policy = supervisor_policy_from_env(mode="contract_graph")

        def atom_model_factory(contract, scoped_harness):
            def audit(event: Mapping[str, Any]) -> None:
                if model_audit_hook is not None:
                    model_audit_hook(
                        {
                            **dict(event),
                            "atom_id": contract.atom.atom_id,
                            "contract_digest": contract.contract_digest,
                        }
                    )

            return LongHorizonModel(
                create_model_session(
                    settings=executor_binding.settings,
                    audit_hook=audit,
                ),
                harness=scoped_harness,
                tool_selector=_product_tool_selector(),
            )

        atom_pool = ThreadedRWKVAtomPool(
            root / "atom_workers" / state.run_id,
            harness=harness,
            model_factory=atom_model_factory,
        )
    controller = LongHorizonController(
        store,
        model=model,
        harness=harness,
        supervisor=supervisor,
        supervisor_policy=policy,
        atom_worker_pool=atom_pool,
        max_transitions=max_transitions,
    )
    return wrap_controller_for_shadow(
        controller,
        state,
        state_root=root,
    )


__all__ = ["build_product_controller", "supervisor_mode_from_policy"]
