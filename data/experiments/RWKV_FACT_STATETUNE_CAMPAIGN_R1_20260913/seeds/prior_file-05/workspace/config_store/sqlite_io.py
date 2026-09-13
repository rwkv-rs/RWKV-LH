from __future__ import annotations
import os
import sqlite3
import tempfile
from pathlib import Path

def validate(connection):
    if connection.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        raise ValueError('invalid SQLite database')
    version = connection.execute('PRAGMA user_version').fetchone()[0]
    if version not in (1, 2):
        raise ValueError('unsupported schema version')
    connection.execute('SELECT key,value FROM settings LIMIT 0')
    if version == 2:
        connection.execute('SELECT value_type,updated_at FROM settings LIMIT 0')
    return version

def temporary_path(parent):
    descriptor, name = tempfile.mkstemp(prefix='.config-stage-', suffix='.sqlite3', dir=parent)
    os.close(descriptor)
    return Path(name)

def copy_database(source, destination):
    with sqlite3.connect(source.resolve().as_uri() + '?mode=ro', uri=True) as original:
        validate(original)
        with sqlite3.connect(destination) as copied:
            original.backup(copied)
    with destination.open('rb') as stream:
        os.fsync(stream.fileno())

def write_backup_exclusive(source, backup):
    staged = temporary_path(backup.parent)
    try:
        copy_database(source, staged)
        os.link(staged, backup)
    finally:
        staged.unlink(missing_ok=True)
