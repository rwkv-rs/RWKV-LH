"""Work-order Planner requests and one durable native Executor conversation."""
from dataclasses import replace
import json
import os
from pathlib import Path
import time

from .model_session import InputBudgetError, create_model_session
from .model_io import ModelCommand, ModelCommandNormalization, canonical_json, render_bootstrap
from .schema import ModelLaneKind, ModelEvent
from .runtime.settings import RuntimeSettings, direct_agent_settings
from .runtime.role_config import role_int
from .runtime.structured_output import build_transcript_decoder_contract
from .strong_session import StrongCompletion, StrongModelSession, KnownStrongOutputBudgetExpired
from .project_planner_settings import ProjectPlannerSettings
from .project_runtime import RoleReply
from .project_contracts import digest, fields
from .project_protocols import planner, executor
from .project_output_validation import validate_role_output
from .project_model_io import parse_role_call
from .token_budget import get_token_count
from .transcript.parse import parse_assistant, validate_messages
from .transcript.render import PROTOCOL as TRANSCRIPT_PROTOCOL, render_message, render_turns
from .transcript.tools import TOOL_PROTOCOL


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


def _suffix(messages, checkpoint):
    validate_messages(messages, allow_pending=False)
    if checkpoint is None:
        return ''.join(render_turns(messages))
    old = checkpoint.get('messages')
    if not isinstance(old, list) or messages[:len(old)] != old:
        raise ValueError('Executor conversation changed before its committed State boundary')
    # Validate the complete conversation before rendering a tool-only suffix.
    return ''.join(render_message(message) + '\n' for message in messages[len(old):])


def _event_renderer(event, visible_definitions=(), **kwargs):
    return event.payload['text']


def _verify_checkpoint(checkpoint, role):
    keys = ('binding', 'checkpoint', 'identity_digest')
    if role == 'executor':
        keys += ('messages', 'needs_newline')
    fields(checkpoint, keys)
    if role == 'executor' and type(checkpoint['needs_newline']) is not bool:
        raise ValueError('Executor checkpoint newline identity must be boolean')
    if checkpoint['identity_digest'] != digest({key: value for key, value in checkpoint.items()
                                               if key != 'identity_digest'}):
        raise ValueError('role checkpoint metadata identity mismatch')


