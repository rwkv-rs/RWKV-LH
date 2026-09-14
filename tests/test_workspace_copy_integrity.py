from pathlib import Path
import json
import pytest
from rwkv_lh.coding_agent import CodingJob, run_coding_job
from test_read_only_agent import factory
from test_unified_controller import call, settings


def test_source_changed_during_copy_is_rejected_before_model_start(tmp_path, monkeypatch):
    import rwkv_lh.coding_agent as coding
    source = tmp_path / 'source'; source.mkdir(); (source / 'a').write_text('before')
    original = coding.shutil.copytree
    def changing(src, dst, *args, **kwargs):
        result = original(src, dst, *args, **kwargs)
        if Path(src) == source:
            (source / 'a').write_text('changed externally')
        return result
    monkeypatch.setattr(coding.shutil, 'copytree', changing)
    started = []
    def create(**kwargs):
        started.append(True)
        return factory([call('final_answer', text='raw')])(**kwargs)
    with pytest.raises(ValueError, match='source changed'):
        run_coding_job(CodingJob('copy', 'Read', str(source), str(tmp_path / 'run')),
                       settings=settings(), session_factory=create)
    assert not started


def test_delivery_records_permission_only_change(tmp_path):
    source = tmp_path / 'source'; source.mkdir(); script = source / 'a.sh'; script.write_text('echo ok\n'); script.chmod(0o644)
    result = run_coding_job(CodingJob('mode', 'Make a.sh executable', str(source), str(tmp_path / 'run')),
        settings=settings(), session_factory=factory([
            call('run_command', argv=['python', '-c', 'import os; os.chmod("a.sh", 0o755)']),
            call('final_answer', text='raw')]))
    assert 'a.sh' in result['changed_files']
    assert result['final_tree']['a.sh']['mode'] == 0o755
    assert script.stat().st_mode & 0o777 == 0o644


def test_integration_rejects_permission_only_change_instead_of_dropping_it(tmp_path):
    from rwkv_lh.agent_integration import integrate_deliveries
    source = tmp_path / 'source'; source.mkdir(); script = source / 'a.sh'; script.write_text('echo ok\n'); script.chmod(0o644)
    run_coding_job(CodingJob('mode', 'Make a.sh executable', str(source), str(tmp_path / 'run')),
        settings=settings(), session_factory=factory([
            call('run_command', argv=['python', '-c', 'import os; os.chmod("a.sh", 0o755)']),
            call('final_answer', text='raw')]))
    with pytest.raises(ValueError, match='permission-only'):
        integrate_deliveries(source, [tmp_path / 'run'], tmp_path / 'merged')
    assert not (tmp_path / 'merged').exists()


def test_reconsideration_rejects_incomplete_parent_trace(tmp_path):
    from rwkv_lh.read_only_agent import ReadOnlyJob, run_read_only_job
    source = tmp_path / 'source'; source.mkdir()
    run_read_only_job(ReadOnlyJob('parent', 'Read', str(source), str(tmp_path / 'parent')),
        settings=settings(), session_factory=factory([call('final_answer', text='parent')]))
    path = tmp_path / 'parent/model_trace.jsonl'
    records = [json.loads(line) for line in path.read_text().splitlines()]
    path.write_text(''.join(json.dumps(r)+'\n' for r in records if r['type'] != 'model_session_generation_returned'))
    result = run_read_only_job(ReadOnlyJob('child', 'Read', str(source), str(tmp_path / 'child'),
        reconsider_from=str(tmp_path / 'parent'), advice='Check', advice_model='test'),
        settings=settings(), session_factory=factory([call('final_answer', text='child')]))
    assert result['termination'] == 'error'
    assert result['generation_started'] == 0
    assert result['final'] is None


def test_directory_rename_does_not_leave_old_empty_directory_after_integration(tmp_path):
    from rwkv_lh.agent_integration import integrate_deliveries
    source = tmp_path / 'source'; (source / 'old').mkdir(parents=True); (source / 'old/a').write_text('data')
    run_coding_job(CodingJob('rename', 'Rename old to new', str(source), str(tmp_path / 'run')),
        settings=settings(), session_factory=factory([
            call('run_command', argv=['python', '-c', 'from pathlib import Path; Path("old").rename("new")']),
            call('final_answer', text='raw')]))
    integrate_deliveries(source, [tmp_path / 'run'], tmp_path / 'merged')
    assert not (tmp_path / 'merged/old').exists()
    assert (tmp_path / 'merged/new/a').read_text() == 'data'


def test_integration_rejects_empty_directory_change(tmp_path):
    from rwkv_lh.agent_integration import integrate_deliveries
    source = tmp_path / 'source'; source.mkdir()
    run_coding_job(CodingJob('empty', 'Create empty', str(source), str(tmp_path / 'run')),
        settings=settings(), session_factory=factory([
            call('make_directory', path='empty'), call('final_answer', text='raw')]))
    with pytest.raises(ValueError, match='empty directory'):
        integrate_deliveries(source, [tmp_path / 'run'], tmp_path / 'merged')


def test_dependent_delivery_without_tree_identity_is_not_silently_trusted(tmp_path):
    from rwkv_lh.agent_integration import _load_delivery
    source = tmp_path / 'source'; source.mkdir()
    run_coding_job(CodingJob('parent', 'Read', str(source), str(tmp_path / 'run')),
        settings=settings(), session_factory=factory([call('final_answer', text='raw')]))
    path = tmp_path / 'run/DELIVERY.json'
    result = json.loads(path.read_text()); result.pop('final_tree'); path.write_text(json.dumps(result))
    with pytest.raises(ValueError, match='tree identity'):
        _load_delivery(tmp_path / 'run')
