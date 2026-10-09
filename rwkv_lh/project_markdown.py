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


def render_tools(definitions):
    return '\n\n'.join(section(item['name'], {'description': item['description'],
        'parameter contract': item['parameters']}) for item in definitions)
