"""One native message layout for host turns, receipts and model targets.

The source document renderer uses the production collector's UTF-8 JSON
layout. Individual model turns use compact JSON plus one newline; callers
must use render_turns for both incremental serving and token supervision.
This module does not convert source vocabularies or export a dataset.
"""
from copy import deepcopy
import json

from ..schema_validation import validate_schema
from .parse import catalog, validate_message, validate_messages

PROTOCOL = 'rwkv-lh.coder.transcript.v1'
MESSAGE_KEYS = {'system': ('role', 'content'), 'user': ('role', 'content'),
                'assistant': ('role', 'content', 'reasoning_content', 'tool_calls'),
                'tool': ('role', 'tool_call_id', 'content')}
CALL_KEYS = ('id', 'type', 'function')
FUNCTION_KEYS = ('name', 'arguments')


def compact(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def user_message(content):
    """Host reports are User turns, never fabricated tool responses."""
    return validate_message({'role': 'user', 'content': content})


def system_message(content):
    return validate_message({'role': 'system', 'content': content})


def assistant_message(*, content=None, reasoning_content=None, tool_calls=()):
    return validate_message({'role': 'assistant', 'content': content,
        'reasoning_content': reasoning_content, 'tool_calls': deepcopy(list(tool_calls))})


def ordered_arguments(arguments, schema):
    """Order declared keys exactly as guidance does; never fill missing defaults."""
    validate_schema(arguments, schema)
    if isinstance(arguments, dict):
        props = schema.get('properties', {})
        keys = [key for key in props if key in arguments]
        keys.extend(key for key in arguments if key not in props)
        extra = schema.get('additionalProperties', {})
        return {key: ordered_arguments(arguments[key], props.get(key, extra if isinstance(extra, dict) else {}))
                for key in keys}
    if isinstance(arguments, list):
        return [ordered_arguments(item, schema.get('items', {})) for item in arguments]
    return arguments


def tool_call(identifier, name, arguments, native_tools):
    schemas = catalog(native_tools)
    if name not in schemas:
        raise ValueError('unknown canonical tool: ' + str(name))
    args = ordered_arguments(arguments, schemas[name])
    call = dict(zip(CALL_KEYS, (identifier, 'function',
        dict(zip(FUNCTION_KEYS, (name, compact(args)))))))
    validate_message(assistant_message(tool_calls=[call]))
    return call


def tool_result(identifier, result):
    """Render a raw Harness receipt with the production collector's field projection.

    Only host bookkeeping is omitted. Source/output strings and actual facts
    are unchanged; success, liveness and completion are never inferred. Passing
    an already rendered receipt is idempotent. JSON separators match collection.
    """
    if not isinstance(result, dict):
        raise ValueError('structured receipt object required')
    result = model_tool_result(result)
    if isinstance(result.get('metadata'), dict):
        # The originating call already carries these; the native collector
        # removes them after its shared project receipt projection as well.
        for key in ('command', 'argv', 'resolved_argv'):
            result['metadata'].pop(key, None)
    return validate_message({'role': 'tool', 'tool_call_id': identifier,
        'content': json.dumps(result, ensure_ascii=False, allow_nan=False)})


def render_message(message):
    validate_message(message)
    value = {key: deepcopy(message[key]) for key in MESSAGE_KEYS[message['role']] if key in message}
    if 'tool_calls' in value:
        value['tool_calls'] = [{key: (dict((k, call['function'][k]) for k in FUNCTION_KEYS)
            if key == 'function' else call[key]) for key in CALL_KEYS} for call in value['tool_calls']]
    return compact(value)


def render_turns(messages):
    validate_messages(messages)
    return [render_message(message) + '\n' for message in messages]


def render_transcript(document):
    """Serialize the parsed production document, not a cached copy of its bytes."""
    if not isinstance(document, dict) or set(document) != {'messages', 'tools'}:
        raise ValueError('native transcript document required')
    validate_messages(document['messages'])
    return (json.dumps(document, ensure_ascii=False, allow_nan=False, indent=2) + '\n').encode('utf-8')


def _host_view(value):
    if isinstance(value, dict):
        return {key: _host_view(item) for key, item in value.items()
                if key != 'sha256' and not key.endswith('_sha256')
                and key not in {'source_snapshots', 'snapshot_transition_verified',
                                'content_digest', 'contract_digest'}}
    if isinstance(value, list):
        return [_host_view(item) for item in value]
    return value


READ_ONLY_TOOLS = frozenset({'read_file', 'list_directory', 'search_files'})


def _without_empty(value):
    """Drop absent host facts; False and 0 remain observable values."""
    if isinstance(value, dict):
        kept = {key: _without_empty(item) for key, item in value.items()}
        return {key: item for key, item in kept.items() if item not in (None, '', [], {})}
    if isinstance(value, list):
        return [_without_empty(item) for item in value]
    return value


def _host_metadata(metadata, action_type):
    """Omit bookkeeping restated elsewhere in the same receipt or the action."""
    view = _host_view(metadata)
    # The read cursor repeats start/end/next_start_byte and the source line range.
    view.pop('chunk', None)
    # Stream byte offsets summarize the literal output, which is shown in full.
    view.pop('command_streams', None)
    if view.get('executable_resolution') == 'unchanged':
        # The shell wrapper argv restates `command`; only a resolved change is a fact.
        for key in ('executable_resolution', 'argv', 'resolved_argv'):
            view.pop(key, None)
    if isinstance(view.get('command_stdin'), dict) and view['command_stdin'].get('bytes') == 0:
        view.pop('command_stdin')
    if action_type in READ_ONLY_TOOLS and view.get('workspace_committed') is False:
        view.pop('workspace_committed')
    return _without_empty(view)


def model_tool_result(result):
    """Keep operational facts and literal contents, omitting host bookkeeping."""
    view = deepcopy(result)
    if 'artifacts' in view:
        view['artifacts'] = _without_empty(_host_view(view['artifacts']))
    if 'metadata' in view:
        view['metadata'] = _host_metadata(view['metadata'], view.get('action_type'))
    for key in ('artifacts', 'evidence', 'metadata', 'exit_code', 'error'):
        if key in view and (view[key] is None or view[key] == [] or view[key] == {}):
            del view[key]
    # search_files.output is a host-generated envelope, unlike file/command text.
    # Preserve each actual match and the opaque pagination cursor verbatim.
    if view.get('action_type') == 'search_files' and view.get('success'):
        try:
            payload = json.loads(view['output'])
        except (KeyError, TypeError, ValueError):
            pass
        else:
            if isinstance(payload, dict) and payload.get('schema_version') == 'rwkv-lh.search-files-result.v1':
                view['output'] = json.dumps(_host_view(payload), ensure_ascii=False, sort_keys=True)
    return view
