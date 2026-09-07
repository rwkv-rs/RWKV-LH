from __future__ import annotations
import concurrent.futures
import hashlib
import http.client
import json
import os
from pathlib import Path
import random
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unicodedata
from urllib.parse import quote
import uuid

WORKSPACE = Path(sys.argv[1]).resolve()
TASK_ID = 'RP-MAINT-01'
ARTIFACT_ROOT = os.environ.get('RWKV_LH_VERIFY_ARTIFACT_ROOT')
if ARTIFACT_ROOT:
    Path(ARTIFACT_ROOT).mkdir(parents=True, exist_ok=True)
RUN_CONTEXT = tempfile.TemporaryDirectory(prefix=TASK_ID + '-', dir=ARTIFACT_ROOT)
RUN = Path(RUN_CONTEXT.name)
CHECKS = []

def check(condition, name):
    if not condition:
        raise AssertionError(name)
    CHECKS.append(name)

def cli(script, *arguments, expect=0):
    result = subprocess.run([sys.executable, str(WORKSPACE / script), *map(str, arguments)], cwd=WORKSPACE, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=20)
    with (RUN / 'cli.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({'script': script, 'arguments': list(map(str, arguments)), 'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}, ensure_ascii=False) + '\n')
    check(result.returncode == 0 if expect == 0 else result.returncode != 0, f'{script} exit expected={expect}: {result.stderr[-300:]}')
    if expect != 0:
        return result
    value = json.loads(result.stdout.strip().splitlines()[-1])
    check(isinstance(value, dict), f'{script} JSON object output')
    return value

class RunningServer:
    def __init__(self, database):
        self.database = Path(database)
        self.process = None
        self.log = None
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            self.port = probe.getsockname()[1]

    def start(self):
        self.log = (RUN / 'server.log').open('ab')
        self.process = subprocess.Popen([sys.executable, str(WORKSPACE / 'server.py'), '--db', str(self.database), '--host', '127.0.0.1', '--port', str(self.port)], cwd=WORKSPACE, stdout=self.log, stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise AssertionError('server exited during startup')
            try:
                status, value = self.request('GET', '/health')
                if status == 200 and value.get('ok') is True:
                    return self
            except (OSError, ValueError):
                pass
            time.sleep(0.05)
        raise AssertionError('server /health did not become ready')

    def stop(self):
        if self.process is not None:
            if self.process.poll() is None:
                os.killpg(self.process.pid, signal.SIGTERM)
                try:
                    self.process.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    os.killpg(self.process.pid, signal.SIGKILL)
                    self.process.wait(timeout=4)
            self.process = None
        if self.log is not None:
            self.log.close()
            self.log = None

    def request(self, method, path, body=None, headers=None):
        selected = dict(headers or {})
        if body is not None:
            body = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode('utf-8')
            selected['Content-Type'] = 'application/json'
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=8)
        try:
            connection.request(method, path, body=body, headers=selected)
            response = connection.getresponse()
            value = json.loads(response.read().decode('utf-8'))
            return response.status, value
        finally:
            connection.close()

def integrity(database):
    with sqlite3.connect(database) as connection:
        check(connection.execute('PRAGMA integrity_check').fetchone()[0] == 'ok', 'SQLite integrity after operations')

