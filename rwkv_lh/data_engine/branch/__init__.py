"""Verified offline forks; the production runtime executes every replacement tool."""
from copy import deepcopy
import json
from pathlib import Path

from rwkv_lh.project_contracts import digest
from rwkv_lh.project_ledger import ProjectLedger
from rwkv_lh.project_generation_snapshots import validate_snapshot
from rwkv_lh.project_protocols import agent
from rwkv_lh.project_runtime import AgentReply
from rwkv_lh.project_trace import agent_boundaries
from rwkv_lh.workspace_snapshot import copy_verified_workspace, tree_identity
from rwkv_lh.transcript.parse import catalog, validate_assistant, validate_messages
from rwkv_lh.transcript.wire import render_body, parse_assistant
from rwkv_lh.data_engine.records import write_immutable
from rwkv_lh.data_engine.tasks import dump


def _boundary(ledger, operation_id):
    selected = []
    def visit(event):
        pending = event['state']['pending']
        if event['kind'] == 'operation_started' and pending and pending['id'] == operation_id:
            selected.append(event)
    tip = ledger.scan_verified_events(visit)
    if len(selected) != 1 or selected[0]['state']['pending']['kind'] != 'model':
        raise ValueError('fork requires one actual original model boundary')
    return tip, selected[0]


def fork_episode(source, output, operation_id):
    """Create a new ledger, never edit a sealed source or reuse its native State."""
    source, output = Path(source).resolve(strict=True), Path(output).resolve()
    if output.exists():
        raise ValueError('fork destination already exists; resume its confirmed ledger')
    if source == output or source in output.parents or output in source.parents:
        raise ValueError('fork output overlaps source')
    validate_fork(source)
    with ProjectLedger.read_snapshot(source / 'execution') as ledger:
        tip, boundary = _boundary(ledger, operation_id)
        if tip['state']['pending'] or tip['state']['inbox']:
            raise ValueError('cannot fork an uncertain source')
        list(agent_boundaries(source / 'execution'))
        before = validate_snapshot(ledger, operation_id)
        original = boundary['state']
        # An external process cannot be resurrected by a workspace snapshot.
        # Until process-state forks exist, fail closed for background histories.
        for message in original['transcript']:
            for call in message.get('tool_calls', []):
                if call['function']['name'] == 'Bash' and json.loads(call['function']['arguments']).get('run_in_background'):
                    raise ValueError('background process history requires a separate fork capability')
        tree = copy_verified_workspace(before, output / 'workspace', exclude_git=False,
                                       audit_path=output / 'SOURCE_COPY.json')
        write_immutable(output / 'INITIAL_TREE.json', dump(tree).encode())
        record = {'schema_version': 'rwkv-lh.correction-fork.v1', 'source': str(source),
                  'source_tip': tip['digest'], 'source_event': boundary['digest'],
                  'operation_id': operation_id, 'workspace_digest': digest(tree),
                  'prefix_digest': digest(original['transcript']),
                  'prefix_messages': len(original['transcript']),
                  'native_state': 'rebuild_from_corrected_production_prefix',
                  'source_training_eligible': tip['state'].get('correction_fork', {}).get('source_training_eligible', True)}
        from rwkv_lh.evaluation_policy import assert_training_source_allowed
        try:
            assert_training_source_allowed(source)
            assert_training_source_allowed(original.get('source_workspace', source))
        except ValueError:
            record['source_training_eligible'] = False
        permissions = original['permissions']
        db = ProjectLedger.create(output / 'execution', request=original['requests'][0]['text'],
            workspace=output / 'workspace', max_calls=original['max_calls'], max_seconds=original['max_seconds'],
            writable=permissions['writable'], protected_paths=permissions['protected'],
            rejection_limit=original['rejection_limit'])
        def inherit(state):
            state['transcript'] = deepcopy(original['transcript'])
            state['requests'] = deepcopy(original['requests'])
            for request in state['requests']:
                request['calls'] = 0
                request['receipt_ids'] = []
            state['requests'][-1].update(declaration=None, termination_reason=None)
            state.update(task_id=original.get('task_id', source.name), source_workspace=str(before),
                         record_generation_snapshots=True, correction_fork=record)
        with db.lease():
            db.update('offline_prefix_inherited', inherit)
        write_immutable(output / 'FORK.json', dump(record).encode())
    validate_fork(output)
    return record


