"""Durable autonomous execution ledger; claims never become verified success."""
from contextlib import contextmanager, closing
from copy import deepcopy
import fcntl
import json
from pathlib import Path, PurePosixPath
import sqlite3
from uuid import uuid4

from .project_contracts import digest, make_assignment, validate_plan, text, strings, make_goal, validate_goal, work_map
from .workspace_snapshot import tree_identity
from .project_record_store import RecordStore

PROTOCOL = 'rwkv-lh.project-ledger.v17'


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
            raise ValueError('unsupported project ledger protocol; start a new run')
        validate_goal(state['goal'])
        if state['goal']['request'] != state['request'] or state['goal']['protected_paths'] != state['protected_paths']:
            raise ValueError('original goal differs from owner authority')
        if state['plan'] is not None:
            validate_plan(state['plan'])

    @classmethod
    def create(cls, root, *, request, workspace, max_calls, max_seconds, protected_paths=()):
        import math
        from .project_contracts import scope_path
        strings(list(protected_paths))
        for path in protected_paths:
            scope_path(path)
        root = Path(root).resolve()
        workspace = Path(workspace).resolve(strict=True)
        if root == workspace or root in workspace.parents or workspace in root.parents:
            raise ValueError('project records must be outside workspace')
        if (type(max_calls) is not int or max_calls < 1 or type(max_seconds) not in (int, float)
                or not math.isfinite(max_seconds) or max_seconds <= 0):
            raise ValueError('positive finite budgets required')
        root.mkdir(parents=True, exist_ok=False)
        state = {'protocol': PROTOCOL, 'request': text(request), 'workspace': str(workspace),
            'workspace_digest': digest(tree_identity(workspace)), 'plan': None, 'plan_version': 0,
            'goal': make_goal(request, protected_paths), 'active': None, 'current_step_id': None,
            'reports': {}, 'pending': None, 'evidence': {}, 'feedback': None, 'sessions': {},
            'calls': 0, 'elapsed': 0.0, 'max_calls': max_calls, 'max_seconds': max_seconds,
            'status': 'running', 'final': None, 'final_claim': None,
            'role_rejections': {}, 'protected_paths': list(protected_paths),
            'selected_evidence': {}, 'input_delivery': {}, 'inbox': None}
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
        # This baseline records workspace versions, never accepted proof.
        state['workspace_digest'] = current

    def refresh_workspace(self):
        current = self.workspace_digest()
        return self.update('workspace_observed', lambda s: self.invalidate(s, current))

    def install_plan(self, plan):
        plan = validate_plan(plan)
        def change(state):
            if state['plan'] is not None or state['active']:
                raise ValueError('initial plan is already installed; no online replanning')
            if {PurePosixPath(p) for p in state['protected_paths']} - {PurePosixPath(p) for p in plan['protected_paths']}:
                raise ValueError('plan must preserve owner protected paths')
            state['plan'] = plan
            state['plan_version'] = 1
            state['active'] = make_assignment(state['goal'], assignment_id='W-' + uuid4().hex,
                plan_version=1, workspace_digest=state['workspace_digest'])
            state['feedback'] = {'kind': 'plan_installed', 'authority': 'unreviewed_planner_plan'}
            state['inbox'] = None
        return self.update('plan_installed', change)

    def select_step(self, task_id):
        def change(state):
            if task_id not in work_map(state):
                raise ValueError('unknown plan task')
            state['current_step_id'] = task_id
            state['feedback'] = {'kind': 'step_selected', 'task_id': task_id,
                'authority': 'executor_choice'}
            state['inbox'] = None
        return self.update('step_selected', change)

    @staticmethod
    def _claim(state, summary, evidence_ids):
        from .project_evidence import executor_evidence_ids
        text(summary); strings(evidence_ids)
        if set(evidence_ids) - executor_evidence_ids(state):
            raise ValueError('unknown or unauthorized report evidence')
        return {'summary': summary, 'evidence_ids': list(evidence_ids),
            'authority': 'executor_claim', 'source_operation_id': state['inbox']['operation_id'],
            'workspace_digest': state['workspace_digest']}

    def report_step(self, task_id, status, summary, evidence_ids):
        if status not in ('progress', 'done', 'blocked'):
            raise ValueError('unknown step claim')
        def change(state):
            if task_id not in work_map(state):
                raise ValueError('unknown plan task')
            report = {**self._claim(state, summary, evidence_ids), 'status': status}
            state['reports'][task_id] = report
            state['feedback'] = {'kind': 'step_reported', 'task_id': task_id, 'report': report}
            state['inbox'] = None
        return self.update('step_reported', change)

    def finish_work(self, status, summary, evidence_ids):
        if status not in ('finished', 'blocked'):
            raise ValueError('unknown final claim')
        def change(state):
            if state['pending'] or not state['active']:
                raise ValueError('finish requires a confirmed execution boundary')
            claim = {**self._claim(state, summary, evidence_ids), 'status': status}
            state.update(status=status, final=summary, final_claim=claim, inbox=None,
                         feedback={'kind': 'executor_finished', 'claim': claim})
        return self.update('executor_finished', change)

    def begin_operation(self, kind, payload):
        identifier = 'OP-' + uuid4().hex
        def change(state):
            if state['pending']:
                raise UncertainOperation(state['pending']['id'])
            state['pending'] = {'id': identifier, 'kind': kind, 'payload': deepcopy(payload),
                                'workspace_digest': state['workspace_digest']}
        self.update('operation_started', change)
        return identifier

    def finish_operation(self, identifier, result, *, mutate=None, raw_result=None):
        def change(state):
            if not state['pending'] or state['pending']['id'] != identifier:
                raise ValueError('operation receipt does not match intent')
            state['evidence'][identifier] = {'kind': state['pending']['kind'],
                'intent': state['pending']['payload'], 'result': deepcopy(result)}
            if mutate:
                mutate(state)
            if state['pending']['kind'] != 'model':
                from .project_evidence import publish_executor_receipt
                publish_executor_receipt(state, identifier, raw_result=raw_result)
            state['pending'] = None
        return self.update('operation_returned', change)

    def require_recoverable(self):
        self.scan_verified_events()
        state = self.state()
        if state['pending']:
            raise UncertainOperation('operation needs reconciliation: ' + state['pending']['id'])
        if self.workspace_digest() != state['workspace_digest']:
            raise ValueError('workspace differs from last confirmed receipt')
        return state
