"""Project confirmed rejected-attempt facts without retaining failed model State.

Each preceding rejection is attested by the next original model input. Walking
adjacent confirmed receipts prevents crossing a recovery, observation or lane.
No counters are persisted, no action is selected, and no output is repaired.
"""
from .model_io import canonical_json


def _context(intent):
    payload = intent['input']
    if intent['role'] == 'decision':
        return (payload['protocol'], payload['boundary']['id'], payload['selected_evidence'])
    return (payload['protocol'], payload['assignment'], payload['original_request'])


def _attempt_identity(rejection):
    raw = rejection['raw_output']
    return (raw if isinstance(raw, str) else canonical_json(rejection['call']), rejection['error'])


def rejection_attempt_history(state, rejection, *, assignment=None, workers=(), boundary_id=None):
    """Count an unchanged current context's consecutive confirmed rejections.

The latest rejection comes from the ledger's role_rejections projection; earlier
ones come from the actual next input, never inferred from an invalid-looking
answer. First/last OPs and counts are a compact view of the intact receipt chain.
    """
    records = list(state['evidence'].items())
    target = rejection['operation_id']
    if not records or records[-1][0] != target:
        return None  # A later confirmed operation makes this a historical error.
    intent = records[-1][1]['intent']
    role, lane = intent['role'], intent['lane']
    context = _context(intent)
    if role == 'decision':
        from .project_evidence import evidence_stream
        if (boundary_id != intent['input']['boundary']['id']
                or evidence_stream(state, lane)[0] != intent['input']['selected_evidence']):
            return None
    else:
        current = assignment if assignment is not None else next(
            (worker for worker in workers if worker['id'] == lane), None)
        if current != intent['input']['assignment'] or state['request'] != intent['input']['original_request']:
            return None
    cursor = rejection
    newest_identity = _attempt_identity(rejection)
    identifiers = []
    identical = []
    for identifier, receipt in reversed(records):
        if (receipt['kind'] != 'model' or not cursor
                or cursor['operation_id'] != identifier or cursor['role'] != role):
            break
        prior = receipt['intent']
        if prior['role'] != role or prior['lane'] != lane or _context(prior) != context:
            break
        identifiers.append(identifier)
        if len(identical) == len(identifiers) - 1 and _attempt_identity(cursor) == newest_identity:
            identical.append(identifier)
        cursor = prior['input']['action_feedback']['rejected_call']
    return {
        'consecutive_rejections': len(identifiers),
        'identical_tail': len(identical),
        'first_operation_id': identifiers[-1],
        'identical_tail_first_operation_id': identical[-1],
        'last_operation_id': target,
    }


def validate_attempt_history(history, operation_id):
    if history is None:
        return
    from .project_contracts import fields
    try:
        fields(history, ('consecutive_rejections', 'identical_tail', 'first_operation_id',
                         'identical_tail_first_operation_id', 'last_operation_id'))
        total, tail = history['consecutive_rejections'], history['identical_tail']
        first, last = history['first_operation_id'], history['last_operation_id']
        tail_first = history['identical_tail_first_operation_id']
        if (type(total) is not int or type(tail) is not int or not 1 <= tail <= total
                or any(not isinstance(value, str) or not value for value in (first, last, tail_first))
                or last != operation_id or (total == 1) != (first == last)
                or (tail == 1) != (tail_first == last)
                or (total == tail) != (first == tail_first)):
            raise ValueError('inconsistent counts or source identities')
    except (ValueError, TypeError, KeyError) as exc:
        raise ValueError('invalid rejection attempt history') from exc
