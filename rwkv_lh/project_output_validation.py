"""Validate current role output without repairing fields or judging correctness."""
from .schema_validation import validate_schema
from .project_protocols import planner, executor
from .project_work_orders import validate_order
from .transcript.parse import parse_assistant
from .transcript.render import compact


def validate_role_output(role, payload, command, definitions):
    if role == 'executor':
        executor.validate_references(payload, command.to_wire_dict())
        parse_assistant(compact(command.arguments['message']), definitions)
        return
    if role != 'planner':
        raise ValueError('unknown Project role')
    planner.validate_input(payload)
    if command.name not in planner.allowed_operations(payload):
        raise ValueError('operation not available to Planner')
    selected = next((d for d in definitions if d['name'] == command.name), None)
    if selected is None:
        raise ValueError('operation not available to Planner')
    validate_schema(command.arguments, selected['parameters'])
    if command.name == 'issue_work_order':
        remaining = payload['remaining']['calls']
        validate_order(command.arguments, issued_ids=[item['order']['id'] for item in payload['work_orders']],
            total_remaining_calls=None if remaining is None else max(0, remaining - 1))
