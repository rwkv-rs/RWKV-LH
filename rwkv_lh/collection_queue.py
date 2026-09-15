"""Durable collection inventory; recorded execution is never task acceptance.

A crash leaves running rows untouched: callers must reconcile real trace and
native request identity before deciding whether another attempt is appropriate.
"""
import hashlib
import json
import re
import sqlite3
import time


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


class CollectionQueue:
    def __init__(self, path):
        self.db = sqlite3.connect(path, timeout=30, isolation_level=None)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('''CREATE TABLE IF NOT EXISTS tasks (
            source_id TEXT PRIMARY KEY, payload TEXT NOT NULL,
            payload_sha256 TEXT NOT NULL, status TEXT NOT NULL,
            result TEXT, updated REAL NOT NULL)''')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.db.close()

    def admit(self, item):
        for key in ('source_sha256', 'environment_sha256', 'acceptance_sha256'):
            if not re.fullmatch('[0-9a-f]{64}', str(item.get(key, ''))):
                raise ValueError(f'{key} requires a frozen SHA-256')
        if not isinstance(item.get('source_id'), str) or not item['source_id'].strip():
            raise ValueError('source identity required')
        if not isinstance(item.get('job'), dict) or not item['job'].get('task_id'):
            raise ValueError('job identity required')
        payload = _json(item)
        try:
            self.db.execute('INSERT INTO tasks VALUES (?, ?, ?, ?, NULL, ?)',
                            (item['source_id'], payload,
                             hashlib.sha256(payload.encode()).hexdigest(), 'pending', time.time()))
        except sqlite3.IntegrityError as exc:
            raise ValueError('duplicate source; frozen tasks cannot be replaced') from exc

    def claim(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            row = self.db.execute("SELECT source_id, payload FROM tasks WHERE status='pending' ORDER BY rowid LIMIT 1").fetchone()
            if row:
                self.db.execute("UPDATE tasks SET status='running', updated=? WHERE source_id=?", (time.time(), row[0]))
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise
        return json.loads(row[1]) if row else None

    def finish(self, source_id, result):
        changed = self.db.execute("UPDATE tasks SET status='recorded', result=?, updated=? WHERE source_id=? AND status='running'",
                                  (_json(result), time.time(), source_id))
        if changed.rowcount != 1:
            raise ValueError('only a running task can record a result')

    def counts(self):
        return dict(self.db.execute('SELECT status, COUNT(*) FROM tasks GROUP BY status'))
