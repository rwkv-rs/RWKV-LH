"""Lossless, task-scoped model handles for existing ledger receipts.

Receipt order is the ledger's confirmed return order. Filtering a role's scope
never renumbers that order. Bindings are host metadata in the canonical input;
only typed reference positions are translated, never tool data or report prose.
"""
from copy import deepcopy
import re

from .model_io import ModelCommand


def build_bindings(state, allowed):
    allowed = set(allowed)
    ordered = ([key for key, item in state['evidence'].items() if item['kind'] != 'model']
               if state is not None else sorted(allowed))
    if allowed - set(ordered):
        raise ValueError('receipt scope contains no corresponding confirmed ledger receipt')
    return {f'receipt:{index}': key for index, key in enumerate(ordered, 1) if key in allowed}


def validate_bindings(bindings, allowed):
    if (not isinstance(bindings, dict)
            or any(not isinstance(key, str) or not re.fullmatch(r'receipt:[1-9][0-9]*', key)
                   or not isinstance(value, str) or not value for key, value in bindings.items())
            or len(set(bindings.values())) != len(bindings)
            or set(bindings.values()) != set(allowed)):
        raise ValueError('receipt bindings differ from the current evidence scope')


def visible_references(payload):
    inverse = {value: key for key, value in payload['receipt_bindings'].items()}
    result = deepcopy(payload['references'])
    for fields in result.values():
        for field, values in fields.items():
            if field in ('evidence_id', 'evidence_ids', 'receipt_id', 'receipt_ids'):
                fields[field] = [inverse[key] for key in values]
    return result


def resolve_command(payload, command):
    """Resolve exactly the model's selections; never infer or repair a reference."""
    paths = {'read_receipt': ('receipt_id',), 'finish_work': ('receipt_ids',)}.get(command.name, ())
    if not paths:
        return command
    params = deepcopy(command.arguments)
    bindings = payload['receipt_bindings']
    for path in paths:
        node = params
        *parents, field = path.split('.')
        for key in parents:
            node = node.get(key, {}) if isinstance(node, dict) else {}
        if not isinstance(node, dict) or field not in node:
            continue  # Missing/ill-typed parameters still fail the original schema.
        values = node[field] if field.endswith('_ids') else [node[field]]
        if (not isinstance(values, list) or any(not isinstance(value, str) or value not in bindings for value in values)):
            raise ValueError(f'params.{path}: select an available receipt handle from current parameter references')
        resolved = [bindings[value] for value in values]
        references = payload['references'].get(command.name, {})
        allowed = references.get(path, [])
        if set(resolved) - set(allowed):
            raise ValueError(f'params.{path}: receipt handle is outside this action/task scope')
        node[field] = resolved if field.endswith('_ids') else resolved[0]
    return ModelCommand(command.name, params)


def render_view(fields):
    """Project host-owned identities only; preserve all literal user/tool content."""
    if 'receipt_bindings' not in fields:
        return deepcopy(fields)
    inverse = {value: key for key, value in fields['receipt_bindings'].items()}
    receipt_fields = {'receipt_id', 'receipt_ids', 'evidence_id', 'evidence_ids', 'action_id', 'operation_id', 'usable_evidence_ids'}
    opaque = {'arguments', 'params', 'result', 'raw_result', 'output', 'raw_output',
              'parameter_schema', 'plan', 'current_step', 'goal', 'task', 'requirements'}

    def visit(value, field=None):
        if field in opaque:
            return deepcopy(value)
        if isinstance(value, str):
            return inverse.get(value, value) if field in receipt_fields else value
        if isinstance(value, list):
            return [visit(item, field) for item in value]
        if not isinstance(value, dict):
            return value
        if field in ('references', 'parameter_references'):
            return visible_references({'references': value, 'receipt_bindings': fields['receipt_bindings']})
        return {(inverse.get(key, key) if field in ('evidence_updates', 'selected_evidence') else key):
                visit(item, key) for key, item in value.items()
                if key not in ('receipt_bindings', 'assignment_id') and not (field in ('assignment', 'active') and key == 'id')}

    return visit(fields)
