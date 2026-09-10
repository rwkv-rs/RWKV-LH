"""Read only completed black-box execution metadata, never private verifier programs or expectations."""
from pathlib import Path
import hashlib
import json

root = Path('/home/chase/GitHub/RWKV-LH')
out = root / 'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R2_20260910'
registration = json.loads((out / 'REGISTRATION.json').read_text())
rows = []
for case in registration['task_ids']:
    assert (out / 'all_zero' / f'{case}.result.json').is_file(), 'all cases must finish first'
    audit_path = out / 'all_zero/cases' / case / 'audit.json'
    audit = json.loads(audit_path.read_text())
    checks = []
    for check in audit['external_checks']:
        observed = check['observation']
        if check['kind'] == 'project_behavior':
            checks.append({**{key: observed.get(key) for key in ('program_sha256', 'actual_exit_code', 'browser')},
                'captured_output_sha256': hashlib.sha256(str(observed.get('output') or '').encode()).hexdigest(),
                'playwright_diagnostic_present': 'playwright' in str(observed.get('output') or '').casefold()})
    rows.append({'case': case, 'agent_completed': audit['agent_completed'],
        'isolation': audit['anti_cheating'], 'verifier_failure': audit['verifier_failure'],
        'project_behavior_checks': checks, 'audit_sha256': hashlib.sha256(audit_path.read_bytes()).hexdigest()})
value = {'cases': rows, 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'private_programs_or_expected_values_read': False,
    'scope': 'existing verifier invocation/isolation and browser requirement metadata; no new execution or rescore'}
with (out / 'VERIFIER_EXECUTION_METADATA.json').open('x') as handle:
    json.dump(value, handle, ensure_ascii=False, indent=2)
    handle.write('\n')
print(json.dumps({'cases': len(rows), 'browser_cases': [{'case': row['case'], 'checks': row['project_behavior_checks']}
    for row in rows if any(item['browser'] for item in row['project_behavior_checks'])],
    'verifier_failures': sum(bool(row['verifier_failure']) for row in rows)}))
