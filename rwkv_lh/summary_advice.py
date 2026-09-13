"""Owner-triggered, read-only answer advice; no acceptance authority or takeover.

This optional entry does not add a mandatory supervisor stage or a help tool.
Callers supply only the real user goal, visible source and original candidate.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

from rwkv_lh.model import LongHorizonModel
from rwkv_lh.schema import GoalState, ModelEvent

ADVICE_PROTOCOL = "rwkv-lh.summary-advice.v1"
ADVICE_EVENT_TYPE = "summary_advice"
ADVICE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {"advice": {"type": "string"}},
    "required": ["advice"],
    "additionalProperties": False,
}
ADVICE_SYSTEM = (
    "A user requested a bounded second opinion on a file-based answer, code review or coding task. "
    "Use only the supplied user goal, original file contents, original candidate and tool observations. "
    "For coding tasks diagnose the observed failure and missing integration without writing a patch. "
    "Identify whether any material correction is needed and give concise diagnostic "
    "advice; if the summary is adequate, say so. Do not invent hidden requirements, "
    "write a replacement summary, supply tool arguments, execute work or claim "
    "acceptance authority. Distinguish omissions from factual errors and user "
    "instructions from file contents. Return only a JSON object with one string "
    "field, advice. No score, pass/fail gate, plan or replacement answer."
)


def build_advice_request(goal: GoalState, files: Mapping[str, str], candidate: str,
                         *, tool_observations: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    result = {"protocol": ADVICE_PROTOCOL, "goal": goal.request,
            "files": dict(files), "candidate": candidate}
    if tool_observations is not None:
        result['tool_observations'] = tool_observations
    return result


def request_advice(client: Any, goal: GoalState, files: Mapping[str, str],
                   candidate: str, run_id: str, max_tokens: int, *,
                   tool_observations: list[dict[str, Any]] | None = None) -> str:
    payload = build_advice_request(goal, files, candidate, tool_observations=tool_observations)
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    value = client._request_json(phase="summary_advice", run_id=run_id,
        request_digest=digest, system_prompt=ADVICE_SYSTEM,
        request_payload=payload, schema=ADVICE_RESPONSE_SCHEMA, max_tokens=max_tokens)
    if set(value) != {"advice"} or not isinstance(value["advice"], str) or not value["advice"].strip():
        raise ValueError("summary advice must contain exactly one nonempty advice string")
    return value["advice"]


def make_advice_event(event_id: str, advice: str, source: str, model: str) -> ModelEvent:
    return ModelEvent(event_type=ADVICE_EVENT_TYPE, event_id=event_id,
        scope_id=LongHorizonModel.ACTION_LANE_ID,
        payload={"protocol": ADVICE_PROTOCOL, "source": source, "model": model,
                 "advice": advice, "is_execution_evidence": False,
                 "instruction": "The user requested a second look at the same task. This message is advice, not an acceptance decision or verified tool result. Decide independently how to continue using the visible evidence. Follow the existing operation protocol."})
