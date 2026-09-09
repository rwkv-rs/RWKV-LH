from __future__ import annotations
import json
import sqlite3
from .values import decode, value_type

def migrate(database, backup):
    backup.write_bytes(database.read_bytes())
    with sqlite3.connect(database) as connection:
        version = connection.execute('PRAGMA user_version').fetchone()[0]
        if version == 2:
            return {'from_version': 2, 'to_version': 2, 'migrated_rows': 0, 'changed': False}
        connection.execute("ALTER TABLE settings ADD COLUMN value_type TEXT NOT NULL DEFAULT 'string'")
        connection.execute('ALTER TABLE settings ADD COLUMN updated_at INTEGER NOT NULL DEFAULT 0')
        connection.execute('PRAGMA user_version=2')
        connection.commit()
        rows = connection.execute('SELECT key,value FROM settings ORDER BY key').fetchall()
        for key, text in rows:
            value = decode(text)
            connection.execute('UPDATE settings SET value=?,value_type=? WHERE key=?', (json.dumps(value), value_type(value), key))
            connection.commit()
        return {'from_version': version, 'to_version': 2, 'migrated_rows': len(rows), 'changed': True}

def restore(database, backup):
    database.write_bytes(backup.read_bytes())
    with sqlite3.connect(database) as connection:
        version = connection.execute('PRAGMA user_version').fetchone()[0]
    return {'restored': True, 'schema_version': version}
