"""Project-role text boundaries and single-call transport normalization."""
import json
from collections.abc import Mapping

from . import model_io
from .model_io import ModelCommandNormalization, ModelIOError
from .project_input_delta import DELTA_EVENT_TYPE
from .project_input_rendering import render_fields


PROJECT_CALL_NORMALIZER_VERSION = 'project-call-envelope.v1'
PROJECT_INPUT_PREFIX = (
    "\n\nUser: Controller role update: Follow the current payload instruction and "
    "its observed facts. Choose exactly one available function and return only "
    "its declared parameters inside a function/params JSON call. Role input: "
)
_GENERIC_INPUT_PREFIX = "\n\nUser: Function output: "
PROMPT_LAYOUT_VERSION = 'project-role-prompt.v10'


def project_prompt_identity(role):
    from .project_protocols import executor
    from .project_contracts import digest
    module = {'executor': executor}[role]
    return digest({'layout': PROMPT_LAYOUT_VERSION, 'rules': module.RULES,
                   'question': module.INSTRUCTION})


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
                    + model_io.canonical_json(tool_update) + _GENERIC_INPUT_PREFIX + body)
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
        removals = '\nRemoved fields: ' + model_io.canonical_json(event.payload['remove']) if event.payload['remove'] else ''
        return lead + prefix + render_fields(event.payload['set']) + removals + '\n' + INSTRUCTION + anchor
    if event.event_type != 'project_role_input':
        return rendered
    if _GENERIC_INPUT_PREFIX not in rendered:
        raise ModelIOError('project role event lacked the generic event prefix')
    lead = rendered.split(_GENERIC_INPUT_PREFIX, 1)[0]
    return lead + PROJECT_INPUT_PREFIX + render_project_assignment(event.payload) + model_io.ASSISTANT_JSON_CONTINUATION_ANCHOR


def parse_project_model_command_with_trace(raw_output, *, bare_call=None):
    """Accept one explicit Project call plus surplus envelope IDs and annotations."""
    try:
        return model_io.parse_model_command_with_trace(raw_output)
    except ModelIOError as error:
        parse_error = error
    source, transformations = model_io._extract_json(raw_output)
    try:
        value = model_io.load_model_json(source)
    except json.JSONDecodeError:
        repaired = model_io._repair_structural_escaped_quotes(source)
        if repaired is None:
            raise parse_error
        try:
            value = model_io.load_model_json(repaired)
        except json.JSONDecodeError:
            raise parse_error
        transformations.append('surface:structural_escaped_quotes_repaired')
    if not isinstance(value, Mapping):
        raise parse_error
    input_payload = dict(value)
    value = dict(value)
    outer_ids = [key for key in value if isinstance(key, str) and key.casefold() == 'id']
    if outer_ids:
        for key in outer_ids:
            value.pop(key)
        transformations.append('call_envelope:outer_id_removed')
    if 'content' in value:
        if (set(value) - {'content', 'state', 'summary'} or
                not isinstance(value['content'], list) or len(value['content']) != 1 or
                not isinstance(value['content'][0], Mapping)):
            raise parse_error
        value = dict(value['content'][0])
        content_ids = [key for key in value if isinstance(key, str) and key.casefold() == 'id']
        if content_ids:
            for key in content_ids:
                value.pop(key)
            transformations.append('call_envelope:content_call_id_removed')
        transformations.append('call_envelope:single_content_call->function+params')
    if set(value) == {'function_call'} and isinstance(value['function_call'], Mapping):
        call = dict(value['function_call'])
        call_ids = [key for key in call if isinstance(key, str) and key.casefold() == 'id']
        if call_ids:
            for key in call_ids:
                call.pop(key)
            value['function_call'] = call
            transformations.append('call_envelope:function_call_id_removed')
    if bare_call is not None:
        name, parameter_schema = bare_call
        properties = parameter_schema.get('properties', {})
        required = set(parameter_schema.get('required', ()))
        if (isinstance(properties, Mapping) and required <= set(value) <= set(properties)
                and not ({'function', 'name', 'tool', 'params', 'parameters',
                          'arguments', 'args', 'function_args', 'function_call'} & set(value))):
            value = {'function': name, 'params': value}
            transformations.append(f'call_envelope:bare_role_parameters->{name}')
    if not transformations:
        raise parse_error
    command, nested = model_io.parse_model_command_with_trace(
        json.dumps(value, ensure_ascii=False))
    return command, ModelCommandNormalization(
        input_payload=input_payload,
        normalized_payload=command.to_wire_dict(),
        transformations=tuple(transformations) + nested.transformations,
        normalizer_version=PROJECT_CALL_NORMALIZER_VERSION,
    )


def parse_project_model_command(raw_output):
    command, _normalization = parse_project_model_command_with_trace(raw_output)
    return command