def run(main):
    try:
        main()
    except Exception as error:
        payload = {'task_id': TASK_ID, 'status': 'failed', 'checks_passed': len(CHECKS), 'checks': CHECKS, 'error': type(error).__name__ + ': ' + str(error), 'artifacts': str(RUN)}
        (RUN / 'result.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(payload, ensure_ascii=False))
        return 1
    payload = {'task_id': TASK_ID, 'status': 'passed', 'checks_passed': len(CHECKS), 'checks': CHECKS, 'artifacts': str(RUN)}
    (RUN / 'result.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(payload, ensure_ascii=False))
    return 0


def make_v1(path, entries, version=1, incompatible=False):
    with sqlite3.connect(path) as connection:
        connection.execute('CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        connection.executemany('INSERT INTO settings VALUES (?,?)', entries)
        connection.execute('CREATE TABLE user_notes (note TEXT NOT NULL)')
        connection.execute('INSERT INTO user_notes VALUES (?)', ('保留用户历史 é',))
        connection.execute(f'PRAGMA user_version={version}')
        if incompatible:
            connection.execute('CREATE TABLE schema_migrations (unrelated TEXT NOT NULL)')
            connection.execute("INSERT INTO schema_migrations VALUES ('preserve-me')")

def raw_state(path):
    with sqlite3.connect(path) as connection:
        return {'version': connection.execute('PRAGMA user_version').fetchone()[0],
                'settings': connection.execute('SELECT key,value FROM settings ORDER BY key').fetchall(),
                'notes': connection.execute('SELECT * FROM user_notes').fetchall()}

def main():
    randomizer = random.Random(73071)
    semantic = {'enabled': True, 'attempts': randomizer.randint(11, 99), 'nothing': None,
                'caption': '配置 é 雪', 'ratio': 1.25, 'list': [3, 'é', False],
                'nested': {'z': 4, 'a': {'enabled': False}}, 'disabled': False}
    entries = [(key, json.dumps(value, ensure_ascii=False, indent=2)) for key, value in semantic.items()]
    database, backup = RUN / 'config.sqlite3', RUN / 'config-before.sqlite3'
    make_v1(database, entries)
    original_state = raw_state(database)
    result = cli('config_cli.py', 'migrate', '--db', database, '--backup', backup)
    check(result.get('from_version') == 1 and result.get('to_version') == 2 and result.get('changed') is True and result.get('migrated_rows') == len(entries), 'migration summary')
    check(backup.is_file() and raw_state(backup) == original_state, 'backup is complete pre-migration SQLite')
    listed = cli('config_cli.py', 'list', '--db', database)
    expected_types = {'enabled': 'boolean', 'attempts': 'number', 'nothing': 'null', 'caption': 'string', 'ratio': 'number', 'list': 'array', 'nested': 'object', 'disabled': 'boolean'}
    expected = [{'key': key, 'value': semantic[key], 'value_type': expected_types[key]} for key in sorted(semantic)]
    typed_rows = [{key: row[key] for key in ('key', 'value', 'value_type')} for row in listed.get('settings', [])]
    check(listed.get('schema_version') == 2 and typed_rows == expected, 'all JSON types and Unicode preserved')
    for key in ('enabled', 'nested', 'caption'):
        value = cli('config_cli.py', 'get', '--db', database, '--key', key)
        check({name: value[name] for name in ('key', 'value', 'value_type')} == next(row for row in expected if row['key'] == key), 'get typed value')
    cli('config_cli.py', 'get', '--db', database, '--key', 'not-present', expect=1)
    with sqlite3.connect(database) as connection:
        check(connection.execute('PRAGMA user_version').fetchone()[0] == 2, 'schema version committed')
        columns = {row[1]: row for row in connection.execute('PRAGMA table_info(settings)')}
        check({'key', 'value', 'value_type', 'updated_at'} <= set(columns) and columns['value_type'][3] == 1 and columns['updated_at'][3] == 1, 'public v2 columns are non-null')
        rows = connection.execute('SELECT key,value,value_type,updated_at FROM settings ORDER BY key').fetchall()
        check(all(text == json.dumps(semantic[key], ensure_ascii=False, sort_keys=True, separators=(',', ':')) and kind == expected_types[key] and stamp == 0 for key, text, kind, stamp in rows), 'canonical durable values and migration timestamp')
        check(connection.execute('SELECT version FROM schema_migrations WHERE version=2').fetchone() == (2,), 'migration history registered')
        check(connection.execute('SELECT * FROM user_notes').fetchall() == original_state['notes'], 'unrelated table preserved')
    before_bytes, backup_bytes = database.read_bytes(), backup.read_bytes()
    result = cli('config_cli.py', 'migrate', '--db', database, '--backup', backup)
    check(result.get('changed') is False and result.get('from_version') == 2 and result.get('to_version') == 2 and result.get('migrated_rows') == 0, 'second migration is a no-op')
    check(database.read_bytes() == before_bytes and backup.read_bytes() == backup_bytes, 'no-op preserves database and backup bytes')
    for kind in ('bad-json', 'non-finite', 'unsupported', 'schema-conflict', 'existing-backup'):
        source, destination = RUN / (kind + '.sqlite3'), RUN / (kind + '-backup.sqlite3')
        values = [('a-valid', '{"a":1}'), ('z-last', '{broken' if kind == 'bad-json' else 'NaN' if kind == 'non-finite' else 'false')]
        make_v1(source, values, version=9 if kind == 'unsupported' else 1, incompatible=kind == 'schema-conflict')
        if kind == 'existing-backup':
            destination.write_bytes(b'owner backup must not be overwritten')
        source_bytes = source.read_bytes()
        destination_bytes = destination.read_bytes() if destination.exists() else None
        cli('config_cli.py', 'migrate', '--db', source, '--backup', destination, expect=1)
        check(source.read_bytes() == source_bytes, f'{kind} leaves entire source byte-identical')
        if destination_bytes is not None:
            check(destination.read_bytes() == destination_bytes, 'existing backup unchanged')
    result = cli('config_cli.py', 'restore', '--db', database, '--backup', backup)
    check(result.get('restored') is True and result.get('schema_version') == 1 and raw_state(database) == original_state, 'restore reverts schema, rows and user table')
    check(backup.read_bytes() == backup_bytes, 'restore preserves source backup')
    before_restore = database.read_bytes()
    damaged = RUN / 'damaged.sqlite3'; damaged.write_bytes(b'not a database')
    unrelated = RUN / 'unrelated.sqlite3'
    with sqlite3.connect(unrelated) as connection:
        connection.execute('CREATE TABLE unrelated (value TEXT)')
    for path in (damaged, unrelated, RUN / 'missing.sqlite3'):
        cli('config_cli.py', 'restore', '--db', database, '--backup', path, expect=1)
        check(database.read_bytes() == before_restore, 'invalid restore preserves original bytes')
    integrity(database); integrity(backup)

if __name__ == '__main__':
    raise SystemExit(run(main))
