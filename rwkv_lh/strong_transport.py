"""Official DeepSeek transport for the current Planner, with original response evidence."""
import base64
from collections.abc import Mapping
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import threading
import time
import uuid

import requests

from . import deepseek_api
from .strong_structured_output import tool_response_content


class StrongTransportError(RuntimeError):
    def __init__(self, message, *, category='transport', status_code=0, retryable=False):
        super().__init__(message)
        self.category, self.status_code, self.retryable = category, status_code, retryable


class StrongProtocolError(RuntimeError):
    """The provider envelope was incomplete or structurally invalid."""


class StrongGenerationInterrupted(StrongProtocolError):
    """A complete provider envelope explicitly reports output truncation."""


def render_user_payload(payload):
    return payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, separators=(',', ':'))


def decode_chat_completion_stream(response, *, deadline, on_line=None):
    """Assemble SSE carriers without parsing or repairing model-generated arguments."""
    pending, text, reasoning, tools = [], [], [], {}
    identity, usage, finished = {}, {}, None
    for raw in response.iter_lines():
        raw_bytes = raw if isinstance(raw, bytes) else raw.encode('utf-8')
        if on_line is not None:
            on_line(raw_bytes)
        if time.monotonic() > deadline:
            raise requests.ReadTimeout('Planner stream exceeded the request read budget')
        try:
            line = raw_bytes.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise StrongProtocolError('Planner stream is not UTF-8') from exc
        if line:
            if line.startswith('data:'):
                pending.append(line[5:].removeprefix(' '))
            continue
        if not pending:
            continue
        event, pending = '\n'.join(pending), []
        if event == '[DONE]':
            if finished is None:
                raise StrongProtocolError('Planner stream ended without finish_reason')
            if sorted(tools) != list(range(len(tools))):
                raise StrongProtocolError('Planner stream has noncontiguous tool indexes')
            message = {'role': 'assistant', 'content': ''.join(text)}
            if reasoning:
                message['reasoning_content'] = ''.join(reasoning)
            if tools:
                message['tool_calls'] = [tools[index] for index in sorted(tools)]
            return {**identity, 'choices': [{'message': message, 'finish_reason': finished}], 'usage': usage}
        try:
            chunk = json.loads(event)
        except ValueError as exc:
            raise StrongProtocolError('Planner stream contains invalid JSON') from exc
        if not isinstance(chunk, dict) or chunk.get('error'):
            raise StrongProtocolError('Planner stream contains an invalid/error event')
        for key in ('id', 'model'):
            value = chunk.get(key)
            if value is not None:
                if not isinstance(value, str) or (key in identity and identity[key] != value):
                    raise StrongProtocolError('Planner stream changed response identity')
                identity[key] = value
        if chunk.get('usage') is not None:
            if not isinstance(chunk['usage'], dict):
                raise StrongProtocolError('Planner stream usage must be an object')
            usage = deepcopy(chunk['usage'])
        choices = chunk.get('choices')
        if not isinstance(choices, list) or len(choices) > 1:
            raise StrongProtocolError('Planner stream requires one choice')
        if not choices:
            continue
        choice = choices[0]
        if not isinstance(choice, dict) or type(choice.get('index')) is not int or choice['index'] != 0:
            raise StrongProtocolError('Planner stream requires choice index 0')
        delta, reason = choice.get('delta'), choice.get('finish_reason')
        if not isinstance(delta, dict) or delta.get('refusal'):
            raise StrongProtocolError('Planner stream requires an assistant delta')
        if reason is not None and (not isinstance(reason, str) or not reason):
            raise StrongProtocolError('Planner stream finish_reason must be nonempty text')
        for key in ('content', 'reasoning_content'):
            if delta.get(key) is not None and not isinstance(delta[key], str):
                raise StrongProtocolError('Planner stream content and reasoning must be text')
        if finished is not None:
            if any(delta.get(key) for key in ('content', 'reasoning_content', 'tool_calls')):
                raise StrongProtocolError('Planner stream contains output after its finish')
            if reason is not None and reason != finished:
                raise StrongProtocolError('Planner stream changed finish_reason after its finish')
            continue
        for key, output in (('content', text), ('reasoning_content', reasoning)):
            value = delta.get(key)
            if value is not None:
                output.append(value)
        updates = delta.get('tool_calls')
        if updates is None:
            updates = []
        if not isinstance(updates, list):
            raise StrongProtocolError('Planner stream tool updates must be an array')
        for update in updates:
            if (not isinstance(update, dict) or type(update.get('index')) is not int
                    or update['index'] < 0 or set(update) - {'index', 'id', 'type', 'function'}):
                raise StrongProtocolError('Planner stream has an invalid tool update')
            target = tools.setdefault(update['index'], {'function': {}})
            for key in ('id', 'type'):
                if key in update:
                    if not isinstance(update[key], str) or (key in target and target[key] != update[key]):
                        raise StrongProtocolError('Planner stream changed tool identity')
                    target[key] = update[key]
            function = update.get('function', {})
            if not isinstance(function, dict) or set(function) - {'name', 'arguments'}:
                raise StrongProtocolError('Planner stream has an invalid function update')
            for key, value in function.items():
                if not isinstance(value, str):
                    raise StrongProtocolError('Planner stream function updates must be text')
                target['function'][key] = target['function'].get(key, '') + value
        if reason is not None:
            finished = reason
    raise StrongProtocolError('Planner stream ended before [DONE]')


