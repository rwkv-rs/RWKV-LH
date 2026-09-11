"""Exactly reconstruct a completed collection case without changing its labels or score."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

root = Path('/home/chase/GitHub/RWKV-LH')
sys.path.insert(0, str(root))
from rwkv_lh.goal_state_protocols.role_trace_dataset_v1 import register_case, load_source_run
from rwkv_lh.role_trace_inputs import rebuild_role_input
from rwkv_lh.role_trace_context import reconstruct_context, bind_server_input_tokens
parser = argparse.ArgumentParser()
parser.add_argument('round')
parser.add_argument('case')
args = parser.parse_args()
out = root / 'data/experiments' / args.round
registration = json.loads((out / 'REGISTRATION.json').read_text())
assert args.case in registration['task_ids']
output = out / 'all_zero'
assert (output / f'{args.case}.result.json').is_file()
protocol = json.loads((output / 'RUN_PROTOCOL.json').read_text())
record = register_case(output / 'cases' / args.case, run_id=args.case,
    source_run_id=protocol['round'], project_family=registration['project_families'][args.case],
    suite=protocol['suite'])['source_runs'][0]
source = load_source_run(record, base_dir=out,
    coverage_scope_sha256=hashlib.sha256((out / 'COVERAGE_SCOPE.json').read_bytes()).hexdigest())
rows, errors = [], []
starts = {r['request_id']: r for r in source.model_trace if r.get('type') == 'model_session_generation_started'}
for returned in source.model_trace:
    if returned.get('type') != 'model_session_generation_returned':
        continue
    start = starts[returned['request_id']]
    context = reconstruct_context(start['input_checkpoint_id'], source.final_state.model_states, source.model_trace)
    checked = bind_server_input_tokens(context, returned['raw_generation'])
    assert checked['token_ids_complete']
    rows.append({'kind': 'generation_context', 'role': returned['model_role'], 'request_id': returned['request_id'],
        'full_input_token_match': True, 'input_tokens': len(checked['token_ids']),
        'finish_reason': returned['finish_reason'], 'prompt_sha256': hashlib.sha256(checked['prompt_text'].encode()).hexdigest()})
for event in source.final_state.causal_records.values():
    if event.event_type == 'tool_schema_disclosed':
        role = 'executor_args'
    elif event.event_type == 'goal_auditor_session_started':
        role = event.payload['auditor_role']
    elif event.event_type == 'goal_finalizer_session_started':
        role = 'finalizer_answer'
    else:
        continue
    try:
        rebuilt = rebuild_role_input(role, source.snapshots[event.event_id],
            {'boundary_event_id': event.event_id, 'checkpoint_id': event.payload['checkpoint_id']})
    except Exception as exc:
        errors.append({'role': role, 'event_id': event.event_id, 'error_type': type(exc).__name__, 'error': str(exc)})
        continue
    actual = source.snapshots[event.event_id].model_states[event.payload['checkpoint_id']].transcript
    assert rebuilt['expected_checkpoint_transcript'] == actual
    original = rebuilt['prompt_source'].get('immutable_goal')
    if role in ('executor_args', 'auditor_step'):
        assert original == source.final_state.goal.request
    rows.append({'kind': 'role_input', 'role': role, 'event_id': event.event_id,
        'production_rebuild_exact': True, 'immutable_goal_preserved': original == source.final_state.goal.request,
        'prompt_sha256': hashlib.sha256(actual.encode()).hexdigest()})
result = {'case': args.case, 'purpose': 'exact handoff reconstruction only; no corrected labels or rescoring',
    'source_registration': record, 'rows': rows,
    'generation_contexts': sum(r['kind'] == 'generation_context' for r in rows),
    'role_inputs': sum(r['kind'] == 'role_input' for r in rows), 'errors': errors, 'all_verified': not errors,
    'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
with (out / f'{args.case}.HANDOFF_VERIFICATION.json').open('x') as handle:
    json.dump(result, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
print(json.dumps({k: result[k] for k in ('case', 'generation_contexts', 'role_inputs', 'all_verified', 'errors')}))
