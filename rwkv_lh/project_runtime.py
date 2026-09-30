"""One plan/decision/worker loop over a durable ledger and the existing Harness."""
from dataclasses import dataclass
from copy import deepcopy
import json
from pathlib import Path
import shutil
import time

from .project_contracts import digest, fields, text, strings, work_map, protected_paths, goal_check_context
from .project_ledger import ProjectLedger, UncertainOperation
from .project_protocols import planner, decision, executor
from .harness import ActionHarness, ActionResult, HarnessError
from .project_workspace import explicit_write_targets, violations as write_violations, publish_workspace
from .schema import GoalState, TaskAction
from .workspace_snapshot import tree_identity, copy_verified_workspace
from .observation_funnel import project_action_result
from .project_deadline import project_deadline
from .model_session import InputBudgetError
from .model_io import ModelCommand
from .project_output_validation import normalize_role_output, validate_schema
from .project_evidence import (evidence_stream, executor_observations, record_delivery,
                               executor_evidence_ids, select_evidence)

ARCHITECTURE = 'rwkv-lh.goal-decision-execution.v5'


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
    # Full schemas already specify every parameter, requirement and constraint.
    # Copy custom Harness contracts without repeating them as description prose.
    return deepcopy(_role_definitions(role, harness))


def _role_definitions(role, harness):
    if role == 'planner':
        read_file = next(item for item in harness.g1i_tool_definitions() if item['name'] == 'read_file')
        return [read_file, definition('read_files', {'requests': {
                    'type': 'array', 'items': read_file['parameters'], 'minItems': 1}},
                    description='Read every explicitly requested file in order, preserving separate read-only receipts.'),
                definition('submit_plan', {'plan': planner.PLAN_SCHEMA}, description='Submit the complete current plan contract.'),
                definition('submit_checks', {'checks': {'type': 'array', 'items': planner.CHECK_SCHEMA, 'minItems': 1},
                    'rationale': STRING, 'replacements': {'type': 'array', 'items': planner.REPLACEMENT_SCHEMA}},
                    description='Bind independent original-goal checks after implementation, without creating a project plan.'),
                definition('review_checks', {'verdict': {'type': 'string', 'enum': ['accept', 'reject']},
                    'issues': {'type': 'array', 'items': STRING, 'uniqueItems': True}},
                    description='Independently review goal proof coverage; acceptance is not execution success.'),
                definition('review_plan', {'verdict': {'type': 'string', 'enum': ['accept', 'reject']},
                    'issues': {'type': 'array', 'items': STRING, 'uniqueItems': True}},
                    description='Independently review a candidate; accept requires no unresolved issues.'),
                definition('revise_plan', {'plan': planner.PLAN_SCHEMA,
                    'replacements': {'type': 'array', 'items': planner.REPLACEMENT_SCHEMA}},
                    description='Explicitly replace erroneous checks using original requirements and failure evidence.'),
                definition('advise', {'text': STRING, 'evidence_ids': {'type': 'array', 'items': STRING}},
                           description='Return diagnostic advice, never an execution fact.')]
    if role == 'executor':
        return [*harness.g1i_tool_definitions(), definition('request_info', {'evidence_id': STRING},
                    description='Retrieve an existing receipt using an authorized references.request_info.evidence_id; goal IDs and file paths are not receipt IDs.'),
            definition('report_work', {
            'status': {'type': 'string', 'enum': ['submitted', 'blocked']}, 'summary': STRING,
            'evidence_ids': {'type': 'array', 'items': STRING}}, description='Report local work or a gap, not global completion.'),
            definition('yield_work', {'summary': STRING, 'evidence_ids': {'type': 'array', 'items': STRING}},
                description='Report local progress and return direction control without claiming task completion.')]
    common = {'reason': STRING}
    definitions = [definition(name, {**common, **extra}, description=description) for name, extra, description in (
        ('delegate', {'task_id': STRING, 'advice_ids': {'type': 'array', 'items': STRING}}, 'Delegate the original goal directly, or an existing ready planned task; optionally reference work-scoped diagnosis.'),
        ('continue_current', {'task_id': STRING, 'advice_ids': {'type': 'array', 'items': STRING}}, 'Continue an unchanged assignment along its saved executor State.'),
        ('verify', {'task_id': STRING}, 'Run the declared checks on a copy of the current workspace.'),
        ('bind_checks', {'task_id': STRING}, 'Request independent goal-check construction and review after submitted direct work; no project plan required.'),
        ('accept_task', {'task_id': STRING, 'verification_id': STRING}, 'Judge that current evidence satisfies the original task objective.'),
        ('request_info', {'evidence_id': STRING}, 'Retrieve an existing receipt by evidence_id; delegate or continue work for new observations.'),
        ('replan', {'subject_id': {'enum': ['project']}}, 'Request strong planning or an evidenced revision; reason describes the gap.'),
        ('help', {'subject_id': STRING}, 'Request strong-model diagnosis for an existing task or project; reason describes the uncertainty.'),
        ('finish', {'task_id': STRING}, 'Select a worker report verbatim for delivery after current goal acceptance.'),
        ('blocked', {'subject_id': {'enum': ['project']}}, 'Record the missing external condition in the audit reason.'))]
    for item in definitions:
        if item['name'] in ('delegate', 'continue_current'):
            item['parameters']['properties']['handoff'] = decision.HANDOFF_SCHEMA
            item['description'] += ' Optional handoff passes an explicit task focus and authorized receipts, never execution authority.'
    return definitions