class AuditedStrongClient:
    """One provider/model, no legacy role dispatch, repair, cache, or unknown-call replay."""
    def __init__(self, settings, *, audit_hook=None, session=None):
        settings.validate()
        if settings.backend_profile != deepseek_api.BACKEND_PROFILE:
            raise ValueError('Planner calls require the official DeepSeek backend')
        self.settings, self.audit_hook = settings, audit_hook
        self._main_session = session or requests.Session()
        self._main_session.trust_env = False
        self._lock = threading.RLock()
        self._failures, self._opened_at = 0, 0.0

    def _emit(self, event):
        if self.audit_hook is not None:
            self.audit_hook(deepcopy(event))

    @contextmanager
    def _request_slot(self):
        with self._lock:
            if not self.settings.serialize_requests:
                yield
                return
            import fcntl
            path = Path(self.settings.request_lock_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('a+b') as handle:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _wire_request(self, *, phase, selected_model, system_prompt, payload_text, max_tokens, tool_contract=None):
        if selected_model != self.settings.model:
            raise ValueError('Planner requests cannot change the configured model')
        return deepseek_api.chat_request(base_url=self.settings.base_url, model=selected_model,
            system=system_prompt, user=payload_text, max_tokens=max_tokens,
            stream=self.settings.stream_responses, options=dict(self.settings.planner_request_options),
            tool_contract=tool_contract)

    def _post_completion(self, endpoint, body, *, audit_context):
        expected = deepseek_api.endpoint(self.settings.base_url, strict='tools' in body)
        if endpoint != expected:
            raise ValueError('Planner requests cannot leave their official Chat endpoint')
        self._emit({'type': 'strong_execution_wire_request', 'endpoint': endpoint,
                    'body': body, **audit_context})
        with self._request_slot():
            deadline = time.monotonic() + self.settings.read_timeout_seconds
            response = self._main_session.post(endpoint, json=body,
                headers={'Authorization': 'Bearer ' + self.settings.api_key,
                         'Content-Type': 'application/json', 'Accept': 'application/json'},
                timeout=(self.settings.connect_timeout_seconds, self.settings.read_timeout_seconds),
                verify=self.settings.verify_tls, allow_redirects=False,
                **({'stream': True} if body['stream'] else {}))
            if not body['stream']:
                return response, None, None
            lines, digest, decoded = [], hashlib.sha256(), False
            def record(line):
                lines.append(base64.b64encode(line).decode('ascii'))
                digest.update(len(line).to_bytes(8, 'big'))
                digest.update(line)
            try:
                if response.status_code != 200:
                    getattr(response, 'content', None)
                    return response, None, None
                result = decode_chat_completion_stream(response, deadline=deadline, on_line=record)
                decoded = True
                return response, result, None
            except Exception as exc:
                return response, None, exc
            finally:
                self._emit({'type': 'supervisor_stream_received', **audit_context,
                    'http_status': response.status_code, 'lines_base64': lines,
                    'lines_sha256': digest.hexdigest(), 'decoded': decoded,
                    'evidence_format': 'iter_lines_base64_length_u64be_sha256'})
                response.close()

    def _request_json(self, *, phase, run_id, request_digest, system_prompt, request_payload,
                      schema, max_tokens, return_raw_content=False, tool_contract=None):
        if not return_raw_content:
            raise ValueError('Planner transport returns original content for its role parser')
        context = {'phase': phase, 'run_id': run_id, 'request_digest': request_digest,
                   'call_id': 'PLANNER-' + uuid.uuid4().hex[:20]}
        if (self._failures >= self.settings.circuit_breaker_failures
                and time.monotonic() - self._opened_at < self.settings.circuit_breaker_cooldown_seconds):
            self._emit({'type': 'supervisor_route_skipped', **context, 'reason': 'circuit_open'})
            raise StrongTransportError('configured Planner circuit is open')
        endpoint, body, transport = self._wire_request(phase=phase, selected_model=self.settings.model,
            system_prompt=system_prompt, payload_text=render_user_payload(request_payload),
            max_tokens=max_tokens, tool_contract=tool_contract)
        self._emit({'type': 'supervisor_request_started', **context, 'model': self.settings.model,
            'transport': transport, 'max_tokens': max_tokens,
            'wire_body_sha256': hashlib.sha256(json.dumps(body, ensure_ascii=False,
                sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()})
        started = time.perf_counter()
        status, attempt = 0, 0
        try:
            for attempt in range(1, self.settings.retry_attempts + 1):
                self._emit({'type': 'supervisor_http_attempt_started', **context, 'attempt': attempt})
                try:
                    response, streamed, stream_error = self._post_completion(endpoint, body,
                        audit_context={**context, 'attempt': attempt})
                except requests.ConnectTimeout:
                    # requests proves connection establishment failed. A read timeout,
                    # dropped connection, or incomplete stream is never replayed here.
                    if attempt == self.settings.retry_attempts:
                        raise
                    time.sleep(self.settings.retry_backoff_seconds * 2 ** (attempt - 1))
                    continue
                break
            status = response.status_code
            if status != 200:
                category = ('authorization' if status in (401, 403) else
                            'rate_limit' if status == 429 else 'upstream' if status >= 500 else 'request')
                raise StrongTransportError(f'Planner HTTP {status}', category=category, status_code=status)
            if stream_error is not None:
                raise stream_error
            raw = streamed if streamed is not None else response.json()
            if not isinstance(raw, Mapping):
                raise StrongProtocolError('Planner response envelope must be an object')
            choices = raw.get('choices')
            choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
            latency_ms = round((time.perf_counter() - started) * 1000, 1)
            self._emit({'type': 'supervisor_response_envelope_received', **context,
                'raw_response': dict(raw), 'usage': deepcopy(raw.get('usage', {})),
                'finish_reason': choice.get('finish_reason'), 'max_tokens': max_tokens,
                'attempt': attempt, 'latency_ms': latency_ms, 'transport': transport,
                'model': raw.get('model', self.settings.model)})
            if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
                raise StrongProtocolError('Planner response requires exactly one choice')
            if choice.get('finish_reason') == 'length':
                self._failures = 0
                raise StrongGenerationInterrupted('Planner generation exhausted its output budget')
            message = choice.get('message')
            if not isinstance(message, dict):
                raise StrongProtocolError('Planner response requires an assistant message')
            if not isinstance(choice.get('finish_reason'), str) or not choice['finish_reason']:
                raise StrongProtocolError('Planner response requires a finish reason')
            content = tool_response_content(message) if tool_contract is not None else message.get('content')
            if not isinstance(content, str):
                raise StrongProtocolError('Planner response content must be text')
            self._failures = 0
            self._emit({'type': 'supervisor_request_returned', **context,
                'model': raw.get('model', self.settings.model), 'transport': transport,
                'latency_ms': latency_ms, 'http_attempts': attempt,
                'finish_reason': choice['finish_reason'], 'usage': deepcopy(raw.get('usage', {})),
                'output_sha256': hashlib.sha256(content.encode()).hexdigest(), 'output_chars': len(content)})
            return content
        except StrongGenerationInterrupted:
            raise
        except Exception as exc:
            self._failures += 1
            self._opened_at = time.monotonic()
            category = ('connect_timeout' if isinstance(exc, requests.ConnectTimeout) else
                        'read_timeout' if isinstance(exc, requests.ReadTimeout) else
                        'connection' if isinstance(exc, requests.ConnectionError) else
                        getattr(exc, 'category', 'protocol'))
            self._emit({'type': 'supervisor_request_failed', **context, 'http_status': status,
                'http_attempts': attempt, 'error_category': category, 'retryable': False,
                'error': type(exc).__name__})
            if isinstance(exc, requests.RequestException):
                raise StrongTransportError('Planner request failed: ' + category, category=category) from exc
            raise

    def close(self):
        self._main_session.close()
