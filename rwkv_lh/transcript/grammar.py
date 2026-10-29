"""Native guidance grammar from the frozen tool schemas and transcript layout.

function.arguments is a JSON *string*, so constraining it as an arbitrary
string or using contentSchema would silently lose its inner schema. Generate
quoted object productions instead. Numeric domains use guidance's JSON
compiler; unsupported schema/regex constraints fail closed.
"""
from dataclasses import dataclass
import hashlib
import re
from re import _parser as regex_parser, _constants as rc

from .parse import catalog
from .render import CALL_KEYS, FUNCTION_KEYS, MESSAGE_KEYS, PROTOCOL, compact
from .tools import TOOL_PROTOCOL


def _literal(value, quoted=False):
    return compact(compact(value)[1:-1] if quoted else value)


def _character(pattern):
    """One decoded character, serialized inside a doubly quoted JSON value."""
    ordinary = '[[' + pattern + ']&&[^"\\\\\\x00-\\x1f]]'
    alternatives = [ordinary]
    for char in map(chr, [*range(32), 34, 92]):
        if re.fullmatch('[' + pattern + ']', char):
            alternatives.append(re.escape(compact(compact(char)[1:-1])[1:-1]))
    return '(?:' + '|'.join(alternatives) + ')'


def _quoted_pattern(parsed):
    categories = {rc.CATEGORY_SPACE: r'\s', rc.CATEGORY_NOT_SPACE: r'\S',
                  rc.CATEGORY_DIGIT: r'\d', rc.CATEGORY_NOT_DIGIT: r'\D',
                  rc.CATEGORY_WORD: r'\w', rc.CATEGORY_NOT_WORD: r'\W'}
    parts = []
    for op, value in parsed:
        if op is rc.LITERAL:
            parts.append(re.escape(compact(compact(chr(value))[1:-1])[1:-1]))
        elif op is rc.NOT_LITERAL:
            parts.append(_character('^' + re.escape(chr(value))))
        elif op is rc.ANY:
            parts.append(_character(r'^\n'))
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
                    raise ValueError('unsupported quoted string character class')
            parts.append(_character(chars))
        elif op is rc.SUBPATTERN:
            if value[1] or value[2]:
                raise ValueError('unsupported quoted string regex flags')
            parts.append('(?:' + _quoted_pattern(value[3]) + ')')
        elif op is rc.BRANCH:
            parts.append('(?:' + '|'.join(_quoted_pattern(branch) for branch in value[1]) + ')')
        elif op in (rc.MAX_REPEAT, rc.MIN_REPEAT):
            low, high, child = value
            parts.append('(?:' + _quoted_pattern(child) + '){' + str(low) + ','
                         + (str(high) if high != rc.MAXREPEAT else '') + '}')
        else:
            # Anchors are removed only at the outer boundary by _string.
            raise ValueError('unsupported quoted string regex operator: ' + str(op))
    return ''.join(parts)


def _regex(value):
    return '/' + value.replace('/', r'\/') + '/'


def _string(schema):
    atom = _character(r'\s\S')
    quote = re.escape(r'\"')
    low, high = schema.get('minLength', 0), schema.get('maxLength')
    length = atom + '{' + str(low) + ',' + (str(high) if high is not None else '') + '}'
    result = _regex(quote + length + quote)
    if 'pattern' in schema:
        parsed = list(regex_parser.parse(schema['pattern']))
        anchored_start = bool(parsed and parsed[0][0] is rc.AT and parsed[0][1] in (rc.AT_BEGINNING, rc.AT_BEGINNING_STRING))
        if anchored_start:
            parsed.pop(0)
        anchored_end = bool(parsed and parsed[-1][0] is rc.AT and parsed[-1][1] in (rc.AT_END, rc.AT_END_STRING))
        if anchored_end:
            parsed.pop()
        body = ('' if anchored_start else atom + '*') + _quoted_pattern(parsed) + ('' if anchored_end else atom + '*')
        result += ' & ' + _regex(quote + body + quote)
    return result


