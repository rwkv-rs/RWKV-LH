"""Read-only execution using the production controller and original model answers."""
from dataclasses import dataclass
from pathlib import Path
import json
import hashlib
import math
import signal
import shutil
import threading
import time
import traceback

from .controller import LongHorizonController
from .harness import ActionHarness
from .model import LongHorizonModel
from .model_session import create_model_session
from .run_lifecycle import RUN_LIFECYCLE_POLICY_KEY, run_lifecycle_policy_document
from .schema import RunStatus, RunState
from .store import LongHorizonStore


@dataclass(frozen=True)
class ReadOnlyJob:
    task_id: str
    request: str
    workspace: str
    output_dir: str
    max_calls: int = 6
    max_seconds: float = 300
    tool_scope: str = 'files'
    reconsider_from: str = ''
    advice: str = ''
    advice_model: str = ''


class ReadOnlyHarness(ActionHarness):
    def __init__(self, *args, tool_scope='inspect', **kwargs):
        if tool_scope not in ('files', 'inspect'):
            raise ValueError('unknown read-only tool scope')
        super().__init__(*args, **kwargs)
        self.tool_scope = tool_scope

    def g1i_tool_definitions(self, action_types=None):
        return [item for item in super().g1i_tool_definitions(action_types)
                if self.definition(item['name']).read_only
                and not self.definition(item['name']).side_effect
                and (self.tool_scope == 'inspect' or item['name'] == 'read_file')]


class ReadOnlyBudgetExpired(TimeoutError):
    pass


class _WallDeadlineExpired(BaseException):
    """Do not let protocol recovery or best-effort audit hooks swallow a deadline."""


class _BudgetedSession:
    def __init__(self, session, limit, deadline, audit_errors=()):
        self.session, self.limit, self.deadline = session, limit, deadline
        self.audit_errors = audit_errors
        self.calls = 0

    def __getattr__(self, name):
        return getattr(self.session, name)

    def generate(self, *args, **kwargs):
        if self.audit_errors:
            raise OSError('model trace persistence failed; generation stopped')
        if self.calls >= self.limit or time.monotonic() >= self.deadline:
            raise ReadOnlyBudgetExpired('generation budget exhausted')
        self.calls += 1
        return self.session.generate(*args, **kwargs)


class _ReadOnlyController(LongHorizonController):
    def _execute_decision(self, state, decision):
        definition = self.harness.definition(decision.command.name)
        if not definition.read_only or definition.side_effect:
            raise PermissionError('operation outside read-only permissions')
        if decision.command.name not in {d['name'] for d in self.harness.g1i_tool_definitions()}:
            raise PermissionError('operation outside selected read-only scope')
        return super()._execute_decision(state, decision)


def _save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def _prepare_reconsideration(job, workspace, output):
    previous = Path(job.reconsider_from).resolve(strict=True)
    raw_result = (previous / 'RESULT.json').read_bytes()
    result = json.loads(raw_result)
    snapshot = (previous / 'state_snapshot.json').read_bytes()
    state = RunState.from_dict(json.loads(snapshot))
    if result.get('tool_scope') != 'files' or job.tool_scope != 'files':
        raise ValueError('requested advice currently supports file-reading tasks only')
    if state.goal.request != job.request or Path(state.goal.workspace_root).resolve() != workspace:
        raise ValueError('advice cannot silently change the task or workspace')
    if (state.final_output or None) != result.get('final'):
        raise ValueError('parent answer and State do not agree')
    parent = state.lane_head('executor')
    if not parent:
        raise ValueError('no parent model State to continue')
    for action in state.actions.values():
        value = action.result or {}
        chunk = value.get('metadata', {}).get('chunk', {})
        if action.action_type == 'read_file' and value.get('success'):
            path = (workspace / chunk['source_ref']).resolve(strict=True)
            if not path.is_relative_to(workspace) or hashlib.sha256(path.read_bytes()).hexdigest() != chunk['source_sha256']:
                raise ValueError('source changed since the parent observation')
    # A finished job is immutable. Copy its local store and retain the original
    # model history separately; the new trace contains only the extra calls.
    shutil.copytree(previous / 'state', output / 'state')
    ancestor_trace = previous / 'PARENT_TRACE.jsonl'
    history = ancestor_trace.read_bytes() if ancestor_trace.exists() else b''
    (output / 'PARENT_TRACE.jsonl').write_bytes(
        history + (previous / 'model_trace.jsonl').read_bytes()
    )
    (output / 'PARENT_RESULT.json').write_bytes(raw_result)
    (output / 'PARENT_STATE_SNAPSHOT.json').write_bytes(snapshot)
    store = LongHorizonStore(output / 'state', checkpoint_retention=1000)
    copied = store.load(state.run_id)
    if copied.to_dict() != state.to_dict():
        raise ValueError('parent store is not the recorded immutable snapshot')
    info = {'directory': str(previous), 'result_sha256': hashlib.sha256(raw_result).hexdigest(),
            'state_sha256': hashlib.sha256(snapshot).hexdigest(), 'parent_checkpoint_id': parent,
            'parent_final_decision_id': state.final_decision_id,
            'parent_generation_started': result['generation_started'],
            'parent_elapsed_seconds': result['elapsed_seconds'], 'advice_model': job.advice_model}
    _save(output / 'CONTINUATION.json', info)
    return store, copied, info


