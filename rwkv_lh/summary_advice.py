"""Owner-triggered, read-only summary advice; no acceptance authority or takeover.

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
ADVICE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {"advice": {"type": "string"}},
    "required": ["advice"],
    "additionalProperties": False,
}
ADVICE_SYSTEM = (
    "A user requested a bounded second opinion on a short file summary. "
    "Use only the supplied user goal, original file contents and original candidate. "
    "Identify whether any material correction is needed and give concise diagnostic "
    "advice; if the summary is adequate, say so. Do not invent hidden requirements, "
    "write a replacement summary, supply tool arguments, execute work or claim "
    "acceptance authority. Distinguish omissions from factual errors and user "
    "instructions from file contents. Return only a JSON object with one string "
    "field, advice. No score, pass/fail gate, plan or replacement answer."
)


def build_advice_request(goal: GoalState, files: Mapping[str, str], candidate: str) -> dict[str, Any]:
    return {"protocol": ADVICE_PROTOCOL, "goal": goal.request,
            "files": dict(files), "candidate": candidate}


def request_advice(client: Any, goal: GoalState, files: Mapping[str, str],
                   candidate: str, run_id: str, max_tokens: int) -> str:
    payload = build_advice_request(goal, files, candidate)
    digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    value = client._request_json(phase="summary_advice", run_id=run_id,
        request_digest=digest, system_prompt=ADVICE_SYSTEM,
        request_payload=payload, schema=ADVICE_RESPONSE_SCHEMA, max_tokens=max_tokens)
    if set(value) != {"advice"} or not isinstance(value["advice"], str) or not value["advice"].strip():
        raise ValueError("summary advice must contain exactly one nonempty advice string")
    return value["advice"]


def make_advice_event(event_id: str, advice: str, source: str, model: str) -> ModelEvent:
    return ModelEvent(event_type="summary_advice", event_id=event_id,
        scope_id=LongHorizonModel.ACTION_LANE_ID,
        payload={"protocol": ADVICE_PROTOCOL, "source": source, "model": model,
                 "advice": advice, "is_execution_evidence": False,
                 "instruction": "The user requested a second look at the same task. This message is advice, not an acceptance decision or verified tool result. Decide independently whether to revise or retain your answer using the visible file. Follow the existing operation protocol."})
