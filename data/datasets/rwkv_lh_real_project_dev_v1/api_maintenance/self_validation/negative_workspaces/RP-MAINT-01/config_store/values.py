from __future__ import annotations
import json
import sqlite3

def decode(text):
    def invalid_constant(value):
        raise ValueError('non-finite JSON number')
    return json.loads(text, parse_constant=invalid_constant)

def value_type(value):
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'string'
    if isinstance(value, (int, float)):
        return 'number'
    if isinstance(value, str):
        return 'string'
    if isinstance(value, list):
        return 'array'
    if isinstance(value, dict):
        return 'object'
    raise ValueError('unsupported JSON value')

def read_values(database):
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as connection:
        connection.row_factory = sqlite3.Row
        version = connection.execute('PRAGMA user_version').fetchone()[0]
        if version not in (1, 2):
            raise ValueError('unsupported schema version')
        rows = connection.execute('SELECT * FROM settings ORDER BY key').fetchall()
        settings = []
        for row in rows:
            value = decode(row['value'])
            settings.append({'key': row['key'], 'value': value,
                             'value_type': row['value_type'] if version == 2 else value_type(value)})
        return {'schema_version': version, 'settings': settings}
