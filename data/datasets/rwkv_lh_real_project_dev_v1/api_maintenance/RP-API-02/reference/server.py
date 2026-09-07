from __future__ import annotations
import argparse
import json
import sqlite3
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlsplit

def integer(value):
    return isinstance(value, int) and not isinstance(value, bool)

class APIError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def read_json(self):
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if length <= 0 or length > 1_000_000:
                raise ValueError('body size')
            value = json.loads(self.rfile.read(length).decode('utf-8'))
            if not isinstance(value, dict):
                raise ValueError('object required')
            return value
        except (ValueError, UnicodeError):
            raise APIError(400, 'invalid_json')

    def respond(self, status, value):
        body = json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def dispatch(self):
        try:
            with sqlite3.connect(self.server.database, timeout=20) as connection:
                connection.row_factory = sqlite3.Row
                status, value = route(self, connection)
            self.respond(status, value)
        except APIError as error:
            self.respond(error.status, {'error': error.message})
        except Exception:
            self.respond(500, {'error': 'internal_error'})

    do_GET = dispatch
    do_POST = dispatch
    do_PUT = dispatch
    do_DELETE = dispatch

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', required=True)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', required=True, type=int)
    arguments = parser.parse_args()
    with sqlite3.connect(arguments.db) as connection:
        initialize(connection)
    server = ThreadingHTTPServer((arguments.host, arguments.port), Handler)
    server.database = arguments.db
    server.serve_forever()


def initialize(connection):
    connection.execute('CREATE TABLE IF NOT EXISTS inventory (sku TEXT PRIMARY KEY, stock INTEGER NOT NULL CHECK(stock >= 0))')
    connection.execute('CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, idem_key TEXT NOT NULL UNIQUE, fingerprint TEXT NOT NULL, payload TEXT NOT NULL)')

def normalize(body):
    customer, items = body.get('customer'), body.get('items')
    if not isinstance(customer, str) or not customer.strip() or not isinstance(items, list) or not items:
        raise APIError(400, 'invalid_order')
    quantities = {}
    for item in items:
        if not isinstance(item, dict):
            raise APIError(400, 'invalid_item')
        sku, quantity = item.get('sku'), item.get('quantity')
        if not isinstance(sku, str) or not sku.strip() or not integer(quantity) or quantity <= 0:
            raise APIError(400, 'invalid_item')
        quantities[sku] = quantities.get(sku, 0) + quantity
    return {'customer': customer, 'items': [{'sku': sku, 'quantity': quantities[sku]} for sku in sorted(quantities)]}

def route(handler, connection):
    path = urlsplit(handler.path).path
    if handler.command == 'GET' and path == '/health':
        return 200, {'ok': True}
    if path.startswith('/inventory/') and handler.command in ('GET', 'PUT'):
        sku = unquote(path[len('/inventory/'):])
        if not sku.strip():
            raise APIError(400, 'invalid_sku')
        if handler.command == 'PUT':
            stock = handler.read_json().get('stock')
            if not integer(stock) or stock < 0:
                raise APIError(400, 'invalid_stock')
            connection.execute('INSERT INTO inventory VALUES (?,?) ON CONFLICT(sku) DO UPDATE SET stock=excluded.stock', (sku, stock))
            return 200, {'sku': sku, 'stock': stock}
        row = connection.execute('SELECT stock FROM inventory WHERE sku=?', (sku,)).fetchone()
        if row is None:
            raise APIError(404, 'not_found')
        return 200, {'sku': sku, 'stock': row['stock']}
    if handler.command == 'POST' and path == '/orders':
        key = handler.headers.get('Idempotency-Key', '')
        if not key.strip() or len(key) > 128:
            raise APIError(400, 'invalid_idempotency_key')
        order = normalize(handler.read_json())
        fingerprint = json.dumps(order, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        connection.execute('BEGIN IMMEDIATE')
        previous = connection.execute('SELECT fingerprint,payload FROM orders WHERE idem_key=?', (key,)).fetchone()
        if previous is not None:
            if previous['fingerprint'] != fingerprint:
                raise APIError(409, 'idempotency_conflict')
            return 200, json.loads(previous['payload'])
        for item in order['items']:
            row = connection.execute('SELECT stock FROM inventory WHERE sku=?', (item['sku'],)).fetchone()
            if row is None:
                raise APIError(404, 'sku_not_found')
            if row['stock'] < item['quantity']:
                raise APIError(409, 'insufficient_stock')
        for item in order['items']:
            connection.execute('UPDATE inventory SET stock=stock-? WHERE sku=?', (item['quantity'], item['sku']))
        result = {'id': uuid.uuid4().hex, **order, 'status': 'confirmed'}
        connection.execute('INSERT INTO orders VALUES (?,?,?,?)', (result['id'], key, fingerprint, json.dumps(result, ensure_ascii=False)))
        return 201, result
    if handler.command == 'GET' and path == '/orders':
        return 200, {'orders': [json.loads(row['payload']) for row in connection.execute('SELECT payload FROM orders ORDER BY id')]}
    if handler.command == 'GET' and path.startswith('/orders/'):
        row = connection.execute('SELECT payload FROM orders WHERE id=?', (unquote(path[len('/orders/'):]),)).fetchone()
        if row is None:
            raise APIError(404, 'not_found')
        return 200, json.loads(row['payload'])
    raise APIError(404, 'not_found')

if __name__ == '__main__':
    main()
