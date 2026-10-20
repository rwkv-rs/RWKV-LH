"""Opt-in CC-view runtime; production ProjectRuntime and sessions are unchanged."""
from copy import deepcopy
from dataclasses import asdict
import json
from uuid import uuid4

from . import cc_view_experiment as cc
from .cc_view_decoder import build_decoder
from .model_io import ModelCommand
from .model_session import create_model_session, InputBudgetError
from .project_contracts import digest
from .project_deadline import project_deadline
from .project_protocols import executor
from .project_runtime import ProjectRuntime, RoleReply
from .project_action_feedback import render_result
from .schema import ModelLaneKind, ModelEvent
from .token_budget import get_token_count


def turn_command(turn):
    return {'function': 'cc_view_turn', 'params': {'think': turn.think,
            'calls': [[name, args] for name, args in turn.calls], 'summary': turn.summary,
            **({'narration':turn.narration} if turn.narration.strip() else {})}}


class CCViewSessions:
    """The same Native State transport with the experimental renderer and parser."""
    def __init__(self, settings, directory, *, session_factory=create_model_session):
        from pathlib import Path
        self.settings, self.factory = settings, session_factory
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.sessions = {}

    def _audit(self, role, lane):
        def record(event):
            with (self.directory / 'model_trace.jsonl').open('a') as stream:
                stream.write(json.dumps({'project_role': role, 'project_lane': lane,
                    'input_protocol': cc.PROTOCOL, **event}, ensure_ascii=False) + '\n')
        return record

    def preflight(self, role, lane, payload, definitions, checkpoint):
        if role != 'executor' or payload['protocol'] != cc.PROTOCOL:
            raise ValueError('CC experiment requires a frozen plan and its own protocol')
        if get_token_count(payload['text']) > self.settings.max_prompt_tokens(1):
            raise InputBudgetError('CC-view Native input delta exceeds the unchanged deployment capacity')
        if lane not in self.sessions:
            self.sessions[lane] = self.factory(settings=self.settings, audit_hook=self._audit(role, lane))

    def request(self, role, lane, payload, definitions, checkpoint):
        self.preflight(role, lane, payload, definitions, checkpoint)
        session = self.sessions[lane]
        def parse(raw):
            command = turn_command(cc.parse_output(raw, definitions))
            return ModelCommand(command['function'], command['params'])
        session.command_parser = parse
        binding = {'protocol': cc.PROTOCOL, 'tools_digest': digest(definitions),
                   'settings': asdict(self.settings)}
        if checkpoint:
            if checkpoint['binding'] != binding:
                raise ValueError('CC-view checkpoint identity changed')
            previous = session.import_checkpoint(checkpoint['checkpoint'])
            session.event_renderer = lambda *args, **kwargs: payload['text']
            parent = session.append(previous, ModelEvent(event_type='cc_tool_results',
                event_id='CC-' + uuid4().hex, scope_id=lane, payload={}))
        else:
            session.bootstrap_renderer = lambda *args, **kwargs: payload['text']
            parent = session.bootstrap(ModelLaneKind.ACTION, '', definitions, lane_id=lane)
        candidate = session.generate(parent, max_output_tokens=self.settings.action_max_output_tokens,
                                     decoder=build_decoder(definitions))
        checkpoint_value = lambda current: {'binding': binding, 'checkpoint': session.export(current)}
        if candidate.finish_reason == 'length':
            session.rollback(candidate, error='model output budget exhausted')
            return RoleReply({'function': 'model_output_budget_exhausted', 'params': {}}, checkpoint_value(parent),
                             {'known_budget_exhaustion': True, 'raw_generation': candidate.raw_record()})
        try:
            turn = cc.parse_output(candidate.raw_output, definitions)
        except (ValueError, TypeError, KeyError) as exc:
            session.rollback(candidate, error=str(exc))
            return RoleReply({'function': 'protocol_rejected', 'params': {'error': str(exc)}}, checkpoint_value(parent),
                             {'rejected': True, 'raw_generation': candidate.raw_record()})
        command = turn_command(turn)
        committed = session.commit(candidate, ModelCommand(command['function'], command['params']))
        return RoleReply(command, checkpoint_value(committed),
                         {'rejected': False, 'raw_generation': candidate.raw_record()})


class _UnionScopeLedger:
    """Read-time permission policy only; never mutate the installed frozen plan."""
    def __init__(self, original):
        self.original = original

    def __getattr__(self, key):
        return getattr(self.original, key)

    def state(self):
        state = self.original.state()
        scope = cc.union_scope(state['plan'])
        for task in state['plan']['tasks']:
            task['scope'] = deepcopy(scope)
        return state


