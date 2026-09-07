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
TASK_ID = 'RP-MAINT-02'
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


def main():
    documents = RUN / 'docs'; (documents / '团队').mkdir(parents=True)
    database = RUN / 'index.sqlite3'
    files = {'guide.md': 'Alpha marker\nStraße und CAFÉ\n', '团队/规划.txt': '团队 计划\nCafe\u0301 meeting\n', '团队/literal.MD': "A literal 100%_quote' token\n"}
    for name, content in files.items():
        (documents / name).write_text(content, encoding='utf-8')
    (documents / 'ignore.json').write_text('{"secret":"ignored-target"}', encoding='utf-8')
    outside = RUN / 'outside'; outside.mkdir()
    (outside / 'secret.md').write_text('outside forbidden marker', encoding='utf-8')
    (documents / 'external.md').symlink_to(outside / 'secret.md')
    (documents / 'external-dir').symlink_to(outside, target_is_directory=True)
    def sync(expect=0):
        result = cli('index_cli.py', 'sync', '--root', documents, '--db', database, expect=expect)
        return result if expect else {key: result[key] for key in ('added', 'updated', 'deleted', 'unchanged', 'generation')}
    def info():
        result = cli('index_cli.py', 'status', '--db', database)
        return {key: result[key] for key in ('document_count', 'generation', 'root')}
    def query(text):
        return cli('index_cli.py', 'query', '--db', database, '--text', text)
    def expect_paths(text, expected):
        value = query(text)
        check(value.get('count') == len(expected) and [{'path': row['path']} for row in value['matches']] == [{'path': path} for path in sorted(expected)], 'literal Unicode query ' + repr(text))
    check(sync() == {'added': 3, 'updated': 0, 'deleted': 0, 'unchanged': 0, 'generation': 1}, 'initial recursive indexing excludes symlinks/non-doc files')
    check(info() == {'document_count': 3, 'generation': 1, 'root': str(documents.resolve())}, 'persistent status metadata')
    expect_paths('STRASSE', ['guide.md'])
    expect_paths('café', ['guide.md', '团队/规划.txt'])
    expect_paths('CAFE\u0301', ['guide.md', '团队/规划.txt'])
    expect_paths('计划', ['团队/规划.txt'])
    expect_paths("100%_quote'", ['团队/literal.MD'])
    expect_paths('outside forbidden', [])
    expect_paths('ignored-target', [])
    check(sync() == {'added': 0, 'updated': 0, 'deleted': 0, 'unchanged': 3, 'generation': 1}, 'unchanged sync preserves generation')
    target = documents / 'guide.md'
    original_stat = target.stat()
    new_text = files['guide.md'].replace('Alpha', 'Omega')
    check(len(new_text.encode('utf-8')) == original_stat.st_size, 'fixture same-size update')
    target.write_text(new_text, encoding='utf-8')
    os.utime(target, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    (documents / '团队/规划.txt').unlink()
    (documents / 'new.txt').write_text('Brand-new content É', encoding='utf-8')
    check(sync() == {'added': 1, 'updated': 1, 'deleted': 1, 'unchanged': 1, 'generation': 2}, 'incremental add/update/delete including unchanged mtime')
    expect_paths('Alpha marker', [])
    expect_paths('Omega marker', ['guide.md'])
    expect_paths('计划', [])
    expect_paths('brand-NEW', ['new.txt'])
    before_status = info()
    (documents / 'guide.md').write_text('Pending replacement', encoding='utf-8')
    (documents / 'new.txt').unlink()
    (documents / 'bad.md').write_bytes(b'bad UTF8 \xff\xfe')
    sync(expect=1)
    check(info() == before_status, 'invalid UTF-8 leaves metadata and generation unchanged')
    expect_paths('Omega marker', ['guide.md'])
    expect_paths('brand-new', ['new.txt'])
    expect_paths('Pending replacement', [])
    (documents / 'bad.md').unlink()
    check(sync() == {'added': 0, 'updated': 1, 'deleted': 1, 'unchanged': 1, 'generation': 3}, 'recovery applies all pending changes together')
    expect_paths('Pending replacement', ['guide.md'])
    expect_paths('brand-new', [])
    check(info()['document_count'] == 2, 'deleted document removed durably')
    for path in documents.rglob('*'):
        if path.is_file() and not path.is_symlink():
            path.unlink()
    expect_paths('Pending replacement', ['guide.md'])
    check(info()['generation'] == 3, 'new CLI processes query persisted snapshot without source files')
    wrong_root = RUN / 'other-docs'; wrong_root.mkdir()
    cli('index_cli.py', 'sync', '--root', wrong_root, '--db', database, expect=1)
    check(info()['generation'] == 3, 'different root does not replace index')
    cli('index_cli.py', 'query', '--db', database, '--text', '   ', expect=1)
    missing = RUN / 'missing.sqlite3'
    cli('index_cli.py', 'status', '--db', missing, expect=1)
    check(not missing.exists(), 'missing index status does not create a database')
    integrity(database)

if __name__ == '__main__':
    raise SystemExit(run(main))
