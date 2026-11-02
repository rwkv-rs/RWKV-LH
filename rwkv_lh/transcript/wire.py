"""The one model-visible text format: rendering, parsing and its invariant.

Storage stays the production native message schema (``parse.py``); this module
is the single structured -> text conversion used by serving, training tokens,
trace rebuild, evaluation and the decoding grammar.

No serialized value is nested inside another. Tool argument strings and receipt
output appear literally, without JSON string escaping. Non-string argument
values are compact JSON. Role framing follows g1k's native template
(``### System`` / ``### User`` / ``### Assistant`` / ``### Tool Output``); an
assistant turn is ``<think>`` reasoning, optional narration, then one or more
calls in the public Qwen3-Coder tag layout. The host appends the assistant
header; the model produces exactly the body and then ends its turn with the
vocabulary EOS token (``END_OF_TURN_TOKEN_ID``). The EOS is a token, not text: it
is supervised in training, it is the only way the decoding grammar lets a turn
end, and it stays in the persistent State, so the host's next header follows it
identically in training and serving.

Every accepted model turn satisfies ``render_body(parse_assistant(raw)) == raw``,
so the State always holds exactly the bytes training renders for that message.
"""
from .parse import catalog, loads, validate_assistant, validate_messages
from .render import assistant_message, compact, ordered_arguments

PROTOCOL = 'rwkv-lh.coder.transcript.v3'
END_OF_TURN_TOKEN_ID = 0  # frozen RWKV vocabulary EOS
HEADERS = {'system': '### System\n', 'user': '### User\n',
           'assistant': '### Assistant\n', 'tool': '### Tool Output\n'}
THINK_OPEN, THINK_CLOSE = '<think>\n', '\n</think>\n'
CALL_OPEN, CALL_CLOSE = '<tool_call>\n', '</function>\n</tool_call>\n'
FUNCTION_OPEN, FUNCTION_END = '<function=', '>\n'
PARAMETER_OPEN, PARAMETER_CLOSE = '<parameter=', '\n</parameter>\n'
OUTPUT_OPEN, OUTPUT_CLOSE = '\n<output>\n', '\n</output>'
# Literal text may not contain the delimiter that ends it.
FORBIDDEN = {'reasoning': THINK_CLOSE.rstrip('\n'), 'content': CALL_OPEN.rstrip('\n'),
             'argument': PARAMETER_CLOSE.rstrip('\n')}


def raw_string(schema):
    """String-typed parameters are literal; every other type is compact JSON."""
    return schema.get('type') == 'string'


def _literal(value, kind):
    if FORBIDDEN[kind] in value:
        raise ValueError(kind + ' text contains its delimiter ' + repr(FORBIDDEN[kind]))
    return value


def render_body(message, schemas):
    """The exact bytes the model generates for one assistant message."""
    validate_assistant(message, schemas=schemas)
    parts = [THINK_OPEN, _literal(message.get('reasoning_content') or '', 'reasoning'), THINK_CLOSE]
    if message.get('content'):
        parts += [_literal(message['content'], 'content'), '\n']
    for call in message['tool_calls']:
        name = call['function']['name']
        schema = schemas[name]
        arguments = ordered_arguments(loads(call['function']['arguments']), schema)
        parts += [CALL_OPEN, FUNCTION_OPEN, name, FUNCTION_END]
        for key, value in arguments.items():
            child = schema['properties'][key]
            parts += [PARAMETER_OPEN, key, '>\n',
                      _literal(value, 'argument') if raw_string(child) else compact(value), PARAMETER_CLOSE]
        parts.append(CALL_CLOSE)
    return ''.join(parts)


def render_receipt(content):
    """Receipt facts once: compact JSON header, then literal output text."""
    receipt = loads(content)
    output = receipt.pop('output', None)
    text = compact(receipt)
    if output is not None:
        if not isinstance(output, str):
            raise ValueError('receipt output must be text')
        text += OUTPUT_OPEN + output + OUTPUT_CLOSE
    return text


def render_message(message, schemas):
    role = message['role']
    if role == 'assistant':
        return HEADERS[role] + render_body(message, schemas)
    if role == 'tool':
        return HEADERS[role] + render_receipt(message['content']) + '\n'
    return HEADERS[role] + message['content'] + '\n'


def render_turns(messages, native_tools):
    """Per-message text; every turn ends with a newline and the next starts with '#'.

    The frozen vocabulary has no token spanning '\\n#' or '\\n<', so encoding
    turns separately or concatenated yields the same ids.
    """
    validate_messages(messages)
    schemas = catalog(native_tools)
    return [render_message(message, schemas) for message in messages]


def generation_prompt():
    """Host-appended framing after which the model writes one assistant body."""
    return HEADERS['assistant']


def _take(raw, position, prefix, error):
    if not raw.startswith(prefix, position):
        raise ValueError(error)
    return position + len(prefix)


def _until(raw, position, delimiter, error):
    end = raw.find(delimiter, position)
    if end < 0:
        raise ValueError(error)
    return raw[position:end], end + len(delimiter)


def parse_assistant(raw, native_tools, *, id_prefix):
    """Parse one generated body into a native message; never repair it.

    Call IDs are host bookkeeping, assigned by position, and are not part of
    the model-visible text. A body is accepted only if it re-renders to the
    identical bytes.
    """
    if not isinstance(raw, str) or not isinstance(id_prefix, str) or not id_prefix:
        raise ValueError('assistant text and call id prefix required')
    schemas = catalog(native_tools)
    position = _take(raw, 0, THINK_OPEN, 'assistant turn must start with ' + repr(THINK_OPEN))
    reasoning, position = _until(raw, position, THINK_CLOSE, 'unterminated think block')
    start = raw.find(CALL_OPEN, position)
    if start < 0:
        raise ValueError('assistant turn requires at least one tool call')
    content = raw[position:start]
    if content:
        if not content.endswith('\n'):
            raise ValueError('narration must end with a newline before the first call')
        content = content[:-1]
    position, calls = start, []
    while position < len(raw):
        position = _take(raw, position, CALL_OPEN + FUNCTION_OPEN, 'expected a tool call')
        name, position = _until(raw, position, FUNCTION_END, 'unterminated function name')
        if name not in schemas:
            raise ValueError('canonical tool is not registered: ' + name)
        properties, arguments = schemas[name]['properties'], {}
        while raw.startswith(PARAMETER_OPEN, position):
            key, position = _until(raw, position + len(PARAMETER_OPEN), '>\n', 'unterminated parameter name')
            if key in arguments or key not in properties:
                raise ValueError('duplicate or undeclared parameter: ' + key)
            value, position = _until(raw, position, PARAMETER_CLOSE, 'unterminated parameter value')
            arguments[key] = value if raw_string(properties[key]) else loads(value)
        position = _take(raw, position, CALL_CLOSE, 'expected the end of a tool call')
        calls.append({'id': id_prefix + '_' + str(len(calls)), 'type': 'function',
                      'function': {'name': name, 'arguments': compact(arguments)}})
    message = assistant_message(content=content or None, reasoning_content=reasoning or None, tool_calls=calls)
    if render_body(message, schemas) != raw:
        raise ValueError('assistant text is not in canonical form')
    return message
