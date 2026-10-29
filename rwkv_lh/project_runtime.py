"""Work-order Planner loop with one persistent, transactional Executor lane."""
from dataclasses import dataclass
from copy import deepcopy
import json
import shutil
import time

from .project_contracts import digest, fields, text, protected_paths
from .project_ledger import ProjectLedger, UncertainOperation
from .project_protocols import planner, executor
from .harness import ActionHarness, ActionResult, HarnessError, UncertainToolOutcome
from .project_tools import configure_project_tools
from .project_workspace import explicit_write_targets, violations as write_violations, publish_workspace
from .schema import GoalState, TaskAction
from .workspace_snapshot import tree_identity, copy_verified_workspace, invalid_entries
from .transcript.render import tool_result, user_message, compact
from .transcript.parse import parse_assistant, validate_messages, loads
from .transcript.tools import native_call
from .project_work_orders import build_report
from .job_budget import WallDeadlineExpired
from .project_deadline import project_deadline
from .model_session import InputBudgetError
from .model_io import ModelCommand
from .project_output_validation import validate_role_output

ARCHITECTURE = 'rwkv-lh.coder.architecture.v2'


@dataclass(frozen=True)
class RoleReply:
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

    Raw receipt bodies are delivered to the Executor, so they carry only the
    bounded summary and a count, never the unbounded path list nor the
    operation-specific location of the full record.
    """
    entry_errors = entry_errors or {}
    (transaction / 'scope_violation_paths.json').write_text(
        json.dumps({'paths': violations, 'entry_errors': entry_errors}, ensure_ascii=False, indent=2) + '\n')
    return {'scope_violation': violation_summary(violations), 'scope_violation_count': len(violations),
            'workspace_entry_errors': dict(sorted(entry_errors.items())[:SCOPE_VIOLATION_LIMIT])}


def role_definitions(role, harness):
    if role == 'planner':
        return planner.action_definitions()
    if role != 'executor':
        raise ValueError('current project roles are planner and executor')
    configure_project_tools(harness)
    return executor.action_definitions(harness.g1i_tool_definitions())


class ProjectRuntime:
    def __init__(self, ledger, roles, *, harness=None):
        self.db, self.roles = ledger, roles
        self.harness = configure_project_tools(harness or ActionHarness())
        self.started = None
        self.initial_elapsed = 0.0
        self._pending_background = {}

    def remaining(self):
        s = self.db.state()
        elapsed = self.initial_elapsed + time.monotonic() - self.started if self.started is not None else s['elapsed']
        return {'calls': max(0, s['max_calls'] - s['calls']), 'seconds': max(0.0, s['max_seconds'] - elapsed)}

    def _feedback(self, kind, **value):
        def change(s):
            inbox = s.get('inbox') or {}
            if kind.endswith('_rejected'):
                receipt = s['evidence'].get(inbox.get('operation_id'), {})
                raw = receipt.get('result', {}).get('evidence', {}).get('raw_generation', {})
                value['rejected_operation_id'] = inbox.get('operation_id')
                value['rejected_output'] = raw.get('raw_output')
                s['role_rejections'][inbox['lane']] = {'kind': kind, **value}
                if inbox['role'] == 'executor':
                    s['consecutive_rejections'] += 1
                    s['transcript'].append(user_message(compact({'kind': kind, **value})))
            s['feedback'] = {'kind': kind, **value}
            if inbox.get('role') == 'planner' and kind in ('planner_rejected', 'model_output_budget_exhausted'):
                # The terminal decision and consumed inbox are one durable
                # boundary. A sidecar failure must never permit replanning.
                s.update(status='failed', stop_reason='planner_protocol_error')
            s['inbox'] = None
        self.db.update(kind, change)

    def _request(self):
        configure_project_tools(self.harness)
        s = self.db.state()
        remaining = self.remaining()
        if s['current_order'] is None:
            role, lane = 'planner', 'planner'
            initial = s['initial_context']
            if not s['work_orders'] and (digest(initial['workspace']) != s['workspace_digest']
                    or tree_identity(s['workspace']) != initial['workspace']):
                raise ValueError('workspace changed before initial planning')
            payload = planner.build_input(s['request'], workspace=initial['workspace'],
                materials=initial['materials'], work_orders=s['work_orders'], protected_paths=s['protected_paths'],
                remaining=remaining, execution_capabilities=self.harness.planning_capabilities())
        else:
            role, lane = 'executor', s['active']['id']
            self.db.update('executor_budget_disclosed', lambda state: state['transcript'].append(
                user_message(compact({'project_remaining': remaining,
                    'work_order_calls_remaining': state['current_order']['call_budget'] - state['order_calls']}))))
            s = self.db.state()
            payload = executor.build_input(s['active'], project_state=s, remaining=remaining,
                native_tools=role_definitions('executor', self.harness))
        definitions = role_definitions(role, self.harness)
        preflight = getattr(self.roles, 'preflight', None)
        if preflight:
            try:
                preflight(role, lane, payload, definitions, s['sessions'].get(lane))
            except InputBudgetError as exc:
                self.db.update('model_input_rejected', lambda state:
                    state.setdefault('input_rejections', []).append({
                        'role': role, 'lane': lane, 'input': payload, 'input_digest': digest(payload),
                        'definitions': definitions, 'checkpoint': s['sessions'].get(lane), 'error': str(exc),
                        'measurement': getattr(exc, 'input_budget_evidence', None),
                        'call_reserved': False, 'generation_started': False}))
                raise
        def reserve(state):
            state['calls'] += 1
            state['role_calls'][role] += 1
            if role == 'executor':
                state['order_calls'] += 1
        self.db.update('call_reserved', reserve)
        identifier = self.db.begin_operation('model', {'role': role, 'lane': lane,
            'input': payload, 'input_digest': digest(payload), 'work_order_id':
                s['current_order']['id'] if s['current_order'] else None})
        if s.get('record_generation_snapshots', False):
            from .project_generation_snapshots import capture_snapshot
            capture_snapshot(self.db, identifier)
        started = time.monotonic()
        reply = self.roles.request(role, lane, payload, definitions, s['sessions'].get(lane))
        duration = time.monotonic() - started
        def change(state):
            state['sessions'][lane] = reply.checkpoint
            state['inbox'] = {'role': role, 'lane': lane, 'command': reply.command,
                'operation_id': identifier, 'cursor': 0}
        self.db.finish_operation(identifier, {'command': reply.command, 'evidence': reply.evidence,
            'generation_seconds': duration}, mutate=change)

    def _consume(self):
        s = self.db.state()
        inbox = s['inbox']
        command = inbox['command']
        fields(command, ('function', 'params'))
        name, params, role = command['function'], command['params'], inbox['role']
        if not isinstance(params, dict):
            raise ValueError('parameter object required')
        receipt = s['evidence'][inbox['operation_id']]
        attestation = receipt['result']['evidence']
        if name == 'protocol_rejected':
            if attestation.get('rejected') is not True:
                raise ValueError('protocol rejection requires host attestation')
            fields(params, ('error',))
            self._feedback(role + '_rejected', error=text(params['error']))
            return
        if name == 'model_output_budget_exhausted':
            if params or attestation.get('known_budget_exhaustion') is not True:
                raise ValueError('output budget interruption requires host attestation')
            if role == 'executor':
                # Keep the known returned command until the report transaction
                # also clears it. A process loss before handoff consumes this
                # same inbox on recovery, without another model request.
                self._return_order('model_output_budget_exhausted')
            else:
                self._feedback(name, role=role, evidence_id=inbox['operation_id'])
            return
        definitions = role_definitions(role, self.harness)
        if role == 'planner':
            accepted = ModelCommand(name, params)
            validate_role_output(role, receipt['intent']['input'], accepted, definitions)
            if name == 'issue_work_order':
                self.db.issue_work_order(accepted.arguments)
            elif name == 'finish_project':
                self.db.finish_project(**accepted.arguments)
            else:
                raise ValueError('unknown Planner action')
            return
        if name != 'assistant':
            raise ValueError('Executor requires a native assistant message')
        fields(params, ('message',))
        if 'batch' not in inbox:
            message = parse_assistant(compact(params['message']), definitions)
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
                state['role_rejections'].pop(inbox['lane'], None)
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
                receipt = tool_result(selected['id'], {'declaration': declaration})
                self._return_order('model_finished', declaration=declaration, declaration_receipt=receipt)
                break
            self._tool(selected['name'], selected['arguments'], inbox['lane'], s['current_order']['id'], selected['id'])

    def _return_order(self, reason, *, declaration=None, declaration_receipt=None):
        s = self.db.state()
        order = s['current_order']
        receipts, committed = [], []
        for identifier in s['work_orders'][-1]['receipt_ids']:
            evidence = s['evidence'][identifier]
            reference = evidence['result']['raw_receipt']
            path = (self.db.root / reference['path']).resolve(strict=True)
            if self.db.root not in path.parents:
                raise ValueError('raw receipt outside project records')
            raw = json.loads(path.read_text())
            if digest(raw) != reference['content_digest']:
                raise ValueError('raw receipt digest mismatch')
            intent = evidence['intent']
            if intent['step_id'] != order['id']:
                raise ValueError('work order receipt identity mismatch')
            metadata = raw.get('metadata', {})
            committed.extend(metadata.get('changed_paths', []))
            arguments = intent['arguments']
            execution_metadata = metadata.get('isolated_result', {}).get('metadata', metadata)
            if (intent['name'] == 'run_shell' and execution_metadata.get('cwd') in ('.', './')
                    and not arguments.get('run_in_background') and type(raw.get('exit_code')) is int):
                stream = execution_metadata.get('command_streams', {}).get('stderr', {})
                output = str(raw.get('output') or '').encode('utf-8')
                stderr = output[stream.get('start_byte', len(output)):stream.get('end_byte', len(output))].decode('utf-8')
                receipts.append({'receipt_id': identifier, 'name': 'run_shell',
                    'command': arguments['command'], 'confirmed': True,
                    'exit_code': raw['exit_code'], 'stderr': stderr})
        report = build_report(order, receipts=receipts, committed_paths=committed,
            calls_used=s['order_calls'], declaration=declaration, remaining=self.remaining(),
            interrupted_reason='' if reason == 'model_finished' else reason)
        self.db.return_work_order(report, reason=reason, declaration_receipt=declaration_receipt)

    def _tool(self, name, params, lane, step_id, tool_call_id):
        s = self.db.state()
        if not s['active'] or s['active']['id'] != lane:
            raise ValueError('stale worker assignment')
        params = deepcopy(params)
        task = s['current_order']
        if task is None or task['id'] != step_id:
            raise ValueError('unknown work order')
        allowed = {d['name'] for d in self.harness.g1i_tool_definitions()}
        if name not in allowed:
            raise ValueError('unknown execution operation')
        action = self.harness.normalize_action(TaskAction(name, params))
        goal = GoalState.create(request=task['goal'], workspace_root=s['workspace'], constraints=[])
        with self.harness.action_transaction(goal):
            before_tree = tree_identity(s['workspace'])
            if digest(before_tree) != s['workspace_digest']:
                raise ValueError('workspace changed outside the recorded worker')
            policy = {'scope': task['scope'], 'protected': protected_paths(s)}
            control = name in ('read_job_output', 'kill_job')
            targets = [] if control else explicit_write_targets(self.harness, action, identity=before_tree)
            violations = write_violations(targets,
                                          before=before_tree, **policy)
            identifier = self.db.begin_tool_operation({'assignment_id': lane, 'name': name,
                'arguments': action.arguments, 'requested_arguments': params,
                'before': s['workspace_digest'], 'step_id': task['id'],
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
                        'scope': task['scope'], 'job_identity': result.metadata.get('job_identity')}
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
                state['work_orders'][-1]['receipt_ids'].append(identifier)
                if background is not None:
                    state.setdefault('background_workspaces', {})[background['handle']] = background
                if finished_background is not None:
                    state['background_workspaces'].pop(finished_background)
                state['feedback'] = {'kind': 'tool_returned' if result.success else 'execution_failed',
                    'evidence_id': identifier, 'assignment_id': lane, 'step_id': task['id']}
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
        row = {'operation_id': operation_id, 'role': source['intent']['role'],
            'step_id': state['current_step_id'], 'command': source['result']['command'],
            'input_digest': source['intent']['input_digest'],
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

    def run(self, *, max_turns=None):
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
                        if s['current_order'] is not None and s['inbox'] is None:
                            if s['consecutive_rejections'] >= s['rejection_limit']:
                                self._return_order('repeated_rejection')
                                continue
                            if s['order_calls'] >= s['current_order']['call_budget']:
                                self._return_order('call_budget_exhausted')
                                continue
                        if s['current_order'] is None and s['consecutive_no_progress'] >= s['no_progress_limit']:
                            reason = 'no_progress'
                            break
                        if max_turns is not None and turns >= max_turns and s['inbox'] is None:
                            reason = 'checkpoint_yield'
                            break
                        if s['inbox'] is None:
                            remaining = self.remaining()
                            if remaining['seconds'] <= 0:
                                reason = 'wall_budget_exhausted'
                                break
                            if remaining['calls'] <= 0:
                                reason = 'resource_budget_exhausted'
                                break
                            self._request()
                            turns += 1
                        consumed = self.db.state()['inbox']
                        try:
                            self._consume()
                        except (ValueError, KeyError, TypeError, HarnessError) as exc:
                            boundary = self.db.state()
                            proof = boundary['evidence'][consumed['operation_id']]['result']['evidence']
                            known_output_stop = (consumed['role'] == 'executor'
                                and consumed['command'] == {'function': 'model_output_budget_exhausted', 'params': {}}
                                and proof.get('known_budget_exhaustion') is True)
                            if boundary['pending'] or (boundary['inbox'] or {}).get('batch') or known_output_stop:
                                raise
                            self._feedback(consumed['role'] + '_rejected', error=str(exc))
                        self._progress(consumed['operation_id'])
                        boundary = self.db.state()
                        if boundary['status'] == 'failed':
                            reason = boundary['stop_reason']
                            break
            except InputBudgetError as exc:
                boundary = self.db.state()
                reason = ('uncertain_operation' if boundary['pending']
                          else boundary.get('stop_reason') or 'model_input_budget_exhausted')
                self.db.update('input_budget_exhausted', lambda state: state.update(error={'type': type(exc).__name__, 'message': str(exc)}))
            except UncertainOperation:
                reason = 'uncertain_operation'
            except WallDeadlineExpired as exc:
                boundary = self.db.state()
                reason = ('uncertain_operation' if boundary['pending']
                          else boundary.get('stop_reason') or 'wall_budget_exhausted')
                self.db.update('wall_budget_exhausted', lambda state: state.update(error={'type': type(exc).__name__, 'message': str(exc)}))
            except Exception as exc:
                boundary = self.db.state()
                reason = ('uncertain_operation' if boundary['pending']
                          else boundary.get('stop_reason') or 'execution_error')
                self.db.update('runtime_error', lambda state: state.update(error={'type': type(exc).__name__, 'message': str(exc)}))
            finally:
                self.db.update('runtime_checkpoint', lambda state: state.update(
                    elapsed=self.initial_elapsed + time.monotonic() - self.started))
                try:
                    self.reclaimed_jobs = self.reclaim_background_jobs()
                except Exception as exc:
                    from .harness import UncertainToolOutcome
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
                # At checkpoint_yield the continued Executor must learn that
                # its old server was stopped. An unresolved tool stays pending.
                if state['inbox'] is None:
                    state['transcript'].append(user_message(compact(fact)))
            if identifier is not None:
                db.finish_operation(identifier, fact, mutate=changed)
            else:
                db.update('background_cleanup_observed', changed)
        self._pending_background = {}
        return reclaimed

    def result(self, reason=''):
        s = self.db.state()
        ended = s['status'] in ('finished', 'blocked') and not s['pending']
        tool_receipts = [r for r in s['evidence'].values() if r['kind'] == 'tool']
        usage = {}
        for role in ('planner', 'executor'):
            models = [r for r in s['evidence'].values() if r['kind'] == 'model' and r['intent']['role'] == role]
            measured = []
            for receipt in models:
                proof = receipt['result']['evidence']
                tokens = proof.get('usage') or proof.get('provider_response', {}).get('usage') or {}
                prompt, output = tokens.get('input_tokens', tokens.get('prompt_tokens')), tokens.get('output_tokens', tokens.get('completion_tokens'))
                if type(prompt) is int and type(output) is int and prompt >= 0 and output >= 0:
                    measured.append((prompt, output))
            usage[role] = {'model_calls': len(models), 'calls_reserved': s['role_calls'][role], 'generation_seconds': sum(r['result'].get('generation_seconds', 0) for r in models),
                'input_tokens': sum(x[0] for x in measured) if len(measured) == len(models) else None,
                'output_tokens': sum(x[1] for x in measured) if len(measured) == len(models) else None,
                'token_measurement_calls': len(measured)}
        result = {'architecture': ARCHITECTURE,
            'status': s['status'] if ended or s['status'] == 'failed' else 'interrupted',
            'termination_reason': reason or s.get('stop_reason') or 'interrupted',
            'final': s['final'], 'final_claim': s['final_claim'], 'model_finished': ended and s['status'] == 'finished',
            'completed': False, 'acceptance': 'not_evaluated', 'model_calls': s['calls'],
            'planner_usage': usage['planner'], 'executor_usage': usage['executor'],
            'work_order_count': len(s['work_orders']), 'work_orders': deepcopy(s['work_orders']),
            'task_count': len(s['work_orders']), 'verified_tasks': 0,
            'mutation_count': sum(bool(r['result'].get('metadata', {}).get('workspace_committed')) for r in tool_receipts),
            'workspace': s['workspace'], 'workspace_digest': s['workspace_digest'], 'elapsed': s['elapsed'],
            'diagnostics': {'next_role': None if ended or s['status'] == 'failed' else 'executor' if s['current_order'] else 'planner',
                'pending_operation': s['pending'], 'runtime_error': s.get('error'),
                'last_obstacle': s['feedback'], 'rejections': deepcopy(s['role_rejections']),
                'reclaimed_background_jobs': getattr(self, 'reclaimed_jobs', [])}}
        (self.db.root / 'RESULT.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        return result
