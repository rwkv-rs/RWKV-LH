"""Generation grammar for the opt-in CC-view experiment only."""
import json
import math
import re
from re import _parser as regex_parser, _constants as rc

from .cc_view_experiment import PROTOCOL, THINK_LIMIT, SUMMARY_FORBIDDEN_PATTERN
from .runtime.structured_output import build_decoder_contract, validate_decoder_contract

EXTENSION = 'x-rwkv-lh-cc-view'


def compact(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def _character(pattern):
    """JSON-encode one decoded character; keep Unicode literal as in native JSON."""
    ordinary = '[[' + pattern + ']&&[^"\\\\\\x00-\\x1f]]'
    alternatives = [ordinary]
    for char in map(chr, [*range(32), 34, 92]):
        if re.fullmatch('[' + pattern + ']', char):
            alternatives.append(re.escape(compact(char)[1:-1]))
    return '(?:' + '|'.join(alternatives) + ')'


JSON_CHAR = _character(r'\s\S')


def _escaped_pattern(parsed):
    result = []
    categories = {rc.CATEGORY_SPACE: r'\s', rc.CATEGORY_NOT_SPACE: r'\S',
                  rc.CATEGORY_DIGIT: r'\d', rc.CATEGORY_NOT_DIGIT: r'\D',
                  rc.CATEGORY_WORD: r'\w', rc.CATEGORY_NOT_WORD: r'\W'}
    for op, value in parsed:
        if op is rc.LITERAL:
            result.append(re.escape(compact(chr(value))[1:-1]))
        elif op is rc.NOT_LITERAL:
            result.append(_character('^' + re.escape(chr(value))))
        elif op is rc.IN:
            chars = ''
            for child, data in value:
                if child is rc.NEGATE:
                    chars += '^'
                elif child is rc.LITERAL:
                    chars += re.escape(chr(data))
                elif child is rc.RANGE:
                    chars += re.escape(chr(data[0])) + '-' + re.escape(chr(data[1]))
                elif child is rc.CATEGORY and data in categories:
                    chars += categories[data]
                else:
                    raise ValueError('Unsupported character class in CC schema')
            result.append(_character(chars))
        elif op is rc.SUBPATTERN:
            if value[1] or value[2]:
                raise ValueError('Regex flags are not supported in CC schemas')
            result.append('(?:' + _escaped_pattern(value[3]) + ')')
        elif op is rc.BRANCH:
            result.append('(?:' + '|'.join(_escaped_pattern(branch) for branch in value[1]) + ')')
        elif op in (rc.MAX_REPEAT, rc.MIN_REPEAT):
            low, high, child = value
            bound = '{' + str(low) + ',' + (str(high) if high != rc.MAXREPEAT else '') + '}'
            result.append('(?:' + _escaped_pattern(child) + ')' + bound)
        elif op is rc.ANY:
            result.append(_character(r'^\n'))
        elif op is rc.AT:
            if value not in (rc.AT_BEGINNING, rc.AT_BEGINNING_STRING, rc.AT_END, rc.AT_END_STRING):
                raise ValueError('Unsupported regex anchor')
        else:
            raise ValueError('Unsupported regex operator in CC schema: ' + str(op))
    return ''.join(result)


def _string(schema):
    low, high = schema.get('minLength', 0), schema.get('maxLength')
    pattern = schema.get('pattern')
    if pattern:
        parsed = regex_parser.parse(pattern)
        if high is not None or parsed.getwidth()[0] < low:
            raise ValueError('Cannot enforce both length and this string pattern')
        body = _escaped_pattern(parsed)
        if not pattern.startswith('^'):
            body = JSON_CHAR + '*' + body
        if not pattern.endswith('$'):
            body += JSON_CHAR + '*'
    else:
        body = JSON_CHAR + '{' + str(low) + ',' + (str(high) if high is not None else '') + '}'
    return '"' + body + '"'


def _digits(low, high):
    """A compact regular language for inclusive fixed-width decimal bounds."""
    if low == high:
        return low
    if low == '0' * len(low) and high == '9' * len(high):
        return '[0-9]{' + str(len(low)) + '}'
    if low[0] == high[0]:
        return low[0] + _digits(low[1:], high[1:])
    options = []
    for digit in range(int(low[0]), int(high[0]) + 1):
        tail_low = low[1:] if digit == int(low[0]) else '0' * (len(low) - 1)
        tail_high = high[1:] if digit == int(high[0]) else '9' * (len(high) - 1)
        options.append(str(digit) + (_digits(tail_low, tail_high) if tail_low else ''))
    return '(?:' + '|'.join(options) + ')'


def integer_range(low, high=None):
    if low < 0 or high is not None and high < low:
        raise ValueError('CC catalog requires a nonnegative integer range')
    if high is None:
        options = [integer_range(low, 10 ** len(str(low)) - 1)] if low > 1 else (['0'] if low == 0 else [])
        width = len(str(low)) + 1 if low > 1 else 1
        options.append('[1-9][0-9]{' + str(width - 1) + ',}')
        return '(?:' + '|'.join(options) + ')'
    options = []
    for width in range(len(str(low)), len(str(high)) + 1):
        lower = max(low, 0 if width == 1 else 10 ** (width - 1))
        upper = min(high, 10 ** width - 1)
        if lower <= upper:
            options.append(_digits(str(lower), str(upper)))
    return '(?:' + '|'.join(options) + ')'


def parameter_regex(schema):
    """Regular language of compact argument JSON, before its outer JSON quoting.

    Property order follows the schema, as in the unchanged guidance JSON backend.
    Finite decimals are used for bounded numbers; exponents are not emitted.
    Unsupported schemas fail rather than silently dropping constraints.
    """
    allowed = {'type', 'properties', 'required', 'additionalProperties', 'minLength', 'maxLength',
               'pattern', 'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'enum', 'const', 'default',
               'items', 'minItems', 'maxItems'}
    if set(schema) - allowed:
        raise ValueError('Unsupported CC schema keywords: ' + str(set(schema) - allowed))
    if 'const' in schema or 'enum' in schema:
        return '(?:' + '|'.join(re.escape(compact(v)) for v in schema.get('enum', [schema.get('const')])) + ')'
    kind = schema['type']
    if kind == 'string':
        return _string(schema)
    if kind == 'boolean':
        return '(?:true|false)'
    if kind == 'array':
        item = parameter_regex(schema['items'])
        minimum, maximum = schema.get('minItems', 0), schema.get('maxItems')
        if maximum is not None and maximum < max(1, minimum):
            if maximum == 0:
                return r'\[\]'
            raise ValueError('Invalid array bounds')
        tail_min = max(0, minimum - 1)
        tail_max = '' if maximum is None else str(maximum - 1)
        body = item + '(?:,' + item + '){' + str(tail_min) + ',' + tail_max + '}'
        return r'\[' + ('(?:' + body + ')?' if minimum == 0 else body) + r'\]'
    if kind == 'integer':
        low = max(0, math.ceil(schema.get('minimum', 0)), math.floor(schema.get('exclusiveMinimum', -1)) + 1)
        high = schema.get('maximum')
        if 'exclusiveMaximum' in schema:
            high = min(high if high is not None else math.inf, math.ceil(schema['exclusiveMaximum']) - 1)
        return integer_range(low, math.floor(high) if high is not None else None)
    if kind == 'number':
        # All current number fields have integer upper bounds and a positive domain.
        high = schema.get('maximum')
        zero_allowed=schema.get('minimum')==0 and 'exclusiveMinimum' not in schema
        if not (schema.get('exclusiveMinimum')==0 or zero_allowed) or high is None or high != int(high) or high < 1:
            raise ValueError('Unsupported number bounds in CC schema')
        return ('(?:'+('0(?:\\.0+)?|' if zero_allowed else '')+'0\\.0*[1-9][0-9]*|'
                + (integer_range(1,int(high)-1)+'(?:\\.[0-9]+)?|' if high>1 else '')
                + str(int(high))+'(?:\\.0+)?)')
    if kind != 'object':
        raise ValueError('Unsupported CC schema type')
    props, required = list(schema.get('properties', {}).items()), set(schema.get('required', ()))
    if not props and isinstance(schema.get('additionalProperties'), dict):
        pair = _string({'type': 'string'}) + ':' + parameter_regex(schema['additionalProperties'])
        return r'\{(?:' + pair + '(?:,' + pair + ')*)?' + r'\}'
    if schema.get('additionalProperties') is not False:
        raise ValueError('Named CC objects must reject extra parameters')
    def tail(index, populated):
        if index == len(props):
            return ''
        key, child = props[index]
        pair = (',' if populated else '') + re.escape(compact(key)) + ':' + parameter_regex(child)
        if key in required:
            return pair + tail(index + 1, True)
        if populated:
            return '(?:' + pair + ')?' + tail(index + 1, True)
        return '(?:' + pair + tail(index + 1, True) + '|' + tail(index + 1, False) + ')'
    return r'\{' + tail(0, False) + r'\}'


def build_decoder(definitions):
    calls = []
    for definition in definitions:
        function = definition['function']
        argument = {'type': 'string', 'pattern': '^' + parameter_regex(function['parameters']) + '$'}
        calls.append({'type': 'object', 'properties': {'type': {'const': 'function'},
            'function': {'type': 'object', 'properties': {'name': {'const': function['name']}, 'arguments': argument},
                         'required': ['name', 'arguments'], 'additionalProperties': False}},
            'required': ['type', 'function'], 'additionalProperties': False})
    schema = {'type': 'array', 'items': {'anyOf': calls}, 'minItems': 1,
              'x-guidance': {'whitespace_flexible': False}}
    grammar = ('%llguidance {}\n// ' + PROTOCOL + '\n'
               'start: ("<think>" thought)? after\n'
               'thought[suffix="</think>"]: /(?s:.*)/\n'
               'after: before_tools tools | SUMMARY\n'
               'before_tools[suffix="<tool_calls>"]: /(?s:.*)/ & ~/(?:' + SUMMARY_FORBIDDEN_PATTERN + ')/\n'
               'SUMMARY: /(?s:.*\\S.*)/ & ~/(?:' + SUMMARY_FORBIDDEN_PATTERN + ')/\n'
               'tools: %json ' + compact(schema) + ' "</tool_calls>"\n')
    carrier = {'type': 'object', EXTENSION: {'protocol': PROTOCOL, 'grammar': grammar,
                'definitions': definitions, 'think_limit': THINK_LIMIT}, 'additionalProperties': False}
    return build_decoder_contract(carrier)


def extract_grammar(contract):
    validate_decoder_contract(contract)
    value = contract['original_schema'].get(EXTENSION)
    if not isinstance(value, dict) or value.get('protocol') != PROTOCOL:
        raise ValueError('CC-view grammar contract required')
    if build_decoder(value['definitions']) != contract:
        raise ValueError('CC-view decoder identity mismatch')
    return value['grammar']


def forced_think_suffix(token_bytes, *, limit=THINK_LIMIT):
    """The remaining literal closing tag when the free-think token cap is hit.

    Count sampled tokens overlapping the body, including tokens spanning framing.
    A partially emitted closing tag is completed rather than duplicated.
    """
    prefix, closing = b'<think>', b'</think>'
    raw = b''.join(token_bytes)
    if not raw.startswith(prefix) or closing in raw[len(prefix):]:
        return None
    partial = max((n for n in range(len(closing)) if raw.endswith(closing[:n])), default=0)
    body_end = len(raw) - partial
    offset, count = 0, 0
    for token in token_bytes:
        end = offset + len(token)
        if end > len(prefix) and offset < body_end:
            count += 1
        offset = end
    return closing[partial:] if count >= limit else None


def token_continues_suffix(token, suffix):
    return bool(token) and (suffix.startswith(token) or token.startswith(suffix))


def think_limited_prefix(history, candidates, *, limit=THINK_LIMIT):
    """Validate speculative batches against the same cap as one-token sampling."""
    current=list(history)
    for index,token in enumerate(candidates):
        suffix=forced_think_suffix(current,limit=limit)
        if suffix is not None and not token_continues_suffix(token,suffix):
            return index
        current.append(token)
    return len(candidates)
