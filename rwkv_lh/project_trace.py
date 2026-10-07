"""Reconstruct actual role boundaries; this is not a StateTune admission gate."""
from .project_contracts import digest, work_check_context, protected_paths
from .project_ledger import ProjectLedger
from .project_protocols import planner, decision, executor
from .project_evidence import evidence_stream, executor_observations


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
                candidate = state['pending_plan']
                if state['pending_checks'] or state.get('planner_request') == 'checks':
                    pending_checks = state['pending_checks']
                    lane = pending_checks['lane'] if pending_checks else 'work-check-author'
                    payload = planner.build_input(state['request'],
                        feedback=planner.review_feedback(state, lane) if pending_checks else state['feedback'],
                        protected_paths=protected_paths(state),
                        evidence=[{'id': key, **value} for key, value in state['evidence'].items() if value['kind'] != 'model'],
                        workspace=source['workspace'], mode='review_checks' if pending_checks else 'checks',
                        remaining=source['remaining'], work_context=work_check_context(state), project_state=state)
                elif candidate:
                    payload = planner.build_input(state['request'], plan=candidate['plan'],
                        feedback=planner.review_feedback(state, candidate['lane']), protected_paths=state['protected_paths'],
                        evidence=[{'id': key, **value} for key, value in state['evidence'].items() if value['kind'] != 'model'],
                        workspace=source['workspace'], mode='review', remaining=source['remaining'],
                        review_context={key: value for key, value in candidate.items() if key != 'plan'}
                            | {'previous_plan': state['plan']}, project_state=state)
                else:
                    payload = planner.build_input(state['request'], plan=state['plan'], feedback=state['feedback'],
                        protected_paths=state['protected_paths'],
                        evidence=[{'id': key, **value} for key, value in state['evidence'].items() if value['kind'] != 'model'],
                        workspace=source['workspace'], mode='diagnose' if state.get('planner_request') == 'diagnose' else 'plan',
                        target_contracts=state.get('planner_target_contracts'), remaining=source['remaining'], project_state=state)
                if digest(source['workspace']) != state['workspace_digest']:
                    raise ValueError('planner workspace digest mismatch')
            elif role == 'executor':
                selected, updates = evidence_stream(state, state['active']['id'])
                payload = executor.build_input(state['active'], observations=executor_observations(state),
                    feedback=executor.local_feedback(state), selected_evidence=selected, evidence_updates=updates,
                    project_state=state, remaining=source['remaining'], unit_remaining=source['unit_remaining'])
            elif role == 'decision':
                payload = decision.build_input(state, remaining=source['remaining'])
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