def run_read_only_job(job, *, settings, session_factory=create_model_session):
    if (type(job.max_calls) is not int or job.max_calls < 1
            or type(job.max_seconds) not in (int, float)
            or not math.isfinite(job.max_seconds) or job.max_seconds <= 0):
        raise ValueError('positive integer calls and finite positive wall budget required')
    if job.tool_scope not in ('files', 'inspect'):
        raise ValueError('unknown read-only tool scope')
    advice_fields = (job.reconsider_from, job.advice, job.advice_model)
    if any(advice_fields) and not all(advice_fields):
        raise ValueError('reconsideration requires explicit advice and its model identity')
    if threading.current_thread() is not threading.main_thread():
        raise ValueError('run each job in a process main thread for deadline handling')
    workspace = Path(job.workspace).resolve(strict=True)
    if not workspace.is_dir():
        raise ValueError('workspace must be a directory')
    output = Path(job.output_dir).resolve()
    if job.reconsider_from:
        previous = Path(job.reconsider_from).resolve(strict=True)
        if previous == output or previous in output.parents or output in previous.parents:
            raise ValueError('reconsideration output must not overlap the parent run')
    if output == workspace or workspace in output.parents:
        raise ValueError('audit output must be outside the model workspace')
    output.mkdir(parents=True, exist_ok=False)
    records = []
    audit_errors = []
    trace_path = output / 'model_trace.jsonl'
    trace_path.touch(exist_ok=False)
    def audit(event):
        records.append(dict(event))
        try:
            with trace_path.open('a') as stream:
                stream.write(json.dumps(dict(event), ensure_ascii=False) + '\n')
        except Exception as exc:
            audit_errors.append({'event_type': event.get('type'), 'error': str(exc)})
            raise
    started = time.monotonic()
    state = None
    store = None
    continuation = None
    error = None
    termination = None
    def deadline(signum, frame):
        raise _WallDeadlineExpired('wall budget exhausted')
    old_handler = signal.signal(signal.SIGALRM, deadline)
    old_timer = signal.setitimer(signal.ITIMER_REAL, job.max_seconds)
    try:
        if job.reconsider_from:
            store, state, continuation = _prepare_reconsideration(job, workspace, output)
        harness = ReadOnlyHarness(tool_scope=job.tool_scope)
        model = LongHorizonModel(session_factory(settings=settings, audit_hook=audit), harness=harness)
        model.session = _BudgetedSession(model.session, job.max_calls, started + job.max_seconds, audit_errors)
        if state is None:
            store = LongHorizonStore(output / 'state', checkpoint_retention=1000)
            goal = model.create_literal_goal(job.request, str(workspace), runtime_policy={
                RUN_LIFECYCLE_POLICY_KEY: run_lifecycle_policy_document('goal')})
            state = store.create_run(goal, run_id=job.task_id)
        controller = _ReadOnlyController(store, model=model, harness=harness,
                                         max_transitions=job.max_calls, min_actions=0)
        _save(output / 'goal.json', state.goal.to_dict())
        if continuation is not None:
            from .summary_advice import make_advice_event
            event = make_advice_event('ADVICE-' + job.task_id, job.advice, 'external_strong_model', job.advice_model)
            _save(output / 'ADVICE_EVENT.json', event.to_dict())
            state.status = RunStatus.RUNNING
            state.final_output = ''
            terminal_id = next((key for key in reversed(state.causal_order)
                                if state.causal_records[key].event_type in ('run_completed', 'run_interrupted')), '')
            controller._persist(state, 'run_started', {
                **continuation, 'reason': 'owner_requested_reconsideration',
                'resumed': True, 'supersedes_terminal_event_id': terminal_id})
            model._append_event(state, state.model_states[continuation['parent_checkpoint_id']], event, controller._persist_callback)
        controller.run(state.run_id)
    except (Exception, _WallDeadlineExpired) as exc:
        termination = 'budget' if isinstance(exc, (ReadOnlyBudgetExpired, _WallDeadlineExpired)) else 'error'
        error = {'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()}
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        if old_timer[0]:
            signal.setitimer(signal.ITIMER_REAL, max(.001, old_timer[0] - (time.monotonic()-started)), old_timer[1])
    if state is not None:
        state = store.load(state.run_id)
    generations = [r for r in records if r['type'] == 'model_session_generation_started']
    items = []
    for event in state.model_events.values() if state is not None else ():
        if event.event_type != 'action_result':
            continue
        consumed = [r['request_id'] for r in generations
                    if r['input_checkpoint_id'] in state.model_states
                    and event.event_id in state.model_states[r['input_checkpoint_id']].event_ids]
        items.append({'event': event.to_model_dict(), 'event_id': event.event_id,
                      'consumed_by_requests': consumed})
    final = (state.final_output or None) if state is not None else None
    if continuation is not None and state.final_decision_id == continuation['parent_final_decision_id']:
        final = None  # The old submission remains in PARENT_RESULT, not a new delivery.
    result = {'id': job.task_id, 'final': final,
              'termination': termination or ('submitted' if state is not None and state.status == RunStatus.COMPLETED else 'budget'),
              'acceptance': 'unreviewable' if audit_errors else 'not_evaluated',
              'assistance': 'strong_advised' if job.reconsider_from else 'rwkv_independent',
              'continuation': continuation,
              'error': error, 'status': state.status.value if state is not None else 'not_started',
              'trace_complete': not audit_errors, 'trace_errors': audit_errors, 'tool_scope': job.tool_scope,
              'generation_started': len(generations), 'protocol_rejections': state.protocol_rejections if state is not None else 0,
              'actions': [a.to_dict() for a in state.actions.values()] if state is not None else [],
              'elapsed_seconds': time.monotonic()-started}
    _save(output / 'MATERIALS.json', {'items': items})
    if state is not None:
        _save(output / 'state_snapshot.json', state.to_dict())
    _save(output / 'RESULT.json', result)
    return result


def _worker(arguments):
    job, settings = arguments
    return run_read_only_job(job, settings=settings)


def run_read_only_jobs(jobs, *, settings, concurrency=1):
    """Schedule whole independent tasks; never split a task or merge its State."""
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context
    jobs = list(jobs)
    if concurrency < 1:
        raise ValueError('positive concurrency required')
    if len({job.task_id for job in jobs}) != len(jobs):
        raise ValueError('duplicate task IDs')
    paths = [Path(job.output_dir).resolve() for job in jobs]
    for index, path in enumerate(paths):
        if path.exists():
            raise FileExistsError(path)
        if any(path == other or path in other.parents or other in path.parents
               for other in paths[:index]):
            raise ValueError('overlapping task outputs')
        if any(path == Path(job.workspace).resolve() or Path(job.workspace).resolve() in path.parents
               for job in jobs):
            raise ValueError('audit output overlaps a task workspace')
    if concurrency == 1:
        return [_worker((job, settings)) for job in jobs]
    with ProcessPoolExecutor(max_workers=concurrency, mp_context=get_context('spawn')) as pool:
        return list(pool.map(_worker, [(job, settings) for job in jobs]))
