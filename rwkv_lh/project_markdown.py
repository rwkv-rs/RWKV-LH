"""Lossless Markdown presentation of model input; JSON is reserved for output."""
import re


def literal(value):
    """Fence literal material without escaping, stripping or interpreting it."""
    runs = [len(match.group()) for match in re.finditer(r'`+', value)]
    fence = '`' * max(3, 1 + max(runs, default=0))
    return fence + '\n' + value + ('\n' if not value.endswith('\n') else '') + fence


def section(title, value, *, level=2):
    heading = '#' * min(level, 6) + ' ' + str(title)
    if isinstance(value, dict):
        body = '\n\n'.join(section(key, child, level=level + 1) for key, child in value.items()) or 'None.'
    elif isinstance(value, list):
        body = '\n\n'.join(section(str(index), child, level=level + 1) for index, child in enumerate(value, 1)) or 'None.'
    elif value is None:
        body = 'None.'
    elif isinstance(value, bool):
        body = 'true' if value else 'false'
    elif isinstance(value, str):
        body = literal(value) if '\n' in value else value
    else:
        body = str(value)
    return heading + '\n' + body


# Every schema key this view understands. Grammar keys (type, bounds, pattern,
# additionalProperties, uniqueItems) are enforced by the constrained decoder
# from the same schema; showing them spends State on rules the model cannot
# violate and cannot decide with. The view keeps names, choices, defaults,
# descriptions and whether a field must be supplied. An unlisted key fails
# closed instead of silently vanishing from the model's view.
_KNOWN_KEYS = frozenset({'type', 'minLength', 'maxLength', 'pattern', 'minimum', 'maximum',
    'exclusiveMinimum', 'exclusiveMaximum', 'additionalProperties', 'uniqueItems',
    'minItems', 'maxItems', 'required', 'properties', 'items', 'anyOf', 'default',
    'const', 'enum', 'description'})


def _value(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if value == '':
        return '""'
    if isinstance(value, (dict, list)) and not value:
        return '{}' if isinstance(value, dict) else '[]'
    return str(value)


def _field(name, schema, required, depth):
    pad = '  ' * depth
    if 'const' in schema and not required:
        return []  # A fixed optional value is no decision; the decoder supplies it.
    notes = []
    if 'const' in schema:
        notes.append('= ' + _value(schema['const']))
    elif required:
        notes.append('required')
    elif 'default' in schema:
        notes.append('default ' + _value(schema['default']))
    if 'enum' in schema:
        notes.append('one of ' + ' | '.join(_value(choice) for choice in schema['enum']))
    if schema.get('type') == 'array':
        notes.append('list')
    line = pad + '- ' + name + (' (' + ', '.join(notes) + ')' if notes else '')
    if schema.get('description'):
        line += ': ' + schema['description']
    lines = [line]
    if 'properties' in schema:
        lines.extend(_fields(schema, depth + 1) or [pad + '  (no fields)'])
    return lines


def _fields(schema, depth):
    required = set(schema.get('required', ()))
    return [line for name, child in schema.get('properties', {}).items()
            for line in _field(name, child, name in required, depth)]


def _check_keys(schema):
    unknown = set(schema) - _KNOWN_KEYS
    if unknown:
        raise ValueError('unrenderable schema keys: ' + ', '.join(sorted(unknown)))
    for child in [*schema.get('properties', {}).values(), *schema.get('anyOf', ()),
                  *([schema['items']] if isinstance(schema.get('items'), dict) else [])]:
        _check_keys(child)


def render_contract(schema):
    """Decision-bearing view of one parameter schema; never the full grammar.

    A union of object forms renders the fields every form shares once, then
    each form only by what distinguishes it, so siblings never repeat.
    """
    _check_keys(schema)
    variants = schema.get('anyOf')
    if not variants:
        return '\n'.join(_fields(schema, 0)) or '(no fields)'
    shared = [name for name in variants[0].get('properties', {})
              if all(v.get('properties', {}).get(name) == variants[0]['properties'][name]
                     and (name in v.get('required', ())) == (name in variants[0].get('required', ()))
                     for v in variants)]
    lines = [line for name in shared for line in _field(
        name, variants[0]['properties'][name], name in variants[0].get('required', ()), 0)]
    for variant in variants:
        distinct = {name: child for name, child in variant.get('properties', {}).items() if name not in shared}
        tag = next((name for name, child in distinct.items() if 'const' in child), None)
        heading = ('Form ' + tag + ' = ' + _value(distinct[tag]['const'])) if tag else 'Form'
        description = distinct.get(tag, {}).get('description') if tag else None
        lines.append('\n' + heading + (': ' + description if description else ''))
        rest = {name: child for name, child in distinct.items() if name != tag}
        lines.extend(_fields({'properties': rest, 'required': variant.get('required', ())}, 0)
                     or ['(no other fields)'])
    return '\n'.join(lines)


def render_tools(definitions):
    return '\n\n'.join('## ' + item['name'] + '\n' + item['description'] + '\n'
                       + render_contract(item['parameters']) for item in definitions)
