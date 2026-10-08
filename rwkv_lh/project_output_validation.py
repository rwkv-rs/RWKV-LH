"""Discard surplus identity echoes and validate the selected role operation."""
from .schema_validation import validate_schema
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


def validate_role_output(role, payload, command, definitions):
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
