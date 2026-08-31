"""Disposable retrieval/evidence ledgers folded from CausalEvent authority."""

from __future__ import annotations

from typing import Any, Mapping

from rwkv_lh.schema import RunState


def fold_retrieval_ledger(state: RunState) -> dict[str, Any]:
    routes: list[dict[str, Any]] = []
    records: dict[str, dict[str, Any]] = {}
    for event_id in state.causal_order:
        event = state.causal_records[event_id]
        if event.event_type != "action_finished":
            continue
        action = event.payload.get("action")
        if not isinstance(action, Mapping):
            continue
        result = action.get("result")
        metadata = result.get("metadata") if isinstance(result, Mapping) else None
        envelope = metadata.get("external_evidence") if isinstance(metadata, Mapping) else None
        if not isinstance(envelope, Mapping):
            continue
        route = {
            "action_id": str(action.get("action_id") or ""),
            "route_id": str(envelope.get("route_id") or ""),
            "tool": str(envelope.get("tool") or ""),
            "request_digest": str(envelope.get("request_digest") or ""),
            "status": str(envelope.get("status") or ""),
            "as_of": str(envelope.get("as_of") or ""),
            "record_ids": [],
        }
        for item in envelope.get("records") or ():
            if not isinstance(item, Mapping):
                continue
            identifier = str(item.get("evidence_record_id") or "")
            if not identifier:
                continue
            records[identifier] = dict(item)
            route["record_ids"].append(identifier)
        routes.append(route)
    return {
        "schema_version": "rwkv-lh.retrieval-ledger-projection.v1",
        "run_id": state.run_id,
        "routes": routes,
        "records": records,
    }


__all__ = ["fold_retrieval_ledger"]
