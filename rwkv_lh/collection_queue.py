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

        self.db.execute("CREATE UNIQUE INDEX IF NOT EXISTS source_bytes_unique ON tasks(json_extract(payload, '$.source_sha256'))")
        self.db.execute('CREATE INDEX IF NOT EXISTS tasks_status_idx ON tasks(status)')
        self.db.execute('CREATE TABLE IF NOT EXISTS freeze (name TEXT PRIMARY KEY, value TEXT NOT NULL)')

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
        if self.db.execute('SELECT 1 FROM freeze LIMIT 1').fetchone():
            raise ValueError('inventory is frozen')
        payload = _json(item)
        try:
            self.db.execute('INSERT INTO tasks VALUES (?, ?, ?, ?, NULL, ?)',
                            (item['source_id'], payload,
                             hashlib.sha256(payload.encode()).hexdigest(), 'pending', time.time()))
        except sqlite3.IntegrityError as exc:
            raise ValueError('duplicate source; frozen tasks cannot be replaced') from exc

    def items(self, status=None):
        query = "SELECT source_id, payload, payload_sha256 FROM tasks"
        args = ()
        if status is not None:
            query += " WHERE status=?"
            args = (status,)
        for source_id, payload, digest in self.db.execute(query + " ORDER BY rowid", args):
            if hashlib.sha256(payload.encode()).hexdigest() != digest:
                raise ValueError("task payload digest mismatch")
            item = json.loads(payload)
            if item["source_id"] != source_id:
                raise ValueError("source identity mismatch")
            yield item

    def seal(self, identity):
        value = _json(identity)
        previous = self.db.execute("SELECT value FROM freeze WHERE name='campaign'").fetchone()
        if previous and previous[0] != value:
            raise ValueError("campaign identity changed")
        self.db.execute("INSERT OR IGNORE INTO freeze VALUES ('campaign', ?)", (value,))

    def claim(self, verify=None):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            item = next(self.items("pending"), None)
            row = (item["source_id"], _json(item)) if item else None
            if item is not None and verify is not None:
                verify(item)
            if row:
                self.db.execute("UPDATE tasks SET status='running', updated=? WHERE source_id=?", (time.time(), row[0]))
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise
        return json.loads(row[1]) if row else None

    def finish(self, source_id, result):
        item = next((item for item in self.items("running") if item["source_id"] == source_id), None)
        if item is None or result.get("id") != item["job"]["task_id"]:
            raise ValueError("running task result identity mismatch")
        changed = self.db.execute("UPDATE tasks SET status='recorded', result=?, updated=? WHERE source_id=? AND status='running'",
                                  (_json(result), time.time(), source_id))
        if changed.rowcount != 1:
            raise ValueError('only a running task can record a result')

    def counts(self):
        return dict(self.db.execute('SELECT status, COUNT(*) FROM tasks GROUP BY status'))
