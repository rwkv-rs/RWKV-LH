"""Auditable output grammar contract; execution schemas remain authoritative."""
from copy import deepcopy
from typing import Any, Mapping

from .native_request_protocol import native_result_digest

DECODER_PROTOCOL = 'rwkv-lh.structured-output.v2'
DECODER_BACKEND = 'guidance'
STATE_OUTPUT_POLICY = 'exclude_terminal_eos'


def _generation_schema(schema, path='$', deferred=None):
    if deferred is None:
        deferred = []
    if not isinstance(schema, dict):
        return deepcopy(schema)
    result = {}
    for key, value in schema.items():
        if key == 'uniqueItems' and type(value) is not bool:
            raise ValueError('uniqueItems must be a boolean schema keyword')
        if key == 'uniqueItems' and schema.get('type') == 'array':
            if value is True:
                deferred.append({'path': path, 'keyword': key, 'value': True,
                                 'validator': 'original_execution_schema'})
            continue
        if key in ('properties', 'patternProperties', '$defs', 'definitions', 'dependentSchemas'):
            result[key] = {name: _generation_schema(item, f'{path}.{key}.{name}', deferred)
                           for name, item in value.items()}
        elif key in ('items', 'additionalProperties', 'not', 'if', 'then', 'else', 'contains', 'propertyNames') and isinstance(value, dict):
            result[key] = _generation_schema(value, f'{path}.{key}', deferred)
        elif key in ('allOf', 'anyOf', 'oneOf', 'prefixItems'):
            result[key] = [_generation_schema(item, f'{path}.{key}[{index}]', deferred)
                           for index, item in enumerate(value)]
        else:
            result[key] = deepcopy(value)
    return result


def build_decoder_contract(schema: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(schema, dict) or not schema:
        raise ValueError('decoder requires a nonempty JSON schema')
    original = deepcopy(schema)
    deferred = []
    generated = _generation_schema(original, deferred=deferred)
    value = {'protocol': DECODER_PROTOCOL, 'backend': DECODER_BACKEND,
             'state_output_policy': STATE_OUTPUT_POLICY,
             'original_schema': original, 'original_schema_sha256': native_result_digest(original),
             'generation_schema': generated, 'generation_schema_sha256': native_result_digest(generated),
             'deferred_constraints': deferred}
    value['contract_sha256'] = native_result_digest(value)
    return value


def validate_decoder_contract(value: Mapping[str, Any]) -> None:
    if not isinstance(value, dict) or value.get('protocol') != DECODER_PROTOCOL:
        raise ValueError('unsupported decoder contract')
    if value != build_decoder_contract(value.get('original_schema')):
        raise ValueError('decoder contract identity or projection mismatch')


def decoder_receipt(value: Mapping[str, Any]) -> dict[str, Any]:
    validate_decoder_contract(value)
    return {key: value[key] for key in ('protocol', 'backend', 'state_output_policy', 'contract_sha256',
                                       'original_schema_sha256', 'generation_schema_sha256')}


def state_output_token_ids(token_ids, finish_reason, decoder):
    """Keep the sampled stop token in raw evidence, outside the next prompt.

    A terminal RWKV EOS ends generation; the caller supplies the next turn's
    framing. No semantic token, field or action is added or repaired here.
    """
    validate_decoder_contract(decoder)
    if (not isinstance(token_ids, (list, tuple)) or not token_ids
            or any(type(token) is not int or token < 0 for token in token_ids)):
        raise ValueError('invalid decoder State output token IDs')
    result = list(token_ids)
    if 0 in result:
        if finish_reason != 'stop' or result[-1] != 0 or result.count(0) != 1 or len(result) == 1:
            raise ValueError('invalid decoder EOS boundary')
        result.pop()
    return result