def validate_fork(run, _seen=None):
    run = Path(run).resolve(strict=True)
    seen = set() if _seen is None else _seen
    if run in seen:
        raise ValueError('cyclic correction ancestry')
    seen.add(run)
    with ProjectLedger.read_snapshot(run / 'execution') as db:
        tip = db.scan_verified_events()
        record = tip['state'].get('correction_fork')
        if record is None:
            if (run / 'FORK.json').exists():
                raise ValueError('fork ledger provenance missing')
            return None
        if json.loads((run / 'FORK.json').read_text()) != record:
            raise ValueError('fork provenance changed')
        prefix = tip['state']['transcript'][:record['prefix_messages']]
        if digest(prefix) != record['prefix_digest']:
            raise ValueError('fork conversation prefix changed')
        permissions = tip['state']['permissions']
    source = Path(record['source'])
    validate_fork(source, seen)
    with ProjectLedger.read_snapshot(source / 'execution') as db:
        parent_tip, boundary = _boundary(db, record['operation_id'])
        before = validate_snapshot(db, record['operation_id'])
        if (parent_tip['digest'] != record['source_tip'] or boundary['digest'] != record['source_event']
                or boundary['state']['transcript'] != prefix or boundary['state']['permissions'] != permissions
                or digest(tree_identity(before)) != record['workspace_digest']):
            raise ValueError('fork differs from its actual source boundary')
    return record


class ReplacementThenStudent:
    """An offline one-turn intervention; all subsequent turns use ProjectSessions."""
    def __init__(self, run, message, student, *, teacher):
        self.run, self.student = Path(run), student
        self.record = validate_fork(run)
        if self.record is None:
            raise ValueError('replacement requires a verified fork')
        self.message, self.teacher = deepcopy(message), dict(teacher)
        write_immutable(self.run / 'REPLACEMENT.json', dump({'message': message, 'teacher': teacher}).encode())

    def _applied(self):
        state = ProjectLedger(self.run / 'execution').state()
        return any(r['kind'] == 'model' and r['result'].get('evidence', {}).get('offline_correction')
                   for r in state['evidence'].values())

    def preflight(self, lane, payload, definitions, checkpoint):
        if self._applied() and hasattr(self.student, 'preflight'):
            self.student.preflight(lane, payload, definitions, checkpoint)

    def request(self, lane, payload, definitions, checkpoint):
        if self._applied():
            return self.student.request(lane, payload, definitions, checkpoint)
        agent.validate_input(payload)
        if digest(payload['messages'][1:]) != self.record['prefix_digest']:
            raise ValueError('replacement is not at the frozen source boundary')
        validate_assistant(self.message, definitions)
        raw = render_body(self.message, catalog(definitions))
        message = parse_assistant(raw, definitions, id_prefix='call_' + str(len(payload['messages'])))
        if render_body(message, catalog(definitions)) != raw:
            raise ValueError('replacement is not canonical production bytes')
        validate_messages([*payload['messages'], message])
        command = {'function': 'assistant', 'params': {'message': message}}
        agent.validate_references(payload, command)
        # None deliberately makes the student rebuild State from the full exact
        # corrected prefix, including the replacement's real receipts and EOS.
        return AgentReply(command, None, {'offline_correction': True, 'teacher': self.teacher,
            'source_operation_id': self.record['operation_id'], 'rejected': False,
            'raw_generation': {'raw_output': raw, 'finish_reason': 'stop'}})
