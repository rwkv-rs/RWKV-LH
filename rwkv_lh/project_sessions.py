"""The agent's one durable native RWKV conversation: State bootstrap, delta append, generate.

The host renders only text not yet in the State (the exact suffix after the last
committed boundary), so the State always equals what training renders for the
same messages. Rejected or truncated candidates are rolled back; nothing in
them becomes a call.
"""
import json
import os
from pathlib import Path
import time

from .model_session import InputBudgetError, create_model_session
from .model_io import ModelCommand, ModelCommandNormalization
from .schema import ModelLaneKind, ModelEvent
from .runtime.settings import RuntimeSettings, direct_agent_settings
from .runtime.structured_output import build_transcript_decoder_contract
from .project_runtime import AgentReply
from .project_contracts import digest, fields
from .project_protocols import agent
from .token_budget import get_token_count
from .transcript.parse import validate_assistant, validate_messages
from .transcript.wire import PROTOCOL as TRANSCRIPT_PROTOCOL, generation_prompt, parse_assistant, render_turns
from .transcript.tools import TOOL_PROTOCOL

# Environment role for the RWKV agent endpoint (RWKV_LH_PROJECT_EXECUTOR_*, falling
# back to RWKV_LH_EXECUTOR_*). The names are deployment configuration, kept stable.
SETTINGS_ROLE = 'project_executor'


class ProjectInputBudgetError(InputBudgetError):
    def __init__(self, message, *, input_tokens, input_limit, capacity, output_reserved,
                 configured_output, transport, **original_input):
        super().__init__(message)
        import hashlib
        from .token_budget import VOCAB_PATH
        self.input_budget_evidence = {
            'input_tokens': input_tokens, 'input_limit': input_limit, 'capacity': capacity,
            'output_reserved': output_reserved, 'configured_output': configured_output,
            'transport': transport, 'estimator': 'rwkv_lh.token_budget.get_token_count',
            'tokenizer_sha256': hashlib.sha256(VOCAB_PATH.read_bytes()).hexdigest(), **original_input}


def _suffix(messages, checkpoint, native_tools):
    """Host text not yet in the State, ending with the assistant generation prompt."""
    validate_messages(messages, allow_pending=False)
    old = [] if checkpoint is None else checkpoint.get('messages')
    if not isinstance(old, list) or messages[:len(old)] != old:
        raise ValueError('agent conversation changed before its committed State boundary')
    if len(messages) == len(old):
        raise ValueError('agent request has no new host turn after its State boundary')
    # Render the complete conversation so the suffix is validated in context.
    return ''.join(render_turns(messages, native_tools)[len(old):]) + generation_prompt()


def _event_renderer(event, visible_definitions=(), **kwargs):
    return event.payload['text']


def _verify_checkpoint(checkpoint):
    fields(checkpoint, ('binding', 'checkpoint', 'identity_digest', 'messages', 'needs_newline'))
    if type(checkpoint['needs_newline']) is not bool:
        raise ValueError('agent checkpoint newline identity must be boolean')
    if checkpoint['identity_digest'] != digest({key: value for key, value in checkpoint.items()
                                               if key != 'identity_digest'}):
        raise ValueError('agent checkpoint metadata identity mismatch')


