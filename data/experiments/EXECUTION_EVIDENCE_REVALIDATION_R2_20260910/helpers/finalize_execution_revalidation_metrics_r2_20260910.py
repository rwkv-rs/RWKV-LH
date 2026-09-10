"""Seal role, verifier and upstream failure facts; do not rescore any case."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import sys

ROOT = Path('/home/chase/GitHub/RWKV-LH')
sys.path.insert(0, str(ROOT))
from scripts import run_rwkv_e2e_benchmark as benchmark
OUT = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R2_20260910'
names = ('EXECUTION_EVIDENCE_REVALIDATION_R2_20260910',)
roles = Counter()
selector = Counter()
actions = Counter()
handoffs = []
failures = []
verifiers = []
zero_generation = []
finish_reasons = Counter()
length_generations = []
for name in names:
    folder = ROOT / 'data/experiments' / name
    completion = json.loads((folder / 'COMPLETION.json').read_text())
    if not completion['source_unchanged']:
        raise SystemExit('Source changed during evaluation')
    if benchmark._source_tree_manifest(ROOT) != json.loads((folder / 'all_zero/source_tree_manifest.json').read_text()):
        raise SystemExit('Current source differs from frozen source')
    for case in json.loads((folder / 'REGISTRATION.json').read_text())['task_ids']:
        audit = json.loads((folder / 'all_zero/cases' / case / 'audit.json').read_text())
        handoff = json.loads((folder / f'{case}.HANDOFF_VERIFICATION.json').read_text())
        handoffs.append({k: handoff[k] for k in ('case', 'generation_contexts', 'role_inputs', 'errors', 'all_verified')})
        if handoff['generation_contexts'] == 0:
            zero_generation.append(case)
        roles.update(e.get('model_role', 'unknown') for e in audit['model_trace'] if e.get('type') == 'model_session_generation_started')
        for event in audit['model_trace']:
            if event.get('type') != 'model_session_generation_returned':
                continue
            finish_reasons[event.get('model_role', 'unknown') + ':' + str(event.get('finish_reason'))] += 1
            if event.get('finish_reason') == 'length':
                raw = event.get('raw_generation', {})
                length_generations.append({'case': case, 'role': event.get('model_role'),
                                           'request_id': event['request_id'],
                                           'max_output_tokens': raw.get('max_output_tokens'),
                                           'returned_token_count': len(raw.get('raw_token_ids', [])),
                                           'output_sha256': raw.get('raw_output_sha256')})
        events = [e['causal_event'] for e in audit['events']]
        selector['boundaries'] += sum(e['event_type'] == 'exact_tool_selection_staged' for e in events)
        actions.update(a['action_type'] for a in audit['action_ledger'].values())
        for failure in audit['supervisor_trace']:
            if failure.get('type') == 'supervisor_request_failed':
                failures.append({'case': case, 'event': failure})
        metadata = audit.get('anti_cheating', {}).get('isolated_verifier', {})
        verifiers.append({'case': case, 'metadata': metadata})
value = {'role_calls': dict(roles), 'selector': dict(selector), 'actions': dict(actions),
         'generation_finish_reasons': dict(finish_reasons), 'length_generations': length_generations,
         'native_first_error_counter_observable': False,
         'generation_contexts_verified': sum(r['generation_contexts'] for r in handoffs),
         'role_inputs_verified': sum(r['role_inputs'] for r in handoffs), 'handoffs': handoffs,
         'zero_generation_cases': zero_generation,
         'all_returned_handoffs_verified': all(r['all_verified'] for r in handoffs),
         'warning': 'Zero-generation cases have no handoff evidence; 0/0 is never role capability success.',
         'supervisor_failures': failures, 'verifiers': verifiers,
         'source_unchanged': True, 'optimizer_steps': 0, 'holdout_accessed': False,
         'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
with (OUT / 'ROLE_AND_INFRASTRUCTURE_EVIDENCE.json').open('x') as f:
    json.dump(value, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps({k: v for k, v in value.items() if k not in ('verifiers', 'handoffs', 'supervisor_failures')}, ensure_ascii=False))
print(json.dumps({'upstream_failures': [{'case': f['case'], **{k: f['event'].get(k) for k in ('http_status', 'error_category', 'error', 'provider_error')}} for f in failures]}, ensure_ascii=False))
print(json.dumps({'verifier_example': verifiers[-1]}, ensure_ascii=False))
