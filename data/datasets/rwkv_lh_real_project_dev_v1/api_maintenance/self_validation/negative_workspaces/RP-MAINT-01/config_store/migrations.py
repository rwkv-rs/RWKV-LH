from __future__ import annotations
import json
import os
import sqlite3
from .sqlite_io import copy_database, temporary_path, validate, write_backup_exclusive
from .values import decode, value_type

def migrate(database, backup):
    if database.resolve() == backup.resolve():
        raise ValueError('backup must differ from database')
    with sqlite3.connect(database.resolve().as_uri() + '?mode=ro', uri=True) as original:
        version = validate(original)
        count = original.execute('SELECT COUNT(*) FROM settings').fetchone()[0]
    if version == 2:
        return {'from_version': 2, 'to_version': 2, 'migrated_rows': 0, 'changed': False}
    if backup.exists():
        raise ValueError('backup already exists')
    staged = temporary_path(database.parent)
    try:
        copy_database(database, staged)
        with sqlite3.connect(staged) as connection:
            connection.execute('BEGIN IMMEDIATE')
            rows = connection.execute('SELECT key,value FROM settings ORDER BY key').fetchall()
            transformed = [(json.dumps(decode(text), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False), value_type(decode(text)), key) for key, text in rows]
            connection.execute("ALTER TABLE settings ADD COLUMN value_type TEXT NOT NULL DEFAULT 'unknown'")
            connection.execute('ALTER TABLE settings ADD COLUMN updated_at INTEGER NOT NULL DEFAULT 0')
            connection.executemany('UPDATE settings SET value=?,value_type=?,updated_at=0 WHERE key=?', transformed)
            connection.execute('CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, description TEXT NOT NULL)')
            connection.execute("INSERT INTO schema_migrations(version,description) VALUES (2,'typed configuration values')")
            connection.execute('PRAGMA user_version=2')
        write_backup_exclusive(database, backup)
        os.replace(staged, database)
        return {'from_version': 1, 'to_version': 2, 'migrated_rows': count, 'changed': True, 'backup': str(backup)}
    finally:
        staged.unlink(missing_ok=True)

def restore(database, backup):
    if database.resolve() == backup.resolve():
        raise ValueError('backup must differ from database')
    staged = temporary_path(database.parent)
    try:
        copy_database(backup, staged)
        with sqlite3.connect(staged) as connection:
            version = validate(connection)
        os.replace(staged, database)
        return {'restored': True, 'schema_version': version}
    finally:
        staged.unlink(missing_ok=True)
