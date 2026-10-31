"""Decoding grammar derived from the wire format and the frozen tool schemas.

Literal text is one lexeme together with the delimiter that ends it: the
guidance lexer is greedy and does not backtrack, so free text followed by a
separate closing lexeme would never be able to stop. String parameters keep
their schema constraints on the literal value; every other parameter type is
compact JSON through guidance's own JSON compiler. Keys follow schema order,
which is also the order ``wire.render_body`` emits.
"""
import hashlib
import re
from re import _parser as regex_parser, _constants as rc

from .parse import catalog
from .render import compact
from .tools import TOOL_PROTOCOL
from .wire import (CALL_CLOSE, CALL_OPEN, FORBIDDEN, FUNCTION_END, FUNCTION_OPEN, PARAMETER_CLOSE,
                   PARAMETER_OPEN, PROTOCOL, THINK_CLOSE, THINK_OPEN, raw_string)

ANY = '(.|\\n)'
JSON_LAYOUT = {'whitespace_flexible': False, 'item_separator': ',', 'key_separator': ':'}
UNSUPPORTED_REGEX = {rc.ASSERT, rc.ASSERT_NOT, rc.GROUPREF, rc.GROUPREF_EXISTS, rc.ATOMIC_GROUP,
                     rc.POSSESSIVE_REPEAT}


def _literal(text):
    return compact(text)


def _regex(value):
    return '/' + value.replace('/', '\\/') + '/'


def _escape(text):
    """Regex-escape literal text; a newline stays the two characters \\n."""
    return re.escape(text).replace('\\\n', '\\n')


def _without(delimiter):
    """Any text that does not contain `delimiter` anywhere."""
    return '(' + _regex(ANY + '*') + ' & ~' + _regex(ANY + '*' + _escape(delimiter) + ANY + '*') + ')'


def _check_regex(parsed):
    for op, value in parsed:
        if op in UNSUPPORTED_REGEX:
            raise ValueError('unsupported string pattern operator: ' + str(op))
        if op is rc.SUBPATTERN:
            if value[1] or value[2]:
                raise ValueError('unsupported string pattern flags')
            _check_regex(value[3])
        elif op is rc.BRANCH:
            for branch in value[1]:
                _check_regex(branch)
        elif op in (rc.MAX_REPEAT, rc.MIN_REPEAT):
            _check_regex(value[2])


def _pattern(pattern):
    """JSON Schema patterns search, so unanchored ends admit any text."""
    parsed = list(regex_parser.parse(pattern))
    _check_regex(parsed)
    body = pattern
    start = bool(parsed and parsed[0][0] is rc.AT and parsed[0][1] in (rc.AT_BEGINNING, rc.AT_BEGINNING_STRING))
    end = bool(parsed and parsed[-1][0] is rc.AT and parsed[-1][1] in (rc.AT_END, rc.AT_END_STRING))
    if start:
        body = body[1:]
    if end:
        body = body[:-1]
    return _regex(('' if start else ANY + '*') + body + ('' if end else ANY + '*'))


def _string_value(schema):
    allowed = {'type', 'description', 'default', 'minLength', 'maxLength', 'pattern', 'enum', 'const'}
    if set(schema) - allowed:
        raise ValueError('unsupported string constraints: ' + repr(sorted(set(schema) - allowed)))
    if 'enum' in schema or 'const' in schema:
        values = schema['enum'] if 'enum' in schema else [schema['const']]
        if any(not isinstance(v, str) or FORBIDDEN['argument'] in v for v in values):
            raise ValueError('string enum values must be literal text')
        return '(' + ' | '.join(_literal(v) for v in values) + ')'
    parts = [_without(FORBIDDEN['argument'])]
    low, high = schema.get('minLength', 0), schema.get('maxLength')
    if low or high is not None:
        parts.append(_regex(ANY + '{' + str(low) + ',' + ('' if high is None else str(high)) + '}'))
    if 'pattern' in schema:
        parts.append(_pattern(schema['pattern']))
    return '(' + ' & '.join(parts) + ')'


def _json_value(schema):
    kept = {key: value for key, value in schema.items() if key not in ('description', 'default')}
    return '%json ' + compact({**kept, 'x-guidance': JSON_LAYOUT})


def build_grammar(native_tools):
    """Return built-in guidance Lark, without a custom processor or backend.

    A turn is think, optional narration, then one or more calls; finish_work
    may only be last. No name, parameter, default or call-count ceiling is
    introduced here. The host parser still enforces canonical re-rendering.
    """
    schemas = catalog(native_tools)
    rules, terminals = [], []
    normal, finish = [], None
    for index, (name, parameters) in enumerate(schemas.items()):
        pieces = []
        required = set(parameters.get('required', ()))
        for position, (key, schema) in enumerate(parameters['properties'].items()):
            opening = _literal(PARAMETER_OPEN + key + '>\n')
            if raw_string(schema):
                terminal = 'V' + str(index) + '_' + str(position)
                terminals.append(terminal + ': ' + _string_value(schema) + ' ' + _literal(PARAMETER_CLOSE))
                value = terminal
            else:
                value = _json_value(schema) + ' ' + _literal(PARAMETER_CLOSE)
            rule = 'p' + str(index) + '_' + str(position)
            rules.append(rule + ': ' + opening + ' ' + value)
            pieces.append(rule if key in required else rule + '?')
        body = 'b' + str(index)
        rules.append(body + ': ' + ' '.join([_literal(FUNCTION_OPEN + name + FUNCTION_END), *pieces,
                                             _literal(CALL_CLOSE)]))
        if name == 'finish_work':
            finish = body
        else:
            normal.append(body)
    choices = []
    if normal:
        rules.append('normal: ' + ' | '.join(normal))
        tail = ' (' + _literal(CALL_OPEN) + ' normal)*'
        if finish:
            tail += ' (' + _literal(CALL_OPEN) + ' ' + finish + ')?'
        choices.append('normal' + tail)
    if finish:
        choices.append(finish)
    narration = _without(FORBIDDEN['content'])
    terminals += [
        'THINK: ' + _literal(THINK_OPEN) + ' ' + _without(FORBIDDEN['reasoning']) + ' ' + _literal(THINK_CLOSE),
        # Narration, when present, is one lexeme with the first call's opening tag.
        'OPEN: ((' + narration + ' & ' + _regex(ANY + '+') + ') "\\n")? ' + _literal(CALL_OPEN)]
    identity = hashlib.sha256(compact(schemas).encode('utf-8')).hexdigest()
    return ('%llguidance {}\n// ' + PROTOCOL + ' / ' + TOOL_PROTOCOL + ' / ' + identity + '\n'
            + 'start: THINK OPEN (' + ' | '.join(choices) + ')\n'
            + '\n'.join(rules + terminals) + '\n')
