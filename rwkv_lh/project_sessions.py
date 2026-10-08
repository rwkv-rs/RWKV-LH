"""Role-isolated Native RWKV and audited strong transport for project contracts."""
from dataclasses import replace
from functools import partial
import json
import os
from pathlib import Path

from .model_session import ModelSession, InputBudgetError, create_model_session
from .model_io import canonical_json, render_bootstrap
from .project_model_io import (render_project_event_append, parse_project_model_command,
                               parse_project_model_command_with_trace,
                               render_project_assignment, project_prompt_identity)
from .schema import ModelLaneKind, ModelEvent
from .runtime.settings import RuntimeSettings, direct_agent_settings
from .runtime.role_config import role_int
from .strong_session import StrongCompletion, StrongModelSession, KnownStrongOutputBudgetExpired
from .supervisor_openai import SupervisorAPISettings
from .project_runtime import RoleReply
from .project_contracts import digest
from .project_protocols import planner, decision, executor
from .project_output_validation import normalize_role_output, validate_role_output
from .project_format_adapter import FORMAT_ADAPTER_VERSION, parse_role_call, rejected_call_definition
from .token_budget import get_token_count
from .project_input_delta import INPUT_HANDOFF_VERSION, input_update, seal_input_state
from .project_decoder import build_role_decoder, available_definitions, tool_menu_update, INPUT_FRAMING, BOUNDARY_POLICY


class ProjectInputBudgetError(InputBudgetError):
    def __init__(self, message, *, input_tokens, input_limit, capacity, output_reserved,
                 configured_output, transport, **original_input):
        super().__init__(message)
        import hashlib
        from .token_budget import VOCAB_PATH
        self.input_budget_evidence = {
            'input_tokens': input_tokens, 'input_limit': input_limit,
            'capacity': capacity, 'output_reserved': output_reserved,
            'configured_output': configured_output, 'transport': transport,
            'estimator': 'rwkv_lh.token_budget.get_token_count',
            'tokenizer_sha256': hashlib.sha256(VOCAB_PATH.read_bytes()).hexdigest(),
            **original_input}


