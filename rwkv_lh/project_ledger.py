"""Durable single-agent session ledger; model claims never become verified success.

One session holds one workspace, one persistent agent conversation (one model
State) and the user's requests in order. A follow-up request appends a User
turn to the same conversation; it never resets the State or rewrites history.
"""
from contextlib import contextmanager, closing
from copy import deepcopy
import fcntl
import json
import math
from pathlib import Path
import sqlite3
from uuid import uuid4

from .project_contracts import digest, text
from .project_protocols import agent
from .transcript.parse import validate_messages
from .workspace_snapshot import tree_identity
from .project_record_store import RecordStore

PROTOCOL = 'rwkv-lh.coder.ledger.v3'
IMMUTABLE = ('protocol', 'session_id', 'permissions', 'initial_workspace_digest')
# Ended at a clean boundary; only a new user request (with any budget increase) continues.
ENDED = ('finished', 'blocked', 'interrupted')


class UncertainOperation(RuntimeError):
    pass


def _budgets(max_calls, max_seconds):
    if ((max_calls is not None and (type(max_calls) is not int or max_calls < 1))
            or (max_seconds is not None and (type(max_seconds) not in (int, float)
                or not math.isfinite(max_seconds) or max_seconds <= 0))):
        raise ValueError('positive finite budgets required')


def _request_record(index, request, position):
    return {'id': 'R' + str(index), 'text': text(request), 'message_index': position,
            'calls': 0, 'receipt_ids': [], 'declaration': None, 'termination_reason': None}


