"""Durable, append-only batches of reviewed tasks; no task or answer synthesis."""
import hashlib
import json
from pathlib import Path
import sqlite3
from .collection_queue import _json


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Campaign:
    def __init__(self, path, identity):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS identity (value TEXT NOT NULL)')
        old = self.db.execute('SELECT value FROM identity').fetchone()
        if old and old[0] != _json(identity):
            self.db.close()
            raise ValueError('campaign identity changed')
        if not old:
            self.db.execute('INSERT INTO identity VALUES (?)', (_json(identity),))
        self.db.execute('''CREATE TABLE IF NOT EXISTS batches (
            id TEXT PRIMARY KEY, path TEXT UNIQUE NOT NULL, sha TEXT NOT NULL,
            payload TEXT NOT NULL, status TEXT NOT NULL, result TEXT)''')
        self.db.execute('''CREATE TABLE IF NOT EXISTS tasks (
            source_id TEXT PRIMARY KEY, source_sha TEXT UNIQUE NOT NULL,
            family TEXT UNIQUE NOT NULL, task_id TEXT UNIQUE NOT NULL,
            workspace TEXT NOT NULL, output TEXT UNIQUE NOT NULL, batch_id TEXT NOT NULL)''')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.db.close()

    def admit(self, manifest):
        path = Path(manifest).resolve(strict=True)
        sha = digest(path)
        value = json.loads(path.read_text())
        if set(value) != {'batch_id', 'inventory', 'inventory_sha256', 'families'}:
            raise ValueError('explicit batch identity, inventory and family review required')
        name = value['batch_id']
        if not isinstance(name, str) or not name or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for c in name):
            raise ValueError('invalid batch id')
        previous = self.db.execute('SELECT path, sha FROM batches WHERE id=?', (name,)).fetchone()
        if previous:
            if previous != (str(path), sha):
                raise ValueError('batch manifest changed')
            return False
        inventory = Path(value['inventory']).resolve(strict=True)
        if digest(inventory) != value['inventory_sha256']:
            raise ValueError('inventory changed')
        items = [json.loads(line) for line in inventory.read_text().splitlines()]
        if not items or set(value['families']) != {i['source_id'] for i in items}:
            raise ValueError('each source requires a reviewed family')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            for item in items:
                family = value['families'][item['source_id']]
                if not isinstance(family, str) or not family.strip():
                    raise ValueError('nonempty reviewed family required')
                workspace = str(Path(item['job']['workspace']).resolve())
                output = str(Path(item['job']['output_dir']).resolve())
                self.db.execute('INSERT INTO tasks VALUES (?,?,?,?,?,?,?)',
                    (item['source_id'], item['source_sha256'], family, item['job']['task_id'], workspace, output, name))
            workspaces = {Path(r[0]) for r in self.db.execute('SELECT workspace FROM tasks')}
            outputs = {Path(r[0]) for r in self.db.execute('SELECT output FROM tasks')}
            for output in outputs:
                if output in workspaces or any(p in outputs or p in workspaces for p in output.parents):
                    raise ValueError('cross-batch paths overlap')
            if any(any(p in outputs for p in w.parents) for w in workspaces):
                raise ValueError('cross-batch paths overlap')
            self.db.execute('INSERT INTO batches VALUES (?,?,?,?,?,NULL)',
                (name, str(path), sha, _json(value), 'pending'))
            self.db.execute('COMMIT')
        except BaseException as exc:
            self.db.execute('ROLLBACK')
            if isinstance(exc, sqlite3.IntegrityError):
                raise ValueError('duplicate source, family, task or output across batches') from exc
            raise
        return True

    def next_batch(self):
        row = self.db.execute("SELECT path,sha,payload FROM batches WHERE status='pending' ORDER BY rowid LIMIT 1").fetchone()
        if row is None:
            return None
        path, sha, raw = row
        value = json.loads(raw)
        if digest(path) != sha or digest(value['inventory']) != value['inventory_sha256']:
            raise ValueError('admitted batch changed')
        return value

    def finish(self, name, outcome):
        expected = self.db.execute('SELECT COUNT(*) FROM tasks WHERE batch_id=?', (name,)).fetchone()[0]
        if outcome.get('reason') != 'exhausted' or outcome.get('counts') != {'recorded': expected} or not expected:
            raise ValueError('incomplete batch cannot advance campaign')
        changed = self.db.execute("UPDATE batches SET status='recorded',result=? WHERE id=? AND status='pending'",
                                  (_json(outcome), name))
        if changed.rowcount != 1:
            raise ValueError('batch is not pending')

    def counts(self):
        return dict(self.db.execute('SELECT status,COUNT(*) FROM batches GROUP BY status'))
