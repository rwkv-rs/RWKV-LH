"""Native chat structure and strict live calls; archival output is never repaired."""
import json
from copy import deepcopy

from ..schema_validation import validate_schema
from .tools import canonical_definitions, native_name


def loads(raw):
    """Reject duplicate keys and non-JSON numbers, including inside arguments."""
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key: ' + key)
            result[key] = value
        return result

    def constant(value):
        raise ValueError('non-finite JSON number: ' + value)

    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    # JSON's exponent syntax can overflow Python floats without parse_constant.
    json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
    return value


def _fields(value, required, optional=()):
    if not isinstance(value, dict) or set(required) - value.keys() or value.keys() - set(required) - set(optional):
        raise ValueError('invalid transcript fields; required: ' + ', '.join(required))


def _text(value, *, nonempty=False):
    if not isinstance(value, str) or nonempty and not value:
        raise ValueError('transcript text required')
    value.encode('utf-8')


def validate_message(message):
    """Validate the wire envelope, without accepting a recorded action for execution."""
    if not isinstance(message, dict):
        raise ValueError('message object required')
    role = message.get('role')
    if role in ('system', 'user'):
        _fields(message, ('role', 'content'))
        _text(message['content'])
    elif role == 'assistant':
        _fields(message, ('role', 'content'), ('reasoning_content', 'tool_calls'))
        for field in ('content', 'reasoning_content'):
            if message.get(field) is not None:
                _text(message[field])
        calls = message.get('tool_calls', [])
        if not isinstance(calls, list):
            raise ValueError('tool_calls array required')
        for call in calls:
            _fields(call, ('id', 'type', 'function'))
            _text(call['id'], nonempty=True)
            if call['type'] != 'function':
                raise ValueError('only native function tool calls are supported')
            _fields(call['function'], ('name', 'arguments'))
            _text(call['function']['name'], nonempty=True)
            _text(call['function']['arguments'])
    elif role == 'tool':
        _fields(message, ('role', 'tool_call_id', 'content'))
        _text(message['tool_call_id'], nonempty=True)
        _text(message['content'])
        if not isinstance(loads(message['content']), dict):
            raise ValueError('tool content must contain a structured JSON receipt')
    else:
        raise ValueError('unknown transcript role')
    return message


def validate_messages(messages, *, allow_pending=True):
    """Match every tool receipt to one issued call; retain interrupted tails explicitly.

    A source transcript can contain an invalid model argument string or a
    terminal assistant call whose outcome is unknown. Parsing that evidence
    does not authorize executing or replaying it. Live calls use parse_assistant.
    """
    if not isinstance(messages, list):
        raise ValueError('messages array required')
    pending, seen = {}, set()
    for index, message in enumerate(messages):
        validate_message(message)
        role = message['role']
        if role == 'tool':
            identifier = message['tool_call_id']
            if identifier not in pending:
                raise ValueError('orphan or duplicate tool receipt: ' + identifier)
            del pending[identifier]
            continue
        if pending:
            raise ValueError('missing tool receipts before the next turn')
        if role == 'system' and index != 0:
            raise ValueError('system message must be first')
        for call in message.get('tool_calls', []):
            identifier = call['id']
            if identifier in seen:
                raise ValueError('duplicate tool call id: ' + identifier)
            seen.add(identifier)
            pending[identifier] = call
    if pending and not allow_pending:
        raise ValueError('unresolved tool calls at transcript boundary')
    return deepcopy(pending)


def parse_transcript(raw):
    """Read the production native_messages.json envelope without changing vocabulary.

    This is an evidence reader, not an old-protocol execution compatibility
    path. Argument strings and tool content are retained byte for byte.
    """
    value = loads(raw)
    _fields(value, ('messages', 'tools'))
    if not isinstance(value['tools'], list):
        raise ValueError('tools array required')
    validate_messages(value['messages'])
    return value


def catalog(native_tools):
    """Use only the frozen vocabulary adapter for the current live catalog."""
    result = {}
    for definition in canonical_definitions(native_tools):
        function = definition['function']
        name = function['name']
        if name in result:
            raise ValueError('duplicate tool definition: ' + name)
        if function['parameters'].get('additionalProperties') is not False:
            raise ValueError('tool parameter objects must reject additional properties')
        result[name] = function['parameters']
    if not result:
        raise ValueError('nonempty tool catalog required')
    return result


def validate_call(call, schemas):
    name = call['function']['name']
    native_name(name)  # Native spellings never enter the live execution path.
    if name not in schemas:
        raise ValueError('canonical tool is not registered: ' + name)
    arguments = loads(call['function']['arguments'])
    validate_schema(arguments, schemas[name])
    return arguments


def parse_assistant(raw, native_tools):
    """Validate every call before any call in a multi-call turn can execute."""
    message = loads(raw)
    validate_message(message)
    if message['role'] != 'assistant':
        raise ValueError('assistant message required')
    schemas = catalog(native_tools)
    seen = set()
    calls = message.get('tool_calls', [])
    if not calls and not (message.get('content') or message.get('reasoning_content')):
        raise ValueError('empty assistant message')
    for index, call in enumerate(calls):
        if call['id'] in seen:
            raise ValueError('duplicate tool call id')
        seen.add(call['id'])
        validate_call(call, schemas)
        if call['function']['name'] == 'finish_work' and index != len(calls) - 1:
            raise ValueError('finish_work must be the last call')
    return message
