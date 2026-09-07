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
TASK_ID = 'RP-API-01'
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
    randomizer = random.Random(73191)
    database = RUN / 'bookings.sqlite3'
    server = RunningServer(database)
    known = []
    def booking_rows(payload):
        return [{key: row[key] for key in ('id', 'resource', 'start', 'end', 'customer', 'status')} for row in payload['bookings']]
    def collection():
        status, payload = server.request('GET', '/bookings')
        check(status == 200, 'booking collection accessible')
        return booking_rows(payload)
    try:
        server.start()
        status, value = server.request('GET', '/bookings')
        check(status == 200 and value.get('bookings') == [], 'empty persisted collection')
        for index in range(32):
            resource = randomizer.choice(['会议室 雪', "lab'quote", 'studio'])
            start = randomizer.randint(0, 20) * 10
            end = start + randomizer.choice([10, 20, 30])
            customer = f'用户-{index}-é'
            conflict = any(row['resource'] == resource and row['status'] == 'confirmed' and row['start'] < end and row['end'] > start for row in known)
            status, value = server.request('POST', '/bookings', {'resource': resource, 'start': start, 'end': end, 'customer': customer})
            check(status == (409 if conflict else 201), f'interval oracle case {index}')
            if not conflict:
                check(all(value.get(key) == expected for key, expected in {'resource': resource, 'start': start, 'end': end, 'customer': customer, 'status': 'confirmed'}.items()), f'booking fields case {index}')
                check(isinstance(value.get('id'), str) and value['id'] and all(row['id'] != value['id'] for row in known), f'new durable identity case {index}')
                known.append({key: value[key] for key in ('id', 'resource', 'start', 'end', 'customer', 'status')})
        for start, end in [(1000, 1010), (1010, 1020)]:
            status, value = server.request('POST', '/bookings', {'resource': 'adjacent', 'start': start, 'end': end, 'customer': '边界'})
            check(status == 201, 'half-open adjacent interval accepted')
            known.append({key: value[key] for key in ('id', 'resource', 'start', 'end', 'customer', 'status')})
        cancelled = known[0]
        for repeat in range(2):
            status, value = server.request('DELETE', '/bookings/' + quote(cancelled['id']))
            check(status == 200 and value.get('status') == 'cancelled', f'cancel idempotent repeat {repeat}')
        cancelled['status'] = 'cancelled'
        status, replacement = server.request('POST', '/bookings', {key: cancelled[key] for key in ('resource', 'start', 'end', 'customer')})
        check(status == 201, 'cancelled slot can be booked again')
        known.append({key: replacement[key] for key in ('id', 'resource', 'start', 'end', 'customer', 'status')})
        for resource in ('会议室 雪', "lab'quote", 'not-present'):
            status, value = server.request('GET', '/bookings?resource=' + quote(resource))
            expected = sorted((row for row in known if row['resource'] == resource), key=lambda row: (row['start'], row['id']))
            check(status == 200 and booking_rows(value) == expected, 'exact resource filtering including Unicode/quotes')
        snapshot = collection()
        invalid = [
            {'resource': '', 'start': 0, 'end': 1, 'customer': 'x'},
            {'resource': 'x', 'start': -1, 'end': 1, 'customer': 'x'},
            {'resource': 'x', 'start': 1, 'end': 1, 'customer': 'x'},
            {'resource': 'x', 'start': True, 'end': 10, 'customer': 'x'},
            {'resource': 'x', 'start': 1.5, 'end': 10, 'customer': 'x'},
            {'resource': 'x', 'start': 1, 'end': 10, 'customer': ''},
            b'{bad json',
        ]
        for body in invalid:
            check(server.request('POST', '/bookings', body)[0] == 400, 'invalid request rejected')
        check(collection() == snapshot, 'invalid requests leave all rows unchanged')
        check(server.request('GET', '/bookings/missing')[0] == 404, 'unknown booking read')
        check(server.request('DELETE', '/bookings/missing')[0] == 404, 'unknown booking cancel')
        def contend(index):
            return server.request('POST', '/bookings', {'resource': 'race-only', 'start': 5000, 'end': 5010, 'customer': str(index)})
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            responses = list(pool.map(contend, range(8)))
        check(sum(status == 201 for status, value in responses) == 1 and sum(status == 409 for status, value in responses) == 7, 'concurrent overlaps have one winner')
        before_restart = collection()
        server.stop()
        integrity(database)
        server.start()
        check(collection() == before_restart, 'all bookings and cancellation survive restart')
        check(server.request('POST', '/bookings', {'resource': 'race-only', 'start': 5001, 'end': 5009, 'customer': 'late'})[0] == 409, 'conflict enforcement survives restart')
        status, value = server.request('GET', '/bookings/' + quote(cancelled['id']))
        check(status == 200 and value.get('status') == 'cancelled', 'cancelled state survives restart')
    finally:
        server.stop()

if __name__ == '__main__':
    raise SystemExit(run(main))
