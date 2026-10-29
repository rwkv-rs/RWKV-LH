"""Audited Planner completion and model-session binding."""
import hashlib
import json
from types import SimpleNamespace
from .strong_transport import AuditedStrongClient, StrongGenerationInterrupted, render_user_payload
from .model_session import ModelSession
from .model_io import canonical_json
from .token_budget import get_token_count


class KnownStrongOutputBudgetExpired(TimeoutError):
    """A complete provider envelope proves truncation, not an unknown request."""
    def __init__(self, response):
        super().__init__('Planner output budget exhausted before action content')
        self.reason = 'output_budget_exhausted'
        self.provider_response = response


class StrongCompletion:
    def __init__(self, settings, output, max_calls, *, input_builder=None, phase='project_planning'):
        self.model_name = settings.model
        self.events, self.output, self.calls, self.max_calls = [], output, 0, max_calls
        self.client = AuditedStrongClient(settings, audit_hook=self.audit)
        self.input_builder = input_builder
        self.tools_builder = None
        self.phase = phase

    def audit(self, event):
        self.events.append(dict(event))
        with (self.output / 'strong_trace.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(event), ensure_ascii=False) + '\n')

    def _input(self, prompt):
        system_prompt, request_payload = (
            self.input_builder() if self.input_builder is not None else (prompt, {})
        )
        contract = None
        if self.tools_builder is not None:
            from .strong_structured_output import build_tool_contract
            contract = build_tool_contract(self.tools_builder())
        return system_prompt, request_payload, contract

    def wire_request(self, prompt, max_tokens):
        """Build the actual request shape without sending or reserving a call."""
        system, payload, contract = self._input(prompt)
        endpoint, body, _ = self.client._wire_request(phase=self.phase, selected_model=self.model_name,
            system_prompt=system, payload_text=render_user_payload(payload),
            max_tokens=max_tokens, tool_contract=contract)
        return {'endpoint': endpoint, 'body': body}

    def wire_input_tokens(self, prompt, max_tokens):
        """Conservative local estimate; provider tokenizer/template remain distinct."""
        return get_token_count(canonical_json(self.wire_request(prompt, max_tokens)['body']))

    def text_completion(self, prompt, max_tokens=1800, stop=None):
        if self.calls >= self.max_calls:
            raise RuntimeError('strong request budget exhausted')
        self.calls += 1
        start = len(self.events)
        system_prompt, request_payload, contract = self._input(prompt)
        if contract is not None:
            self.audit({'type': 'strong_decoder_contract', 'contract': contract})
        try:
            content = self.client._request_json(phase=self.phase, run_id=self.output.parent.name,
                request_digest=hashlib.sha256(prompt.encode()).hexdigest(), system_prompt=system_prompt,
                request_payload=request_payload, schema={'type': 'object'}, max_tokens=max_tokens,
                return_raw_content=True, **({'tool_contract': contract} if contract is not None else {}))
        except StrongGenerationInterrupted:
            interrupted = [e for e in self.events[start:]
                if e['type'] == 'supervisor_response_envelope_received']
            if len(interrupted) != 1:
                raise
            raise KnownStrongOutputBudgetExpired(interrupted[0]['raw_response']) from None
        envelopes = [e for e in self.events[start:] if e['type'] == 'supervisor_response_envelope_received']
        if len(envelopes) != 1:
            raise ValueError('one original strong response required')
        raw = envelopes[0]['raw_response']
        if len(raw['choices']) != 1:
            raise ValueError('one original strong choice required')
        choice = raw['choices'][0]
        if contract is None:
            content = choice['message']['content']
        if not content and choice.get('finish_reason') == 'length':
            raise KnownStrongOutputBudgetExpired(raw)
        if not isinstance(content, str):
            raise ValueError('strong content must be text')
        return SimpleNamespace(content=content, finish_reason=choice['finish_reason'],
            model=raw.get('model', self.model_name), response_id=raw.get('id', ''),
            metadata={'strong_decoder_contract_sha256': contract['contract_sha256']} if contract is not None else {})


class StrongModelSession(ModelSession):
    """Keep the complete audit checkpoint; budget only the strong request wire."""
    def generation_input_tokens(self, transcript, max_output_tokens):
        return self.client.wire_input_tokens(transcript, max_output_tokens)
