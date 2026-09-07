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
    connection.execute('CREATE TABLE IF NOT EXISTS bookings (id TEXT PRIMARY KEY, resource TEXT NOT NULL, start INTEGER NOT NULL, end INTEGER NOT NULL, customer TEXT NOT NULL, status TEXT NOT NULL)')

def booking(row):
    return {key: row[key] for key in ('id', 'resource', 'start', 'end', 'customer', 'status')}

def route(handler, connection):
    parsed = urlsplit(handler.path)
    path = parsed.path
    if handler.command == 'GET' and path == '/health':
        return 200, {'ok': True}
    if handler.command == 'POST' and path == '/bookings':
        body = handler.read_json()
        resource, customer = body.get('resource'), body.get('customer')
        start, end = body.get('start'), body.get('end')
        if not isinstance(resource, str) or not resource.strip() or not isinstance(customer, str) or not customer.strip():
            raise APIError(400, 'invalid_fields')
        if not integer(start) or not integer(end) or start < 0 or start >= end:
            raise APIError(400, 'invalid_interval')
        connection.execute('BEGIN IMMEDIATE')
        conflict = connection.execute("SELECT 1 FROM bookings WHERE resource=? AND status='confirmed' AND start < ? AND end > ?", (resource, end, start)).fetchone()
        if conflict:
            raise APIError(409, 'overlap')
        identifier = uuid.uuid4().hex
        connection.execute('INSERT INTO bookings VALUES (?,?,?,?,?,?)', (identifier, resource, start, end, customer, 'confirmed'))
        return 201, booking(connection.execute('SELECT * FROM bookings WHERE id=?', (identifier,)).fetchone())
    if handler.command == 'GET' and path == '/bookings':
        resource = parse_qs(parsed.query, keep_blank_values=True).get('resource')
        if resource is None:
            rows = connection.execute('SELECT * FROM bookings ORDER BY start,id').fetchall()
        else:
            rows = connection.execute('SELECT * FROM bookings WHERE resource=? ORDER BY start,id', (resource[0],)).fetchall()
        return 200, {'bookings': [booking(row) for row in rows]}
    if path.startswith('/bookings/') and handler.command in ('GET', 'DELETE'):
        identifier = unquote(path[len('/bookings/'):])
        if handler.command == 'DELETE':
            connection.execute('BEGIN IMMEDIATE')
        row = connection.execute('SELECT * FROM bookings WHERE id=?', (identifier,)).fetchone()
        if row is None:
            raise APIError(404, 'not_found')
        if handler.command == 'GET':
            return 200, booking(row)
        connection.execute("UPDATE bookings SET status='cancelled' WHERE id=?", (identifier,))
        return 200, {'id': identifier, 'status': 'cancelled'}
    raise APIError(404, 'not_found')

if __name__ == '__main__':
    main()
