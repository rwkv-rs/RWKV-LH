"""Strict Planner carrier; Executor messages use transcript.parse exclusively."""
from .model_io import ModelCommand, ModelCommandNormalization, ModelIOError
from .transcript.parse import loads
from .project_protocols.planner import PROTOCOL


def parse_role_call(raw, *, role, payload):
    if role != 'planner':
        raise ModelIOError('Planner carrier required; Executor uses native transcript messages')
    from .project_protocols import planner
    planner.validate_input(payload)
    try:
        value = loads(raw)
        if not isinstance(value, dict) or set(value) != {'tool_calls'}:
            raise ValueError('Planner requires the original provider tool-call carrier')
        calls = value['tool_calls']
        if not isinstance(calls, list) or len(calls) != 1:
            raise ValueError('Planner requires exactly one tool call')
        call = calls[0]
        if (not isinstance(call, dict) or set(call) != {'id', 'type', 'function'}
                or call['type'] != 'function' or not isinstance(call['id'], str) or not call['id']
                or not isinstance(call['function'], dict) or set(call['function']) != {'name', 'arguments'}
                or not isinstance(call['function']['arguments'], str)):
            raise ValueError('invalid Planner API function carrier')
        name = call['function']['name']
        arguments = loads(call['function']['arguments'])
        if not isinstance(name, str) or not name.strip() or not isinstance(arguments, dict):
            raise ValueError('Planner function name and parameter object required')
    except (ValueError, TypeError, KeyError) as exc:
        raise ModelIOError(str(exc)) from exc
    command = ModelCommand(name, arguments)
    return command, ModelCommandNormalization(input_payload=value, normalized_payload=command.to_wire_dict(),
        transformations=('transport:provider_single_tool_call',), normalizer_version=PROTOCOL)
