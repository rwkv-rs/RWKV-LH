from pathlib import Path
from rwkv_lh.coding_agent import CodingJob, run_coding_job
from rwkv_lh.read_only_agent import ReadOnlyJob, run_read_only_job
from rwkv_lh.model_session import ModelSession
from test_read_only_agent import factory
from test_unified_controller import call, settings


def test_goal_repeated_noop_does_not_force_final_or_hide_new_action(tmp_path):
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'a.txt').write_text('old')
    result = run_coding_job(CodingJob('noop', 'Fix a.txt', str(source), str(tmp_path / 'run')),
        settings=settings(), session_factory=factory([
            call('write_file', path='a.txt', content='old'),
            call('write_file', path='a.txt', content='old'),
            call('write_file', path='a.txt', content='fixed'),
            call('final_answer', text='Changed a.txt.')]))
    assert (Path(result['workspace']) / 'a.txt').read_text() == 'fixed'
    assert result['protocol_rejections'] == 0
    assert result['final'] == 'Changed a.txt.'


def test_missing_generation_response_is_not_complete_trace(tmp_path):
    class Client:
        model_name = 'test-rwkv'
        def text_completion(self, *args, **kwargs):
            raise ConnectionError('controlled missing response')
    def create(**kwargs):
        return ModelSession(Client(), **kwargs)
    source = tmp_path / 'source'
    source.mkdir()
    result = run_read_only_job(ReadOnlyJob('lost', 'Read', str(source), str(tmp_path / 'run'), max_calls=1),
        settings=settings(), session_factory=create)
    assert result['generation_started'] == 1
    assert result['trace_complete'] is False
    assert result['trace_persistence_ok'] is True
    assert result['generation_returned'] == 0
    assert len(result['unresolved_request_ids']) == 1
    assert result['final'] is None


def test_copy_time_exhausts_task_budget_before_model_start(tmp_path, monkeypatch):
    import time
    import rwkv_lh.coding_agent as coding
    source = tmp_path / 'source'; source.mkdir()
    original = coding.shutil.copytree
    def slow(*args, **kwargs):
        time.sleep(.2)
        return original(*args, **kwargs)
    monkeypatch.setattr(coding.shutil, 'copytree', slow)
    def forbidden(**kwargs):
        raise AssertionError('model started after preparation exhausted budget')
    started = time.monotonic()
    result = run_coding_job(CodingJob('slowcopy', 'Read', str(source), str(tmp_path / 'run'), max_seconds=.03),
        settings=settings(), session_factory=forbidden)
    assert result['termination'] == 'budget'
    assert result['termination_reason'] == 'wall_budget_exhausted'
    assert result['generation_started'] == 0
    assert time.monotonic() - started < .15
    assert result['final'] is None


def test_pool_crash_preserves_other_results_and_marks_unknown_calls(tmp_path, monkeypatch):
    from concurrent.futures import Future
    from concurrent.futures.process import BrokenProcessPool
    import rwkv_lh.agent_batch as batch
    source = tmp_path / 'source'; source.mkdir()
    jobs = [ReadOnlyJob(name, 'Read', str(source), str(tmp_path / name)) for name in ('ok', 'dead')]
    class Pool:
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def map(self, *args): raise BrokenProcessPool('controlled hard worker exit')
        def submit(self, function, arguments):
            future = Future()
            if arguments[0].task_id == 'ok':
                future.set_result({'id': 'ok', 'final': 'raw', 'termination': 'submitted', 'acceptance': 'not_evaluated'})
            else:
                future.set_exception(BrokenProcessPool('controlled hard worker exit'))
            return future
    monkeypatch.setattr(batch, 'ProcessPoolExecutor', Pool)
    results = batch.run_agent_jobs(jobs, settings=settings(), concurrency=2)
    assert results[0]['final'] == 'raw'
    assert results[1]['termination'] == 'error'
    assert results[1]['termination_reason'] == 'worker_process_lost'
    assert results[1]['generation_started'] is None
    assert results[1]['final'] is None
    assert (tmp_path / 'dead/BATCH_ERROR.json').is_file()


def test_read_only_tool_does_not_duplicate_whole_coding_workspace(tmp_path):
    source = tmp_path / 'source'; source.mkdir()
    (source / 'a.txt').write_text('visible')
    run_coding_job(CodingJob('read', 'Read a.txt', str(source), str(tmp_path / 'run')),
        settings=settings(), session_factory=factory([
            call('read_file', path='a.txt'), call('final_answer', text='visible')]))
    snapshot = tmp_path / 'run/execution/tool_snapshots/001'
    assert (snapshot / 'call.json').is_file()
    assert not (snapshot / 'before').exists()
    assert not (snapshot / 'after').exists()


def test_assisted_worker_timeout_kills_descendant(tmp_path):
    import subprocess
    import sys
    import time
    import pytest
    from rwkv_lh.assisted_agent import _run_worker
    marker = tmp_path / 'orphan.txt'
    child = f'import time; time.sleep(.25); open({str(marker)!r}, "w").write("orphan")'
    parent = f'import subprocess,sys,time; subprocess.Popen([sys.executable,"-c",{child!r}]); time.sleep(10)'
    with pytest.raises(subprocess.TimeoutExpired):
        _run_worker([sys.executable, '-c', parent], '', .08)
    time.sleep(.3)
    assert not marker.exists()


def test_assistance_rejects_missing_parent_response_despite_old_complete_flag(tmp_path):
    import json
    import pytest
    from rwkv_lh.assisted_agent import AssistedJob, load_parent
    source = tmp_path / 'source'; source.mkdir()
    run_read_only_job(ReadOnlyJob('parent', 'Read', str(source), str(tmp_path / 'parent')),
        settings=settings(), session_factory=factory([call('final_answer', text='raw')]))
    path = tmp_path / 'parent/model_trace.jsonl'
    events = [json.loads(line) for line in path.read_text().splitlines()]
    path.write_text(''.join(json.dumps(e) + '\n' for e in events if e['type'] != 'model_session_generation_returned'))
    with pytest.raises(ValueError, match='parent generation trace'):
        load_parent(AssistedJob('child', str(tmp_path / 'parent'), str(tmp_path / 'child'), 'advice'))


def test_read_only_reconsideration_delivers_pending_observation_before_advice(tmp_path):
    import json
    source = tmp_path / 'source'; source.mkdir(); (source / 'a').write_text('actual')
    run_read_only_job(ReadOnlyJob('parent', 'Read a', str(source), str(tmp_path / 'parent'), max_calls=1),
        settings=settings(), session_factory=factory([call('read_file', path='a')]))
    job = ReadOnlyJob('child', 'Read a', str(source), str(tmp_path / 'child'),
        reconsider_from=str(tmp_path / 'parent'), advice='Check the evidence', advice_model='test-adviser')
    run_read_only_job(job, settings=settings(), session_factory=factory([call('final_answer', text='actual')]))
    state = json.loads((tmp_path / 'child/state_snapshot.json').read_text())
    events = list(state['model_events'].values())
    observation = next(i for i,e in enumerate(events) if e['event_type'] == 'action_result')
    advice = next(i for i,e in enumerate(events) if 'advice' in e['event_type'])
    assert observation < advice
