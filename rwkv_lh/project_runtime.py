"""One initial Planner call followed by one autonomous, persistent Executor."""
from dataclasses import dataclass
from copy import deepcopy
import json
import shutil
import time

from .project_contracts import digest, fields, text, work_map, protected_paths
from .project_ledger import ProjectLedger, UncertainOperation
from .project_materials import capture_materials
from .project_protocols import planner, executor
from .harness import ActionHarness, ActionResult, HarnessError
from .project_launch import register_project_check
from .project_workspace import explicit_write_targets, violations as write_violations, publish_workspace
from .schema import GoalState, TaskAction
from .workspace_snapshot import tree_identity, copy_verified_workspace
from .observation_funnel import project_action_result
from .project_deadline import project_deadline
from .model_session import InputBudgetError
from .model_io import ModelCommand
from .project_output_validation import normalize_role_output, validate_role_output
from .project_evidence import record_delivery, executor_evidence_ids, select_evidence

ARCHITECTURE = 'rwkv-lh.planned-autonomous-executor.v1'


@dataclass(frozen=True)
class RoleReply:
    command: dict
    checkpoint: dict
    evidence: dict


def definition(name, properties, *, description):
    return {'name': name, 'description': description, 'parameters': {'type': 'object',
        'properties': properties, 'required': list(properties), 'additionalProperties': False}}


STRING = {'type': 'string', 'minLength': 1}


def role_definitions(role, harness):
    if role == 'planner':
        return [definition('submit_plan', {'plan': deepcopy(planner.PLAN_SCHEMA)},
            description='Submit the initial plan for autonomous RWKV execution, without online quality review.')]
    if role != 'executor':
        raise ValueError('current project roles are planner and executor')
    register_project_check(harness)
    receipts = {'type': 'array', 'items': STRING, 'uniqueItems': True}
    return deepcopy([*harness.g1i_tool_definitions(),
        definition('select_step', {'task_id': STRING},
            description='Select any declared plan step, including revisiting one. Preserve the same project State. This does not prove dependencies or completion.'),
        definition('report_step', {'task_id': STRING,
            'status': {'type': 'string', 'enum': ['progress', 'done', 'blocked']},
            'summary': STRING, 'evidence_ids': receipts},
            description='Record your step claim and actual receipts. Keep executing in the same State; no reviewer is called. This does not switch steps or verify correctness.'),
        definition('finish_work', {'status': {'type': 'string', 'enum': ['finished', 'blocked']},
            'summary': STRING, 'evidence_ids': receipts},
            description='End the entire run with your report verbatim, even if steps remain or tests were not run. Finished is your claim, not verified success.'),
        definition('read_receipt', {'evidence_id': STRING},
            description='Retrieve an existing receipt by its listed receipt:N handle. Return its original body again; this does not rerun a tool.')])


