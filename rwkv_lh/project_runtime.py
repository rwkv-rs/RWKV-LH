"""The single-agent loop: one RWKV conversation, one persistent State, transactional tools.

Each model turn is validated as a whole before any effect; its calls then run in
order in an isolated copy and are published only within the session write
permissions. ``finish_work`` records the agent's declaration for the current
user request. The host never judges correctness, rewrites model output or
writes task text; a follow-up request continues the same conversation.
"""
from dataclasses import dataclass
from copy import deepcopy
import json
import shutil
import time

from .project_contracts import digest, fields, text
from .project_ledger import UncertainOperation
from .project_protocols import agent
from .harness import ActionHarness, ActionResult, HarnessError, UncertainToolOutcome
from .project_tools import configure_project_tools
from .project_workspace import explicit_write_targets, violations as write_violations, publish_workspace
from .schema import GoalState, TaskAction
from .workspace_snapshot import tree_identity, copy_verified_workspace, invalid_entries
from .transcript.render import tool_result
from .transcript.parse import validate_assistant, validate_messages, loads
from .transcript.tools import native_call
from .job_budget import WallDeadlineExpired
from .project_deadline import project_deadline
from .model_session import InputBudgetError

ARCHITECTURE = 'rwkv-lh.coder.architecture.v3'
BUDGET_REASONS = ('resource_budget_exhausted', 'wall_budget_exhausted',
                  'model_output_budget_exhausted', 'model_input_budget_exhausted')


@dataclass(frozen=True)
class AgentReply:
    command: dict
    checkpoint: dict
    evidence: dict


SCOPE_VIOLATION_LIMIT = 20


def violation_summary(paths, limit=SCOPE_VIOLATION_LIMIT):
    """Bounded view of rejected paths; the transaction directory keeps every path.

    One install can create thousands of entries. Past the limit, group by the
    top-level segment with a count so the observation stays within one input.
    """
    paths = sorted(paths)
    if len(paths) <= limit:
        return paths
    groups = {}
    for path in paths:
        groups.setdefault(path.split('/', 1)[0], []).append(path)
    items = [members[0] if len(members) == 1 else f'{top}/** ({len(members)} paths)'
             for top, members in groups.items()]
    return items if len(items) <= limit else [*items[:limit], f'... {len(items) - limit} more top-level paths']


def violation_record(transaction, violations, entry_errors=None):
    """Receipt metadata for a rejected write; full lists go to the transaction directory.

    Raw receipt bodies are delivered to the agent, so they carry only the
    bounded summary and a count, never the unbounded path list nor the
    operation-specific location of the full record.
    """
    entry_errors = entry_errors or {}
    (transaction / 'scope_violation_paths.json').write_text(
        json.dumps({'paths': violations, 'entry_errors': entry_errors}, ensure_ascii=False, indent=2) + '\n')
    return {'scope_violation': violation_summary(violations), 'scope_violation_count': len(violations),
            'workspace_entry_errors': dict(sorted(entry_errors.items())[:SCOPE_VIOLATION_LIMIT])}


def agent_definitions(harness):
    """The frozen nine-tool catalog: eight Harness tools plus finish_work."""
    configure_project_tools(harness)
    return agent.action_definitions(harness.g1i_tool_definitions())


