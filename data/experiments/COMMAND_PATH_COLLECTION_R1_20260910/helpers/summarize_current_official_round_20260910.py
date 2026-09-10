"""Summarize generated public execution evidence; never open private acceptance."""
from collections import Counter
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path('/home/chase/GitHub/RWKV-LH')
parser = argparse.ArgumentParser()
parser.add_argument('round')
parser.add_argument('--seal', action='store_true')
args = parser.parse_args()
OUT = ROOT / 'data/experiments' / args.round
ROUNDS = (args.round,)
rows = []
for name in ROUNDS:
    folder = ROOT / 'data/experiments' / name
    reg = json.loads((folder / 'REGISTRATION.json').read_text())
    for task in reg['task_ids']:
        result_path = folder / 'all_zero' / f'{task}.result.json'
        audit_path = folder / 'all_zero/cases' / task / 'audit.json'
        row = {'task_id': task, 'round': name, 'recorded': result_path.exists() and audit_path.exists()}
        if not row['recorded']:
            completion = folder / f'{task}.completion.json'
            if completion.exists():
                row['completion'] = json.loads(completion.read_text())
            rows.append(row)
            continue
        result = json.loads(result_path.read_text())
        audit = json.loads(audit_path.read_text())
        events = [e['causal_event'] for e in audit['events']]
        terminal = [e for e in events if e['event_type'] in ('run_yielded', 'run_blocked', 'run_completed', 'run_interrupted')]
        actions = list(audit['action_ledger'].values())
        mutations = [a for a in actions if a.get('workspace_digest_before') and a.get('workspace_digest_before') != a.get('workspace_digest_after')]
        model = audit['model_trace']
        supervisor = audit['supervisor_trace']
        row.update(
            strict=result['passed'], completed=result['agent_completed'], status=result['status'],
            action_count=result['action_count'], mutation_count=sum(a.get('status') == 'succeeded' for a in mutations),
            all_status_workspace_deltas=len(mutations),
            termination=terminal[-1]['payload'].get('reason') if terminal else None,
            terminal_events=terminal,
            role_calls=dict(Counter(e.get('model_role', 'unknown') for e in model if e.get('type') == 'model_session_generation_started')),
            supervisor_requests=result['supervisor_request_count'],
            supervisor_failures=[e for e in supervisor if e.get('type') == 'supervisor_request_failed'],
            supervisor_generation_interruptions=[
                {k: e.get(k) for k in ('call_id', 'phase', 'attempt', 'finish_reason', 'usage')}
                for e in supervisor
                if e.get('type') == 'supervisor_response_envelope_received'
                and (e.get('finish_reason') == 'length' or
                     (e.get('raw_response', {}).get('incomplete_details') or {}).get('reason') == 'max_output_tokens')
            ],
            native_transport_events=[e for e in model if e.get('type') in ('native_request_transport_error', 'native_request_resubmitted', 'selector_transport_error')],
            runtime_failures=[e for e in events if e['event_type'] == 'model_transport_failure'],
            infra_retry=result.get('infra_retry', result.get('observations', {}).get('infra_retry')),
            isolated_verifier=audit.get('anti_cheating', {}).get('isolated_verifier', {}),
            command_actions=[{'action_id':a.get('action_id'),'tool_name':a.get('action_type'),'status':a.get('status')} for a in actions if a.get('action_type') in ('check_command','run_command')],
            executor_returned=sum(e.get('type')=='model_session_generation_returned' and e.get('model_role')=='executor_args' for e in model),
            executor_length=sum(e.get('type')=='model_session_generation_returned' and e.get('model_role')=='executor_args' and e.get('finish_reason')=='length' for e in model),
            audit_path=str(audit_path), audit_sha256=hashlib.sha256(audit_path.read_bytes()).hexdigest(),
        )
        rows.append(row)
recorded = [r for r in rows if r['recorded']]
summary = {'selected': len(rows), 'recorded': len(recorded),
           'strict': sum(r['strict'] for r in recorded), 'completed': sum(r['completed'] for r in recorded),
           'mutation_count': sum(r['mutation_count'] for r in recorded),
           'action_count': sum(r['action_count'] for r in recorded),
           'termination_reasons': dict(Counter(r['termination'] for r in recorded)),
           'supervisor_failures': sum(len(r['supervisor_failures']) for r in recorded),
           'supervisor_generation_interruptions': sum(len(r['supervisor_generation_interruptions']) for r in recorded),
           'runtime_transport_failures': sum(len(r['runtime_failures']) for r in recorded),
           'native_first_errors': sum(len([e for e in r['native_transport_events'] if e.get('type') == 'native_request_transport_error']) for r in recorded),
           'native_first_error_counter_observable': True,
           'native_first_error_counter_limitation': 'Factory and per-atom audit subscribers wired in frozen source21c0cf45; zero observed errors is not an exercised recovery-path claim.',
           'command_actions': sum(len(r['command_actions']) for r in recorded),
           'executor_returned': sum(r['executor_returned'] for r in recorded),
           'executor_length': sum(r['executor_length'] for r in recorded),
           'counts_complete': len(recorded) == len(rows), 'optimizer_steps': 0, 'holdout_accessed': False}
if args.seal:
    assert all((ROOT / 'data/experiments' / name / 'COMPLETION.json').exists() for name in ROUNDS)
    with (OUT / 'AGENT_SUMMARY.json').open('x') as f:
        json.dump({'agent': summary, 'cases': rows}, f, ensure_ascii=False, indent=2)
        f.write('\n')
print(json.dumps({'agent': summary, 'cases': [{k: v for k, v in r.items() if k in ('task_id', 'recorded', 'strict', 'completed', 'mutation_count', 'termination', 'completion')} for r in rows if r['recorded'] or 'completion' in r]}, ensure_ascii=False))
