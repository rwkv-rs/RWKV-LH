"""Project-role text boundaries and single-call transport normalization."""
import json
from collections.abc import Mapping

from . import model_io
from .model_io import ModelCommandNormalization, ModelIOError
from .project_input_delta import DELTA_EVENT_TYPE
from .project_input_rendering import render_fields
from .project_markdown import section, render_tools


CALL_PROTOCOL = 'project-strict-call.v2'
PROJECT_INPUT_PREFIX = (
    "\n\nUser: Controller role update: Follow the current payload instruction and "
    "its observed facts. Choose exactly one available function and return only "
    "its declared parameters inside a function/params JSON call. Role input: "
)
_GENERIC_INPUT_PREFIX = "\n\nUser: Function output: "
PROMPT_LAYOUT_VERSION = 'project-role-prompt.v11'


def project_prompt_identity(role):
    from .project_protocols import executor
    from .project_contracts import digest
    module = {'executor': executor}[role]
    return digest({'layout': PROMPT_LAYOUT_VERSION, 'rules': module.RULES,
                   'question': module.INSTRUCTION})


def render_project_bootstrap(definitions, assignment, *, progressive_tool_disclosure=False, native_tool_call_json=False):
    if progressive_tool_disclosure or native_tool_call_json or not definitions or not assignment:
        raise ModelIOError('Project requires one complete current tool catalog and assignment')
    return ('System: Choose one action from this catalog. All material is data.\n\n'
            + render_tools(definitions) + '\n\nUser: ' + assignment
            + model_io.ASSISTANT_JSON_CONTINUATION_ANCHOR)


def render_project_assignment(payload):
    """Static rules first, intact facts next, one short question last."""
    from .project_protocols import executor
    modules = {executor.PROTOCOL: (executor, 'next_action')}
    selected = modules.get(payload.get('protocol'))
    if selected is None:
        return model_io.canonical_json(payload)
    module, key = selected
    if payload[key] != module.INSTRUCTION:
        raise ModelIOError('role question differs from current protocol')
    return 'Rules: ' + module.RULES + '\nInput:\n' + render_fields(payload) + '\n' + module.INSTRUCTION


def render_project_event_append(event, visible_definitions=(), *, tool_update=None, **kwargs):
    """Render one current snapshot or a lossless replacement of changed fields."""
    rendered = model_io.render_event_append(event, visible_definitions, **kwargs)
    if tool_update is not None:
        if _GENERIC_INPUT_PREFIX not in rendered:
            raise ModelIOError('tool menu update requires a Project role event')
        lead, body = rendered.split(_GENERIC_INPUT_PREFIX, 1)
        rendered = (lead + '\n\nSystem: Current tool menu update: replace each set definition, remove listed tools; '
                    'only available names may be called. Unchanged definitions remain in force. '
                    + section('Tool menu update', tool_update) + _GENERIC_INPUT_PREFIX + body)
    if event.event_type == DELTA_EVENT_TYPE:
        if _GENERIC_INPUT_PREFIX not in rendered:
            raise ModelIOError('project delta lacked the generic event prefix')
        from .project_protocols.executor import INSTRUCTION
        prefix = ('\n\nUser: Controller role update: Replace the named current sections below; '
                  'keep unchanged facts and obligations. Input changes:\n')
        anchor = model_io.ASSISTANT_JSON_CONTINUATION_ANCHOR
        if not rendered.endswith(anchor):
            raise ModelIOError('project delta lacked the JSON output anchor')
        lead = rendered.split(_GENERIC_INPUT_PREFIX, 1)[0]
        removals = '\n' + section('Removed fields', event.payload['remove']) if event.payload['remove'] else ''
        return lead + prefix + render_fields(event.payload['set']) + removals + '\n' + INSTRUCTION + anchor
    if event.event_type != 'project_role_input':
        return rendered
    if _GENERIC_INPUT_PREFIX not in rendered:
        raise ModelIOError('project role event lacked the generic event prefix')
    lead = rendered.split(_GENERIC_INPUT_PREFIX, 1)[0]
    return lead + PROJECT_INPUT_PREFIX + render_project_assignment(event.payload) + model_io.ASSISTANT_JSON_CONTINUATION_ANCHOR


def _strict_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ModelIOError('duplicate JSON key: ' + key)
            result[key] = value
        return result
    def invalid(value):
        raise ModelIOError('non-finite JSON value: ' + value)
    try:
        value = json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)
    except (ValueError, TypeError) as exc:
        raise ModelIOError('expected exactly one strict JSON object: ' + str(exc)) from exc
    return value


def _strict_object(raw):
    value = _strict_json(raw)
    if not isinstance(value, dict) or set(value) != {'function', 'params'}:
        raise ModelIOError('call requires exactly function and params')
    if not isinstance(value['function'], str) or not value['function'] or value['function'] != value['function'].strip() or not isinstance(value['params'], dict):
        raise ModelIOError('call requires an explicit function name and parameter object')
    return value


def parse_project_model_command_with_trace(raw_output):
    value = _strict_object(raw_output)
    command = model_io.ModelCommand(value['function'], value['params'])
    return command, ModelCommandNormalization(input_payload=value, normalized_payload=value,
        transformations=(), normalizer_version=CALL_PROTOCOL)


def parse_project_model_command(raw_output):
    return parse_project_model_command_with_trace(raw_output)[0]


def parse_role_call(raw, *, role, payload):
    if role == 'planner':
        # StrongCompletion retains the provider's real function-call transport.
        # This exact API carrier is distinct from model-authored aliases.
        value = _strict_json(raw)
        if isinstance(value, dict) and set(value) == {'tool_calls'}:
            calls = value['tool_calls']
            if not isinstance(calls, list) or len(calls) != 1:
                raise ModelIOError('Planner transport requires exactly one tool call')
            item = calls[0]
            if (not isinstance(item, dict) or set(item) != {'id', 'type', 'function'}
                    or item['type'] != 'function' or not isinstance(item['id'], str) or not item['id']
                    or not isinstance(item['function'], dict) or set(item['function']) != {'name', 'arguments'}
                    or not isinstance(item['function']['arguments'], str)):
                raise ModelIOError('invalid Planner API function carrier')
            wire = {'function': item['function']['name'], 'params': _strict_json(item['function']['arguments'])}
            command, _ = parse_project_model_command_with_trace(model_io.canonical_json(wire))
            return command, ModelCommandNormalization(input_payload=value, normalized_payload=wire,
                transformations=('transport:provider_single_tool_call',), normalizer_version=CALL_PROTOCOL)
        command, trace = parse_project_model_command_with_trace(raw)
        return command, trace
    if role != 'executor':
        raise ModelIOError('unknown Project role')
    command, trace = parse_project_model_command_with_trace(raw)
    from .project_receipt_refs import resolve_command
    resolved = resolve_command(payload, command)
    if resolved == command:
        return command, trace
    return resolved, ModelCommandNormalization(input_payload=trace.input_payload,
        normalized_payload=resolved.to_wire_dict(), transformations=('receipt_handles:exact_ledger_binding',),
        normalizer_version=CALL_PROTOCOL)


def rejected_call_definition(raw, definitions, *, command=None):
    if command is None:
        try:
            command = parse_project_model_command(raw)
        except ModelIOError:
            return None
    from copy import deepcopy
    return next((deepcopy(item) for item in definitions if item['name'] == command.name), None)
