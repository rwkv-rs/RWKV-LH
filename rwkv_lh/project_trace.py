"""Reconstruct actual role boundaries; this is not a StateTune admission gate."""
from .project_contracts import digest
from .project_ledger import ProjectLedger
from .project_protocols import planner, executor


def role_boundaries(root, *, read_only=True):
    if read_only is not True:
        raise ValueError('Project trace extraction requires read-only access')
    intents, rows = {}, []
    def collect(event):
        state = event['state']
        pending = state['pending']
        if event['kind'] == 'operation_started' and pending['kind'] == 'model':
            intent = pending['payload']
            role, source = intent['role'], intent['input']
            if role == 'planner':
                payload = planner.build_input(state['request'], feedback=state['feedback'],
                    protected_paths=state['protected_paths'], workspace=source['workspace'], materials=source['materials'], remaining=source['remaining'])
                planner.validate_input(payload)
                if digest(source['workspace']) != state['workspace_digest']:
                    raise ValueError('planner workspace digest mismatch')
            elif role == 'executor':
                payload = executor.build_input(state['active'], project_state=state, remaining=source['remaining'])
            else:
                raise ValueError('unknown project role')
            if payload != source or digest(payload) != intent['input_digest']:
                raise ValueError('recorded role input differs from production builder')
            intents[pending['id']] = (event['digest'], payload, intent)
        elif event['kind'] == 'operation_returned':
            inbox = state.get('inbox')
            if not inbox or inbox['operation_id'] not in intents:
                return
            identifier = inbox['operation_id']
            started, payload, intent = intents.pop(identifier)
            rows.append({'source_root': str(ledger.root), 'operation_id': identifier,
                'source_event_digest': started, 'result_event_digest': event['digest'],
                'role': intent['role'], 'lane': intent['lane'], 'input_protocol': payload['protocol'],
                'input': payload, 'result': state['evidence'][identifier]['result'],
                'checkpoint': state['sessions'][intent['lane']],
                'training_eligible': False,
                'eligibility_reason': 'Recorded boundary only: source authorization, labels, coverage and regression gates are separate'})
    with ProjectLedger.read_snapshot(root) as ledger:
        ledger.scan_verified_events(collect)
    # Do not expose an early valid-looking boundary if any later row is corrupt.
    yield from rows