@dataclass(frozen=True)
class _Reference:
    name: str


@dataclass(frozen=True)
class _Arguments:
    schema: dict


class _Compiler:
    def __init__(self):
        self.rules = []
        self.any_values = {}

    def rule(self, expression, *, terminal=False):
        name = ('T' if terminal else 'r') + str(len(self.rules))
        self.rules.append(name + ': ' + expression)
        return name

    def object(self, properties, required, *, quoted):
        unknown = set(required) - properties.keys()
        if unknown:
            raise ValueError('required names are absent from schema properties')
        pairs = [(key, self.emit(value, quoted=quoted)) for key, value in properties.items()]
        # Two tails per position keep optional fields linear in catalog size.
        tails = {False: self.rule('""'), True: self.rule('""')}
        for key, child in reversed(pairs):
            next_tails = {}
            for populated in (False, True):
                pair = (_literal(',', quoted) + ' ' if populated else '') + _literal(compact(key) + ':', quoted) + ' ' + child
                body = pair + ' ' + tails[True]
                if key not in required:
                    body += ' | ' + tails[populated]
                next_tails[populated] = self.rule(body)
            tails = next_tails
        return self.rule(_literal('{', quoted) + ' ' + tails[False] + ' ' + _literal('}', quoted))

    def any_value(self, quoted):
        if quoted in self.any_values:
            return self.any_values[quoted]
        # Reserve a name before recursing through arbitrary JSON arrays/maps.
        ref = self.rule('""')
        index = len(self.rules) - 1
        self.any_values[quoted] = ref
        scalar = self.emit({'anyOf': [{'type': 'string'}, {'type': 'number'},
                                      {'type': 'boolean'}, {'type': 'null'}]}, quoted=quoted)
        array = self.emit({'type': 'array', 'items': _Reference(ref)}, quoted=quoted)
        mapping = self.mapping(_Reference(ref), quoted=quoted)
        self.rules[index] = ref + ': ' + ' | '.join((scalar, array, mapping))
        return ref

    def mapping(self, child, *, quoted):
        key = self.emit({'type': 'string'}, quoted=quoted)
        pair = key + ' ' + _literal(':', quoted) + ' ' + self.emit(child, quoted=quoted)
        return self.rule(_literal('{', quoted) + ' (' + pair + ' (' + _literal(',', quoted)
                         + ' ' + pair + ')*)? ' + _literal('}', quoted))

    def emit(self, schema, *, quoted=False):
        if isinstance(schema, _Reference):
            return schema.name
        if isinstance(schema, _Arguments):
            return self.rule(_literal('"') + ' ' + self.emit(schema.schema, quoted=True) + ' ' + _literal('"'))
        allowed = {'type', 'properties', 'required', 'additionalProperties', 'description', 'default',
                   'enum', 'const', 'anyOf', 'minLength', 'maxLength', 'pattern', 'minimum', 'maximum',
                   'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf', 'items', 'minItems', 'maxItems'}
        if not isinstance(schema, dict) or set(schema) - allowed:
            raise ValueError('unsupported transcript grammar schema: ' + repr(schema))
        if not schema or not (set(schema) - {'description', 'default'}):
            return self.any_value(quoted)
        if 'anyOf' in schema:
            if set(schema) - {'anyOf', 'description', 'default'}:
                raise ValueError('unsupported siblings of anyOf')
            return self.rule(' | '.join(self.emit(part, quoted=quoted) for part in schema['anyOf']))
        if 'const' in schema or 'enum' in schema:
            values = schema['enum'] if 'enum' in schema else [schema['const']]
            return self.rule(' | '.join(_literal(compact(value), quoted) for value in values))
        kind = schema.get('type')
        common = {'type', 'description', 'default'}
        supported = {'object': {'properties', 'required', 'additionalProperties'},
                     'array': {'items', 'minItems', 'maxItems'},
                     'string': {'minLength', 'maxLength', 'pattern'},
                     'number': {'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf'},
                     'integer': {'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf'},
                     'boolean': set(), 'null': set()}
        if kind not in supported or set(schema) - common - supported[kind]:
            raise ValueError('unsupported constraints for transcript grammar type: ' + str(kind))
        if kind == 'object':
            properties = schema.get('properties', {})
            extra = schema.get('additionalProperties', True)
            if properties and extra is not False:
                raise ValueError('named objects must reject additionalProperties')
            if extra is False:
                return self.object(properties, schema.get('required', ()), quoted=quoted)
            if schema.get('required'):
                raise ValueError('unsupported required properties in open map')
            if extra is not True and not isinstance(extra, dict):
                raise ValueError('unsupported additionalProperties')
            return self.mapping({} if extra is True else extra, quoted=quoted)
        if kind == 'array':
            child = self.emit(schema.get('items', {}), quoted=quoted)
            low, high = schema.get('minItems', 0), schema.get('maxItems')
            if type(low) is not int or low < 0 or high is not None and (type(high) is not int or high < low):
                raise ValueError('invalid array bounds')
            if high == 0:
                return self.rule(_literal('[]', quoted))
            body = child + ' (' + _literal(',', quoted) + ' ' + child + '){' + str(max(0, low - 1)) + ',' + (str(high - 1) if high is not None else '') + '}'
            if low == 0:
                body = '(' + body + ')?'
            return self.rule(_literal('[', quoted) + ' ' + body + ' ' + _literal(']', quoted))
        if kind == 'string' and quoted:
            return self.rule(_string(schema), terminal=True)
        # Numbers, booleans and null need no extra escaping inside argument JSON.
        return self.rule('%json ' + compact({**schema, 'x-guidance': {'whitespace_flexible': False}}))


