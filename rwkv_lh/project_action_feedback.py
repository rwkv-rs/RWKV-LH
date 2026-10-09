"""Literal tool feedback and protocol rejections for autonomous execution."""
from copy import deepcopy
from .project_evidence import executor_evidence_ids


def build_action_feedback(state, *, role, assignment=None, references=None):
    if role != 'executor':
        raise ValueError('only Executor receives action feedback')
    lane = assignment['id']
    allowed = executor_evidence_ids(state)
    latest = None
    for identifier, receipt in state['evidence'].items():
        if identifier not in allowed:
            continue
        selected = state['selected_evidence'].get(lane, {}).get(identifier, {}).get('evidence', {})
        latest = {'evidence_id': identifier, 'kind': receipt['kind'],
            'action': deepcopy(receipt['intent']),
            'result': deepcopy(selected.get('raw_result', receipt['result']))}
    rejected = None
    rejection = state['role_rejections'].get(lane)
    if rejection:
        identifier = rejection['rejected_operation_id']
        receipt = state['evidence'][identifier]
        recorded = receipt['result']['evidence']
        command = recorded.get('rejected_command') or receipt['result']['command']
        from .project_runtime import role_definitions
        from .harness import ActionHarness
        definition = next((d for d in role_definitions(role, ActionHarness()) if d['name'] == command.get('function')), None)
        rejected = {'operation_id': identifier, 'role': role, 'call': deepcopy(command),
            'raw_output': rejection.get('rejected_output'), 'error': rejection['error'],
            'is_execution_evidence': False, 'usable_evidence_ids': [k for k in state['evidence'] if k in allowed],
            'parameter_schema': recorded.get('rejected_parameter_schema') or (definition['parameters'] if definition else None),
            'function_name': recorded.get('rejected_function_name') or (definition['name'] if definition else None),
            'parameter_references': deepcopy(references or {}), 'attempt_history': None}
        from .project_rejection_history import rejection_attempt_history
        rejected['attempt_history'] = rejection_attempt_history(state, rejected, assignment=assignment)
    return {'receiving_role': role, 'last_execution': latest, 'rejected_call': rejected}


def action_call(intent):
    """One invocation spelling; audit identity is rendered separately, not as a call."""
    if 'name' in intent and 'arguments' in intent:
        return {'function': 'execute_tool', 'params': {'step_id': intent['step_id'], 'tool': intent['name'], 'arguments': deepcopy(intent['arguments'])}}
    return intent


def action_origin(intent):
    if 'name' not in intent or 'arguments' not in intent:
        return {}  # Verification intent is already shown intact as the action.
    return {key: value for key, value in intent.items() if key not in ('name', 'arguments')}


def render_result(result):
    from .project_markdown import section, literal
    body = deepcopy(result)
    output = body.pop('output', None)
    lines = [section('Observed result', body)]
    if output is not None:
        lines.append(section('Output (literal data)', output))
    return '\n\n'.join(lines)


def render_action_feedback(value):
    from .project_markdown import section
    lines = ['## Actual action feedback']
    execution = value['last_execution']
    if execution is None:
        lines.append('No confirmed tool execution yet.')
    else:
        lines.extend([section('Receipt', execution['evidence_id']),
            section('Executed action', action_call(execution['action'])),
            section('Origin', action_origin(execution['action'])), render_result(execution['result'])])
    rejected = value['rejected_call']
    if rejected is not None:
        lines.append(section('Rejected model call (no tool execution)', rejected))
    return '\n\n'.join(lines)


def validate_action_feedback(value):
    """Check the view's shape; complete original-ledger replay proves its facts."""
    from .project_contracts import fields, strings
    fields(value, ('receiving_role', 'last_execution', 'rejected_call'))
    if value['receiving_role'] != 'executor':
        raise ValueError('unknown feedback receiver')
    execution = value['last_execution']
    if execution is not None:
        fields(execution, ('evidence_id', 'kind', 'action', 'result'))
        if (not isinstance(execution['evidence_id'], str) or not execution['evidence_id']
                or not isinstance(execution['kind'], str) or not execution['kind']
                or execution['kind'] == 'model'
                or not isinstance(execution['action'], dict)
                or not isinstance(execution['result'], dict)):
            raise ValueError('action feedback requires a confirmed non-model receipt')
    rejected = value['rejected_call']
    if rejected is not None:
        fields(rejected, ('operation_id', 'role', 'call', 'raw_output', 'error',
                          'is_execution_evidence', 'usable_evidence_ids',
                          'parameter_schema', 'parameter_references', 'function_name', 'attempt_history'))
        if (not isinstance(rejected['operation_id'], str) or not rejected['operation_id']
                or rejected['role'] != 'executor'
                or not isinstance(rejected['call'], dict)
                or not isinstance(rejected['error'], str) or not rejected['error']
                or rejected['is_execution_evidence'] is not False):
            raise ValueError('a rejected call is not execution evidence')
        from .project_rejection_history import validate_attempt_history
        validate_attempt_history(rejected['attempt_history'], rejected['operation_id'])
        name, schema = rejected['function_name'], rejected['parameter_schema']
        if ((name is None) != (schema is None) or (name is not None and
                (not isinstance(name, str) or not name or name != name.strip() or not isinstance(schema, dict)))):
            raise ValueError('rejected function name and schema must be bound together')
        strings(rejected['usable_evidence_ids'])
    return value