class ProjectSessions:
    """The agent port used by ProjectRuntime: preflight(...) and request(...)."""

    def __init__(self, settings, directory, *, session_factory=create_model_session, constrained_decoding=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.settings = direct_agent_settings(RuntimeSettings.for_role(SETTINGS_ROLE, fallback=settings))
        self.factory = session_factory
        self.sessions = {}
        if constrained_decoding is None:
            mode = os.getenv('RWKV_LH_PROJECT_CONSTRAINED_DECODING', 'on')
            if mode not in ('on', 'off'):
                raise ValueError('RWKV_LH_PROJECT_CONSTRAINED_DECODING must be on or off')
            constrained_decoding = mode == 'on'
        if type(constrained_decoding) is not bool:
            raise ValueError('constrained_decoding must be boolean')
        self.constrained_decoding = constrained_decoding

    def _audit(self, lane):
        def record(event):
            with (self.directory / 'model_trace.jsonl').open('a') as stream:
                stream.write(json.dumps({'project_role': 'agent', 'project_lane': lane,
                    **event}, ensure_ascii=False) + '\n')
        return record

    def _session(self, lane):
        if lane not in self.sessions:
            session = self.factory(settings=self.settings, audit_hook=self._audit(lane))
            session.bootstrap_renderer = lambda definitions, assignment, **kwargs: assignment
            session.event_renderer = _event_renderer
            self.sessions[lane] = session
        return self.sessions[lane]

    def preflight(self, lane, payload, definitions, checkpoint):
        agent.validate_input(payload)
        if checkpoint is not None:
            _verify_checkpoint(checkpoint)
        if lane != payload['session_id']:
            raise ValueError('agent lane differs from its session')
        if payload['native_tools'] != definitions:
            raise ValueError('agent input tool catalog differs from live definitions')
        delta = _suffix(payload['messages'], checkpoint, definitions)
        count, limit = get_token_count(delta), self.settings.max_prompt_tokens(1)
        if count > limit:
            raise ProjectInputBudgetError(f'agent visible input requires {count} tokens; limit is {limit}',
                input_tokens=count, input_limit=limit, capacity=self.settings.max_model_len,
                output_reserved=1, configured_output=self.settings.action_max_output_tokens,
                transport='native_delta' if checkpoint else 'native_bootstrap', input_text=delta)
        self._session(lane)

    def request(self, lane, payload, definitions, checkpoint):
        self.preflight(lane, payload, definitions, checkpoint)
        session = self._session(lane)
        decoder = build_transcript_decoder_contract(definitions) if self.constrained_decoding else None
        binding = {'role': 'agent', 'lane': lane, 'protocol': agent.PROTOCOL,
            'model': session.settings.model, 'model_sha256': session.settings.model_sha256,
            'profile': session.settings.state_profile_id, 'profile_sha256': session.settings.state_profile_sha256,
            'tools_digest': digest(definitions), 'sampling_seed': session.settings.sampling_seed,
            'transcript_protocol': TRANSCRIPT_PROTOCOL, 'tool_protocol': TOOL_PROTOCOL,
            'constrained_decoding': self.constrained_decoding,
            'decoder_digest': decoder['contract_sha256'] if decoder else None,
            'instruction_digest': digest(agent.RULES)}
        if checkpoint and checkpoint['binding'] != binding:
            raise ValueError('agent checkpoint model/protocol/tool identity mismatch')
        # Call IDs are host bookkeeping: unique by conversation position.
        id_prefix = 'call_' + str(len(payload['messages']))
        def parse(raw):
            message = parse_assistant(raw, definitions, id_prefix=id_prefix)
            command = ModelCommand('assistant', {'message': message})
            return command, ModelCommandNormalization(input_payload=message, normalized_payload=message,
                transformations=(), normalizer_version=TRANSCRIPT_PROTOCOL)
        session.command_parser_with_trace = parse
        session.command_parser = lambda raw: parse(raw)[0]
        if checkpoint:
            parent = session.import_checkpoint(checkpoint['checkpoint'])
            suffix = _suffix(payload['messages'], checkpoint, definitions)
            if checkpoint.get('needs_newline'):
                suffix = '\n' + suffix
            parent = session.append(parent, ModelEvent(event_type='transcript_append',
                event_id='PT-' + digest([payload['messages'], parent.checkpoint_id]), scope_id=lane,
                payload={'text': suffix}))
        else:
            parent = session.bootstrap(ModelLaneKind.ACTION, _suffix(payload['messages'], None, definitions),
                                       definitions, lane_id=lane)
        started = time.monotonic()
        def evidence(extra):
            return {**extra, 'usage': None, 'generation_seconds': time.monotonic() - started}
        def export(current, message=None, *, needs_newline=False):
            value = {'binding': binding, 'checkpoint': session.export(current),
                     'messages': [*payload['messages'], *([message] if message is not None else [])],
                     'needs_newline': needs_newline}
            value['identity_digest'] = digest(value)
            return value
        candidate = session.generate(parent, max_output_tokens=session.settings.action_max_output_tokens,
            json_output=False, **({'decoder': decoder} if decoder is not None else {}))
        if candidate.finish_reason == 'length':
            session.rollback(candidate, error='model output budget exhausted')
            return AgentReply({'function': 'model_output_budget_exhausted', 'params': {}}, export(parent),
                evidence({'known_budget_exhaustion': True, 'raw_generation': candidate.raw_record()}))
        try:
            command, normalization = session.parse_with_trace(candidate)
            agent.validate_references(payload, command.to_wire_dict())
            message = validate_assistant(command.arguments['message'], definitions)
            # IDs are unique across the conversation, not merely this batch.
            validate_messages([*payload['messages'], message])
        except (ValueError, TypeError, KeyError) as exc:
            session.rollback(candidate, error=str(exc))
            return AgentReply({'function': 'protocol_rejected', 'params': {'error': str(exc)}}, export(parent),
                evidence({'rejected': True, 'raw_generation': candidate.raw_record()}))
        committed = session.commit(candidate, command)
        return AgentReply(command.to_wire_dict(), export(committed, message,
                needs_newline=not candidate.raw_output.endswith('\n')),
            evidence({'raw_generation': candidate.raw_record(), 'rejected': False,
                      'normalization': normalization.to_dict() if normalization.changed else None}))
