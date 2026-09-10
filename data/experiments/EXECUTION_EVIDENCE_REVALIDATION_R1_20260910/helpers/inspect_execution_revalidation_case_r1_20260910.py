"""Inspect public causal failure chains after a case finishes, without rescoring."""
from pathlib import Path
import argparse
import json

ROOT = Path('/home/chase/GitHub/RWKV-LH')
parser = argparse.ArgumentParser()
parser.add_argument('case')
parser.add_argument('--print-only', action='store_true')
args = parser.parse_args()
name = ('ULTRADATA' if args.case.startswith('ULTRA-') else 'REALPROJECT') + '_EXECUTION_REVALIDATION_R1_20260910'
path = ROOT / 'data/experiments' / name / 'all_zero/cases' / args.case / 'audit.json'
audit = json.loads(path.read_text())
events = [e['causal_event'] for e in audit['events']]
keep = {'goal_plan_patch_committed', 'action_finished', 'goal_audit_recorded', 'goal_audit_accepted',
        'goal_stage_review_committed', 'protocol_rejection_recorded', 'model_transport_failure', 'run_blocked', 'run_interrupted'}
selected = [e for e in events if e['event_type'] in keep]
result = {'case': args.case, 'events': selected, 'actions': audit['action_ledger'],
          'supervisor_failures': [e for e in audit['supervisor_trace'] if e.get('type') == 'supervisor_request_failed'],
          'verifier_metadata': audit.get('anti_cheating', {}).get('isolated_verifier', {})}
out = ROOT / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910' / f'{args.case}.PUBLIC_CAUSAL_OBSERVATION.json'
if not args.print_only:
    with out.open('x') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write('\n')
for event in selected:
    payload = event['payload']
    compact = {key: payload[key] for key in ('reason', 'active_step_id', 'selected_operation', 'error', 'audit', 'review') if key in payload}
    if 'action' in payload:
        compact['action'] = {key: payload['action'].get(key) for key in ('action_id', 'action_type', 'status')}
    print(json.dumps({'event_id': event['event_id'], 'event_type': event['event_type'], 'payload': compact}, ensure_ascii=False)[:1800])
