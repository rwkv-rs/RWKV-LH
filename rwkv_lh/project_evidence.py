"""Exact per-receipt delivery events for the one persistent Executor lane."""
from copy import deepcopy
from .project_contracts import digest


def select_evidence(state, lane, identifier, evidence):
    selected = state['selected_evidence'].setdefault(lane, {})
    revision = selected.get(identifier, {}).get('revision', 0) + 1
    selected[identifier] = {'revision': revision, 'evidence': deepcopy(evidence)}


def publish_executor_receipt(state, identifier, *, raw_result=None):
    receipt = state['evidence'][identifier]
    if receipt['kind'] != 'tool' or not state['active']:
        raise ValueError('only confirmed tool receipts enter the Executor evidence stream')
    select_evidence(state, state['active']['id'], identifier, {
        'kind': receipt['kind'], 'intent': receipt['intent'],
        'raw_result': receipt['result'] if raw_result is None else raw_result,
        'is_execution_evidence': True})


def evidence_stream(state, lane):
    selected = state['selected_evidence'].get(lane, {})
    delivered = state['input_delivery'].get(lane, {}).get('evidence', {}) if lane in state['sessions'] else {}
    index = {key: {'digest': digest(item['evidence']), 'revision': item['revision']}
             for key, item in selected.items()}
    # Revision is part of the visible event, not just a hidden delivery cursor.
    updates = {key: {**deepcopy(item['evidence']), 'delivery_revision': item['revision']}
               for key, item in selected.items() if delivered.get(key) != item['revision']}
    return index, updates


def executor_observations(state):
    lane = state['active']['id']
    delivered = state['input_delivery'].get(lane, {}).get('observations', []) if lane in state['sessions'] else []
    return [{'action_id': key, 'result': deepcopy(value['result'])} for key, value in state['evidence'].items()
            if value['kind'] == 'tool' and value['intent']['assignment_id'] == lane and key not in delivered]


def record_delivery(state, lane, payload):
    if payload.get('protocol') is None:
        raise ValueError('delivery requires the current input')
    delivered = state['input_delivery'].setdefault(lane, {'observations': [], 'evidence': {}})
    delivered['observations'] += [item['action_id'] for item in payload.get('observations', [])]
    # Only events actually present in the input can advance the receipt cursor.
    for key, item in payload.get('evidence_updates', {}).items():
        delivered['evidence'][key] = item['delivery_revision']


def executor_evidence_ids(state):
    if not state['active']:
        return set()
    return {key for key, item in state['evidence'].items()
            if item['kind'] == 'tool' and item['intent']['assignment_id'] == state['active']['id']}