class ProjectSessions:
    def __init__(self, settings, directory, *, session_factory=create_model_session,
                 strong_settings=None, max_calls=128, decision_settings=None,
                 constrained_decoding=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.settings = direct_agent_settings(RuntimeSettings.for_role('project_executor', fallback=settings))
        self.decision_settings = decision_settings or direct_agent_settings(
            RuntimeSettings.for_role('project_decision', fallback=settings))
        self.factory = session_factory
        self.strong_settings = strong_settings
        # Explicit deployment capacity, not a prompt/plan/evidence truncation rule.
        self.planner_context_tokens = role_int('project_planner', 'max_model_len', default=65536)
        self.max_calls = max_calls
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
        if lane in self.sessions:
            return self.sessions[lane]
        if role == 'planner':
            strong = self.strong_settings or SupervisorAPISettings.from_env()
            strong = replace(strong, retry_attempts=1, semantic_repair_attempts=0,
                             plan_cache_enabled=False)
            phase = 'project_plan_review' if lane.startswith(('plan-review-', 'check-review-')) else 'project_planning'
            output_tokens = strong.max_review_tokens if phase == 'project_plan_review' else strong.max_plan_tokens
            if self.planner_context_tokens <= output_tokens + 33:
                raise ValueError('Project Planner context must exceed reserved output and safety margin')
            local = RuntimeSettings(base_url='http://unused.invalid', api_key='', model=strong.model,
                state_transport='prompt_replay', tool_disclosure_mode='full', max_model_len=self.planner_context_tokens,
                state_profile_id='', state_profile_sha256='', action_max_output_tokens=output_tokens)
            session = StrongModelSession(StrongCompletion(strong, self.directory, self.max_calls, phase=phase),
                                   settings=local, audit_hook=self._audit(role, lane))
        else:
            selected = self.decision_settings if role == 'decision' else self.settings
            session = self.factory(settings=selected, audit_hook=self._audit(role, lane))
        session.event_renderer = render_project_event_append
        session.command_parser = parse_project_model_command
        session.command_parser_with_trace = parse_project_model_command_with_trace
        self.sessions[lane] = session
        return session

    def preflight(self, role, lane, payload, definitions, checkpoint):
        """Check input capacity and read-only setup before reserving model work."""
        module = {'planner': planner, 'decision': decision, 'executor': executor}[role]
        module.validate_input(payload)
        if role == 'planner':
            session = self._session(role, lane)
            limit = session.settings.max_prompt_tokens(session.settings.action_max_output_tokens)
            if isinstance(session.client, StrongCompletion):
                session.client.input_builder = lambda: planner.chat_input(payload, definitions)
                session.client.tools_builder = lambda: planner.available_definitions(payload, definitions)
            rendered = render_bootstrap(definitions, canonical_json(payload))
            wire = (session.client.wire_request(rendered, session.settings.action_max_output_tokens)
                    if isinstance(session.client, StrongCompletion) else None)
            count = (get_token_count(canonical_json(wire['body'])) if wire is not None
                     else session.generation_input_tokens(rendered, session.settings.action_max_output_tokens))
            if count > limit:
                raise ProjectInputBudgetError(f'planner visible wire input estimate requires {count} tokens; limit is {limit}; '
                    f'max_model_len={session.settings.max_model_len}, output_tokens={session.settings.action_max_output_tokens}',
                    input_tokens=count, input_limit=limit, capacity=session.settings.max_model_len,
                    output_reserved=session.settings.action_max_output_tokens,
                    configured_output=session.settings.action_max_output_tokens,
                    transport='planner_chat', wire_request=wire)
            return
        selected = self.decision_settings if role == 'decision' else self.settings
        if checkpoint:
            parent, event, retry = input_update(role, lane, payload, checkpoint)
            delta = render_project_event_append(event, previous_transcript=parent['transcript'],
                close_generation_anchor=self.constrained_decoding,
                tool_update=tool_menu_update(definitions, role=role, payload=payload, checkpoint=checkpoint, retry=retry))
        else:
            delta = render_bootstrap(available_definitions(definitions, role=role, payload=payload), render_project_assignment(payload))
        count = get_token_count(delta)
        limit = selected.max_prompt_tokens(1)
        if count > limit:
            raise ProjectInputBudgetError(f'{role} Native input delta requires {count} tokens; limit is {limit}',
                input_tokens=count, input_limit=limit, capacity=selected.max_model_len, output_reserved=1,
                configured_output=selected.action_max_output_tokens,
                transport='native_delta' if checkpoint else 'native_bootstrap', input_text=delta)
        self._session(role, lane)

    def request(self, role, lane, payload, definitions, checkpoint):
        self.preflight(role, lane, payload, definitions, checkpoint)
        module = {'planner': planner, 'decision': decision, 'executor': executor}[role]
        session = self._session(role, lane)
        if role == 'planner' and isinstance(session.client, StrongCompletion):
            session.client.input_builder = lambda: planner.chat_input(payload, definitions)
            session.client.tools_builder = lambda: planner.available_definitions(payload, definitions)
            session.client.audit({'type': 'project_planner_input', 'lane': lane,
                'input_protocol': planner.PROTOCOL, 'input_digest': digest(payload),
                'tools_digest': digest(definitions), 'chat_input_digest': digest(planner.chat_input(payload, definitions))})
        # Use one role-aware framing adapter at every call. It retains the raw
        # output and never chooses a Decision direction or accepts a plan.
        session.command_parser_with_trace = lambda raw: parse_role_call(raw, role=role, payload=payload)
        session.command_parser = lambda raw: session.command_parser_with_trace(raw)[0]
        decoder = (build_role_decoder(definitions, role=role, payload=payload)
                   if role != 'planner' and self.constrained_decoding else None)
        session.event_renderer = partial(render_project_event_append,
                                         close_generation_anchor=decoder is not None)
        binding = {'role': role, 'lane': lane, 'protocol': module.PROTOCOL,
            'call_format': FORMAT_ADAPTER_VERSION,
            'model': session.settings.model, 'model_sha256': session.settings.model_sha256,
            'profile': session.settings.state_profile_id, 'profile_sha256': session.settings.state_profile_sha256,
            'tools_digest': digest(definitions), 'sampling_seed': session.settings.sampling_seed}
        if role == 'planner':
            from .strong_structured_output import build_tool_contract
            # Mode and installed-plan changes select a different per-call menu,
            # not a different role identity. StrongCompletion audits the actual
            # request contract separately; checkpoint restoration binds the catalog.
            binding['strong_decoder_catalog_sha256'] = build_tool_contract(definitions)['contract_sha256']
            binding['prompt_identity'] = digest({'layout': planner.CHAT_LAYOUT_VERSION,
                'instructions': planner.INSTRUCTIONS})
        if role != 'planner':
            binding['input_handoff'] = INPUT_HANDOFF_VERSION
            binding['prompt_identity'] = project_prompt_identity(role)
            if decoder is not None:
                binding['decoder_catalog_sha256'] = build_role_decoder(definitions)['contract_sha256']
                binding['decoder_boundary_policy'] = BOUNDARY_POLICY
                binding['decoder_input_framing'] = INPUT_FRAMING
        retry = False
        if checkpoint:
            if checkpoint['binding'] != binding:
                raise ValueError('role checkpoint model/protocol/tool identity mismatch')
            if role == 'planner':
                session.import_checkpoint(checkpoint['checkpoint'])
                # The complete planner input already carries the current plan, feedback,
                # evidence and workspace. Replaying prior full snapshots makes retries
                # grow with the number of attempts and can block before RWKV runs.
                parent = session.bootstrap(ModelLaneKind.ACTION, canonical_json(payload), definitions, lane_id=lane)
            else:
                selected_parent, event, retry = input_update(role, lane, payload, checkpoint)
                session.event_renderer = partial(render_project_event_append, close_generation_anchor=decoder is not None,
                    tool_update=tool_menu_update(definitions, role=role, payload=payload, checkpoint=checkpoint, retry=retry))
                previous = session.import_checkpoint(selected_parent)
                parent = session.append(previous, event)
        else:
            visible = definitions if role == 'planner' else available_definitions(definitions, role=role, payload=payload)
            parent = session.bootstrap(ModelLaneKind.ACTION, render_project_assignment(payload), visible, lane_id=lane)
        def export_checkpoint(current, *, rejected):
            value = {'binding': binding, 'checkpoint': session.export(current)}
            if role != 'planner':
                anchor = checkpoint['input_state'] if retry else None
                value['input_state'] = seal_input_state(payload,
                    anchor['anchor_input'] if anchor else payload,
                    anchor['anchor_checkpoint'] if anchor else session.export(parent), rejected=rejected)
            return value

        output_limit = session.settings.action_max_output_tokens
        def budget_reply(evidence):
            return RoleReply({'function': 'model_output_budget_exhausted', 'params': {}},
                export_checkpoint(parent, rejected=True),
                {'known_budget_exhaustion': True, **evidence})
        try:
            candidate = session.generate(parent, max_output_tokens=output_limit,
                                         **({'decoder': decoder} if decoder is not None else {}))
        except KnownStrongOutputBudgetExpired as exc:
            return budget_reply({'provider_response': exc.provider_response})
        if candidate.finish_reason == 'length':
            session.rollback(candidate, error='model output budget exhausted')
            return budget_reply({'raw_generation': candidate.raw_record()})
        normalization = None
        parameter_normalization = None
        command = None
        try:
            command, normalization = session.parse_with_trace(candidate)
            accepted, parameter_normalization = normalize_role_output(role, command, definitions)
            validate_role_output(role, payload, accepted, definitions)
        except (ValueError, TypeError, KeyError) as exc:
            session.rollback(candidate, error=str(exc))
            # This is contract disclosure, not parser recovery: command stays None
            # when parsing failed, and the rejected generation is never committed.
            rejected_definition = rejected_call_definition(
                candidate.raw_record()['raw_output'], definitions, command=command)
            # A returned invalid generation is known, not an unknown provider call.
            return RoleReply({'function': 'protocol_rejected', 'params': {'error': str(exc)}},
                export_checkpoint(parent, rejected=True),
                {'raw_generation': candidate.raw_record(), 'rejected': True,
                 'rejected_command': command.to_wire_dict() if command is not None else None,
                 'rejected_function_name': rejected_definition['name'] if rejected_definition else None,
                 'rejected_parameter_schema': rejected_definition['parameters'] if rejected_definition else None,
                 'normalization': normalization.to_dict() if normalization and normalization.changed else None,
                 'parameter_normalization': parameter_normalization})
        committed = session.commit(candidate, command)
        return RoleReply(accepted.to_wire_dict(), export_checkpoint(committed, rejected=False),
                         {'raw_generation': candidate.raw_record(), 'rejected': False,
                          'normalization': normalization.to_dict() if normalization and normalization.changed else None,
                          'parameter_normalization': parameter_normalization})