def build_grammar(native_tools):
    """Return built-in guidance Lark, without a custom processor or backend.

    The host parser still checks cross-call ID uniqueness and duplicate map
    keys; these relations are not represented by the context-free grammar.
    No name, parameter, default or call-count ceiling is introduced here.
    """
    schemas = catalog(native_tools)
    compiler = _Compiler()
    normal, finish = [], []
    for name, parameters in schemas.items():
        function = {'type': 'object', 'properties': dict(zip(FUNCTION_KEYS,
            ({'const': name}, _Arguments(parameters)))), 'required': list(FUNCTION_KEYS), 'additionalProperties': False}
        call = {'type': 'object', 'properties': dict(zip(CALL_KEYS,
            ({'type': 'string', 'minLength': 1}, {'const': 'function'}, function))),
            'required': list(CALL_KEYS), 'additionalProperties': False}
        (finish if name == 'finish_work' else normal).append(compiler.emit(call))
    choices = []
    if normal:
        normal_call = compiler.rule(' | '.join(normal))
        repeated = normal_call + ' ("," ' + normal_call + ')*'
        if finish:
            repeated += ' ("," ' + finish[0] + ')?'
        choices.append(repeated)
    choices.extend(finish)
    calls = compiler.rule('"[" (' + ' | '.join(choices) + ')? "]"')
    nullable = {'anyOf': [{'type': 'string'}, {'type': 'null'}]}
    properties = dict(zip(MESSAGE_KEYS['assistant'], ({'const': 'assistant'}, nullable, nullable, _Reference(calls))))
    root = compiler.object(properties, list(properties), quoted=False)
    identity = hashlib.sha256(compact(schemas).encode('utf-8')).hexdigest()
    return ('%llguidance {}\n// ' + PROTOCOL + ' / ' + TOOL_PROTOCOL + ' / ' + identity + '\n'
            + 'start: ' + root + ' "\\n"\n' + '\n'.join(compiler.rules) + '\n')
