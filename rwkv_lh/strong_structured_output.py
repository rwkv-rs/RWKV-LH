"""Auditable provider schema projection; original role validation stays authoritative."""
from copy import deepcopy
from itertools import combinations
from .model_io import canonical_digest, canonical_json

PROTOCOL = 'rwkv-lh.strong-strict-tools.v4'
_KEYWORDS = {'type', 'properties', 'required', 'additionalProperties', 'items', 'anyOf',
             'enum', 'const', 'description', 'title', 'default', 'pattern', 'format',
             'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf',
             'minLength', 'maxLength', 'minItems', 'maxItems', 'uniqueItems'}


def _schema(value, path, deferred):
    if not isinstance(value, dict) or set(value) - _KEYWORDS:
        raise ValueError(f'unsupported strict schema at {path}')
    result = deepcopy(value)
    for key in ('minItems', 'maxItems', 'uniqueItems'):
        if key in result:
            deferred.append({'path': path, 'keyword': key, 'value': result.pop(key),
                             'enforced_by': 'original_role_schema'})
    lengths = {key: result.pop(key) for key in ('minLength', 'maxLength') if key in result}
    if lengths:
        if 'pattern' in result:
            deferred.extend({'path': path, 'keyword': key, 'value': val,
                             'enforced_by': 'original_role_schema'} for key, val in lengths.items())
        else:
            low, high = lengths.get('minLength', 0), lengths.get('maxLength', '')
            result['pattern'] = r'^[\s\S]{' + str(low) + ',' + str(high) + r'}$'
    if 'const' in result:
        const = result.pop('const')
        if 'enum' in result and result['enum'] != [const]:
            raise ValueError('conflicting strict enum and const')
        result['enum'] = [const]
    if 'anyOf' in result:
        result['anyOf'] = [_schema(item, f'{path}/anyOf/{i}', deferred) for i, item in enumerate(result['anyOf'])]
    if 'items' in result:
        result['items'] = _schema(result['items'], path + '/items', deferred)
    if result.get('type') == 'object':
        properties, required = result.get('properties'), result.get('required', [])
        if not isinstance(properties, dict) or result.get('additionalProperties') is not False or set(required) - properties.keys():
            raise ValueError(f'unsupported open object in strict schema at {path}')
        properties = {name: _schema(item, path + '/properties/' + name, deferred) for name, item in properties.items()}
        optional = [name for name in properties if name not in required]
        if optional:
            # Preserve omission semantics exactly. Never require extra values or
            # insert null/default parameters into the model's chosen operation.
            variants = []
            for size in range(len(optional) + 1):
                for subset in combinations(optional, size):
                    names = set(required) | set(subset)
                    chosen = {k: v for k, v in properties.items() if k in names}
                    variants.append({'type': 'object', 'properties': chosen,
                                     'required': list(chosen), 'additionalProperties': False})
            return {'anyOf': variants, **{k: result[k] for k in ('description', 'title') if k in result}}
        result['properties'] = properties
        result['required'] = list(properties)
    return result


def build_tool_contract(definitions):
    if not definitions or len({d['name'] for d in definitions}) != len(definitions):
        raise ValueError('strict tools require unique current role definitions')
    tools, deferred = [], []
    for item in definitions:
        # The provider carrier already identifies the function. Its arguments
        # are the declared parameters, with no second call-envelope layer.
        parameters = _schema(item['parameters'], item['name'], deferred)
        tools.append({'type': 'function', 'function': {'name': item['name'],
            'description': item['description'], 'strict': True,
            'parameters': parameters}})
    choice = ({'type': 'function', 'function': {'name': definitions[0]['name']}}
              if len(definitions) == 1 else 'required')
    contract = {'protocol': PROTOCOL, 'tools': tools, 'original_definitions': deepcopy(definitions),
                'tool_choice': choice, 'argument_encoding': 'direct_parameter_object',
                'deferred_constraints': deferred}
    return {**contract, 'contract_sha256': canonical_digest(contract)}


def tool_response_content(message):
    """Preserve the actual call carriers for the role parser, including invalid ones."""
    value = {'tool_calls': deepcopy(message.get('tool_calls', []))}
    # Keep every arguments string byte-for-byte, including malformed JSON,
    # duplicate keys or an obsolete wrapper. The role parser owns rejection.
    if message.get('content') not in (None, ''):
        value['content'] = message['content']
    if message.get('refusal'):
        value['refusal'] = message['refusal']
    return canonical_json(value)
