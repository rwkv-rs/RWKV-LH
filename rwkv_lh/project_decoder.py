"""Constrain current role choices without choosing an action or resetting State."""
from copy import deepcopy
import json
from .runtime.structured_output import build_decoder_contract
from .project_protocols import executor
from .project_receipt_refs import visible_references

INPUT_FRAMING = 'rwkv-lh.coder.decoder-json-fence.v1'
BOUNDARY_POLICY = 'rwkv-lh.coder.boundary-decoder.v1'


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
    if name == 'read_receipt' and not refs['receipt_id']:
        return []
    variants = schema['anyOf'] if name == 'execute_tool' else [schema]
    result = []
    for variant in variants:
        current = deepcopy(variant)
        for field, values in refs.items():
            _reference(current, field, values)
        result.append(current)
    return result


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


_REJECTED = object()


def _schema_ordered(value, schema):
    """Arrange one value in the property order the boundary grammar emits."""
    if 'anyOf' in schema:
        for branch in schema['anyOf']:
            ordered = _schema_ordered(value, branch)
            if ordered is not _REJECTED:
                return ordered
        return _REJECTED
    if 'const' in schema and value != schema['const'] or 'enum' in schema and value not in schema['enum']:
        return _REJECTED
    if isinstance(value, list):
        if len(value) > schema.get('maxItems', len(value)):
            return _REJECTED
        items = [_schema_ordered(item, schema.get('items', {})) for item in value]
        return _REJECTED if any(item is _REJECTED for item in items) else items
    if not isinstance(value, dict) or 'properties' not in schema:
        return value
    properties = schema['properties']
    if (any(key not in properties for key in value) and schema.get('additionalProperties') is False
            or any(key not in value for key in schema.get('required', ()))):
        return _REJECTED
    ordered = {key: _schema_ordered(value[key], properties[key]) for key in properties if key in value}
    if any(item is _REJECTED for item in ordered.values()):
        return _REJECTED
    return ordered | {key: item for key, item in value.items() if key not in properties}


def render_role_target(definitions, command, *, role, payload):
    """Compact call text in grammar property order; the decoder supplies the EOS."""
    schema = build_role_decoder(definitions, role=role, payload=payload)['generation_schema']
    ordered = _schema_ordered(command, schema)
    if ordered is _REJECTED:
        raise ValueError('target is not admitted by the boundary decoder')
    return json.dumps(ordered, ensure_ascii=False, separators=(',', ':'))


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
