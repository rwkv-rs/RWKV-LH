"""Existing production episode workers share event-loop-owned teacher pools."""
import asyncio
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import secrets
import threading


@contextmanager
def teacher_broker(pools):
    loop = asyncio.get_running_loop()
    token = secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_POST(self):
            if self.headers.get('Authorization') != 'Bearer '+token:
                self.send_error(403)
                return
            status = 200
            try:
                size = int(self.headers['Content-Length'])
                if not 0 < size < 20*1024*1024:
                    raise ValueError('invalid request size')
                body = json.loads(self.rfile.read(size))
                future = asyncio.run_coroutine_threadsafe(
                    pools[body['provider']].complete(body['messages'], key=body['key'],
                        max_output_tokens=body['max_output_tokens'], tools=body.get('tools'),
                        lane=body.get('lane', 'continuation'),
                        generation_options=body.get('generation_options')), loop)
                value = future.result()
            except Exception as exc:
                value = {'error': type(exc).__name__+': '+str(exc)}
                status = 503
            raw = json.dumps(value).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            try: self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError): pass
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield {'url': f'http://127.0.0.1:{server.server_port}/complete', 'token': token}
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


class BrokerPool:
    """Offline worker proxy; credentials remain only in the owner pool."""
    def __init__(self, broker, provider):
        self.broker, self.provider = broker, provider

    async def complete(self, messages, **options):
        import requests
        def send():
            with requests.Session() as http:
                http.trust_env = False
                response = http.post(self.broker['url'],
                    headers={'Authorization': 'Bearer ' + self.broker['token']},
                    json={'provider': self.provider['id'], 'messages': messages, **options}, timeout=(10, 900))
                response.raise_for_status()
                return response.json()
        return await asyncio.to_thread(send)
