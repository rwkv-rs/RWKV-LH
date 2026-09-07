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
TASK_ID = 'RP-API-02'
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
    database = RUN / 'inventory.sqlite3'
    server = RunningServer(database)
    try:
        server.start()
        def stock(sku):
            status, value = server.request('GET', '/inventory/' + quote(sku, safe=''))
            check(status == 200 and value.get('sku') == sku, 'inventory lookup identity')
            return value['stock']
        def set_stock(sku, amount):
            status, value = server.request('PUT', '/inventory/' + quote(sku, safe=''), {'stock': amount})
            check(status == 200 and value.get('stock') == amount, 'inventory setup persisted')
        def order(key, items, customer='顾客é'):
            status, value = server.request('POST', '/orders', {'customer': customer, 'items': items}, {'Idempotency-Key': key})
            return status, core_order(value) if status in (200, 201) else value
        def core_order(value):
            return {'id': value['id'], 'customer': value['customer'], 'status': value['status'],
                    'items': [{'sku': item['sku'], 'quantity': item['quantity']} for item in value['items']]}
        def all_orders():
            status, value = server.request('GET', '/orders')
            check(status == 200, 'order collection accessible')
            return [core_order(item) for item in value['orders']]
        set_stock('A', 12); set_stock('B', 4)
        items = [{'sku': 'A', 'quantity': 3}, {'sku': 'B', 'quantity': 2}]
        status, original = order('stable-order', items)
        check(status == 201 and original.get('status') == 'confirmed' and isinstance(original.get('id'), str), 'initial order created')
        check(original.get('items') == items and original.get('customer') == '顾客é', 'normalized order body')
        replay_items = [{'sku': 'B', 'quantity': 2}, {'sku': 'A', 'quantity': 1}, {'sku': 'A', 'quantity': 2}]
        status, replay = order('stable-order', replay_items)
        check(status == 200 and replay == original, 'semantic replay merges duplicate sku and reorders')
        check(stock('A') == 9 and stock('B') == 2, 'replay does not decrement stock')
        check(order('stable-order', [{'sku': 'A', 'quantity': 1}])[0] == 409, 'changed order conflicts with same key')
        check(stock('A') == 9 and stock('B') == 2, 'idempotency conflict is atomic')
        check(order('retry-after-failure', [{'sku': 'A', 'quantity': 2}, {'sku': 'B', 'quantity': 99}])[0] == 409, 'later insufficient item rejects whole order')
        check(stock('A') == 9 and stock('B') == 2, 'insufficient order does not decrement any line')
        check(order('retry-after-failure', [{'sku': 'A', 'quantity': 2}, {'sku': 'B', 'quantity': 1}])[0] == 201, 'failed key remains reusable')
        check(stock('A') == 7 and stock('B') == 1, 'successful retry deducts exactly once')
        check(order('missing-item', [{'sku': 'A', 'quantity': 1}, {'sku': 'missing', 'quantity': 1}])[0] == 404, 'unknown sku fails order')
        check(stock('A') == 7, 'unknown sku failure is atomic')
        before_invalid = all_orders()
        for quantity in (0, -1, True, 1.5):
            check(order('invalid-' + str(quantity), [{'sku': 'A', 'quantity': quantity}])[0] == 400, 'invalid quantity rejected')
        check(order('empty-list', [])[0] == 400, 'empty order rejected')
        check(order('', items)[0] == 400, 'missing idempotency key rejected')
        check(order('bad-customer', items, customer='')[0] == 400, 'empty customer rejected')
        check(server.request('POST', '/orders', b'{broken', {'Idempotency-Key': 'malformed'})[0] == 400, 'malformed JSON rejected')
        for amount in (-1, True, 2.5):
            check(server.request('PUT', '/inventory/A', {'stock': amount})[0] == 400, 'invalid inventory rejected')
        check(stock('A') == 7 and all_orders() == before_invalid, 'invalid requests do not mutate')
        special = "部品'雪"
        set_stock(special, 100)
        randomizer = random.Random(19073)
        expected = 100
        for index in range(12):
            quantity = randomizer.randint(1, 5)
            body = [{'sku': special, 'quantity': quantity}]
            status, value = order(f'random-{index}', body)
            check(status == 201, f'random order {index}')
            expected -= quantity
            check(order(f'random-{index}', body) == (200, value) and stock(special) == expected, f'random replay accounting {index}')
        set_stock('once', 10)
        def same_key(index):
            return order('concurrent-same', [{'sku': 'once', 'quantity': 1}])
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            replies = list(pool.map(same_key, range(8)))
        check(sorted(status for status, value in replies) == [200] * 7 + [201], 'concurrent identical keys have one creation')
        check(len({value.get('id') for status, value in replies}) == 1 and stock('once') == 9, 'concurrent replay has one durable order')
        set_stock('scarce', 3)
        def scarce(index):
            return order(f'scarce-{index}', [{'sku': 'scarce', 'quantity': 2}])
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            replies = list(pool.map(scarce, range(8)))
        check(sum(status == 201 for status, value in replies) == 1 and sum(status == 409 for status, value in replies) == 7 and stock('scarce') == 1, 'concurrent independent orders cannot oversell')
        before_restart = all_orders()
        server.stop(); integrity(database); server.start()
        check(all_orders() == before_restart, 'order collection survives restart')
        check(order('stable-order', items) == (200, original) and stock('A') == 7 and stock('B') == 1, 'idempotency key and stock survive restart')
        status, value = server.request('GET', '/orders/' + quote(original['id']))
        check(status == 200 and core_order(value) == original, 'individual order survives restart')
        check(server.request('GET', '/orders/not-present')[0] == 404, 'unknown order is 404')
    finally:
        server.stop()

if __name__ == '__main__':
    raise SystemExit(run(main))