class ProjectRuntime:
    def __init__(self, ledger, agent_port, *, harness=None):
        self.db, self.agent = ledger, agent_port
        self.harness = configure_project_tools(harness or ActionHarness())
        self.started = None
        self.initial_elapsed = 0.0
        self._pending_background = {}

    def remaining(self):
        s = self.db.state()
        elapsed = self.initial_elapsed + time.monotonic() - self.started if self.started is not None else s['elapsed']
        return {'calls': None if s['max_calls'] is None else max(0, s['max_calls'] - s['calls']),
                'seconds': None if s['max_seconds'] is None else max(0.0, s['max_seconds'] - elapsed)}

    def _reject(self, error):
        """A turn the host could not accept: rolled back, recorded, and told to the agent."""
        def change(s):
            inbox = s['inbox']
            receipt = s['evidence'].get(inbox['operation_id'], {})
            raw = receipt.get('result', {}).get('evidence', {}).get('raw_generation', {})
            record = {'kind': 'turn_rejected', 'error': error, 'rejected_operation_id': inbox['operation_id'],
                      'rejected_output': raw.get('raw_output'), 'request_id': s['requests'][-1]['id']}
            s['rejections'].append(record)
            s['consecutive_rejections'] += 1
            s['transcript'].append(agent.host_notice('turn_rejected', error=error))
            s['feedback'] = record
            s['inbox'] = None
        self.db.update('turn_rejected', change)

    def _request(self):
        definitions = agent_definitions(self.harness)
        s = self.db.state()
        lane = s['session_id']
        payload = agent.build_input(s, native_tools=definitions)
        preflight = getattr(self.agent, 'preflight', None)
        if preflight:
            try:
                preflight(lane, payload, definitions, s['sessions'].get(lane))
            except InputBudgetError as exc:
                self.db.update('model_input_rejected', lambda state:
                    state.setdefault('input_rejections', []).append({
                        'lane': lane, 'input': payload, 'input_digest': digest(payload),
                        'definitions': definitions, 'checkpoint': s['sessions'].get(lane), 'error': str(exc),
                        'measurement': getattr(exc, 'input_budget_evidence', None),
                        'call_reserved': False, 'generation_started': False}))
                raise
        def reserve(state):
            state['calls'] += 1
            state['requests'][-1]['calls'] += 1
        self.db.update('call_reserved', reserve)
        identifier = self.db.begin_operation('model', {'role': 'agent', 'lane': lane, 'input': payload,
            'input_digest': digest(payload), 'request_id': s['requests'][-1]['id']})
        if s.get('record_generation_snapshots', False):
            from .project_generation_snapshots import capture_snapshot
            capture_snapshot(self.db, identifier)
        started = time.monotonic()
        reply = self.agent.request(lane, payload, definitions, s['sessions'].get(lane))
        duration = time.monotonic() - started
        def change(state):
            state['sessions'][lane] = reply.checkpoint
            state['inbox'] = {'lane': lane, 'command': reply.command, 'operation_id': identifier, 'cursor': 0}
        self.db.finish_operation(identifier, {'command': reply.command, 'evidence': reply.evidence,
            'generation_seconds': duration}, mutate=change)

    def _consume(self):
        s = self.db.state()
        inbox = s['inbox']
        command = inbox['command']
        fields(command, ('function', 'params'))
        name, params = command['function'], command['params']
        if not isinstance(params, dict):
            raise ValueError('parameter object required')
        attestation = s['evidence'][inbox['operation_id']]['result']['evidence']
        if name == 'protocol_rejected':
            if attestation.get('rejected') is not True:
                raise ValueError('protocol rejection requires host attestation')
            fields(params, ('error',))
            self._reject(text(params['error']))
            return
        if name == 'model_output_budget_exhausted':
            if params or attestation.get('known_budget_exhaustion') is not True:
                raise ValueError('output budget interruption requires host attestation')
            # The truncated turn was rolled back and never executed. The notice
            # and the interruption are one event; a follow-up continues here.
            self.db.interrupt('model_output_budget_exhausted', notice=agent.host_notice(
                'turn_truncated', error='reply exceeded the output budget; nothing in it was executed'))
            return
        if name != 'assistant':
            raise ValueError('agent requires a native assistant message')
        definitions = agent_definitions(self.harness)
        fields(params, ('message',))
        if 'batch' not in inbox:
            message = validate_assistant(params['message'], definitions)
            validate_messages([*s['transcript'], message])
            batch = []
            for call in message.get('tool_calls', []):
                native, arguments = native_call(call['function']['name'], loads(call['function']['arguments']))
                if native != 'finish_work':
                    self.harness.normalize_action(TaskAction(native, arguments))
                batch.append({'id': call['id'], 'name': native, 'arguments': arguments})
            def prepared(state):
                state['transcript'].append(message)
                state['inbox'].update(batch=batch, cursor=0)
                state['consecutive_rejections'] = 0
            self.db.update('assistant_batch_prepared', prepared)
        while self.db.state()['inbox']:
            s = self.db.state()
            inbox = s['inbox']
            if inbox['cursor'] >= len(inbox['batch']):
                self.db.update('assistant_consumed', lambda state: state.update(inbox=None))
                break
            selected = inbox['batch'][inbox['cursor']]
            if selected['name'] == 'finish_work':
                declaration = deepcopy(selected['arguments'])
                self.db.finish_request(declaration, tool_result(selected['id'], {'declaration': declaration}))
                break
            self._tool(selected['name'], selected['arguments'], selected['id'])

    def _tool(self, name, params, tool_call_id):
        s = self.db.state()
        params = deepcopy(params)
        request = s['requests'][-1]
        allowed = {d['name'] for d in self.harness.g1i_tool_definitions()}
        if name not in allowed:
            raise ValueError('unknown execution operation')
        action = self.harness.normalize_action(TaskAction(name, params))
        goal = GoalState.create(request=request['text'], workspace_root=s['workspace'], constraints=[])
        with self.harness.action_transaction(goal):
            before_tree = tree_identity(s['workspace'])
            if digest(before_tree) != s['workspace_digest']:
                raise ValueError('workspace changed outside the recorded agent')
            policy = {'scope': s['permissions']['writable'], 'protected': s['permissions']['protected']}
            control = name in ('read_job_output', 'kill_job')
            targets = [] if control else explicit_write_targets(self.harness, action, identity=before_tree)
            violations = write_violations(targets, before=before_tree, **policy)
            identifier = self.db.begin_tool_operation({'session_id': s['session_id'], 'name': name,
                'arguments': action.arguments, 'requested_arguments': params,
                'before': s['workspace_digest'], 'request_id': request['id'],
                'source_operation_id': s['inbox']['operation_id'], 'tool_call_id': tool_call_id})
            transaction = self.db.root / 'tool_transactions' / identifier
            transaction.mkdir(parents=True)
            staged = transaction / 'workspace'
            background = None
            finished_background = None
            if violations:
                result = ActionResult(name, False, metadata=violation_record(transaction, violations),
                    error={'type': 'ScopeViolation',
                    'message': 'Write rejected before execution: ' + ', '.join(violation_summary(violations))})
            elif control:
                # Job control acts on the process table, never on a newly copied
                # workspace. Publication is a separate, stopped-job boundary.
                self._require_background_identities()
                result = self.harness.execute(action, goal)
                handle = action.arguments['job_handle']
                record = s.get('background_workspaces', {}).get(handle)
                if record:
                    if result.error and result.error.get('type') == 'UnknownProcessIdentity':
                        raise UncertainToolOutcome('background job identity is unknown')
                    stopped = None
                    if name == 'kill_job' and result.success:
                        stopped = result.metadata
                    elif name == 'read_job_output' and result.success and result.metadata.get('running') is False:
                        stopped = self.harness._jobs.stop(self.harness._jobs.get(handle))
                    if stopped is not None:
                        if stopped.get('outcome') != 'stopped' or stopped.get('identity_verified') is not True:
                            raise UncertainToolOutcome('background job termination is unconfirmed')
                        result = self._publish_background(record, result, stopped, transaction, before_tree, policy)
                        finished_background = handle
            else:
                copy_verified_workspace(s['workspace'], staged, exclude_git=False)
                isolated = GoalState.create(request=goal.request, workspace_root=str(staged),
                                            constraints=[])
                # Do not catch cancellation, process loss, or uncertain tool errors.
                result = self.harness.execute(action, isolated)
                if name == 'run_shell' and action.arguments.get('run_in_background') and result.success:
                    handle = result.metadata.get('job_handle')
                    if not isinstance(handle, str) or not handle:
                        raise UncertainToolOutcome('background launch did not return a job handle')
                    background = {'handle': handle, 'operation_id': identifier,
                        'workspace': str(staged.relative_to(self.db.root)), 'baseline': before_tree,
                        'scope': policy['scope'], 'job_identity': result.metadata.get('job_identity')}
                    self._pending_background[handle] = background
                    result.metadata.update(workspace_committed=False, background_workspace='isolated_running')
                    # The live process owns this inode. Never publish it, scan
                    # it as a stable snapshot, or remove it at launch return.
                else:
                    result = self._publish_staged(staged, result, transaction, before_tree, policy)
                    shutil.rmtree(staged)
            after_tree = tree_identity(s['workspace'])
            current = digest(after_tree)
            raw = result.to_dict()
            raw['metadata']['changed_paths'] = sorted(p for p in before_tree.keys() | after_tree.keys()
                if before_tree.get(p) != after_tree.get(p))
            projected = json.loads(tool_result(tool_call_id, raw)['content'])
            def change(state):
                self.db.invalidate(state, current)
                state['transcript'].append(tool_result(tool_call_id, raw))
                state['inbox']['cursor'] += 1
                state['requests'][-1]['receipt_ids'].append(identifier)
                if background is not None:
                    state.setdefault('background_workspaces', {})[background['handle']] = background
                if finished_background is not None:
                    state['background_workspaces'].pop(finished_background)
                state['feedback'] = {'kind': 'tool_returned' if result.success else 'execution_failed',
                    'evidence_id': identifier, 'request_id': request['id']}
            # Raw evidence is retained separately from the model-facing projection.
            raw_path = self.db.root / 'raw_tools'
            raw_path.mkdir(exist_ok=True)
            (raw_path / (identifier + '.json')).write_text(json.dumps(raw, ensure_ascii=False, indent=2) + '\n')
            projected['raw_receipt'] = {'path': 'raw_tools/' + identifier + '.json', 'content_digest': digest(raw)}
            self.db.finish_operation(identifier, projected, mutate=change)
            if background is not None:
                self._pending_background.pop(background['handle'], None)

    def _publish_staged(self, staged, result, transaction, before_tree, policy):
        staged_tree = tree_identity(staged, allow_links=True)
        changed = [p for p in before_tree.keys() | staged_tree.keys()
                   if before_tree.get(p) != staged_tree.get(p)]
        violations = write_violations(changed, before=before_tree, after=staged_tree, **policy)
        entry_errors = invalid_entries(staged_tree)
        violations = sorted(set(violations) | set(entry_errors))
        if violations:
            return ActionResult(result.action_type, False, output=result.output, exit_code=result.exit_code,
                metadata={'isolated_result': result.to_dict(), 'workspace_committed': False,
                          **violation_record(transaction, violations, entry_errors)},
                error={'type': 'ScopeViolation', 'message': 'Isolated changes rejected: '
                       + ', '.join(violation_summary(violations))})
        workspace = self.db.state()['workspace']
        if tree_identity(workspace) != before_tree:
            raise ValueError('workspace changed before isolated publication')
        if changed:
            publish_workspace(workspace, staged)
        result.metadata['workspace_committed'] = bool(changed)
        return result

    def _require_background_identities(self):
        table = getattr(self.harness, '_jobs', None)
        for handle, record in self.db.state().get('background_workspaces', {}).items():
            job = table.jobs.get(handle) if table is not None else None
            if (job is None or job.identity_matches() is not True
                    or job.identity() != record['job_identity']):
                raise UncertainToolOutcome('background job cannot be reconciled: ' + handle)

    def _background_path(self, record):
        path = (self.db.root / record['workspace']).resolve(strict=True)
        if self.db.root not in path.parents:
            raise ValueError('background workspace outside project records')
        return path

    def _publish_background(self, record, result, stopped, transaction, before_tree, policy):
        """Publish a new inode only after the entire background job has stopped."""
        private = self._background_path(record)
        metadata = {'background_handle': record['handle'], 'background_stop': deepcopy(stopped),
                    'workspace_committed': False}
        if before_tree != record['baseline']:
            result = ActionResult(result.action_type, False, output=result.output, exit_code=result.exit_code,
                metadata={**result.metadata, **metadata}, error={'type': 'WorkspaceConflict',
                    'message': 'Workspace changed since background launch; private changes were not published'})
        else:
            private_tree = tree_identity(private, allow_links=True)
            changed = [p for p in before_tree.keys() | private_tree.keys()
                       if before_tree.get(p) != private_tree.get(p)]
            violations = write_violations(changed, before=before_tree, after=private_tree, **policy)
            violations += write_violations(changed, before=before_tree, after=private_tree,
                scope=record['scope'], protected=policy['protected'])
            errors = invalid_entries(private_tree)
            violations = sorted(set(violations) | set(errors))
            if violations:
                result = ActionResult(result.action_type, False, output=result.output, exit_code=result.exit_code,
                    metadata={**result.metadata, **metadata, **violation_record(transaction, violations, errors)},
                    error={'type': 'ScopeViolation', 'message': 'Background changes rejected: '
                           + ', '.join(violation_summary(violations))})
            else:
                clone = transaction / 'background_snapshot'
                copied = copy_verified_workspace(private, clone, exclude_git=False,
                    audit_path=transaction / 'background_snapshot.json')
                if copied != private_tree:
                    raise UncertainToolOutcome('background workspace changed after confirmed termination')
                result.metadata.update(metadata)
                result = self._publish_staged(clone, result, transaction, before_tree, policy)
                shutil.rmtree(clone)
        result.metadata['background_workspace'] = ('committed' if result.metadata.get('workspace_committed')
            else 'rejected' if not result.success else 'unchanged')
        shutil.rmtree(private)
        return result

    def _progress(self, operation_id):
        """Readable live projection; the transactional ledger remains authority."""
        state = self.db.state()
        source = state['evidence'][operation_id]
        row = {'operation_id': operation_id, 'role': 'agent', 'request_id': source['intent']['request_id'],
            'command': source['result']['command'], 'input_digest': source['intent']['input_digest'],
            'raw_output': source['result']['evidence'].get('raw_generation', {}).get('raw_output'),
            'feedback': state['feedback'], 'status': state['status']}
        if (state['feedback'] or {}).get('kind') in ('tool_returned', 'execution_failed'):
            identifier = state['feedback']['evidence_id']
            receipt = state['evidence'][identifier]
            raw = receipt['result'].get('raw_receipt')
            if receipt['intent']['source_operation_id'] == operation_id:
                row['tool_receipt'] = json.loads((self.db.root / raw['path']).read_text()) if raw else receipt['result']
                row['tool_operation_id'] = identifier
        with (self.db.root / 'PROGRESS.jsonl').open('a') as stream:
            stream.write(json.dumps(row, ensure_ascii=False) + '\n')

    def _clean_boundary(self):
        s = self.db.state()
        return s['status'] == 'running' and not s['pending'] and s['inbox'] is None

    def _stop(self, reason, error=None):
        """Record why the loop stopped; an interruption is set only at a clean boundary."""
        if error is not None:
            self.db.update(reason, lambda state: state.update(error={'type': type(error).__name__, 'message': str(error)}))
        if self.db.state()['pending']:
            return 'uncertain_operation'
        if self._clean_boundary() and reason in (*BUDGET_REASONS, 'repeated_rejection'):
            self.db.interrupt(reason)
        return reason

    def run(self, *, max_turns=None):
        """Run the current request until the agent declares, a budget stops it, or a yield."""
        self.started = time.monotonic()
        self.initial_elapsed = self.db.state()['elapsed']
        reason = ''
        with self.db.lease():
            try:
                with project_deadline(self.remaining()['seconds']):
                    self.db.require_recoverable()
                    self._require_background_identities()
                    turns = 0
                    while self.db.state()['status'] == 'running':
                        s = self.db.state()
                        if s['inbox'] is None:
                            if s['consecutive_rejections'] >= s['rejection_limit']:
                                reason = self._stop('repeated_rejection')
                                break
                            if max_turns is not None and turns >= max_turns:
                                reason = 'checkpoint_yield'
                                break
                            remaining = self.remaining()
                            if remaining['seconds'] is not None and remaining['seconds'] <= 0:
                                reason = self._stop('wall_budget_exhausted')
                                break
                            if remaining['calls'] is not None and remaining['calls'] <= 0:
                                reason = self._stop('resource_budget_exhausted')
                                break
                            self._request()
                            turns += 1
                        consumed = self.db.state()['inbox']
                        try:
                            self._consume()
                        except (ValueError, KeyError, TypeError, HarnessError) as exc:
                            boundary = self.db.state()
                            proof = boundary['evidence'][consumed['operation_id']]['result']['evidence']
                            known_output_stop = (consumed['command'] == {'function': 'model_output_budget_exhausted', 'params': {}}
                                and proof.get('known_budget_exhaustion') is True)
                            if boundary['pending'] or (boundary['inbox'] or {}).get('batch') or known_output_stop:
                                raise
                            self._reject(str(exc))
                        self._progress(consumed['operation_id'])
            except InputBudgetError as exc:
                reason = self._stop('model_input_budget_exhausted', exc)
            except UncertainOperation:
                reason = 'uncertain_operation'
            except WallDeadlineExpired as exc:
                reason = self._stop('wall_budget_exhausted', exc)
            except Exception as exc:
                reason = self._stop('execution_error', exc)
            finally:
                self.db.update('runtime_checkpoint', lambda state: state.update(
                    elapsed=self.initial_elapsed + time.monotonic() - self.started))
                try:
                    self.reclaimed_jobs = self.reclaim_background_jobs()
                except Exception as exc:
                    if not isinstance(exc, UncertainToolOutcome):
                        raise
                    if not self.db.state()['pending']:
                        self.db.begin_operation('cleanup', {'operation': 'reclaim_background_jobs'})
                    self.db.update('cleanup_uncertain', lambda state: state.update(
                        error={'type': type(exc).__name__, 'message': str(exc)}))
                    reason = 'uncertain_operation'
        return self.result(reason)

    def reclaim_background_jobs(self):
        """Stop every background job this project started.

        A dev server must not outlive the project that launched it. An
        uncertain cleanup propagates as UncertainToolOutcome rather than being
        reported as a clean teardown.
        """
        table = getattr(self.harness, '_jobs', None)
        db = getattr(self, 'db', None)
        records = dict(db.state().get('background_workspaces', {})) if db is not None else {}
        records.update(getattr(self, '_pending_background', {}))
        if not records and (table is None or not table.jobs):
            return []
        identifier = None
        if db is not None and not db.state()['pending']:
            identifier = db.begin_operation('cleanup', {'operation': 'reclaim_background_jobs',
                'handles': sorted(set(records) | set(table.jobs if table else {}))})
        if records and (table is None or any(handle not in table.jobs for handle in records)):
            raise UncertainToolOutcome('background cleanup cannot confirm recorded process identities')
        reclaimed = table.stop_all() if table is not None else []
        if any(item.get('outcome') != 'stopped' or item.get('identity_verified') is not True for item in reclaimed):
            raise UncertainToolOutcome('background cleanup did not confirm every process stopped')
        for record in records.values():
            private = self._background_path(record)
            shutil.rmtree(private)
        fact = {'kind': 'background_jobs_reclaimed', 'jobs': reclaimed,
                'workspace_committed': False, 'private_changes_discarded': sorted(records)}
        if db is not None:
            def changed(state):
                state['background_workspaces'] = {}
                state.setdefault('background_cleanup', []).append(fact)
                # The continued agent must learn that
                # its old server was stopped. An unresolved tool stays pending.
                if state['inbox'] is None:
                    state['transcript'].append(agent.host_notice(fact['kind'],
                        **{key: value for key, value in fact.items() if key != 'kind'}))
            if identifier is not None:
                db.finish_operation(identifier, fact, mutate=changed)
            else:
                db.update('background_cleanup_observed', changed)
        self._pending_background = {}
        return reclaimed

    def result(self, reason=''):
        s = self.db.state()
        ended = s['status'] in ('finished', 'blocked', 'interrupted') and not s['pending']
        declared = ended and s['status'] in ('finished', 'blocked')
        tool_receipts = [r for r in s['evidence'].values() if r['kind'] == 'tool']
        models = [r for r in s['evidence'].values() if r['kind'] == 'model']
        measured = []
        for receipt in models:
            tokens = receipt['result']['evidence'].get('usage') or {}
            prompt, output = tokens.get('input_tokens'), tokens.get('output_tokens')
            if type(prompt) is int and type(output) is int and prompt >= 0 and output >= 0:
                measured.append((prompt, output))
        usage = {'model_calls': len(models), 'calls_reserved': s['calls'],
            'generation_seconds': sum(r['result'].get('generation_seconds', 0) for r in models),
            'input_tokens': sum(x[0] for x in measured) if len(measured) == len(models) else None,
            'output_tokens': sum(x[1] for x in measured) if len(measured) == len(models) else None,
            'token_measurement_calls': len(measured)}
        result = {'architecture': ARCHITECTURE, 'session_id': s['session_id'],
            'status': s['status'] if ended else 'interrupted',
            'termination_reason': reason or s.get('stop_reason') or 'interrupted',
            'final': s['final'], 'final_claim': s['final_claim'], 'model_finished': declared,
            'completed': False, 'acceptance': 'not_evaluated', 'model_calls': s['calls'], 'agent_usage': usage,
            'request_count': len(s['requests']), 'requests': deepcopy(s['requests']),
            'mutation_count': sum(bool(r['result'].get('metadata', {}).get('workspace_committed')) for r in tool_receipts),
            'workspace': s['workspace'], 'workspace_digest': s['workspace_digest'], 'elapsed': s['elapsed'],
            'diagnostics': {'resumable': s['status'] == 'running' and not s['pending'],
                'pending_operation': s['pending'], 'runtime_error': s.get('error'),
                'last_obstacle': s['feedback'], 'rejections': deepcopy(s['rejections']),
                'reclaimed_background_jobs': getattr(self, 'reclaimed_jobs', [])}}
        (self.db.root / 'RESULT.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        return result
