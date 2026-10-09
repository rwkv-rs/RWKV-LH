"""Shared JSON Schema subset for role output and executable tool arguments."""
from collections.abc import Mapping
import json
import re


def validate_schema(value, schema, path='params'):
    """The JSON Schema subset used by production role/tool definitions."""
    if 'anyOf' in schema:
        failures = []
        selected_failures = []
        for variant in schema['anyOf']:
            try:
                validate_schema(value, variant, path)
                break
            except ValueError as exc:
                failures.append(str(exc))
                discriminators = {key: prop['const'] for key, prop in variant.get('properties', {}).items()
                                  if 'const' in prop}
                if (isinstance(value, Mapping) and discriminators
                        and all(key in value and value[key] == expected for key, expected in discriminators.items())):
                    selected_failures.append(str(exc))
        else:
            # Diagnostics use an explicitly selected discriminator only after
            # every variant failed. This never changes union acceptance.
            raise ValueError(f'{path}: no permitted variant: ' + ' | '.join(selected_failures or failures))
    kind = schema.get('type')
    types = {'object': Mapping, 'array': list, 'string': str, 'boolean': bool,
             'integer': int, 'number': (int, float)}
    if kind in types and (not isinstance(value, types[kind]) or
            kind in ('integer', 'number') and isinstance(value, bool)):
        raise ValueError(f'{path}: expected {kind}')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError(f'{path}: must be one of {schema["enum"]!r}')
    if 'const' in schema and value != schema['const']:
        raise ValueError(f'{path}: expected {schema["const"]!r}')
    if isinstance(value, Mapping):
        properties = schema.get('properties', {})
        errors = [f'{path}.{key}: required' for key in schema.get('required', ()) if key not in value]
        if schema.get('additionalProperties') is False:
            errors += [f'{path}.{key}: not permitted' for key in value if key not in properties]
        for key in sorted(value.keys() & properties.keys()):
            try:
                validate_schema(value[key], properties[key], f'{path}.{key}')
            except ValueError as exc:
                errors.append(str(exc))
        if errors:
            raise ValueError('; '.join(errors))
    if isinstance(value, list):
        for bound, op in [('minItems', lambda a, b: a < b), ('maxItems', lambda a, b: a > b)]:
            if bound in schema and op(len(value), schema[bound]):
                raise ValueError(f'{path}: violates {bound}')
        if schema.get('uniqueItems'):
            canonical = {json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
                         for v in value}
            if len(canonical) != len(value):
                raise ValueError(f'{path}: duplicate items')
        if 'items' in schema:
            for index, item in enumerate(value):
                validate_schema(item, schema['items'], f'{path}[{index}]')
    if isinstance(value, str) and len(value) < schema.get('minLength', 0):
        raise ValueError(f'{path}: too short')
    if isinstance(value, str) and 'maxLength' in schema and len(value) > schema['maxLength']:
        raise ValueError(f'{path}: too long')
    if isinstance(value, str) and 'pattern' in schema and re.search(schema['pattern'], value) is None:
        raise ValueError(f'{path}: does not match pattern')
    if type(value) in (int, float):
        for bound, op in [('minimum', lambda a, b: a < b), ('maximum', lambda a, b: a > b),
                          ('exclusiveMinimum', lambda a, b: a <= b)]:
            if bound in schema and op(value, schema[bound]):
                raise ValueError(f'{path}: violates {bound}')
