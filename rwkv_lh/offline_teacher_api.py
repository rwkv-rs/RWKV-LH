"""Single-request DeepSeek transport with a durable, conservative cost ledger.

No retries, fallback, training, or credential persistence. Interrupted reservations
remain charged until explicitly reconciled against the provider's billing evidence.
"""
from contextlib import contextmanager
import fcntl
import hashlib
import json
import math
from pathlib import Path
import time
import uuid

import requests
from .deepseek_api import chat_request


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.pending')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


@contextmanager
def exclusive(path):
    with Path(path).open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


class DeepSeekTeacher:
    def __init__(self, directory, *, key_file, model, budget_usd,
                 input_usd_per_million, output_usd_per_million,
                 max_output_tokens=4096, max_requests=20, timeout_seconds=120):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.key_file = Path(key_file)
        self.model = model
        self.budget = float(budget_usd)
        self.input_rate = float(input_usd_per_million)
        self.output_rate = float(output_usd_per_million)
        if not all(math.isfinite(v) and v > 0 for v in
                   (self.budget, self.input_rate, self.output_rate, timeout_seconds)):
            raise ValueError('positive finite budget, price and timeout required')
        if type(max_output_tokens) is not int or not 0 < max_output_tokens <= 8192:
            raise ValueError('output limit must be 1..8192')
        if type(max_requests) is not int or max_requests <= 0:
            raise ValueError('positive request limit required')
        if model != 'deepseek-flash':
            raise ValueError('this pipeline is registered for deepseek-flash')
        self.output_limit, self.request_limit = max_output_tokens, max_requests
        self.timeout = timeout_seconds
        self.config = {'model': model, 'budget_usd': self.budget,
                       'input_usd_per_million': self.input_rate,
                       'output_usd_per_million': self.output_rate,
                       'max_output_tokens': max_output_tokens, 'max_requests': max_requests,
                       'timeout_seconds': timeout_seconds}

    def complete(self, system, user):
        endpoint, body, _ = chat_request(model=self.model, system=system, user=user,
            max_tokens=self.output_limit, options={'temperature': 0})
        # Deliberately pessimistic UTF-8 bound plus chat framing allowance. This
        # is estimated spend under registered rates, not a provider billing cap.
        prompt_bound = 4 * len(json.dumps(body, ensure_ascii=False).encode()) + 8192
        reservation = (prompt_bound * self.input_rate + self.output_limit * self.output_rate) / 1e6
        with exclusive(self.directory / '.ledger.lock'):
            ledger_path = self.directory / 'LEDGER.json'
            ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {
                'config': self.config, 'requests': []}
            if ledger['config'] != self.config:
                raise ValueError('ledger configuration changed; explicit new budget required')
            spent = sum(r['charged_estimate_usd'] for r in ledger['requests'])
            if len(ledger['requests']) >= self.request_limit or spent + reservation > self.budget:
                raise ValueError('teacher request/cost budget exhausted')
            key = self.key_file.read_text().strip()
            if not key or '\n' in key:
                raise ValueError('invalid credential file')
            rid = uuid.uuid4().hex
            request_path = self.directory / (rid + '.request.json')
            write_json(request_path, body)
            row = {'id': rid, 'status': 'reserved', 'started_unix': time.time(),
                   'request_sha256': digest(request_path.read_text()),
                   'charged_estimate_usd': reservation, 'prompt_token_bound': prompt_bound}
            ledger['requests'].append(row)
            write_json(ledger_path, ledger)  # BEFORE any billable network action.
            try:
                with requests.Session() as session:
                    session.trust_env = False
                    response = session.post(endpoint,
                        headers={'Authorization': 'Bearer ' + key}, json=body,
                        timeout=(min(15, self.timeout), self.timeout), allow_redirects=False)
                if response.status_code != 200:
                    raise ValueError('provider HTTP status ' + str(response.status_code))
                text = response.text.replace(key, '[REDACTED]')
                raw_path = self.directory / (rid + '.response.json')
                raw_path.write_text(text)
                row['response_sha256'] = digest(text)
                raw = json.loads(text)
                usage = raw['usage']
                counts = [usage['prompt_tokens'], usage['completion_tokens']]
                if any(type(v) is not int or v < 0 for v in counts):
                    raise ValueError('invalid provider usage')
                row['usage'] = usage
                if counts[0] > prompt_bound or counts[1] > self.output_limit:
                    row['charged_estimate_usd'] = max(reservation,
                        (counts[0] * self.input_rate + counts[1] * self.output_rate) / 1e6)
                    raise ValueError('provider usage exceeds reservation; reconcile ledger')
                row['charged_estimate_usd'] = (counts[0] * self.input_rate + counts[1] * self.output_rate) / 1e6
                choice = raw['choices'][0]
                content = choice['message']['content']
                if choice['finish_reason'] != 'stop' or not isinstance(content, str) or not content.strip():
                    raise ValueError('incomplete/empty teacher completion')
                value = json.loads(content)
                if not isinstance(value, dict):
                    raise ValueError('teacher must return one JSON object')
                row.update(status='completed', model_returned=raw.get('model'), provider_id=raw.get('id'))
                return value, {'request_id': rid, 'model': raw.get('model'),
                               'response_sha256': row['response_sha256']}
            except BaseException as exc:
                # Never serialize transport exceptions (may contain headers).
                row.update(status='failed_or_uncertain', error_type=type(exc).__name__)
                raise
            finally:
                row['finished_unix'] = time.time()
                write_json(ledger_path, ledger)
