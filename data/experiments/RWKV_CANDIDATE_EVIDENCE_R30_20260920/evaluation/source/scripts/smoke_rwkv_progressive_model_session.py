"""Smoke the deployed server through RWKV-LH's actual progressive ModelSession."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from rwkv_lh.harness import ActionHarness
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_io import parse_model_command, parse_tool_selection
from rwkv_lh.model_session import ModelSession, SessionSampling
from rwkv_lh.schema import ModelLaneKind


parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
harness = ActionHarness(sandbox_commands=False)
model = LongHorizonModel(ModelSession(), harness=harness)
assignment = json.dumps(
    {
        "protocol": "single-rwkv-direct-action.v1",
        "constraints": ["This is a transport smoke; return one valid displayed call."],
        "workspace_manifest": {"entries": [], "complete": True, "truncated": False},
        "action_result_projection_version": "action-result-decision-state.v1",
        "recent_action_sequence_range": {"first": 0, "last": 0, "count": 0},
        "recent_exact_action_records": [],
        "instruction": "Choose one valid operation and then obey its disclosed contract.",
        "immutable_request": "Return one valid direct operation call for this protocol smoke.",
    },
    ensure_ascii=False,
)
session = model.session
checkpoint = session.bootstrap(
    ModelLaneKind.ACTION,
    assignment,
    model._menu_definitions,
    lane_id="LANE:ROUND1-DEPLOY-SMOKE",
    progressive_tool_disclosure=True,
)
sampling = SessionSampling(temperature=0.05)
selector = session.generate(checkpoint, sampling=sampling, max_output_tokens=160)
selected = parse_tool_selection(selector.raw_output)
if selected not in model._definitions_by_name:
    raise SystemExit(f"selector returned undisplayed operation: {selected}")
selector_checkpoint = session.commit(selector, parse_model_command(selector.raw_output))
direct_checkpoint = session.disclose_tool(
    selector_checkpoint,
    model._definitions_by_name[selected],
)
direct = session.generate(direct_checkpoint, sampling=sampling, max_output_tokens=256)
command = parse_model_command(direct.raw_output)
if command.name != selected:
    raise SystemExit(f"direct operation changed: selected={selected} direct={command.name}")
result = {
    "schema_version": "rwkv-lh.progressive-model-session-smoke.v1",
    "status": "passed",
    "transport": session.transport,
    "model": session.model_name,
    "selected_operation": selected,
    "selector_raw": selector.raw_output,
    "direct_raw": direct.raw_output,
    "selector_prompt_tokens": selector.parent.token_count,
    "direct_prompt_tokens": direct.parent.token_count,
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, indent=2))
