"""Audited teacher transport bounded by the remaining execution deadline."""
from dataclasses import replace
import hashlib
import math
import time

from .read_only_agent import ReadOnlyBudgetExpired
from .strong_session import StrongCompletion


class DeadlineStrongCompletion(StrongCompletion):
    def __init__(self, settings, output, max_calls, *, max_seconds,
                 expected_input_sha256=None, require_exact_tokens=True):
        if not math.isfinite(max_seconds) or max_seconds <= 0:
            raise ValueError('positive finite teacher execution budget required')
        settings = replace(settings, retry_attempts=1, semantic_repair_attempts=0,
                           fallback_models=(), plan_cache_enabled=False)
        super().__init__(settings, output, max_calls)
        self.deadline = time.monotonic() + max_seconds
        self.expected_input_sha256 = expected_input_sha256
        self.require_exact_tokens = require_exact_tokens

    def text_completion(self, prompt, max_tokens=8192, stop=None):
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise ReadOnlyBudgetExpired('teacher execution deadline exhausted',
                                        'wall_budget_exhausted')
        if self.calls == 0 and self.expected_input_sha256 is not None:
            if hashlib.sha256(prompt.encode()).hexdigest() != self.expected_input_sha256:
                raise ValueError('teacher first input differs from source boundary')
        self.client.settings = replace(
            self.client.settings, read_timeout_seconds=remaining,
            connect_timeout_seconds=min(self.client.settings.connect_timeout_seconds, remaining))
        self.audit({'type': 'teacher_request_deadline', 'remaining_seconds': remaining,
                    'read_timeout_seconds': remaining, 'automatic_retry': False})
        start = len(self.events)
        response = super().text_completion(prompt, max_tokens=max_tokens, stop=stop)
        if self.require_exact_tokens:
            envelopes = [e['raw_response'] for e in self.events[start:]
                         if e['type'] == 'supervisor_response_envelope_received']
            if len(envelopes) != 1:
                raise ValueError('one teacher response envelope required')
            raw = envelopes[0]
            ids = raw['choices'][0].get('token_ids')
            prompt_ids = raw.get('prompt_token_ids')
            usage = raw.get('usage', {})
            if not isinstance(ids, list) or not isinstance(prompt_ids, list):
                raise ValueError('teacher server omitted exact token ids')
            if (len(ids) != usage.get('completion_tokens')
                    or len(prompt_ids) != usage.get('prompt_tokens')):
                raise ValueError('teacher token accounting differs')
            response.metadata = {'token_ids': ids, 'prompt_token_ids': prompt_ids}
        return response
