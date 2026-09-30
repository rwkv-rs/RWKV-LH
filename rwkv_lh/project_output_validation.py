"""Discard surplus identity echoes and validate the selected role operation."""
import re
from .project_contracts import digest, validate_plan, validate_check
from .model_io import ModelCommand
from .project_protocols import decision, planner, executor

ROLE_PARAMETER_NORMALIZER_VERSION = 'project-role-identity-discard.v1'


def normalize_role_output(role, command, definitions):
    """Discard surplus identity echoes, retaining IDs declared by the chosen operation.

    A task/evidence/tool ID in the operation schema is an argument, not metadata.
    Other unexpected arguments remain untouched so validation can reject them.
    """
    selected = next((item for item in definitions if item['name'] == command.name), None)
    if selected is None or not isinstance(command.arguments, dict):
        return command, None
    declared = selected['parameters'].get('properties', {})
    ignored = {'plan_version', 'workspace_digest'} if role == 'decision' else set()
    discarded = sorted(key for key in command.arguments if key not in declared and
        (key == 'id' or key.endswith('_id') or key.endswith('_ids') or key in ignored))
    if not discarded:
        return command, None
    normalized = ModelCommand(command.name, {
        key: value for key, value in command.arguments.items() if key not in discarded})
    return normalized, {
        'normalizer_version': ROLE_PARAMETER_NORMALIZER_VERSION,
        'discarded_fields': discarded,
        'original_payload': command.to_wire_dict(),
        'normalized_payload': normalized.to_wire_dict(),
        'original_payload_digest': digest(command.to_wire_dict()),
        'normalized_payload_digest': digest(normalized.to_wire_dict()),
        'controller_semantic_fields_generated': False,
    }


def validate_schema(value, schema, path='params'):
    """The JSON Schema subset used by production role/tool definitions."""
    kind = schema.get('type')
    types = {'object': dict, 'array': list, 'string': str, 'boolean': bool,
             'integer': int, 'number': (int, float)}
    if kind in types and (not isinstance(value, types[kind]) or
            kind in ('integer', 'number') and isinstance(value, bool)):
        raise ValueError(f'{path}: expected {kind}')
    if 'enum' in schema and value not in schema['enum']:
        raise ValueError(f'{path}: expected one of {schema["enum"]!r}')
    if 'const' in schema and value != schema['const']:
        raise ValueError(f'{path}: expected {schema["const"]!r}')
    if isinstance(value, dict):
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
        if schema.get('uniqueItems') and len({digest(v) for v in value}) != len(value):
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


def validate_role_output(role, payload, command, definitions):
    selected = next((d for d in definitions if d['name'] == command.name), None)
    if selected is None:
        raise ValueError('operation not available to this role')
    validate_schema(command.arguments, selected['parameters'])
    if role == 'planner':
        mode = payload.get('mode')
        if command.name not in planner.allowed_operations(payload):
            raise ValueError('planner operation is not permitted in the current mode')
        if mode in ('review', 'review_checks') and command.name in ('review_plan', 'review_checks'):
            planner.validate_review(command.arguments)
    if role == 'planner' and command.name in ('submit_plan', 'revise_plan'):
        validate_plan(command.arguments['plan'])
        if payload['plan'] is None and command.arguments.get('replacements'):
            raise ValueError('initial plan cannot replace checks; submit the corrected candidate with submit_plan')
    if role == 'planner' and command.name == 'submit_checks':
        for check in command.arguments['checks']:
            validate_check(check)
    if role == 'decision':
        decision.validate_response(payload, command.to_wire_dict())
    if role == 'executor':
        executor.validate_references(payload, command.to_wire_dict())