class CCViewRuntime(ProjectRuntime):
    """Reuse the production loop, isolation, transaction ledger and real receipts."""
    def __init__(self, ledger, roles, *, harness=None, background=True):
        super().__init__(ledger, roles, harness=harness)
        state = ledger.state()
        if state['plan'] is None or state['calls'] or state['sessions']:
            raise ValueError('CC-view starts fresh from an installed frozen plan')
        self.todos = cc.Todos(state['plan']['tasks'])
        self.results_to_deliver = []
        self.bootstrap_pending = True
        self.definitions = cc.tool_definitions(self.harness.g1i_tool_definitions(),background=background)
        from .cc_view_tools import install
        from .cc_view_jobs import Jobs
        self.jobs=Jobs(self.db.root/'cc_jobs') if background else None
        install(self.harness,jobs=self.jobs)

    def run(self, **kwargs):
        try:
            return super().run(**kwargs)
        finally:
            if self.jobs is not None:
                self.jobs.close()

    def _request(self):
        state = self.db.state()
        lane = state['active']['id']
        remaining = self.remaining()
        remaining = {'calls': remaining['calls'], 'seconds': int(remaining['seconds'])}
        if self.bootstrap_pending:
            original = executor.build_input(state['active'], project_state=state, remaining=remaining)
            rendered = cc.build_input(definitions=self.definitions, context=cc.context_from_payload(original),
                                      todos=self.todos.visible(), remaining=remaining)
        else:
            if not self.results_to_deliver:
                feedback = state.get('feedback') or {}
                self.results_to_deliver.append(json.dumps(feedback, ensure_ascii=False))
            rendered = cc.build_input(definitions=self.definitions, tool_results=self.results_to_deliver,
                                      remaining=remaining)
        payload = {'protocol': cc.PROTOCOL, 'text': rendered}
        preflight = getattr(self.roles, 'preflight', None)
        if preflight:
            preflight('executor', lane, payload, self.definitions, state['sessions'].get(lane))
        self.db.update('call_reserved', lambda s: s.update(calls=s['calls'] + 1))
        identifier = self.db.begin_operation('model', {'role': 'executor', 'lane': lane,
            'input': payload, 'input_digest': digest(payload), 'plan_version': state['plan_version']})
        if state.get('record_generation_snapshots', False):
            from .project_generation_snapshots import capture_snapshot
            capture_snapshot(self.db, identifier)
        reply = self.roles.request('executor', lane, payload, self.definitions, state['sessions'].get(lane))
        def change(s):
            s['sessions'][lane] = reply.checkpoint
            s['inbox'] = {'role': 'executor', 'lane': lane, 'command': reply.command,
                'operation_id': identifier, 'plan_version': s['plan_version']}
        self.db.finish_operation(identifier, {'command': reply.command, 'evidence': reply.evidence}, mutate=change)
        self.bootstrap_pending = False
        self.results_to_deliver = []

    def _tool(self, name, params, lane, step_id):
        original = self.db
        try:
            self.db = _UnionScopeLedger(original)
            # Native transaction permissions use the union scope. The model's
            # todo attribution is recorded independently and never gates a tool.
            actual = self.db.state()['plan']['tasks']
            permitted_step = step_id if any(t['id']==step_id for t in actual) else actual[0]['id']
            return super()._tool(name, params, lane, permitted_step)
        finally:
            self.db = original

    def _consume(self):
        state = self.db.state()
        inbox = state['inbox']
        if inbox['command']['function'] != 'cc_view_turn':
            return super()._consume()
        source = inbox['operation_id']
        receipt = state['evidence'][source]
        raw = receipt['result']['evidence']['raw_generation']['raw_output']
        turn = cc.parse_output(raw, self.definitions)
        if turn_command(turn) != inbox['command']:
            raise ValueError('CC parsed actions differ from the recorded model output')
        if turn.summary is not None:
            self.db.finish_work(outcome='finished', summary=turn.summary, receipt_ids=[])
            return
        for index, (name, arguments) in enumerate(turn.calls):
            try:
                if name.startswith('Task'):
                    result = self.todos.execute(name, arguments)
                    self.db.update('cc_todo_result', lambda s: s.update(feedback={
                        'kind': 'cc_todo_result', 'source_operation_id': source, 'call_index': index,
                        'name': name, 'arguments': arguments, 'result': result}))
                elif name=='Read' and 'receipt_id' in arguments:
                    if set(arguments)!={'receipt_id'}:
                        raise ValueError('Read selects either a file or a receipt, not both')
                    from .project_receipt_refs import build_bindings
                    from .project_evidence import executor_evidence_ids
                    current=self.db.state()
                    bindings=build_bindings(current,executor_evidence_ids(current))
                    if arguments['receipt_id'] not in bindings:
                        raise ValueError('Unknown receipt for this run')
                    identifier=bindings[arguments['receipt_id']]
                    self.expand_evidence(identifier,executor_lane=inbox['lane'])
                    reference=self.db.state()['evidence'][identifier]['result']['raw_receipt']
                    body=json.loads((self.db.root/reference['path']).read_text())
                    if digest(body)!=reference['content_digest']:
                        raise ValueError('Receipt content changed')
                    result=render_result(body)
                else:
                    from .cc_view_tools import native_call
                    attribution=self.todos.active_step()
                    execution_step=(self.db.state()['plan']['tasks'][0]['id']
                                    if attribution=='unassigned' else attribution)
                    command = native_call(name, arguments, execution_step,
                        job_authority=cc.union_scope(self.db.state()['plan'])[0])
                    def select(s):
                        s['inbox'] = {**inbox, 'command': command, 'cc_call_index': index}
                        s['inbox']['cc_todo_attribution']=attribution
                    self.db.update('cc_call_selected', select)
                    params = command['params']
                    self._tool(params['tool'], params['arguments'], inbox['lane'], params['step_id'])
                    after = self.db.state()
                    identifier = after['feedback']['evidence_id']
                    raw_receipt = after['evidence'][identifier]['result']['raw_receipt']
                    body = json.loads((self.db.root / raw_receipt['path']).read_text())
                    result = render_result(body)
                self.results_to_deliver.append(result)
            except (ValueError, KeyError, TypeError) as exc:
                if self.db.state()['pending']:
                    raise
                # A real rejected operation, returned verbatim; no retry or parameter repair.
                result = str(exc)
                self.results_to_deliver.append(result)
                self.db.update('cc_call_rejected', lambda s: s.update(feedback={
                    'kind': 'cc_call_rejected', 'source_operation_id': source, 'call_index': index,
                    'name': name, 'arguments': arguments, 'error': result}))
        self.db.update('cc_turn_consumed', lambda s: s.update(inbox=None))
