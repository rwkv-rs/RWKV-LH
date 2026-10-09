"""Validate the exact current role output; never discard or repair fields."""
from .schema_validation import validate_schema
from .project_contracts import validate_plan
from .project_protocols import planner, executor


def validate_role_output(role, payload, command, definitions):
    {'planner': planner, 'executor': executor}[role].validate_input(payload)
    selected = next((d for d in definitions if d['name'] == command.name), None)
    if selected is None:
        raise ValueError('operation not available to this role')
    validate_schema(command.arguments, selected['parameters'])
    if role == 'planner':
        mode = payload.get('mode')
        allowed = planner.allowed_operations(payload)
        if command.name not in allowed:
            raise ValueError(f'planner operation {command.name!r} is not permitted in mode {mode!r}; '
                             f'available: {", ".join(sorted(allowed))}')
    if role == 'planner' and command.name == 'submit_plan':
        validate_plan(command.arguments['plan'])
    if role == 'executor':
        executor.validate_references(payload, command.to_wire_dict())
