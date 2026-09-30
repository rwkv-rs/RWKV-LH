"""Lossless Project input updates and persisted clean-boundary retry anchors.

The role builders remain authoritative. This transport never selects a direction,
removes obligations, or treats reconstructability as model comprehension.
"""
from copy import deepcopy
from .project_contracts import digest
from .project_protocols import planner, decision, executor
from .schema import ModelEvent

INPUT_HANDOFF_VERSION = 'project-input-handoff.v2'
DELTA_EVENT_TYPE = 'project_role_input_delta'


def _validate(payload):
    if not isinstance(payload, dict):
        raise ValueError('role payload must be an object')
    modules = {module.PROTOCOL:module for module in (planner,decision,executor)}
    module = modules.get(payload.get('protocol'))
    if module is None:
        raise ValueError('current role protocol required')
    module.validate_input(payload)


def make_delta(previous, current):
    _validate(previous)
    _validate(current)
    if previous['protocol'] != current['protocol']:
        raise ValueError('delta cannot cross role protocol')
    return {'base_digest':digest(previous), 'target_digest':digest(current),
            'set':{key:deepcopy(value) for key,value in current.items()
                   if key in ('step_progress', 'action_feedback', 'references') or key not in previous or previous[key] != value},
            'remove':sorted(set(previous)-set(current))}


def apply_delta(previous, patch):
    _validate(previous)
    if not isinstance(patch,dict) or set(patch) != {'base_digest','target_digest','set','remove'}:
        raise ValueError('invalid delta envelope')
    if patch['base_digest'] != digest(previous):
        raise ValueError('delta base differs; do not apply stale or repeated update')
    updates, removals = patch['set'], patch['remove']
    if (not isinstance(updates,dict) or not isinstance(removals,list)
            or any(not isinstance(k,str) for k in list(updates)+removals)
            or len(set(removals)) != len(removals)
            or set(updates).intersection(removals)
            or any(k not in previous for k in removals)):
        raise ValueError('invalid delta changes')
    result = deepcopy(previous)
    for key in removals:
        del result[key]
    result.update(deepcopy(updates))
    if digest(result) != patch['target_digest']:
        raise ValueError('delta target differs')
    if result.get('protocol') != previous['protocol']:
        raise ValueError('delta cannot cross role protocol')
    _validate(result)
    return result


def seal_input_state(payload, anchor_input, anchor_checkpoint, *, rejected):
    """Persist transport provenance outside the model-visible input."""
    value = {'version': INPUT_HANDOFF_VERSION, 'payload': deepcopy(payload),
             'anchor_input': deepcopy(anchor_input),
             'anchor_checkpoint': deepcopy(anchor_checkpoint), 'rejected': rejected}
    return {**value, 'digest': digest(value)}


def input_update(role, lane, payload, checkpoint):
    """Return the exact saved base and event; also used by preflight and replay."""
    if (checkpoint.get('binding', {}).get('role') != role
            or checkpoint.get('binding', {}).get('lane') != lane):
        raise ValueError('role checkpoint input identity mismatch')
    state = checkpoint.get('input_state')
    expected = {'version', 'payload', 'anchor_input', 'anchor_checkpoint', 'rejected', 'digest'}
    if (not isinstance(state, dict) or set(state) != expected
            or state['version'] != INPUT_HANDOFF_VERSION
            or state['digest'] != digest({k: v for k, v in state.items() if k != 'digest'})
            or type(state['rejected']) is not bool):
        raise ValueError('checkpoint input state missing or inconsistent; start a new run')
    _validate(payload)
    _validate(state['payload'])
    _validate(state['anchor_input'])
    anchor = state['anchor_input']
    retry = (role == 'decision' and payload['boundary']['id'] == anchor['boundary']['id']
             and payload['selected_evidence'] == anchor['selected_evidence']
             and (state['rejected'] or (payload['protocol_feedback'] is not None
                  and payload['protocol_feedback'] != state['payload']['protocol_feedback'])))
    if role == 'executor':
        retry = (state['rejected'] and payload['assignment'] == anchor['assignment']
                 and all(item in anchor['observations'] for item in payload['observations'])
                 and (not payload['evidence_updates'] or payload['evidence_updates'] == anchor['evidence_updates']))
    parent = state['anchor_checkpoint'] if retry else checkpoint['checkpoint']
    if (parent.get('lane_id') != lane
            or any(parent.get(key) != checkpoint['checkpoint'].get(key)
                   for key in ('model', 'state_profile_id', 'state_profile_sha256'))):
        raise ValueError('checkpoint input anchor identity mismatch')
    previous = anchor if retry else state['payload']
    patch = make_delta(previous, payload)
    if apply_delta(previous, patch) != payload:
        raise ValueError('input delta failed complete semantic reconstruction')
    event = ModelEvent(event_type=DELTA_EVENT_TYPE,
        event_id='PI-' + digest([patch, parent['checkpoint_id']]), scope_id=lane, payload=patch)
    return parent, event, retry
