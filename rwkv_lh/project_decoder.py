"""Constrain current role choices without choosing an action or resetting State."""
from copy import deepcopy
from .runtime.structured_output import build_decoder_contract
from .project_protocols import executor
from .project_receipt_refs import visible_references
from .project_action_binding import BEFORE_TOOL, CONTROL_ACTIONS, tool_steps

INPUT_FRAMING = 'project-decoder-json-fence.v1'
BOUNDARY_POLICY = 'project-boundary-decoder.v4'


def _reference(schema, field, values):
    """Project the builder's exact ID catalog, including empty evidence arrays."""
    parent = schema
    *parents, name = field.split('.')
    for key in parents:
        child = deepcopy(parent['properties'][key])
        parent['properties'][key] = child
        parent = child
    # Definitions deliberately share STRING/schema objects. deepcopy preserves
    # those aliases: detach this field before narrowing it, so a task enum can
    # never overwrite the verification/advice enum of another property.
    target = deepcopy(parent['properties'][name])
    parent['properties'][name] = target
    if target.get('type') == 'array':
        if values:
            target['items']['enum'] = list(values)
        else:
            target['maxItems'] = 0
    elif values:
        target['enum'] = list(values)
    elif name not in parent.get('required', ()):
        del parent['properties'][name]
    else:
        raise ValueError('required scalar reference has no permitted values')


def _boundary_parameters(role, payload, item, references):
    name, schema = item['name'], item['parameters']
    refs = references.get(name, {})
    if name == 'read_receipt' and not refs['evidence_id']:
        return []
    if name == 'select_step' and payload['step_binding'] != BEFORE_TOOL:
        return []
    if name not in CONTROL_ACTIONS:
        steps = tool_steps(payload)
        if not steps:
            return []
        refs = {'task_id': steps}
    current = deepcopy(schema)
    for field, values in refs.items():
        _reference(current, field, values)
    return [current]


def _current_contracts(definitions, *, role, payload):
    """One source of current availability and exact reference constraints."""
    if role != 'executor':
        raise ValueError('current Native role required')
    executor.validate_input(payload)
    references = visible_references(payload)
    for item in definitions:
        variants = _boundary_parameters(role, payload, item, references)
        if variants:
            yield item, variants


def available_definitions(definitions, *, role, payload):
    """Disclose each available tool shape once; references carry current values."""
    return [deepcopy(item) for item, _ in _current_contracts(definitions, role=role, payload=payload)]


def tool_menu_update(definitions, *, role, payload, checkpoint, retry):
    """Replace changed contracts and remove unavailable tools without repeating the catalog."""
    previous = checkpoint['input_state']['anchor_input' if retry else 'payload']
    old = {item['name']: item for item in available_definitions(definitions, role=role, payload=previous)}
    current = {item['name']: item for item in available_definitions(definitions, role=role, payload=payload)}
    if old == current:
        return None
    return {'available': list(current), 'set': [item for name, item in current.items() if old.get(name) != item],
            'remove': [name for name in old if name not in current]}


def build_role_decoder(definitions, *, role=None, payload=None):
    """Static catalog identity, or the exact grammar for a production boundary.

    Catalog/policy identities stay bound to the lane. Per-call constraints come
    solely from the canonical role input and are attested by the generation.
    """
    if not definitions or len({item['name'] for item in definitions}) != len(definitions):
        raise ValueError('decoder requires unique role tools')
    if role is not None or payload is not None:
        if role != 'executor' or payload is None:
            raise ValueError('boundary decoder requires a Native role and its input')
        contracts = _current_contracts(definitions, role=role, payload=payload)
    else:
        contracts = ((item, [item['parameters']]) for item in definitions)
    return build_decoder_contract({'anyOf': [
        {'type': 'object', 'properties': {
            'function': {'const': item['name']}, 'params': params},
         'required': ['function', 'params'], 'additionalProperties': False}
        for item, variants in contracts for params in variants]})