class ProjectSessions:
    def __init__(self, settings, directory, *, session_factory=create_model_session,
                 strong_settings=None, max_calls=128, constrained_decoding=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.settings = direct_agent_settings(RuntimeSettings.for_role('project_executor', fallback=settings))
        self.factory, self.strong_settings, self.max_calls = session_factory, strong_settings, max_calls
        self.planner_context_tokens = role_int('project_planner', 'max_model_len', default=65536)
        self.sessions = {}
        if constrained_decoding is None:
            mode = os.getenv('RWKV_LH_PROJECT_CONSTRAINED_DECODING', 'on')
            if mode not in ('on', 'off'):
                raise ValueError('RWKV_LH_PROJECT_CONSTRAINED_DECODING must be on or off')
            constrained_decoding = mode == 'on'
        if type(constrained_decoding) is not bool:
            raise ValueError('constrained_decoding must be boolean')
        self.constrained_decoding = constrained_decoding

    def _audit(self, role, lane):
        def record(event):
            with (self.directory / 'model_trace.jsonl').open('a') as stream:
                stream.write(json.dumps({'project_role': role, 'project_lane': lane,
                    **event}, ensure_ascii=False) + '\n')
        return record

    def _session(self, role, lane):
        if role not in ('planner', 'executor'):
            raise ValueError('only Planner and Executor sessions are supported')
        if lane in self.sessions:
            return self.sessions[lane]
        if role == 'planner':
            strong = replace(self.strong_settings or ProjectPlannerSettings.from_env(), retry_attempts=1)
            output_tokens = strong.max_plan_tokens
            if self.planner_context_tokens <= output_tokens + 33:
                raise ValueError('Project Planner context must exceed reserved output and safety margin')
            local = RuntimeSettings(base_url='http://unused.invalid', api_key='', model=strong.model,
                state_transport='prompt_replay', tool_disclosure_mode='full', max_model_len=self.planner_context_tokens,
                state_profile_id='', state_profile_sha256='', action_max_output_tokens=output_tokens)
            session = StrongModelSession(StrongCompletion(strong, self.directory, self.max_calls, phase='project_planning'),
                                         settings=local, audit_hook=self._audit(role, lane))
        else:
            session = self.factory(settings=self.settings, audit_hook=self._audit(role, lane))
            session.bootstrap_renderer = lambda definitions, assignment, **kwargs: assignment
            session.event_renderer = _event_renderer
        self.sessions[lane] = session
        return session

    def _planner_wire(self, session, payload, definitions):
        session.client.input_builder = lambda: planner.chat_input(payload, definitions)
        session.client.tools_builder = lambda: planner.available_definitions(payload, definitions)
        rendered = render_bootstrap(definitions, canonical_json(payload))
        return rendered, session.client.wire_request(rendered, session.settings.action_max_output_tokens)

    def preflight(self, role, lane, payload, definitions, checkpoint):
        {'planner': planner, 'executor': executor}[role].validate_input(payload)
        if checkpoint is not None:
            _verify_checkpoint(checkpoint, role)
        if role == 'executor' and lane != payload['assignment']['id']:
            raise ValueError('Executor lane differs from its persistent assignment')
        if role == 'planner':
            session = self._session(role, lane)
            _, wire = self._planner_wire(session, payload, definitions)
            count = get_token_count(canonical_json(wire['body']))
            selected = session.settings
            reserved = selected.action_max_output_tokens
            original = {'wire_request': wire}
            transport = 'planner_chat'
        else:
            if payload['native_tools'] != definitions:
                raise ValueError('Executor input tool catalog differs from live definitions')
            delta = _suffix(payload['messages'], checkpoint)
            selected, reserved = self.settings, 1
            count, original = get_token_count(delta), {'input_text': delta}
            transport = 'native_delta' if checkpoint else 'native_bootstrap'
        limit = selected.max_prompt_tokens(reserved)
        if count > limit:
            raise ProjectInputBudgetError(f'{role} visible input requires {count} tokens; limit is {limit}',
                input_tokens=count, input_limit=limit, capacity=selected.max_model_len,
                output_reserved=reserved, configured_output=selected.action_max_output_tokens,
                transport=transport, **original)
        self._session(role, lane)

    def request(self, role, lane, payload, definitions, checkpoint):
        self.preflight(role, lane, payload, definitions, checkpoint)
        session = self._session(role, lane)
        module = {'planner': planner, 'executor': executor}[role]
        binding = {'role': role, 'lane': lane, 'protocol': module.PROTOCOL,
            'model': session.settings.model, 'model_sha256': session.settings.model_sha256,
            'profile': session.settings.state_profile_id, 'profile_sha256': session.settings.state_profile_sha256,
            'tools_digest': digest(definitions), 'sampling_seed': session.settings.sampling_seed,
            'transcript_protocol': TRANSCRIPT_PROTOCOL, 'tool_protocol': TOOL_PROTOCOL,
            'constrained_decoding': self.constrained_decoding if role == 'executor' else None}
        decoder = None
        if role == 'executor':
            binding['assignment_digest'] = digest(payload['assignment'])
            decoder = build_transcript_decoder_contract(definitions) if self.constrained_decoding else None
            binding['decoder_digest'] = decoder['contract_sha256'] if decoder else None
            binding['instruction_digest'] = digest(executor.RULES)
            def parse(raw):
                message = parse_assistant(raw, definitions)
                command = ModelCommand('assistant', {'message': message})
                return command, ModelCommandNormalization(input_payload=message, normalized_payload=message,
                    transformations=(), normalizer_version=TRANSCRIPT_PROTOCOL)
        else:
            binding['instruction_digest'] = digest(planner.INSTRUCTIONS)
            parse = lambda raw: parse_role_call(raw, role=role, payload=payload)
        session.command_parser_with_trace = parse
        session.command_parser = lambda raw: parse(raw)[0]
        if checkpoint and checkpoint['binding'] != binding:
            raise ValueError('role checkpoint model/protocol/tool identity mismatch')
        if role == 'planner':
            rendered, _ = self._planner_wire(session, payload, definitions)
            # Each Planner request contains the complete compact order/report list.
            # Its transport replay never changes the Executor lane or State.
            parent = session.bootstrap(ModelLaneKind.ACTION, canonical_json(payload), definitions, lane_id=lane)
        elif checkpoint:
            parent = session.import_checkpoint(checkpoint['checkpoint'])
            suffix = _suffix(payload['messages'], checkpoint)
            if suffix:
                if checkpoint.get('needs_newline'):
                    suffix = '\n' + suffix
                parent = session.append(parent, ModelEvent(event_type='transcript_append',
                    event_id='PT-' + digest([payload['messages'], parent.checkpoint_id]), scope_id=lane,
                    payload={'text': suffix}))
        else:
            rendered = _suffix(payload['messages'], None)
            parent = session.bootstrap(ModelLaneKind.ACTION, rendered, definitions, lane_id=lane)
        started = time.monotonic()
        event_start = len(session.client.events) if role == 'planner' else 0
        def evidence(extra):
            usage = None
            if role == 'planner':
                envelopes = [e for e in session.client.events[event_start:]
                             if e.get('type') == 'supervisor_response_envelope_received']
                if len(envelopes) == 1:
                    raw_usage = envelopes[0]['raw_response'].get('usage', {})
                    usage = {'input_tokens': raw_usage.get('prompt_tokens'),
                             'output_tokens': raw_usage.get('completion_tokens'), 'source': 'provider_usage'}
            return {**extra, 'usage': usage, 'generation_seconds': time.monotonic() - started}
        def export(current, message=None, *, needs_newline=False):
            value = {'binding': binding, 'checkpoint': session.export(current),
                **({'messages': [*payload['messages'], *([message] if message is not None else [])],
                    'needs_newline': needs_newline} if role == 'executor' else {})}
            value['identity_digest'] = digest(value)
            return value
        try:
            candidate = session.generate(parent, max_output_tokens=session.settings.action_max_output_tokens,
                json_output=False, **({'decoder': decoder} if decoder is not None else {}))
        except KnownStrongOutputBudgetExpired as exc:
            return RoleReply({'function': 'model_output_budget_exhausted', 'params': {}}, export(parent),
                evidence({'known_budget_exhaustion': True, 'provider_response': exc.provider_response}))
        if candidate.finish_reason == 'length':
            session.rollback(candidate, error='model output budget exhausted')
            return RoleReply({'function': 'model_output_budget_exhausted', 'params': {}}, export(parent),
                evidence({'known_budget_exhaustion': True, 'raw_generation': candidate.raw_record()}))
        try:
            command, normalization = session.parse_with_trace(candidate)
            validate_role_output(role, payload, command, definitions)
            if role == 'executor':
                # IDs are unique across the conversation, not merely this batch.
                validate_messages([*payload['messages'], command.arguments['message']])
        except (ValueError, TypeError, KeyError) as exc:
            session.rollback(candidate, error=str(exc))
            return RoleReply({'function': 'protocol_rejected', 'params': {'error': str(exc)}}, export(parent),
                evidence({'rejected': True, 'raw_generation': candidate.raw_record()}))
        committed = session.commit(candidate, command)
        message = command.arguments['message'] if role == 'executor' else None
        return RoleReply(command.to_wire_dict(), export(committed, message,
                needs_newline=not candidate.raw_output.endswith('\n')),
            evidence({'raw_generation': candidate.raw_record(), 'rejected': False,
                      'normalization': normalization.to_dict() if normalization.changed else None}))
