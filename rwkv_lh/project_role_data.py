"""Extract auditable current-role candidates; extraction never grants training admission."""
from collections import Counter
import hashlib
import json
from pathlib import Path

from .project_contracts import digest
from .project_ledger import ProjectLedger
from .project_trace import role_boundaries
from .project_protocols import planner, executor


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def generate_packets(source, registration, output):
    source, registration, output = Path(source).resolve(), Path(registration).resolve(), Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    if output == source or source in output.parents or output in source.parents:
        raise ValueError('output must not overlap the production ledger')
    registered_bytes = registration.read_bytes()
    registration_sha = hashlib.sha256(registered_bytes).hexdigest()
    provenance = json.loads(registered_bytes)
    if not isinstance(provenance.get('source_purpose'), str) or not provenance['source_purpose']:
        raise ValueError('explicit source purpose required')
    with ProjectLedger.read_snapshot(source) as ledger:
        return _generate_locked(ledger, registration, registration_sha, provenance, output)


def _generate_locked(ledger, registration, registration_sha, provenance, output):
    source = ledger.root
    before = ledger.scan_verified_events()['digest']
    rows = list(role_boundaries(source))
    outcomes = {}
    def collect(event):
        feedback = event['state'].get('feedback') or {}
        if event['kind'].endswith('_rejected'):
            # Find the last returned operation, without inventing a correction label.
            receipts = event['state']['evidence']
            identifier = next((key for key in reversed(receipts) if receipts[key]['kind'] == 'model'), None)
            if identifier:
                outcomes[identifier] = feedback
    if before != ledger.scan_verified_events(collect)['digest']:
        raise ValueError('source changed during extraction')
    for row in rows:
        row['observed_rejection'] = outcomes.get(row['operation_id'])
        row['candidate_id'] = digest([row['source_event_digest'], row['result_event_digest'], row['operation_id']])
        row['input_digest'] = digest(row['input'])
        row['source_purpose'] = provenance['source_purpose']
        row['correction'] = None
        row['training_eligible'] = False
        row['eligibility_reason'] = 'Unreviewed extraction: no corrected target, token alignment, coverage or regression admission'
    workers = [row for row in rows if row['role'] == 'executor']
    for index, row in enumerate(workers):
        row['trajectory'] = {
            'previous_executor_operation_id': workers[index - 1]['operation_id'] if index else None,
            'next_executor_operation_id': workers[index + 1]['operation_id'] if index + 1 < len(workers) else None,
            'purpose': 'offline provenance only; future outcomes must not enter earlier input'}
    modules = {'planner': planner, 'executor': executor}
    counts = dict(Counter(row['role'] for row in rows))
    outcomes = Counter(row['result']['command']['function'] for row in workers)
    protocol_counts = Counter(row['input_protocol'] for row in rows)
    manifest = {
        'schema': 'rwkv-lh.project-role-candidates.v2',
        'source_run': str(source.parent), 'source_ledger': str(source),
        'source_event_chain_tip': before, 'source_registration': str(registration),
        'source_registration_sha256': registration_sha,
        'source_purpose': provenance['source_purpose'], 'counts': counts,
        'protocol_counts': dict(protocol_counts),
        'generator_sha256': file_sha(__file__),
        'protocol_modules': {role: {'protocol': module.PROTOCOL, 'sha256': file_sha(module.__file__)}
                             for role, module in modules.items()},
        'reconstructor_sha256': file_sha(Path(__file__).with_name('project_trace.py')),
        'coverage': {'observed_executor_operations': dict(outcomes),
                     'boundaries_with_tool_feedback': sum(row['input']['action_feedback']['last_execution'] is not None for row in workers),
                     'observed_step_selections': outcomes['select_step'],
                     'observed_step_reports': outcomes['report_step'],
                     'observed_finish_claims': outcomes['finish_work'],
                     'accepted_training_rows': 0},
        'split_algorithm': 'none: unreviewed source packets, no train/dev/confirmation split',
        'similarity': {'algorithm': 'canonical input SHA-256 exact equality', 'threshold': 1.0,
                       'unique_inputs': len({r['input_digest'] for r in rows}),
                       'near_duplicate_audit': 'not performed; required before admission'},
        'training_eligible': False, 'training_started': False,
    }
    if file_sha(registration) != registration_sha:
        raise ValueError('source registration changed during extraction')
    output.mkdir(parents=True, exist_ok=False)
    path = output / 'boundaries.jsonl'
    path.write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows))
    manifest['boundaries_sha256'] = file_sha(path)
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest
