"""Single-writer durable plan/receipt store. Unknown side effects never auto-replay."""
from contextlib import contextmanager, closing
from copy import deepcopy
import fcntl
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

from .project_contracts import assignment_dependencies_resumable
from .project_contracts import (digest, make_assignment, task_map, validate_plan, text, fields, strings,
    selected_task_advice, require_current_verification, make_goal, validate_goal,
    work_items, work_map, work_requirements, protected_paths, GOAL_ID, work_check_context, validate_check, affected_work)
from .workspace_snapshot import tree_identity
from .project_record_store import RecordStore

PROTOCOL = 'rwkv-lh.project-ledger.v16'


class UncertainOperation(RuntimeError):
    pass


class ProjectLedger:
    def __init__(self, root, *, read_only=False):
        self.root = Path(root).resolve(strict=True)
        self.path = self.root / 'project.sqlite3'
        self.read_only = read_only
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        state = self.state()
        if state.get('protocol') != PROTOCOL:
            raise ValueError('unsupported project ledger protocol')
        validate_goal(state['goal'])
        if state['goal']['request'] != state['request'] or state['goal']['protected_paths'] != state['protected_paths']:
            raise ValueError('original goal differs from owner authority')
        if state.get('plan') is not None:
            validate_plan(state['plan'])

    @classmethod
    def create(cls, root, *, request, workspace, max_calls, max_seconds, unit_calls=None, unit_seconds=None,
               protected_paths=(), require_initial_plan=False):
        import math
        from .project_contracts import scope_path, strings
        strings(list(protected_paths))
        for path in protected_paths:
            scope_path(path)
        if type(require_initial_plan) is not bool:
            raise ValueError('initial planning policy must be boolean')
        root = Path(root).resolve()
        workspace = Path(workspace).resolve(strict=True)
        if root == workspace or root in workspace.parents or workspace in root.parents:
            raise ValueError('project records must be outside workspace')
        if type(max_calls) is not int or max_calls < 1 or type(max_seconds) not in (int, float) or not math.isfinite(max_seconds) or max_seconds <= 0:
            raise ValueError('positive finite budgets required')
        if unit_calls is not None and (type(unit_calls) is not int or unit_calls < 1):
            raise ValueError('positive work-unit calls or no separate limit required')
        if unit_seconds is not None and (type(unit_seconds) not in (int, float) or not math.isfinite(unit_seconds) or unit_seconds <= 0):
            raise ValueError('positive finite work-unit seconds or no separate limit required')
        root.mkdir(parents=True, exist_ok=False)
        state = {'protocol': PROTOCOL, 'request': text(request), 'workspace': str(workspace),
            'workspace_digest': digest(tree_identity(workspace)), 'plan': None, 'plan_version': 0,
            'goal': make_goal(request, protected_paths), 'goal_checks': [], 'pending_checks': None, 'check_reviews': [],
            'planner_request': 'plan' if require_initial_plan else None,
            'planner_request_context': None,
            'task_status': {GOAL_ID: 'pending'}, 'reports': {}, 'verification': {}, 'active': None,
            'pending': None, 'evidence': {}, 'feedback': None, 'sessions': {},
            'calls': 0, 'elapsed': 0.0, 'max_calls': max_calls, 'max_seconds': max_seconds,
            'status': 'running', 'final': None, 'control': 'decision', 'suspended': {},
            'unit_calls': unit_calls, 'unit_seconds': unit_seconds, 'work_unit': None,
            'acceptance': {}, 'check_revisions': [], 'check_catalog': {}, 'advice': {},
            'role_rejections': {}, 'protected_paths': list(protected_paths),
            'selected_evidence': {}, 'input_delivery': {}, 'pending_plan': None, 'plan_reviews': []}
        with closing(sqlite3.connect(root / 'project.sqlite3')) as connection, connection:
            connection.execute('PRAGMA journal_mode=WAL')
            connection.execute('CREATE TABLE current (id INTEGER PRIMARY KEY CHECK(id=1), body TEXT NOT NULL)')
            connection.execute('CREATE TABLE events (seq INTEGER PRIMARY KEY, kind TEXT NOT NULL, body TEXT NOT NULL, digest TEXT NOT NULL)')
            RecordStore.create(connection)
            reference = RecordStore(connection).write(state)
            body = json.dumps(reference, ensure_ascii=False)
            connection.execute('INSERT INTO current VALUES (1,?)', (body,))
            connection.execute('INSERT INTO events VALUES (1,?,?,?)', ('created', body, digest(reference)))
        return cls(root)

    @contextmanager
    def lease(self):
        with (self.root / 'writer.lock').open('r' if self.read_only else 'a') as handle:
            lock = fcntl.LOCK_SH if self.read_only else fcntl.LOCK_EX
            fcntl.flock(handle, lock | fcntl.LOCK_NB)
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    @classmethod
    @contextmanager
    def read_snapshot(cls, root):
        """Pin an existing source before constructor validation opens SQLite.

        A reader must not create a lock file or inspect a writer's database and
        only afterwards discover that the writer owns it. Hold this lease for
        the entire extraction, including any source-dependent publication.
        """
        root = Path(root).resolve(strict=True)
        with (root / 'writer.lock').open('r') as handle:
            fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
            try:
                yield cls(root, read_only=True)
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    @contextmanager
    def _connection(self):
        if self.read_only:
            # immutable=1 prevents SQLite from creating or modifying WAL/SHM.
            # Never ignore committed data still present in an unfinished WAL.
            wal = Path(str(self.path) + '-wal')
            if wal.exists() and wal.stat().st_size:
                raise ValueError('read-only immutable ledger requires a checkpointed WAL')
            connection = sqlite3.connect(self.path.as_uri() + '?mode=ro&immutable=1', uri=True)
        else:
            connection = sqlite3.connect(self.path)
        with closing(connection), connection:
            yield connection

    def state(self):
        with self._connection() as connection:
            connection.execute('BEGIN')
            reference = json.loads(connection.execute('SELECT body FROM current WHERE id=1').fetchone()[0])
            return RecordStore(connection).read(reference)

    def verified_events(self):
        """Materialize verified events only when the caller needs every state."""
        records = []
        self.scan_verified_events(records.append)
        return records

    def scan_verified_events(self, visit=None):
        """Verify a fresh, consistent chain with bounded working memory.

        Visit is for in-memory projections only. Nothing may be published or
        executed until this method returns: a later row can invalidate the
        chain. The returned tip includes the verified current state. No caller
        cache, skipped prefix or unverified tail is accepted.
        """
        with self._connection() as connection:
            connection.execute('BEGIN')
            previous, count, tip, reference = None, 0, None, None
            store, verified = RecordStore(connection), set()
            rows = connection.execute('SELECT seq,kind,body,digest FROM events ORDER BY seq')
            for seq, kind, body, checksum in rows:
                reference = json.loads(body)
                expected = digest(reference) if previous is None else digest([previous, kind, reference])
                if checksum != expected or seq != count + 1 or (seq == 1 and kind != 'created'):
                    raise ValueError('project event digest chain mismatch')
                store.verify(reference, verified)
                tip = {'seq': seq, 'kind': kind, 'digest': checksum}
                if visit is not None:
                    visit({**tip, 'state': store.read(reference)})
                previous, count = checksum, seq
            current = json.loads(connection.execute('SELECT body FROM current WHERE id=1').fetchone()[0])
            if tip is None or reference != current:
                raise ValueError('project current state differs from event digest chain')
            tip['state'] = store.read(reference)
        return tip

    def update(self, kind, mutate):
        if self.read_only:
            raise ValueError('read-only ledger cannot be updated')
        with self._connection() as connection:
            connection.execute('BEGIN IMMEDIATE')
            reference = json.loads(connection.execute('SELECT body FROM current WHERE id=1').fetchone()[0])
            previous, previous_body = connection.execute('SELECT digest,body FROM events ORDER BY seq DESC LIMIT 1').fetchone()
            if reference != json.loads(previous_body):
                raise ValueError('project current state differs from event digest chain')
            store = RecordStore(connection)
            state = store.read(reference)
            mutate(state)
            reference = store.write(state)
            body = json.dumps(reference, ensure_ascii=False, allow_nan=False)
            connection.execute('INSERT INTO events(kind,body,digest) VALUES (?,?,?)', (kind, body, digest([previous, kind, reference])))
            connection.execute('UPDATE current SET body=? WHERE id=1', (body,))
        return deepcopy(state)

    def workspace_digest(self):
        return digest(tree_identity(self.state()['workspace']))

    @staticmethod
    def invalidate(state, current):
        if state['workspace_digest'] != current:
            for key, receipt in state['verification'].items():
                receipt['status'] = 'stale'
                if state['task_status'].get(key) in ('verified', 'checks_passed'):
                    state['task_status'][key] = 'awaiting_verification'
            state['acceptance'] = {}
            state['workspace_digest'] = current

    def refresh_workspace(self):
        current = self.workspace_digest()
        return self.update('workspace_observed', lambda s: self.invalidate(s, current))

    def propose_plan(self, plan, *, expected_version, replacements=()):
        plan = validate_plan(plan)
        def change(state):
            if state['plan_version'] != expected_version or state['pending_plan'] or state['pending_checks']:
                raise ValueError('stale or overlapping plan proposal')
            if set(state['protected_paths']) - set(plan['protected_paths']):
                raise ValueError('plan must preserve owner protected paths')
            if state['plan'] and set(state['plan']['protected_paths']) - set(plan['protected_paths']):
                raise ValueError('cannot remove protected paths')
            self._apply_plan(deepcopy(state), plan, expected_version=expected_version,
                             replacements=replacements, preflight=True)
            author = state['inbox']['operation_id']
            state['pending_plan'] = {'plan': deepcopy(plan), 'expected_version': expected_version,
                'replacements': deepcopy(list(replacements)), 'candidate_digest': digest(plan),
                'author_operation_id': author, 'lane': 'plan-review-' + author}
            state['inbox'] = None
        return self.update('plan_proposed', change)

    def resolve_plan_review(self, params):
        from .project_protocols.planner import validate_review
        validate_review(params)
        state = self.state()
        candidate, inbox = state['pending_plan'], state['inbox']
        if not candidate or inbox['lane'] != candidate['lane'] or inbox['plan_version'] != candidate['expected_version']:
            raise ValueError('review does not bind the pending candidate')
        receipt = state['evidence'][inbox['operation_id']]
        if digest(receipt['intent']['input']['plan']) != candidate['candidate_digest']:
            raise ValueError('review candidate digest mismatch')
        context = {key: value for key, value in candidate.items() if key != 'plan'} | {'previous_plan': state['plan']}
        if receipt['intent']['input']['review_context'] != context:
            raise ValueError('review context changed after request')
        if digest(receipt['intent']['input']['workspace']) != self.workspace_digest():
            self.refresh_workspace()
            raise ValueError('workspace changed after plan review request; fresh review required')
        review = {**deepcopy(params), 'candidate_digest': candidate['candidate_digest'],
            'author_operation_id': candidate['author_operation_id'], 'review_operation_id': inbox['operation_id'],
            'input_digest': receipt['intent']['input_digest'], 'is_execution_evidence': False}
        if params['verdict'] == 'accept':
            return self.install_plan(candidate['plan'], expected_version=candidate['expected_version'],
                                     replacements=candidate['replacements'], review=review)
        def reject(s):
            if s['pending_plan'] != candidate:
                raise ValueError('review candidate changed')
            s['plan_reviews'].append(review)
            s['pending_plan'] = None
            s['planner_request'] = 'plan'
            s['inbox'] = None
            s['feedback'] = {'kind': 'plan_review_rejected', **review, 'candidate_plan': candidate['plan']}
        return self.update('plan_review_rejected', reject)

    @staticmethod
    def _apply_plan(state, plan, *, expected_version, replacements=(), review=None, preflight=False):
        """One installation rule set, also evaluated on a copy before review."""
        if state['plan_version'] != expected_version:
            raise ValueError('stale plan version')
        old = state['plan']
        if set(state['protected_paths']) - set(plan['protected_paths']):
            raise ValueError('plan must preserve owner protected paths')
        old_tasks = task_map(old) if old else {}
        tasks = task_map(plan)
        changed_requirements = set()
        if old:
            if set(old['protected_paths']) - set(plan['protected_paths']):
                raise ValueError('cannot remove protected paths')
            before_requirements = {r['id']: r['text'] for r in old['requirements']}
            after_requirements = {r['id']: r['text'] for r in plan['requirements']}
            if before_requirements.keys() - after_requirements.keys():
                raise ValueError('requirement identities require explicit obligation migration; cannot erase')
            changed_requirements = {key for key, value in after_requirements.items()
                                    if before_requirements.get(key) != value}
            if changed_requirements and review is None and not preflight:
                raise ValueError('requirement interpretation changes require independent review')
            prior_checks = {c['id']: c for t in old['tasks'] for c in t['checks']}
            from .project_protocols.planner import validate_replacements
            validate_replacements(old, plan, replacements, state['evidence'])
            for task in plan['tasks']:
                for check in task['checks']:
                    if check['id'] in prior_checks and check != prior_checks[check['id']]:
                        raise ValueError('changed check identity requires a new identifier')
            # Initial MVP is conservative: tasks may be revised or added, not erased.
            if old_tasks.keys() - tasks.keys():
                raise ValueError('cannot erase existing tasks or their requirements')
        affected = affected_work(list(tasks.values()), {key for key, task in tasks.items()
            if old_tasks.get(key) != task or set(task['requirements']) & changed_requirements})
        if state['active']:
            active = state['active']
            if digest(tasks.get(active['task']['id'])) != active['contract_digest']:
                raise ValueError('cannot change active assignment contract')
            if active['task']['id'] in affected:
                raise ValueError('cannot change active assignment dependencies')
        if not old:
            # Optional decomposition supersedes the root work contract, never
            # its original goal or durable receipts. Old claims/State cannot
            # silently become claims for newly interpreted task contracts.
            for collection in ('task_status', 'reports', 'verification', 'acceptance', 'suspended'):
                state[collection].pop(GOAL_ID, None)
        for key, task in tasks.items():
            if key in affected:
                prior = old_tasks.get(key)
                # A first reviewed check binding changes proof obligations, not
                # an already submitted implementation claim. Never carry proof.
                binding_only = (prior is not None and not prior['checks'] and bool(task['checks'])
                    and not (set(task['requirements']) & changed_requirements)
                    and {k: v for k, v in prior.items() if k != 'checks'} ==
                        {k: v for k, v in task.items() if k != 'checks'})
                state['task_status'][key] = 'pending'
                if not binding_only:
                    state['reports'].pop(key, None)
                state['acceptance'].pop(key, None)
                state['suspended'].pop(key, None)
                if key in state['verification']:
                    state['verification'][key]['status'] = 'stale'
        state['plan'] = plan
        for task in plan['tasks']:
            for check in task['checks']:
                registered = state['check_catalog'].get(check['id'])
                identity = {'task_id': task['id'], 'check': check}
                if registered is not None and registered != identity:
                    raise ValueError('changed historical check identity requires a new identifier')
                state['check_catalog'][check['id']] = deepcopy(identity)
        state['plan_version'] += 1
        if review is not None:
            candidate = state['pending_plan']
            if not candidate or candidate['candidate_digest'] != digest(plan):
                raise ValueError('review candidate changed before installation')
            state['plan_reviews'].append(deepcopy(review))
            state['pending_plan'] = None
        if not old and replacements:
            raise ValueError('initial plan cannot replace checks')
        if replacements:
            state['check_revisions'].append({'plan_version': state['plan_version'],
                'replacements': deepcopy(list(replacements))})
        state['feedback'] = {'kind': 'plan_installed', 'rationale': plan['rationale']}
        state['inbox'] = None
        state['planner_request'] = None
        state['planner_request_context'] = None

    def install_plan(self, plan, *, expected_version, replacements=(), review=None):
        plan = validate_plan(plan)
        return self.update('plan_installed', lambda state: self._apply_plan(
            state, plan, expected_version=expected_version, replacements=replacements, review=review))

    @staticmethod
    def _validate_work_checks(state, checks, replacements):
        task_id = state.get('planner_subject_id')
        if state['active'] or task_id not in work_map(state):
            raise ValueError('work proof requires an inactive selected work contract')
        report = state['reports'].get(task_id)
        if not report or report['status'] != 'submitted':
            raise ValueError('work proof requires an actual submitted worker claim')
        if not isinstance(checks, list) or not checks:
            raise ValueError('reviewed nonempty goal checks required')
        seen = set()
        for check in checks:
            validate_check(check)
            if check['id'] in seen:
                raise ValueError('duplicate goal check identity')
            seen.add(check['id'])
            registered = state['check_catalog'].get(check['id'])
            if registered is not None and registered != {'task_id': task_id, 'check': check}:
                raise ValueError('changed historical check identity requires a new identifier')
        from .project_protocols.planner import validate_work_check_replacements
        old = work_items(state)
        new = deepcopy(old)
        next(t for t in new if t['id'] == task_id)['checks'] = deepcopy(checks)
        validate_work_check_replacements(old, new, replacements, state['evidence'])

    def propose_work_checks(self, checks, rationale, replacements):
        text(rationale)
        current = self.workspace_digest()
        def propose(s):
            if s['pending_plan'] or s['pending_checks'] or s['planner_request'] != 'checks':
                raise ValueError('goal checks require an explicit binding request')
            if current != s['workspace_digest']:
                raise ValueError('workspace changed before goal check proposal')
            self._validate_work_checks(s, checks, replacements)
            context = work_check_context(s)
            inbox = s['inbox']
            if (inbox['plan_version'] != s['plan_version']
                    or s['evidence'][inbox['operation_id']]['intent']['input']['work_context'] != context):
                raise ValueError('work check author context changed')
            author = s['inbox']['operation_id']
            s['pending_checks'] = {'checks': deepcopy(checks), 'rationale': rationale,
                'replacements': deepcopy(replacements), 'task_id': context['task']['id'],
                'work_digest': digest({k: v for k, v in context.items() if k != 'candidate'}),
                'workspace_digest': current, 'expected_version': s['plan_version'],
                'author_operation_id': author, 'lane': 'check-review-' + author}
            s['inbox'] = None
        return self.update('work_checks_proposed', propose)

    def return_planner_advice(self, params):
        """Return an explicit planning gap to RWKV, retaining unaccepted candidates."""
        fields(params, ('text', 'evidence_ids'))
        text(params['text']); strings(params['evidence_ids'])
        state = self.state()
        inbox = state['inbox']
        if not inbox or inbox['role'] != 'planner' or inbox['plan_version'] != state['plan_version']:
            raise ValueError('planner advice requires the current planning boundary')
        mode = inbox['planning']
        proof = mode in ('checks', 'review_checks')
        candidate = state['pending_checks'] if proof else state['pending_plan']
        receipt = state['evidence'][inbox['operation_id']]
        payload = receipt['intent']['input']
        from .project_protocols.planner import _diagnostic_feedback
        if (receipt['intent']['role'] != 'planner' or receipt['intent']['lane'] != inbox['lane']
                or payload['mode'] != mode
                or payload['assistance_request'] != _diagnostic_feedback(state['planner_request_context'])):
            raise ValueError('planner advice request identity changed')
        if proof:
            if state['planner_request'] != 'checks' or payload['work_context'] != work_check_context(state):
                raise ValueError('goal check advice context changed')
        elif mode not in ('plan', 'review', 'diagnose') or state['planner_request'] != ('diagnose' if mode == 'diagnose' else 'plan'):
            raise ValueError('planner advice requires its current request')
        if candidate:
            if mode not in ('review', 'review_checks') or inbox['lane'] != candidate['lane']:
                raise ValueError('planner advice is not bound to its proposal')
            if mode == 'review' and payload['plan'] != candidate['plan']:
                raise ValueError('plan advice candidate changed')
        elif mode in ('review', 'review_checks'):
            raise ValueError('review advice requires its unaccepted candidate')
        visible = {item['id'] for item in payload['evidence'] if item['kind'] != 'model'}
        if set(params['evidence_ids']) - visible:
            raise ValueError('unknown or undisclosed planner advice evidence')
        def advised(s):
            advice = {**deepcopy(params),
                'subject_id': state.get('planner_subject_id', 'project') if proof or mode == 'diagnose' else 'project',
                'is_execution_evidence': False,
                'planning_context': {'mode': mode, 'candidate': deepcopy(candidate),
                    'assistance_request': deepcopy(payload['assistance_request'])}}
            s['advice'][inbox['operation_id']] = advice
            s['feedback'] = {'kind': 'work_check_advice' if proof else 'strong_advice',
                'advice_id': inbox['operation_id'], 'mode': mode, 'candidate': deepcopy(candidate), **advice}
            s['pending_plan'] = None
            s['pending_checks'] = None
            s['planner_request'] = None
            s['planner_request_context'] = None
            s['inbox'] = None
            s['control'] = 'decision'
        return self.update('planner_advised', advised)

    def resolve_work_check_review(self, params):
        from .project_protocols.planner import validate_review
        validate_review(params)
        state = self.state()
        candidate, inbox = state['pending_checks'], state['inbox']
        if (not candidate or inbox['lane'] != candidate['lane']
                or inbox['plan_version'] != candidate['expected_version']
                or state['plan_version'] != candidate['expected_version']):
            raise ValueError('goal check review is not bound to its proposal')
        receipt = state['evidence'][inbox['operation_id']]
        if receipt['intent']['input']['work_context'] != work_check_context(state):
            raise ValueError('goal check review context changed')
        current = self.workspace_digest()
        context = work_check_context(state)
        if (current != candidate['workspace_digest']
                or digest({k: v for k, v in context.items() if k != 'candidate'}) != candidate['work_digest']):
            def stale(s):
                self.invalidate(s, current)
                s['pending_checks'] = None
                s['planner_request'] = 'checks'
                s['inbox'] = None
                s['feedback'] = {'kind': 'work_check_review_stale', 'candidate': candidate}
            return self.update('work_check_review_stale', stale)
        review = {**deepcopy(params), 'candidate': deepcopy(candidate),
            'review_operation_id': inbox['operation_id'], 'input_digest': receipt['intent']['input_digest'],
            'is_execution_evidence': False}
        def resolve(s):
            if s['pending_checks'] != candidate:
                raise ValueError('goal check proposal changed')
            s['check_reviews'].append(review)
            s['pending_checks'] = None
            s['inbox'] = None
            if params['verdict'] == 'reject':
                s['feedback'] = {'kind': 'work_check_review_rejected', **review}
                s['planner_request'] = 'checks'
                return
            self._validate_work_checks(s, candidate['checks'], candidate['replacements'])
            task_id = candidate['task_id']
            if task_id != s['planner_subject_id']:
                raise ValueError('check review task identity changed')
            if s['plan'] is None:
                s['goal_checks'] = deepcopy(candidate['checks'])
            else:
                next(t for t in s['plan']['tasks'] if t['id'] == task_id)['checks'] = deepcopy(candidate['checks'])
            for check in candidate['checks']:
                s['check_catalog'][check['id']] = {'task_id': task_id, 'check': deepcopy(check)}
            s['plan_version'] += 1
            if candidate['replacements']:
                s['check_revisions'].append({'plan_version': s['plan_version'],
                    'replacements': deepcopy(candidate['replacements'])})
            for key in affected_work(work_items(s), {task_id}):
                s['acceptance'].pop(key, None)
                s['suspended'].pop(key, None)
                if key in s['verification']:
                    s['verification'][key]['status'] = 'stale'
                # Proof changes preserve implementation claims, never accepted proof.
                s['task_status'][key] = ('awaiting_verification'
                    if s['reports'].get(key, {}).get('status') == 'submitted' else 'pending')
            s['planner_request'] = None
            s['planner_request_context'] = None
            s['feedback'] = {'kind': 'work_checks_bound', 'review_operation_id': inbox['operation_id']}
        return self.update('work_check_reviewed', resolve)

    @staticmethod
    def selected_advice(state, task_id, advice_ids):
        return selected_task_advice(state, task_id, advice_ids)

    def delegate(self, task_id, *, expected_version, advice_ids=(), handoff=None):
        current = self.workspace_digest()
        def change(state):
            if state['active']:
                raise ValueError('an active assignment already exists')
            if state['plan_version'] != expected_version:
                raise ValueError('stale plan version')
            self.invalidate(state, current)
            task = work_map(state).get(task_id)
            if task is None:
                raise ValueError('unknown task')
            suspended = state['suspended'].get(task_id)
            if suspended and suspended['contract_digest'] == digest(task):
                raise ValueError('unchanged suspended assignment requires continue_current')
            if any(state['task_status'][dep] != 'verified' for dep in task['dependencies']):
                raise ValueError('unverified dependencies')
            state['active'] = make_assignment(task, assignment_id='W-' + uuid4().hex,
                plan_version=expected_version, workspace_digest=current,
                requirements=work_requirements(state, task),
                dependencies=[{'task_id': dep, 'report': state['reports'].get(dep),
                               'verification': state['verification'][dep]} for dep in task['dependencies']])
            state['active']['local_context'] = {
                'protected_paths': protected_paths(state),
                'diagnostic_advice': self.selected_advice(state, task_id, advice_ids),
                'previous_report': deepcopy(state['reports'].get(task_id)),
                'previous_verification': deepcopy(state['verification'].get(task_id))}
            from .project_evidence import install_decision_handoff
            install_decision_handoff(state, state['active'], handoff)
            state['control'] = 'executor'
            state['work_unit'] = {'id': uuid4().hex, 'calls': 0, 'started_elapsed': None}
            state['suspended'].pop(task_id, None)
            state['task_status'][task_id] = 'executing'
            state['inbox'] = None
        return self.update('delegated', change)['active']

    def report_work(self, assignment_id, status, summary, evidence_ids):
        """One worker report boundary; progress keeps the active assignment."""
        from .project_contracts import strings
        if status not in ('progress', 'submitted', 'blocked'):
            raise ValueError('unknown worker status')
        text(summary)
        strings(evidence_ids)
        def change(state):
            active = state['active']
            if (not active or active['id'] != assignment_id or state['pending']
                    or state['control'] != 'executor'):
                raise ValueError('report requires a confirmed active execution boundary')
            from .project_evidence import executor_evidence_ids
            if set(evidence_ids) - executor_evidence_ids(state):
                raise ValueError(f'params.evidence_ids: unknown or unauthorized evidence reference; '
                                 f'permitted {sorted(executor_evidence_ids(state))!r}')
            report = {'assignment_id': assignment_id, 'summary': summary,
                      'evidence_ids': list(evidence_ids), 'authority': 'worker_claim'}
            if status == 'progress':
                active['local_context']['progress_report'] = report
                state['feedback'] = {'kind': 'execution_progress', 'report': deepcopy(report)}
            else:
                report['status'] = status
                key = active['task']['id']
                state['reports'][key] = report
                state['task_status'][key] = 'awaiting_verification' if status == 'submitted' else 'blocked'
                state['suspended'][key] = deepcopy(active)
                state['active'] = None
                state['feedback'] = report
            state['control'] = 'decision'
            state['inbox'] = None
        return self.update('execution_progress' if status == 'progress' else 'worker_reported', change)

    def continue_current(self, task_id, *, advice_ids=(), handoff=None):
        """Resume an unchanged assignment; never rebuild its recurrent State."""
        def change(s):
            active = s['active'] or s['suspended'].get(task_id)
            if not active or active['task']['id'] != task_id or s['control'] != 'decision':
                raise ValueError('no suspended current assignment')
            if active['contract_digest'] != digest(work_map(s)[task_id]):
                raise ValueError('assignment contract changed')
            if not assignment_dependencies_resumable(s, active):
                raise ValueError('unverified dependencies')
            s['active'] = deepcopy(active)
            s['active']['local_context']['diagnostic_advice'] = self.selected_advice(s, task_id, advice_ids)
            from .project_evidence import install_decision_handoff
            install_decision_handoff(s, s['active'], handoff)
            s['suspended'].pop(task_id, None)
            s['control'] = 'executor'
            s['work_unit'] = {'id': uuid4().hex, 'calls': 0, 'started_elapsed': None}
            s['task_status'][task_id] = 'executing'
            s['acceptance'].pop(task_id, None)
            prior_feedback = s['role_rejections'].get(active['id'])
            s['feedback'] = {'kind': 'execution_resumed', 'direction': 'continue_current', 'task_id': task_id,
                'previous_report': s['reports'].get(task_id),
                'verification': s['verification'].get(task_id),
                'protocol_feedback': prior_feedback if (prior_feedback or {}).get('kind') == 'executor_rejected' else None}
            s['inbox'] = None
        return self.update('execution_resumed', change)

    def yield_execution(self, *, cause):
        def change(s):
            if not s['active'] or s['pending'] or s.get('inbox'):
                raise ValueError('yield requires a confirmed execution boundary')
            s['control'] = 'decision'
            s['feedback'] = {'kind': 'execution_yielded', 'cause': cause,
                'previous_feedback': deepcopy(s['feedback']), 'unit': deepcopy(s['work_unit'])}
        return self.update('execution_yielded', change)

    def accept_task(self, task_id, *, verification_id, reason, deliver_report_id=None):
        text(reason)
        current = self.workspace_digest()
        def change(s):
            require_current_verification(s, task_id, verification_id, current)
            s['acceptance'][task_id] = {'verification_id': verification_id, 'reason': reason,
                'authority': 'decision_judgment', 'workspace_digest': current}
            s['task_status'][task_id] = 'verified'
            s['feedback'] = {'kind': 'task_accepted', 'task_id': task_id}
            s['inbox'] = None
            if deliver_report_id is not None:
                self._complete(s, deliver_report_id, current)
        return self.update('accepted_and_completed' if deliver_report_id is not None else 'task_accepted', change)

    @staticmethod
    def _completion_ready(s, current):
        return bool(work_items(s) and not s['active'] and not s['pending'] and not s['pending_plan']
            and not s['pending_checks'] and not s['planner_request']
            and s['workspace_digest'] == current
            and all(t['checks'] and s['task_status'][t['id']] == 'verified'
                and s['reports'].get(t['id'], {}).get('status') == 'submitted'
                and s['verification'].get(t['id'], {}).get('status') == 'passed'
                and s['acceptance'].get(t['id'], {}).get('verification_id') == s['verification'][t['id']]['operation_id']
                and s['acceptance'][t['id']]['workspace_digest'] == current
                and s['verification'][t['id']]['workspace_digest'] == current
                and s['verification'][t['id']]['task_digest'] == digest(t) for t in work_items(s)))

    @classmethod
    def _complete(cls, state, report_id, current):
        text(report_id)
        if not cls._completion_ready(state, current):
            raise ValueError('completion requires current accepted proof of the complete goal and every planned task')
        report = state['reports'].get(report_id)
        if not report or report['status'] != 'submitted':
            raise ValueError('delivery requires an existing submitted worker report')
        state.update(status='completed', final=report['summary'], inbox=None)

    def complete(self, report_id):
        current = self.workspace_digest()
        return self.update('completed', lambda state: self._complete(state, report_id, current))

    def begin_operation(self, kind, payload):
        identifier = 'OP-' + uuid4().hex
        def change(state):
            if state['pending']:
                raise UncertainOperation(state['pending']['id'])
            state['pending'] = {'id': identifier, 'kind': kind, 'payload': deepcopy(payload),
                                'workspace_digest': state['workspace_digest']}
        self.update('operation_started', change)
        return identifier

    def finish_operation(self, identifier, result, *, mutate=None, decision_result=None):
        def change(state):
            if not state['pending'] or state['pending']['id'] != identifier:
                raise ValueError('operation receipt does not match intent')
            state['evidence'][identifier] = {'kind': state['pending']['kind'],
                'intent': state['pending']['payload'], 'result': deepcopy(result)}
            if mutate:
                mutate(state)
            if state['pending']['kind'] != 'model':
                from .project_evidence import publish_decision_receipt
                publish_decision_receipt(state, identifier, raw_result=decision_result)
            state['pending'] = None
        return self.update('operation_returned', change)

    def check_digest(self, task_id, check_id):
        return digest(next(c for c in work_map(self.state())[task_id]['checks'] if c['id'] == check_id))

    def finish_verification(self, identifier, task_id, checks, *, workspace_digest):
        state = self.state()
        pending = state['pending']
        if (not pending or pending['id'] != identifier or pending['kind'] != 'verification'
                or pending['payload'].get('task_id') != task_id
                or pending['workspace_digest'] != workspace_digest):
            raise ValueError('verification receipt does not match intent')
        expected = {c['id']: digest(c) for c in work_map(state)[task_id]['checks']}
        if not expected:
            raise ValueError('verification requires bound nonempty checks')
        if len(checks) != len(expected) or {c['check_id'] for c in checks} != expected.keys():
            raise ValueError('verification checks are missing or duplicated')
        if any(c['check_digest'] != expected[c['check_id']] or type(c['passed']) is not bool for c in checks):
            raise ValueError('verification checks differ from contract')
        current = self.workspace_digest()
        if workspace_digest != current:
            raise ValueError('workspace changed during verification')
        def change(s):
            self.invalidate(s, current)
            passed = all(c['passed'] for c in checks)
            s['verification'][task_id] = {'status': 'passed' if passed else 'failed',
                'workspace_digest': current, 'task_digest': digest(work_map(s)[task_id]),
                'checks': deepcopy(checks), 'operation_id': identifier}
            s['task_status'][task_id] = 'checks_passed' if passed else 'failed'
            s['acceptance'].pop(task_id, None)
            s['feedback'] = {'kind': 'verification', 'task_id': task_id, 'passed': passed, 'checks': deepcopy(checks)}
            s['inbox'] = None
        return self.finish_operation(identifier, {'checks': checks}, mutate=change)

    def completion_ready(self):
        return self._completion_ready(self.state(), self.workspace_digest())

    def require_recoverable(self):
        self.scan_verified_events()
        state = self.state()
        if state['pending']:
            raise UncertainOperation('operation needs reconciliation: ' + state['pending']['id'])
        if self.workspace_digest() != state['workspace_digest']:
            raise ValueError('workspace differs from last confirmed receipt')
        return state
