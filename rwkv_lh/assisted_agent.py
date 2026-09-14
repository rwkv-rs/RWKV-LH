"""Explicit advice or takeover of a recorded direct task in an isolated workspace."""
from dataclasses import dataclass, replace, asdict
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

from .coding_agent import _RecordedHarness, _inventory
from .read_only_agent import ReadOnlyJob, ReadOnlyHarness, _ReadOnlyController, _run_job, _save
from .controller import LongHorizonController
from .model_session import create_model_session, ModelSession
from .schema import RunState, RunStatus, ModelEvent
from .store import LongHorizonStore
from .summary_advice import make_advice_event, request_advice
from .runtime.settings import RuntimeSettings, load_local_env, get_runtime_settings
from .supervisor_openai import SupervisorAPISettings
from .strong_session import AuditedStrongClient, StrongCompletion


@dataclass(frozen=True)
class AssistedJob:
    task_id: str
    parent_run: str
    output_dir: str
    mode: str
    max_calls: int = 6
    max_seconds: float = 600
    advice_max_tokens: int = 1800

    @property
    def workspace(self):
        return json.loads((Path(self.parent_run) / 'state_snapshot.json').read_text())['goal']['workspace_root']

    @property
    def request(self):
        return json.loads((Path(self.parent_run) / 'state_snapshot.json').read_text())['goal']['request']


def load_parent(job):
    if job.mode not in ('advice', 'takeover'):
        raise ValueError('explicit advice or takeover required')
    if type(job.advice_max_tokens) is not int or job.advice_max_tokens < 1:
        raise ValueError('positive advice token budget required')
    previous = Path(job.parent_run).resolve(strict=True)
    result = json.loads((previous / 'RESULT.json').read_text())
    state = RunState.from_dict(json.loads((previous / 'state_snapshot.json').read_text()))
    if result['tool_scope'] not in ('files', 'inspect', 'coding'):
        raise ValueError('only direct task parents supported')
    if (state.final_output or None) != result['final'] or not state.lane_head('executor'):
        raise ValueError('parent answer or State mismatch')
    if not result.get('trace_complete', False):
        raise ValueError('incomplete parent trace')
    if LongHorizonStore(previous / 'state', checkpoint_retention=1000).load(state.run_id).to_dict() != state.to_dict():
        raise ValueError('parent store differs from recorded snapshot')
    workspace = Path(state.goal.workspace_root).resolve(strict=True)
    # A prior assisted job's private mount is gone; its delivery names the copied workspace.
    delivery_path = previous.parent / 'DELIVERY.json'
    if delivery_path.exists():
        delivery = json.loads(delivery_path.read_text())
        workspace = Path(delivery['workspace']).resolve(strict=True)
        if _inventory(workspace) != delivery['final_files']:
            raise ValueError('parent workspace changed')
    for action in state.actions.values():
        chunk = (action.result or {}).get('metadata', {}).get('chunk', {})
        if action.action_type == 'read_file' and (action.result or {}).get('success') and result['tool_scope'] != 'coding':
            path = (workspace / chunk['source_ref']).resolve(strict=True)
            if not path.is_relative_to(workspace) or hashlib.sha256(path.read_bytes()).hexdigest() != chunk['source_sha256']:
                raise ValueError('parent observed file changed')
    output = Path(job.output_dir).resolve()
    for source in (previous, workspace, Path(state.goal.workspace_root).resolve()):
        if output == source or output in source.parents or source in output.parents:
            raise ValueError('assisted output overlaps parent or workspace')
    for p in workspace.rglob('*'):
        if p.is_symlink() or (not p.is_file() and not p.is_dir()):
            raise ValueError('regular-file workspace required')
    return previous, result, state, workspace


