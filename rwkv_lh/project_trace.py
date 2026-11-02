"""Reconstruct actual agent boundaries; this is not a training admission gate."""
from .project_contracts import digest
from .project_ledger import ProjectLedger
from .project_protocols import agent


def agent_boundaries(root, *, read_only=True):
    """Yield each model boundary after proving its input equals the production builder's."""
    if read_only is not True:
        raise ValueError('Project trace extraction requires read-only access')
    intents, rows = {}, []
    def collect(event):
        state = event['state']
        pending = state['pending']
        if event['kind'] == 'operation_started' and pending['kind'] == 'model':
            intent = pending['payload']
            source = intent['input']
            payload = agent.build_input(state, native_tools=source['native_tools'])
            if payload != source or digest(payload) != intent['input_digest']:
                raise ValueError('recorded agent input differs from production builder')
            intents[pending['id']] = (event['digest'], payload, intent)
        elif event['kind'] == 'operation_returned':
            inbox = state.get('inbox')
            if not inbox or inbox['operation_id'] not in intents:
                return
            identifier = inbox['operation_id']
            started, payload, intent = intents.pop(identifier)
            rows.append({'source_root': str(ledger.root), 'operation_id': identifier,
                'source_event_digest': started, 'result_event_digest': event['digest'],
                'role': 'agent', 'lane': intent['lane'], 'request_id': intent['request_id'],
                'input_protocol': payload['protocol'], 'input': payload,
                'result': state['evidence'][identifier]['result'], 'checkpoint': state['sessions'][intent['lane']],
                'training_eligible': False,
                'eligibility_reason': 'Recorded boundary only: source authorization, labels, coverage and regression gates are separate'})
    with ProjectLedger.read_snapshot(root) as ledger:
        ledger.scan_verified_events(collect)
    # Do not expose an early valid-looking boundary if any later row is corrupt.
    yield from rows
