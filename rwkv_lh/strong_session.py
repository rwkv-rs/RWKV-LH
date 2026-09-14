"""Audited strong-model transport for the existing direct execution protocol."""
import hashlib
import json
from types import SimpleNamespace
from .supervisor_openai import OpenAICompatibleSupervisorClient, SupervisorProtocolError


class AuditedStrongClient(OpenAICompatibleSupervisorClient):
    def _post_completion(self, endpoint, body, *, audit_context):
        self._emit({'type': 'strong_execution_wire_request', 'endpoint': endpoint,
                    'body': dict(body), **audit_context})
        return super()._post_completion(endpoint, body, audit_context=audit_context)


class StrongCompletion:
    def __init__(self, settings, output, max_calls):
        self.model_name = settings.model
        self.events, self.output, self.calls, self.max_calls = [], output, 0, max_calls
        self.client = AuditedStrongClient(settings, audit_hook=self.audit)

    def audit(self, event):
        self.events.append(dict(event))
        with (self.output / 'strong_trace.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(event), ensure_ascii=False) + '\n')

    def text_completion(self, prompt, max_tokens=1800, stop=None):
        if self.calls >= self.max_calls:
            raise RuntimeError('strong request budget exhausted')
        self.calls += 1
        start = len(self.events)
        try:
            self.client._request_json(phase='explicit_takeover', run_id=self.output.parent.name,
                request_digest=hashlib.sha256(prompt.encode()).hexdigest(), system_prompt=prompt,
                request_payload={}, schema={'type': 'object'}, max_tokens=max_tokens)
        except SupervisorProtocolError:
            if not any(e['type'] == 'supervisor_response_envelope_received' for e in self.events[start:]):
                raise
        envelopes = [e for e in self.events[start:] if e['type'] == 'supervisor_response_envelope_received']
        if len(envelopes) != 1:
            raise ValueError('one original strong response required')
        raw = envelopes[0]['raw_response']
        if len(raw['choices']) != 1:
            raise ValueError('one original strong choice required')
        choice = raw['choices'][0]
        content = choice['message']['content']
        if not isinstance(content, str):
            raise ValueError('strong content must be text')
        return SimpleNamespace(content=content, finish_reason=choice['finish_reason'],
            model=raw.get('model', self.model_name), response_id=raw.get('id', ''), metadata={})