def continue_assisted(job, *, settings, session_factory=create_model_session,
                      advice='', advice_model='', isolate=True, prepared=False):
    previous, parent_result, snapshot, source = load_parent(job)
    root = Path(job.output_dir).resolve()
    if not prepared:
        root.mkdir(parents=True, exist_ok=False)
    workspace, output = root / 'workspace', root / 'execution'
    shutil.copytree(source, workspace, ignore=shutil.ignore_patterns('.git'))
    initial_files = _inventory(workspace)
    original = Path(snapshot.goal.workspace_root)
    if isolate:
        subprocess.run(['mount', '--bind', str(workspace), str(original)], check=True)
    elif parent_result['tool_scope'] == 'coding':
        raise ValueError('coding continuation requires private mount isolation')
    if job.mode == 'advice' and not (advice and advice_model):
        raise ValueError('advice and its actual model identity required')

    def prepare(ws, out):
        shutil.copytree(previous / 'state', out / 'state')
        store = LongHorizonStore(out / 'state', checkpoint_retention=1000)
        state = store.load(snapshot.run_id)
        history = (previous / 'PARENT_TRACE.jsonl').read_bytes() if (previous / 'PARENT_TRACE.jsonl').exists() else b''
        (out / 'PARENT_TRACE.jsonl').write_bytes(history + (previous / 'model_trace.jsonl').read_bytes())
        shutil.copy2(previous / 'state_snapshot.json', out / 'PARENT_STATE_SNAPSHOT.json')
        shutil.copy2(previous / 'RESULT.json', out / 'PARENT_RESULT.json')
        return store, state, {'directory': str(previous),
            'parent_checkpoint_id': state.lane_head('executor'),
            'parent_final_decision_id': state.final_decision_id,
            'historical_actions': len(state.actions), 'parent_generation_started': parent_result['generation_started'],
            'parent_state_sha256': hashlib.sha256((previous / 'state_snapshot.json').read_bytes()).hexdigest(),
            'advice_model': advice_model if job.mode == 'advice' else ''}

    def before(state, controller, model):
        parent = state.model_states[state.lane_head('executor')]
        state.status = RunStatus.RUNNING
        state.final_output = ''
        controller._persist_callback(state, 'run_started', {'reason': 'explicit_' + job.mode,
            'resumed': True, 'parent_checkpoint_id': parent.checkpoint_id})
        if job.mode == 'advice':
            while (pending := controller._first_unappended_action_observation(state)) is not None:
                parent = model._append_event(state, parent, pending, controller._persist_callback)
            event = make_advice_event('ADVICE-' + job.task_id, advice, 'external_strong_model', advice_model)
        else:
            if model.session.transport != 'prompt_replay':
                raise ValueError('takeover requires a new textual session')
            cp = model.session.bootstrap(parent.lane_kind, model._assignment(state, recent_limit=None),
                model.direct_definitions(), lane_id=parent.lane_id)
            state.model_states[cp.checkpoint_id] = cp
            state.set_lane_head('executor', cp.checkpoint_id)
            transfer = {'source_checkpoint': parent.checkpoint_id, 'source_model': parent.model,
                'source_state_digest': parent.native_state_digest, 'target_checkpoint': cp.checkpoint_id,
                'target_model': settings.model, 'native_tensor_transfer': False}
            _save(output / 'TRANSFER.json', transfer)
            controller._persist_callback(state, 'action_session_started', {**transfer,
                'lane_id': cp.lane_id, 'checkpoint_id': cp.checkpoint_id})
            while (pending := controller._first_unappended_action_observation(state)) is not None:
                cp = model._acknowledge_projected_event(state, cp, pending, controller._persist_callback)
            event = ModelEvent(event_type='execution_authority_transfer', event_id='TAKEOVER-' + job.task_id,
                scope_id=cp.lane_id, payload={'source_model': parent.model, 'target_model': settings.model,
                    'is_execution_evidence': False,
                    'instruction': 'Explicit takeover of the unchanged user goal. Prior observations are historical execution, not your work. Choose tools and parameters yourself; report only actual results. Submission is not acceptance.'})
            parent = cp
        _save(output / 'INTERVENTION.json', event.to_dict())
        model._append_event(state, parent, event, controller._persist_callback)

    scope = parent_result['tool_scope']
    inner = ReadOnlyJob(job.task_id, snapshot.goal.request, str(original), str(output), job.max_calls, job.max_seconds, tool_scope=scope)
    result = _run_job(inner, settings=settings, session_factory=session_factory,
        harness_factory=(lambda: _RecordedHarness(output)) if scope == 'coding' else (lambda: ReadOnlyHarness(tool_scope=scope)),
        controller_type=LongHorizonController if scope == 'coding' else _ReadOnlyController,
        allowed_scopes=('files', 'inspect', 'coding'), prepare_state=prepare, before_run=before,
        execution_authority='strong_takeover' if job.mode == 'takeover' else 'rwkv')
    after = _inventory(workspace)
    result = {**result, 'workspace': str(workspace), 'final_files': after,
              'changed_files': sorted(p for p in after.keys() | initial_files.keys() if after.get(p) != initial_files.get(p))}
    _save(root / 'DELIVERY.json', result)
    return result


def run_assisted_job(job, *, settings):
    load_parent(job)
    output = Path(job.output_dir).resolve()
    if output.exists():
        raise FileExistsError(output)
    # Separate mount namespace: immutable goal paths resolve to this job's private copy.
    command = ['unshare', '--user', '--map-root-user', '--mount', '--propagation', 'private',
               sys.executable, '-m', 'rwkv_lh.assisted_agent']
    payload = {'job': asdict(job), 'settings': asdict(settings)}
    completed = subprocess.run(command, input=json.dumps(payload), text=True, capture_output=True,
                               timeout=job.max_seconds + 240)
    if completed.returncode:
        raise RuntimeError('assisted worker failed: ' + completed.stderr[-2000:])
    return json.loads((output / 'DELIVERY.json').read_text())


def _main():
    payload = json.load(sys.stdin)
    job = AssistedJob(**payload['job'])
    settings = RuntimeSettings(**payload['settings'])
    load_local_env()
    strong = replace(SupervisorAPISettings.from_env(), retry_attempts=1, semantic_repair_attempts=0,
                     fallback_models=(), plan_cache_enabled=False, read_timeout_seconds=180)
    previous, result, state, _ = load_parent(job)
    root = Path(job.output_dir)
    root.mkdir(parents=True, exist_ok=False)
    provider_events = []
    def audit_advice(event):
        provider_events.append(dict(event))
        with (root/'ADVICE_PROVIDER_TRACE.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(event), ensure_ascii=False)+'\n')
    advice = ''
    if job.mode == 'advice':
        client = AuditedStrongClient(strong, audit_hook=audit_advice)
        advice = request_advice(client, state.goal, {}, result['final'] or '', job.task_id,
            job.advice_max_tokens, tool_observations=[a.to_dict() for a in state.actions.values()])
        factory = create_model_session
    else:
        settings = RuntimeSettings(base_url='http://unused.invalid', api_key='', model=strong.model,
            state_transport='prompt_replay', state_profile_id='', state_profile_sha256='',
            max_model_len=65536, bos_token_count=0, tool_disclosure_mode='full')
        def factory(*, settings, audit_hook):
            return ModelSession(StrongCompletion(strong, Path(job.output_dir)/'execution', job.max_calls), settings=settings, audit_hook=audit_hook)
    delivery = continue_assisted(job, settings=settings, session_factory=factory, advice=advice,
        advice_model=strong.model if job.mode == 'advice' else '', prepared=True)
    if provider_events:
        (Path(job.output_dir)/'ADVICE_PROVIDER_TRACE.jsonl').write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in provider_events))
    print(delivery['termination'])


if __name__ == '__main__':
    _main()