class ProjectLedger:
    def __init__(self, root, *, read_only=False):
        self.root = Path(root).resolve(strict=True)
        self.path = self.root / 'project.sqlite3'
        self.read_only = read_only
        if not self.path.is_file():
            raise FileNotFoundError(self.path)
        state = self.state()
        if state.get('protocol') != PROTOCOL:
            raise ValueError('unsupported project ledger protocol; start a new session')
        agent.validate_permissions(state['permissions'])
        validate_messages(state['transcript'])
        users = [index for index, message in enumerate(state['transcript'])
                 if message['role'] == 'user' and not agent.is_host_notice(message)]
        if [item['message_index'] for item in state['requests']] != users:
            raise ValueError('recorded user requests differ from the conversation')
        for item in state['requests']:
            if agent.request_message(item['text']) != state['transcript'][item['message_index']]:
                raise ValueError('recorded user request text differs from its User turn')

    @classmethod
    def create(cls, root, *, request, workspace, max_calls, max_seconds, writable=('.',), protected_paths=(),
               rejection_limit=3):
        """Start one session on an existing workspace with the user's first request."""
        session_permissions = agent.permissions(writable, protected_paths)
        root = Path(root).resolve()
        workspace = Path(workspace).resolve(strict=True)
        if root == workspace or root in workspace.parents or workspace in root.parents:
            raise ValueError('project records must be outside workspace')
        _budgets(max_calls, max_seconds)
        if type(rejection_limit) is not int or rejection_limit < 1:
            raise ValueError('positive integer rejection limit required')
        initial_digest = digest(tree_identity(workspace))
        root.mkdir(parents=True, exist_ok=False)
        state = {'protocol': PROTOCOL, 'session_id': 'S-' + uuid4().hex, 'permissions': session_permissions,
            'workspace': str(workspace), 'workspace_digest': initial_digest,
            'initial_workspace_digest': initial_digest,
            'requests': [_request_record(1, request, 0)], 'transcript': [agent.request_message(request)],
            'consecutive_rejections': 0, 'rejection_limit': rejection_limit,
            'pending': None, 'evidence': {}, 'feedback': None, 'sessions': {}, 'rejections': [],
            'calls': 0, 'elapsed': 0.0, 'max_calls': max_calls, 'max_seconds': max_seconds,
            'status': 'running', 'stop_reason': None, 'final': None, 'final_claim': None, 'inbox': None}
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
            fixed = {key: deepcopy(state[key]) for key in IMMUTABLE}
            mutate(state)
            if any(state[key] != value for key, value in fixed.items()):
                raise ValueError('session identity and permissions are immutable')
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

    def current_request(self, state=None):
        return (state or self.state())['requests'][-1]

    def add_request(self, request, *, extra_calls=0, extra_seconds=0.0):
        """A user follow-up: same conversation, same State; budgets only grow.

        Allowed only at a clean ended boundary: no pending effect, no unconsumed
        model output, and the previous request finished, blocked or interrupted.
        """
        if type(extra_calls) is not int or extra_calls < 0 or type(extra_seconds) not in (int, float) \
                or not math.isfinite(extra_seconds) or extra_seconds < 0:
            raise ValueError('budget increases must be nonnegative and finite')
        def change(state):
            if state['pending'] or state['inbox'] or state['status'] not in ENDED:
                raise ValueError('a follow-up request requires an ended, confirmed session boundary')
            state['requests'].append(_request_record(len(state['requests']) + 1, request, len(state['transcript'])))
            state['transcript'].append(agent.request_message(request))
            if state['max_calls'] is not None:
                state['max_calls'] += extra_calls
            if state['max_seconds'] is not None:
                state['max_seconds'] += extra_seconds
            state.update(status='running', stop_reason=None, final=None, final_claim=None, consecutive_rejections=0,
                         error=None, feedback={'kind': 'user_request', 'request_id': state['requests'][-1]['id']})
        return self.update('user_request', change)

    def begin_tool_operation(self, payload):
        """Persist the next prevalidated batch call before any effect can occur."""
        identifier = 'OP-' + uuid4().hex
        def change(state):
            if state['pending']:
                raise UncertainOperation(state['pending']['id'])
            inbox = state['inbox']
            if not inbox or not inbox.get('batch'):
                raise ValueError('tool intent requires a prevalidated assistant batch')
            selected = inbox['batch'][inbox['cursor']]
            if (payload['source_operation_id'] != inbox['operation_id']
                    or payload['session_id'] != state['session_id']
                    or payload['name'] != selected['name']
                    or payload['requested_arguments'] != selected['arguments']
                    or payload['tool_call_id'] != selected['id']
                    or payload['request_id'] != state['requests'][-1]['id']):
                raise ValueError('tool intent differs from the model-selected operation')
            state['pending'] = {'id': identifier, 'kind': 'tool', 'payload': deepcopy(payload),
                                'workspace_digest': state['workspace_digest']}
        self.update('operation_started', change)
        return identifier

    def finish_request(self, declaration, declaration_receipt):
        """The agent's finish_work: a declaration recorded as a claim, never acceptance."""
        if declaration.get('outcome') not in ('finished', 'blocked'):
            raise ValueError('unknown agent declaration')
        text(declaration.get('summary'))
        def change(state):
            if state['pending'] or not state['inbox']:
                raise ValueError('finish_work requires a confirmed batch boundary')
            claim = {'outcome': declaration['outcome'], 'summary': declaration['summary'], 'authority': 'agent_claim',
                     'request_id': state['requests'][-1]['id'], 'source_operation_id': state['inbox']['operation_id'],
                     'workspace_digest': state['workspace_digest']}
            state['transcript'].append(deepcopy(declaration_receipt))
            state['requests'][-1].update(declaration=deepcopy(declaration), termination_reason='model_finished')
            state.update(status=declaration['outcome'], final=declaration['summary'], final_claim=claim, inbox=None,
                         stop_reason='model_finished', feedback={'kind': 'agent_declared', 'claim': claim})
        return self.update('agent_declared', change)

    def interrupt(self, reason, *, notice=None):
        """Host stop at a clean boundary (budget, repeated rejection, truncation); not completion.

        An optional host notice for the agent is recorded in the same event.
        """
        text(reason)
        def change(state):
            if state['pending']:
                raise ValueError('an interruption cannot hide an unconfirmed operation')
            if notice is not None:
                if not agent.is_host_notice(notice):
                    raise ValueError('interruption notice must be a host notice')
                state['transcript'].append(deepcopy(notice))
            state['requests'][-1]['termination_reason'] = reason
            state.update(status='interrupted', stop_reason=reason, inbox=None,
                         feedback={'kind': 'interrupted', 'reason': reason})
        return self.update('interrupted', change)

    def begin_operation(self, kind, payload):
        identifier = 'OP-' + uuid4().hex
        def change(state):
            if state['pending']:
                raise UncertainOperation(state['pending']['id'])
            state['pending'] = {'id': identifier, 'kind': kind, 'payload': deepcopy(payload),
                                'workspace_digest': state['workspace_digest']}
        self.update('operation_started', change)
        return identifier

    def finish_operation(self, identifier, result, *, mutate=None):
        def change(state):
            if not state['pending'] or state['pending']['id'] != identifier:
                raise ValueError('operation receipt does not match intent')
            state['evidence'][identifier] = {'kind': state['pending']['kind'],
                'intent': state['pending']['payload'], 'result': deepcopy(result)}
            if mutate:
                mutate(state)
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