class ProjectRuntime:
    def __init__(self, ledger, roles, *, harness=None):
        self.db, self.roles = ledger, roles
        self.harness = harness or ActionHarness()
        self.started = None
        self.initial_elapsed = 0.0

    def remaining(self):
        s = self.db.state()
        elapsed = (self.initial_elapsed + time.monotonic() - self.started
                   if self.started is not None else s['elapsed'])
        return {'calls': max(0, s['max_calls'] - s['calls']), 'seconds': max(0.0, s['max_seconds'] - elapsed)}

    def unit_remaining(self):
        s = self.db.state()
        unit = s['work_unit'] or {}
        elapsed = (self.initial_elapsed + time.monotonic() - self.started
                   if self.started is not None else s['elapsed'])
        spent = elapsed - unit['started_elapsed'] if unit.get('started_elapsed') is not None else 0.0
        return {'calls': max(0, s['unit_calls'] - unit.get('calls', 0)) if s['unit_calls'] is not None else None,
                'seconds': max(0.0, s['unit_seconds'] - spent) if s['unit_seconds'] is not None else None}

    def _feedback(self, kind, **value):
        def change(s):
            previous = s['feedback']
            if kind in ('planner_rejected', 'decision_rejected', 'executor_rejected'):
                inbox = s.get('inbox') or {}
                receipt = s['evidence'].get(inbox.get('operation_id'), {})
                raw = receipt.get('result', {}).get('evidence', {}).get('raw_generation', {})
                value['rejected_operation_id'] = inbox.get('operation_id')
                if isinstance(raw.get('raw_output'), str):
                    value['rejected_output'] = raw['raw_output']
                    value['rejected_operation_id'] = inbox['operation_id']
            if kind == 'decision_rejected':
                while (previous or {}).get('kind') == 'decision_rejected':
                    previous = previous.get('previous_feedback')
                value['previous_feedback'] = previous
            s['feedback'] = {'kind': kind, **value}
            if kind in ('planner_rejected', 'decision_rejected', 'executor_rejected'):
                # Keep rejection identity separate from transient control/evidence feedback.
                s['role_rejections'][inbox['lane']] = dict(s['feedback'])
                if kind == 'executor_rejected':
                    select_evidence(s, decision.LANE, inbox['operation_id'], {
                        'kind': 'executor_rejection', 'operation_id': inbox['operation_id'],
                        'assignment_id': inbox['lane'], 'command': inbox['command'],
                        **value, 'is_execution_evidence': False})
            s['inbox'] = None
        self.db.update(kind, change)

    def expand_evidence(self, evidence_id, *, executor_lane=None):
        """Expose one identity-checked receipt requested by the decision role."""
        state = self.db.state()
        if executor_lane is not None and (not state['active'] or state['active']['id'] != executor_lane
                or evidence_id not in executor_evidence_ids(state)):
            raise ValueError('receipt is not authorized for this assignment')
        evidence = state['evidence'].get(evidence_id)
        if evidence is None or evidence['kind'] == 'model':
            raise ValueError('unknown expandable evidence')
        expanded = dict(evidence)
        raw = evidence['result'].get('raw_receipt')
        if raw:
            path = (self.db.root / raw['path']).resolve(strict=True)
            if self.db.root not in path.parents:
                raise ValueError('raw receipt outside records')
            body = json.loads(path.read_text())
            if digest(body) != raw['content_digest']:
                raise ValueError('raw receipt digest mismatch')
            expanded['raw_result'] = body
        lane = executor_lane or decision.LANE
        def select(s):
            select_evidence(s, lane, evidence_id, expanded)
            s['inbox'] = None
        self.db.update('evidence_selected', select)

    def _request(self):
        s = self.db.state()
        planning = s.get('planner_request')
        candidate = s['pending_plan']
        if s['pending_checks'] or planning == 'checks':
            pending_checks = s['pending_checks']
            role, lane, planning = 'planner', pending_checks['lane'] if pending_checks else 'goal-check-author', 'review_checks' if pending_checks else 'checks'
            payload = planner.build_input(s['request'], feedback=planner.review_feedback(s, lane) if pending_checks else s['feedback'],
                protected_paths=protected_paths(s), evidence=[{'id': key, **value}
                    for key, value in s['evidence'].items() if value['kind'] != 'model'],
                workspace=tree_identity(s['workspace']), mode=planning, remaining=self.remaining(),
                goal_context=goal_check_context(s))
        elif candidate:
            role, lane, planning = 'planner', candidate['lane'], 'review'
            payload = planner.build_input(s['request'], plan=candidate['plan'],
                feedback=planner.review_feedback(s, lane), protected_paths=s['protected_paths'],
                evidence=[{'id': key, **value} for key, value in s['evidence'].items() if value['kind'] != 'model'],
                workspace=tree_identity(s['workspace']), mode='review', remaining=self.remaining(),
                review_context={key: value for key, value in candidate.items() if key != 'plan'}
                    | {'previous_plan': s['plan']})
        elif planning:
            role, lane = 'planner', 'planner'
            payload = planner.build_input(s['request'], plan=s['plan'], feedback=s['feedback'],
                protected_paths=s['protected_paths'],
                evidence=[{'id': key, **value} for key, value in s['evidence'].items() if value['kind'] != 'model'],
                workspace=tree_identity(s['workspace']), mode='diagnose' if planning == 'diagnose' else 'plan',
                target_contracts=s.get('planner_target_contracts'), remaining=self.remaining())
        elif s['active'] and s['control'] == 'executor':
            role, lane = 'executor', s['active']['id']
            selected, updates = evidence_stream(s, lane)
            payload = executor.build_input(s['active'], observations=executor_observations(s),
                feedback=executor.local_feedback(s), selected_evidence=selected, evidence_updates=updates,
                project_state=s, remaining=self.remaining(), unit_remaining=self.unit_remaining())
        else:
            payload = decision.build_input(s, remaining=self.remaining())
            role, lane = 'decision', decision.LANE
            if any(key != lane and value.get('binding', {}).get('role') == role
                   for key, value in s['sessions'].items()):
                raise ValueError('legacy decision input State cannot resume; start a new run')
        definitions = role_definitions(role, self.harness)
        preflight = getattr(self.roles, 'preflight', None)
        if preflight is not None:
            preflight(role, lane, payload, definitions, s['sessions'].get(lane))
        def reserve(state):
            state['calls'] += 1
            if role == 'executor':
                state['work_unit']['calls'] += 1
                if state['work_unit']['started_elapsed'] is None:
                    state['work_unit']['started_elapsed'] = self.initial_elapsed + time.monotonic() - self.started
        self.db.update('call_reserved', reserve)
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
                'operation_id': identifier, 'plan_version': s['plan_version'], 'planning': planning}
        self.db.finish_operation(identifier, {'command': reply.command, 'evidence': reply.evidence}, mutate=change)

    def _consume(self):
        s = self.db.state()
        inbox = s['inbox']
        command = inbox['command']
        fields(command, ('function', 'params'))
        name, params = command['function'], command['params']
        role = inbox['role']
        if not isinstance(params, dict):
            raise ValueError('parameter object required')
        normalized, _identity_trace = normalize_role_output(role, ModelCommand(name, params),
            role_definitions(role, self.harness))
        command = normalized.to_wire_dict()
        params = command['params']
        if name == 'protocol_rejected':
            receipt = s['evidence'][inbox['operation_id']]['result']['evidence']
            if receipt.get('rejected') is not True:
                raise ValueError('protocol rejection requires host attestation')
            fields(params, ('error',))
            self._feedback(role + '_rejected', error=text(params['error']))
            return
        if name == 'model_output_budget_exhausted':
            receipt = s['evidence'][inbox['operation_id']]['result']['evidence']
            if params or receipt.get('known_budget_exhaustion') is not True:
                raise ValueError('output budget interruption requires a host-attested response')
            self._feedback('model_output_budget_exhausted', role=role, evidence_id=inbox['operation_id'])
            return
        if role == 'planner':
            if name == 'read_files':
                self._planner_reads(params, inbox['lane'])
                return
            if name == 'read_file':
                self._planner_read(params, inbox['lane'])
                return
            if inbox['planning'] in ('checks', 'review_checks') and name == 'advise':
                self.db.return_goal_check_advice(params)
                return
            if inbox['planning'] == 'review_checks':
                if name != 'review_checks':
                    raise ValueError('independent goal review requires review_checks')
                self.db.resolve_goal_check_review(params)
            elif inbox['planning'] == 'checks':
                if name != 'submit_checks':
                    raise ValueError('goal proof construction requires submit_checks')
                self.db.propose_goal_checks(**params)
            elif inbox['planning'] == 'review':
                if name != 'review_plan':
                    raise ValueError('independent review requires review_plan')
                self.db.resolve_plan_review(params)
            elif inbox['planning'] == 'diagnose':
                if name != 'advise':
                    raise ValueError('diagnosis requires advise')
                fields(params, ('text', 'evidence_ids'))
                text(params['text']); strings(params['evidence_ids'])
                if set(params['evidence_ids']) - s['evidence'].keys():
                    raise ValueError('unknown advice evidence')
                def advised(state):
                    advice = {**params, 'subject_id': state['planner_subject_id'], 'is_execution_evidence': False}
                    state['advice'][inbox['operation_id']] = advice
                    state['feedback'] = {'kind': 'strong_advice', 'advice_id': inbox['operation_id'], **advice}
                    state['planner_request'] = None
                    state['inbox'] = None
                self.db.update('advised', advised)
            else:
                if name not in ('submit_plan', 'revise_plan'):
                    raise ValueError('planning requires submit_plan')
                fields(params, ('plan', 'replacements') if name == 'revise_plan' else ('plan',))
                self.db.propose_plan(params['plan'], expected_version=inbox['plan_version'],
                    replacements=params.get('replacements', ()))
            return
        if role == 'executor':
            if name == 'request_info':
                fields(params, ('evidence_id',))
                self.expand_evidence(params['evidence_id'], executor_lane=inbox['lane'])
            elif name == 'yield_work':
                fields(params, ('summary', 'evidence_ids'))
                strings(params['evidence_ids'])
                self.db.report_progress(inbox['lane'], **params)
            elif name == 'report_work':
                fields(params, ('status', 'summary', 'evidence_ids'))
                strings(params['evidence_ids'])
                self.db.report_work(inbox['lane'], **params)
            else:
                self._tool(name, params, inbox['lane'])
            return
        definitions = {d['name']: d for d in role_definitions('decision', self.harness)}
        if name not in definitions:
            raise ValueError('decision role cannot execute tools')
        validate_schema(params, definitions[name]['parameters'])
        text(params['reason'])
        if inbox['plan_version'] != s['plan_version']:
            raise ValueError('stale plan version')
        current = decision.build_input(s, remaining=self.remaining())
        source = s['evidence'][inbox['operation_id']]['intent']
        if (inbox['lane'] != decision.LANE or source['lane'] != inbox['lane']
                or source['input']['boundary']['id'] != current['boundary']['id']):
            raise ValueError('stale decision boundary')
        if s['workspace_digest'] != self.db.workspace_digest():
            raise ValueError('stale judgment or workspace identity')
        decision.validate_response(current, command)
        if name == 'delegate':
            strings(params['advice_ids'])
            self.db.delegate(params['task_id'], expected_version=inbox['plan_version'], advice_ids=params['advice_ids'],
                             handoff=params.get('handoff'))
        elif name == 'continue_current':
            strings(params['advice_ids'])
            self.db.continue_current(params['task_id'], advice_ids=params['advice_ids'], handoff=params.get('handoff'))
        elif name == 'accept_task':
            self.db.accept_task(params['task_id'], verification_id=params['verification_id'], reason=params['reason'])
        elif name == 'verify':
            self._verify(params['task_id'])
        elif name == 'bind_checks':
            self.db.update('goal_check_binding_requested', lambda state: state.update(
                planner_request='checks', planner_subject_id=params['task_id'], inbox=None,
                feedback={'kind': 'goal_check_binding_requested', 'reason': params['reason']}))
        elif name == 'request_info':
            self.expand_evidence(params['evidence_id'])
        elif name in ('help', 'replan'):
            def request(state):
                state['planner_request'] = 'diagnose' if name == 'help' else 'plan'
                state['planner_subject_id'] = params['subject_id']
                failures = []
                for lane, rejection in state['role_rejections'].items():
                    identifier = rejection['rejected_operation_id']
                    receipt = state['evidence'][identifier]
                    role = receipt['intent']['role']
                    assigned = receipt['intent']['input'].get('assignment')
                    if (params['subject_id'] != 'project' and role == 'executor'
                            and assigned['task']['id'] != params['subject_id']):
                        continue
                    failures.append({'operation_id': identifier, 'lane': lane, 'role': role,
                        'error': rejection['error'], 'command': (receipt['result'].get('evidence', {}).get('rejected_command')
                            or receipt['result']['command']),
                        'raw_generation': receipt['result'].get('evidence', {}).get('raw_generation'),
                        'receipt_digest': digest(receipt), 'is_execution_evidence': False})
                state['planner_target_contracts'] = planner.diagnostic_contracts(self.harness)
                state['feedback'] = {'kind': name, 'subject_id': params['subject_id'],
                    'reason': params['reason'], 'model_failures': failures}
                if name == 'replan' and state['active']:
                    assignment = state['active']
                    state['suspended'][assignment['task']['id']] = assignment
                    state['active'] = None
                    state['control'] = 'decision'
                state['inbox'] = None
            self.db.update('assistance_requested', request)
        elif name == 'finish':
            if not self.db.completion_ready():
                raise ValueError('completion requires current accepted proof of the complete goal and every planned task')
            final = s['reports'][params['task_id']]['summary']
            self.db.update('completed', lambda state: state.update(status='completed', final=final, inbox=None))
        elif name == 'blocked':
            self.db.update('blocked', lambda state: state.update(status='blocked', final=params['reason'], inbox=None))

    def _planner_reads(self, params, lane):
        """Consume every explicit read, resuming from durable receipts after a crash."""
        schema = next(item['parameters'] for item in role_definitions('planner', self.harness)
                      if item['name'] == 'read_files')
        validate_schema(params, schema)  # Validate the entire batch before reading.
        requests = params['requests']
        state = self.db.state()
        operation = state['inbox']['operation_id']
        done = [receipt for receipt in state['evidence'].values()
                if receipt['kind'] == 'planner_read'
                and receipt['intent'].get('model_operation_id') == operation]
        for index, receipt in enumerate(done):
            if (index >= len(requests) or receipt['intent'].get('call_index') != index
                    or receipt['intent']['arguments'] != self.harness.normalize_action(
                        TaskAction('read_file', requests[index])).arguments
                    or receipt['intent']['workspace_digest'] != state['workspace_digest']):
                raise ValueError('planner read batch receipt does not match its original call')
        for index in range(len(done), len(requests)):
            self._planner_read(requests[index], lane, batch={
                'model_operation_id': operation, 'call_index': index, 'call_count': len(requests)})

    def _planner_read(self, params, lane, *, batch=None):
        """Publish a bounded read receipt to the same planning/review lane, never a write."""
        schema = next(item['parameters'] for item in role_definitions('planner', self.harness)
                      if item['name'] == 'read_file')
        validate_schema(params, schema)
        action = self.harness.normalize_action(TaskAction('read_file', params))
        tool = self.harness.definition('read_file')
        if not tool.read_only or tool.side_effect:
            raise ValueError('planner inspection requires a read-only action')
        s = self.db.state()
        before = self.db.workspace_digest()
        if before != s['workspace_digest']:
            raise ValueError('workspace changed before planner inspection')
        identifier = self.db.begin_operation('planner_read', {'lane': lane, 'name': 'read_file',
            'arguments': action.arguments, 'workspace_digest': before, **(batch or {})})
        staged = self.db.root / 'planner_reads' / identifier / 'workspace'
        copy_verified_workspace(s['workspace'], staged)
        goal = GoalState.create(request=s['request'], workspace_root=str(staged), constraints=[])
        result = self.harness.execute(action, goal).to_dict()
        if self.db.workspace_digest() != before or digest(tree_identity(staged)) != before:
            raise ValueError('workspace changed during planner inspection')
        shutil.rmtree(staged.parent)
        def returned(state):
            if batch is None or batch['call_index'] + 1 == batch['call_count']:
                state['inbox'] = None
            state['feedback'] = {'kind': 'planner_read_returned', 'lane': lane,
                'evidence_id': identifier, 'success': result['success']}
        self.db.finish_operation(identifier, result, mutate=returned)

    def _tool(self, name, params, lane):
        s = self.db.state()
        if not s['active'] or s['active']['id'] != lane:
            raise ValueError('stale worker assignment')
        allowed = {d['name'] for d in self.harness.g1i_tool_definitions()}
        if name not in allowed:
            raise ValueError('unknown execution operation')
        action = self.harness.normalize_action(TaskAction(name, params))
        goal = GoalState.create(request=s['active']['task']['objective'], workspace_root=s['workspace'],
                                constraints=s['active']['task']['interfaces'])
        with self.harness.action_transaction(goal):
            before_tree = tree_identity(s['workspace'])
            if digest(before_tree) != s['workspace_digest']:
                raise ValueError('workspace changed outside the recorded worker')
            policy = {'scope': s['active']['task']['scope'], 'protected': protected_paths(s)}
            violations = write_violations(explicit_write_targets(self.harness, action), **policy)
            identifier = self.db.begin_operation('tool', {'assignment_id': lane, 'name': name,
                'arguments': action.arguments, 'before': s['workspace_digest']})
            transaction = self.db.root / 'tool_transactions' / identifier
            transaction.mkdir(parents=True)
            staged = transaction / 'workspace'
            if violations:
                result = ActionResult(name, False, error={'type': 'ScopeViolation',
                    'message': 'Write rejected before execution: ' + ', '.join(violations)})
            else:
                copy_verified_workspace(s['workspace'], staged, exclude_git=False)
                isolated = GoalState.create(request=goal.request, workspace_root=str(staged),
                                            constraints=s['active']['task']['interfaces'])
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
                        'assignment_id': lane, 'task_id': state['active']['task']['id']}
                if violations:
                    key = state['active']['task']['id']
                    report = {'assignment_id': lane, 'status': 'blocked', 'authority': 'scope_violation',
                        'summary': 'Unauthorized workspace writes rejected without publication',
                        'paths': violations, 'evidence_ids': [identifier]}
                    state['reports'][key] = report
                    state['task_status'][key] = 'blocked'
                    state['active'] = None
                    state['control'] = 'decision'
                    state['feedback'] = report
            # Raw evidence is retained separately from the model-facing projection.
            raw_path = self.db.root / 'raw_tools'
            raw_path.mkdir(exist_ok=True)
            (raw_path / (identifier + '.json')).write_text(json.dumps(raw, ensure_ascii=False, indent=2) + '\n')
            projected['raw_receipt'] = {'path': 'raw_tools/' + identifier + '.json', 'content_digest': digest(raw)}
            self.db.finish_operation(identifier, projected, mutate=change, decision_result=raw)

    def _verify(self, task_id):
        s = self.db.state()
        if s['active'] or task_id not in s['reports'] or s['reports'][task_id]['status'] != 'submitted':
            raise ValueError('verification requires a reported local submission')
        task = work_map(s)[task_id]
        if not task['checks']:
            raise ValueError('verification requires reviewed nonempty checks; request replan to bind them')
        current = self.db.workspace_digest()
        if current != s['workspace_digest']:
            self.db.refresh_workspace()
            raise ValueError('workspace changed; refresh decision before verification')
        identifier = self.db.begin_operation('verification', {'task_id': task_id, 'checks': task['checks']})
        root = self.db.root / 'verification' / identifier
        root.mkdir(parents=True)
        checks = []
        for check in task['checks']:
            # Each public check gets the same frozen starting tree, not prior check side effects.
            workspace = root / digest(check)
            copy_verified_workspace(s['workspace'], workspace)
            goal = GoalState.create(request=check['purpose'], workspace_root=str(workspace), constraints=[])
            action = TaskAction('check_command', {'argv': check['argv'], 'cwd': check['cwd'],
                'expected_exit_code': 0, 'timeout': min(120.0, max(0.1, self.remaining()['seconds']))})
            result = self.harness.execute(action, goal)
            checks.append({'check_id': check['id'], 'check_digest': digest(check),
                'passed': bool(result.success and result.exit_code == 0), 'result': result.to_dict()})
        self.db.finish_verification(identifier, task_id, checks, workspace_digest=current)

    def run(self, *, max_turns=None):
        self.started = time.monotonic()
        self.initial_elapsed = self.db.state()['elapsed']
        reason = ''
        with self.db.lease():
            try:
                with project_deadline(self.remaining()['seconds']):
                    self.db.require_recoverable()
                    turns = 0
                    while self.db.state()['status'] not in ('completed', 'blocked'):
                        if max_turns is not None and turns >= max_turns:
                            reason = 'checkpoint_yield'
                            break
                        if not self.db.state().get('inbox'):
                            remaining = self.remaining()
                            if remaining['calls'] <= 0 or remaining['seconds'] <= 0:
                                reason = 'resource_budget_exhausted'
                                break
                            self._request()
                            turns += 1
                        try:
                            consumed = self.db.state()['inbox']
                            self._consume()
                            rejection = self.db.state()['role_rejections'].get(consumed['lane'])
                            if rejection and rejection['rejected_operation_id'] != consumed['operation_id']:
                                self.db.update('role_recovered', lambda state:
                                    state['role_rejections'].pop(consumed['lane'], None))
                        except (ValueError, KeyError, TypeError, HarnessError) as exc:
                            # Executable operations reserve before side effects.
                            # Never turn a reserved unknown outcome into a retry.
                            if self.db.state()['pending']:
                                raise
                            role = (self.db.state().get('inbox') or {}).get('role', 'decision')
                            self._feedback(role + '_rejected', error=str(exc))
                        s = self.db.state()
                        if (s.get('feedback') or {}).get('kind') == 'model_output_budget_exhausted':
                            reason = 'model_output_budget_exhausted'
                            break
                        if s['active'] and s['control'] == 'executor' and not s['pending'] and not s.get('inbox'):
                            unit = s['work_unit']
                            elapsed = self.initial_elapsed + time.monotonic() - self.started
                            if s['unit_calls'] is not None and unit['calls'] >= s['unit_calls']:
                                self.db.yield_execution(cause='unit_call_budget')
                            elif (s['unit_seconds'] is not None and unit['started_elapsed'] is not None
                                  and elapsed - unit['started_elapsed'] >= s['unit_seconds']):
                                self.db.yield_execution(cause='unit_time_budget')
            except InputBudgetError as exc:
                reason = 'uncertain_operation' if self.db.state()['pending'] else 'model_input_budget_exhausted'
                self.db.update('input_budget_exhausted', lambda state: state.update(
                    error={'type': type(exc).__name__, 'message': str(exc)}))
            except UncertainOperation:
                reason = 'uncertain_operation'
            except Exception as exc:
                reason = 'uncertain_operation' if self.db.state()['pending'] else 'execution_error'
                self.db.update('runtime_error', lambda state: state.update(error={'type': type(exc).__name__, 'message': str(exc)}))
            finally:
                elapsed = self.initial_elapsed + time.monotonic() - self.started
                self.db.update('runtime_checkpoint', lambda state: state.update(elapsed=elapsed))
        return self.result(reason)

    def result(self, reason=''):
        s = self.db.state()
        if s['status'] in ('completed', 'blocked'):
            next_role = None
        elif s['pending_plan'] or s['pending_checks'] or s.get('planner_request'):
            next_role = 'planner'
        elif s['active'] and s['control'] == 'executor':
            next_role = 'executor'
        else:
            next_role = 'decision'
        rejections = {}
        for lane, rejection in s['role_rejections'].items():
            identifier = rejection.get('rejected_operation_id')
            receipt = s['evidence'].get(identifier, {})
            intent = receipt.get('intent', {})
            rejections[identifier] = {'role': intent.get('role'), 'lane': lane,
                'operation_id': identifier, 'error': rejection.get('error')}
        model_failures = []
        for identifier, receipt in s['evidence'].items():
            if receipt['kind'] != 'model':
                continue
            command = receipt['result']['command']
            if command['function'] in ('protocol_rejected', 'model_output_budget_exhausted'):
                intent = receipt['intent']
                model_failures.append({'role': intent['role'], 'lane': intent['lane'],
                    'operation_id': identifier,
                    'error': command['params'].get('error', command['function'])})
            elif identifier in rejections:
                model_failures.append(rejections[identifier])
        feedback = s.get('feedback') or {}
        if s.get('error') and s['status'] == 'running' and (
                s['pending'] or reason in ('execution_error', 'model_input_budget_exhausted')):
            last_obstacle = {'kind': 'runtime_error', **s['error']}
        elif feedback.get('kind') == 'plan_review_rejected':
            last_obstacle = {key: feedback[key] for key in
                ('kind', 'candidate_digest', 'review_operation_id', 'issues')}
        elif feedback.get('kind') in ('planner_rejected', 'decision_rejected', 'executor_rejected'):
            last_obstacle = {key: feedback.get(key) for key in ('kind', 'error', 'rejected_operation_id')}
        elif feedback.get('kind') == 'model_output_budget_exhausted':
            last_obstacle = {key: feedback.get(key) for key in ('kind', 'role', 'evidence_id')}
        elif s.get('error'):
            last_obstacle = {'kind': 'runtime_error', **s['error']}
        else:
            last_obstacle = None
        diagnostics = {'next_role': next_role, 'runtime_error': s.get('error'),
            'last_obstacle': last_obstacle,
            'pending_operation': {key: s['pending'][key] for key in ('id', 'kind')} if s['pending'] else None,
            'pending_plan_digest': s['pending_plan']['candidate_digest'] if s['pending_plan'] else None,
            'last_model_failure': model_failures[-1] if model_failures else None,
            'model_failure_count': len(model_failures)}
        result = {'architecture': ARCHITECTURE, 'status': s['status'] if s['status'] in ('completed', 'blocked') else 'interrupted',
            'termination_reason': reason or s['status'], 'final': s['final'], 'model_calls': s['calls'],
            'verified_tasks': sum(v == 'verified' for v in s['task_status'].values()),
            'task_count': len(s['task_status']), 'workspace': s['workspace'],
            'acceptance': ('public_plan_checks_passed' if s['plan'] else 'public_goal_checks_passed')
                if s['status'] == 'completed' else 'not_accepted',
            'assistance': 'strong_planned' if s['plan'] else 'on_demand',
            'hidden_acceptance_run': False, 'diagnostics': diagnostics}
        (self.db.root / 'RESULT.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        return result