class ProjectRuntime:
    def __init__(self, ledger, roles, *, harness=None):
        self.db, self.roles = ledger, roles
        self.harness = harness or ActionHarness()
        register_project_check(self.harness)
        self.started = None
        self.initial_elapsed = 0.0

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
            s['feedback'] = {'kind': kind, **value}
            s['inbox'] = None
        self.db.update(kind, change)

    def expand_evidence(self, evidence_id, *, executor_lane):
        state = self.db.state()
        if (not state['active'] or state['active']['id'] != executor_lane
                or evidence_id not in executor_evidence_ids(state)):
            raise ValueError('receipt is not authorized for this project')
        evidence = deepcopy(state['evidence'][evidence_id])
        raw = evidence['result'].get('raw_receipt')
        if raw:
            path = (self.db.root / raw['path']).resolve(strict=True)
            if self.db.root not in path.parents:
                raise ValueError('raw receipt outside records')
            body = json.loads(path.read_text())
            if digest(body) != raw['content_digest']:
                raise ValueError('raw receipt digest mismatch')
            evidence['raw_result'] = body
        def select(s):
            select_evidence(s, executor_lane, evidence_id, evidence)
            s['feedback'] = {'kind': 'receipt_requested', 'evidence_id': evidence_id,
                'request_operation_id': s['inbox']['operation_id']}
            s['inbox'] = None
        self.db.update('evidence_selected', select)

    def _request(self):
        s = self.db.state()
        if s['plan'] is None:
            role, lane = 'planner', 'planner'
            workspace, materials = capture_materials(s['workspace'], s['request'],
                expected_digest=s['workspace_digest'])
            payload = planner.build_input(s['request'], feedback=s['feedback'],
                workspace=workspace, materials=materials, protected_paths=s['protected_paths'],
                remaining=self.remaining())
        else:
            role, lane = 'executor', s['active']['id']
            payload = executor.build_input(s['active'], project_state=s, remaining=self.remaining())
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
        self.db.update('call_reserved', lambda state: state.update(calls=state['calls'] + 1))
        identifier = self.db.begin_operation('model', {'role': role, 'lane': lane,
            'input': payload, 'input_digest': digest(payload), 'plan_version': s['plan_version']})
        if s.get('record_generation_snapshots', False):
            from .project_generation_snapshots import capture_snapshot
            capture_snapshot(self.db, identifier)
        reply = self.roles.request(role, lane, payload, definitions, s['sessions'].get(lane))
        def change(state):
            record_delivery(state, lane, payload)
            state['sessions'][lane] = reply.checkpoint
            state['inbox'] = {'role': role, 'lane': lane, 'command': reply.command,
                'operation_id': identifier, 'plan_version': s['plan_version']}
        self.db.finish_operation(identifier, {'command': reply.command, 'evidence': reply.evidence}, mutate=change)

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
            self._feedback(name, role=role, evidence_id=inbox['operation_id'])
            return
        definitions = role_definitions(role, self.harness)
        accepted, _ = normalize_role_output(role, ModelCommand(name, params), definitions)
        validate_role_output(role, receipt['intent']['input'], accepted, definitions)
        params = accepted.arguments
        if role == 'planner':
            self.db.install_plan(params['plan'])
        elif name == 'select_step':
            self.db.select_step(**params)
        elif name == 'report_step':
            self.db.report_step(**params)
        elif name == 'finish_work':
            self.db.finish_work(**params)
        elif name == 'read_receipt':
            self.expand_evidence(params['evidence_id'], executor_lane=inbox['lane'])
        else:
            self._tool(name, params, inbox['lane'])

    def _tool(self, name, params, lane):
        s = self.db.state()
        if not s['active'] or s['active']['id'] != lane:
            raise ValueError('stale worker assignment')
        task = work_map(s).get(s['current_step_id'])
        if task is None:
            raise ValueError('select_step is required before workspace tools')
        allowed = {d['name'] for d in self.harness.g1i_tool_definitions()}
        if name not in allowed:
            raise ValueError('unknown execution operation')
        action = self.harness.normalize_action(TaskAction(name, params))
        goal = GoalState.create(request=task['objective'], workspace_root=s['workspace'],
                                constraints=task['interfaces'])
        with self.harness.action_transaction(goal):
            before_tree = tree_identity(s['workspace'])
            if digest(before_tree) != s['workspace_digest']:
                raise ValueError('workspace changed outside the recorded worker')
            policy = {'scope': task['scope'], 'protected': protected_paths(s)}
            violations = write_violations(explicit_write_targets(self.harness, action), **policy)
            identifier = self.db.begin_operation('tool', {'assignment_id': lane, 'name': name,
                'arguments': action.arguments, 'before': s['workspace_digest'], 'task_id': task['id'],
                'source_operation_id': s['inbox']['operation_id']})
            transaction = self.db.root / 'tool_transactions' / identifier
            transaction.mkdir(parents=True)
            staged = transaction / 'workspace'
            if violations:
                result = ActionResult(name, False, error={'type': 'ScopeViolation',
                    'message': 'Write rejected before execution: ' + ', '.join(violations)})
            else:
                copy_verified_workspace(s['workspace'], staged, exclude_git=False)
                isolated = GoalState.create(request=goal.request, workspace_root=str(staged),
                                            constraints=task['interfaces'])
                # Do not catch cancellation, process loss, or uncertain tool errors.
                result = self.harness.execute(action, isolated)
                staged_tree = tree_identity(staged, allow_links=True)
                changed = [p for p in before_tree.keys() | staged_tree.keys()
                           if before_tree.get(p) != staged_tree.get(p)]
                violations = write_violations(changed, before=before_tree, after=staged_tree, **policy)
                violations = sorted(set(violations) | {p for p, value in staged_tree.items()
                    if value['kind'] not in ('file', 'directory')})
                if violations:
                    result = ActionResult(name, False, output=result.output, exit_code=result.exit_code,
                        metadata={'isolated_result': result.to_dict(), 'workspace_committed': False},
                        error={'type': 'ScopeViolation', 'message': 'Isolated changes rejected: ' + ', '.join(violations)})
                else:
                    if tree_identity(s['workspace']) != before_tree:
                        raise ValueError('workspace changed before isolated publication')
                    if changed:
                        publish_workspace(s['workspace'], staged)
                    result.metadata['workspace_committed'] = bool(changed)
                shutil.rmtree(staged)
            after_tree = tree_identity(s['workspace'])
            current = digest(after_tree)
            raw = result.to_dict()
            raw['metadata']['changed_paths'] = sorted(p for p in before_tree.keys() | after_tree.keys()
                if before_tree.get(p) != after_tree.get(p))
            projected = project_action_result(raw, operation=name, arguments=action.arguments,
                                              focus_text=goal.request)
            projected['scope_violation'] = violations
            def change(state):
                self.db.invalidate(state, current)
                state['inbox'] = None
                state['feedback'] = {'kind': 'tool_returned', 'evidence_id': identifier}
                if not result.success:
                    # A known local failure is an observation for the same worker.
                    # The model chooses repair or an explicit handoff; unknown
                    # outcomes and scope violations still use their hard gates.
                    state['feedback'] = {'kind': 'execution_failed', 'evidence_id': identifier,
                        'assignment_id': lane, 'task_id': task['id']}
            # Raw evidence is retained separately from the model-facing projection.
            raw_path = self.db.root / 'raw_tools'
            raw_path.mkdir(exist_ok=True)
            (raw_path / (identifier + '.json')).write_text(json.dumps(raw, ensure_ascii=False, indent=2) + '\n')
            projected['raw_receipt'] = {'path': 'raw_tools/' + identifier + '.json', 'content_digest': digest(raw)}
            self.db.finish_operation(identifier, projected, mutate=change, raw_result=raw)

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
                    turns = 0
                    while self.db.state()['status'] == 'running':
                        if max_turns is not None and turns >= max_turns:
                            reason = 'checkpoint_yield'
                            break
                        if not self.db.state()['inbox']:
                            remaining = self.remaining()
                            if remaining['calls'] <= 0 or remaining['seconds'] <= 0:
                                reason = 'resource_budget_exhausted'
                                break
                            self._request()
                            turns += 1
                        consumed = self.db.state()['inbox']
                        try:
                            self._consume()
                            rejection = self.db.state()['role_rejections'].get(consumed['lane'])
                            if rejection and rejection['rejected_operation_id'] != consumed['operation_id']:
                                self.db.update('role_recovered', lambda state: state['role_rejections'].pop(consumed['lane'], None))
                        except (ValueError, KeyError, TypeError, HarnessError) as exc:
                            if self.db.state()['pending']:
                                raise
                            self._feedback(consumed['role'] + '_rejected', error=str(exc))
                        self._progress(consumed['operation_id'])
                        feedback = self.db.state()['feedback'] or {}
                        if feedback.get('kind') == 'model_output_budget_exhausted':
                            reason = 'model_output_budget_exhausted'
                            break
                        if consumed['role'] == 'planner' and feedback.get('kind') == 'planner_rejected':
                            reason = 'planner_protocol_error'
                            self.db.update('planning_failed', lambda state: state.update(
                                status='failed', stop_reason='planner_protocol_error'))
                            break
            except InputBudgetError as exc:
                reason = 'uncertain_operation' if self.db.state()['pending'] else 'model_input_budget_exhausted'
                self.db.update('input_budget_exhausted', lambda state: state.update(error={'type': type(exc).__name__, 'message': str(exc)}))
            except UncertainOperation:
                reason = 'uncertain_operation'
            except Exception as exc:
                reason = 'uncertain_operation' if self.db.state()['pending'] else 'execution_error'
                self.db.update('runtime_error', lambda state: state.update(error={'type': type(exc).__name__, 'message': str(exc)}))
            finally:
                self.db.update('runtime_checkpoint', lambda state: state.update(
                    elapsed=self.initial_elapsed + time.monotonic() - self.started))
        return self.result(reason)

    def result(self, reason=''):
        from .project_step_progress import build_step_progress
        s = self.db.state()
        ended = s['status'] in ('finished', 'blocked')
        tool_receipts = [r for r in s['evidence'].values() if r['kind'] == 'tool']
        result = {'architecture': ARCHITECTURE, 'status': s['status'] if ended else 'interrupted',
            'termination_reason': reason or s.get('stop_reason') or ('model_' + s['status'] if ended else 'interrupted'),
            'final': s['final'], 'final_claim': s['final_claim'],
            'model_finished': s['status'] == 'finished', 'completed': False, 'acceptance': 'not_evaluated',
            'model_calls': s['calls'], 'task_count': len(work_map(s)), 'verified_tasks': 0,
            'steps': build_step_progress(s)['steps'],
            'mutation_count': sum(bool(r['result'].get('metadata', {}).get('workspace_committed')) for r in tool_receipts),
            'workspace': s['workspace'], 'workspace_digest': s['workspace_digest'], 'elapsed': s['elapsed'],
            'diagnostics': {'next_role': None if ended or s['status'] == 'failed' else 'executor' if s['plan'] else 'planner',
                'pending_operation': s['pending'], 'runtime_error': s.get('error'),
                'last_obstacle': s['feedback'], 'rejections': deepcopy(s['role_rejections'])}}
        (self.db.root / 'RESULT.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        return result
