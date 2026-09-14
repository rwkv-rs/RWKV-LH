import json
from pathlib import Path
import pytest
from rwkv_lh.coding_agent import CodingJob, run_coding_job
from test_read_only_agent import factory
from test_unified_controller import call, settings


def proposal(tmp_path, source, name, file, content):
    root = tmp_path / name
    run_coding_job(CodingJob(name, 'Change file', str(source), str(root)), settings=settings(),
        session_factory=factory([call('write_file', path=file, content=content), call('final_answer', text='raw')]))
    return root


def test_merge_disjoint_changes_preserves_sources_and_requires_external_acceptance(tmp_path):
    from rwkv_lh.agent_integration import integrate_deliveries
    source = tmp_path / 'source'; source.mkdir()
    (source / 'a').write_text('old'); (source / 'b').write_text('old')
    a = proposal(tmp_path, source, 'one', 'a', 'A')
    b = proposal(tmp_path, source, 'two', 'b', 'B')
    result = integrate_deliveries(source, [a, b], tmp_path / 'merged')
    assert (tmp_path / 'merged/a').read_text() == 'A'
    assert (tmp_path / 'merged/b').read_text() == 'B'
    assert (source / 'a').read_text() == 'old'
    assert result['acceptance'] == 'not_evaluated'


def test_merge_conflict_is_explicit_and_does_not_create_partial_output(tmp_path):
    from rwkv_lh.agent_integration import integrate_deliveries
    source = tmp_path / 'source'; source.mkdir(); (source / 'a').write_text('old')
    a = proposal(tmp_path, source, 'one', 'a', 'A')
    b = proposal(tmp_path, source, 'two', 'a', 'B')
    with pytest.raises(ValueError, match='conflict'):
        integrate_deliveries(source, [a, b], tmp_path / 'merged')
    assert not (tmp_path / 'merged').exists()


def test_changed_delivery_is_rejected_before_merge(tmp_path):
    from rwkv_lh.agent_integration import integrate_deliveries
    source = tmp_path / 'source'; source.mkdir(); (source / 'a').write_text('old')
    a = proposal(tmp_path, source, 'one', 'a', 'A')
    (a / 'workspace/a').write_text('tampered')
    with pytest.raises(ValueError, match='changed'):
        integrate_deliveries(source, [a], tmp_path / 'merged')


def test_workflow_cycle_rejected_before_execution(tmp_path):
    from rwkv_lh.agent_integration import run_agent_workflow
    source = tmp_path / 'source'; source.mkdir()
    jobs = [CodingJob(n, 'Change', str(source), str(tmp_path / n)) for n in ('a', 'b')]
    with pytest.raises(ValueError, match='cycle'):
        run_agent_workflow(jobs, {'a': ['b'], 'b': ['a']}, settings=settings())
    assert not (tmp_path / 'a').exists()


def test_failed_dependency_blocks_child_without_model_call(tmp_path, monkeypatch):
    import rwkv_lh.agent_batch as batch
    from rwkv_lh.agent_integration import run_agent_workflow
    source = tmp_path / 'source'; source.mkdir()
    jobs = [CodingJob(n, 'Change', str(source), str(tmp_path / n)) for n in ('a', 'b')]
    seen = []
    def execute(job, configuration):
        seen.append(job.task_id)
        return {'id': job.task_id, 'termination': 'budget', 'final': None}
    monkeypatch.setattr(batch, '_execute', execute)
    results = run_agent_workflow(jobs, {'b': ['a']}, settings=settings())
    assert seen == ['a']
    assert results[1]['termination'] == 'blocked'
    assert results[1]['generation_started'] == 0


def test_dependent_task_reads_actual_parent_artifact(tmp_path, monkeypatch):
    import rwkv_lh.agent_batch as batch
    import rwkv_lh.agent_integration as integration
    source = tmp_path / 'source'; source.mkdir(); (source / 'a').write_text('old')
    jobs = [CodingJob('parent', 'Change a', str(source), str(tmp_path / 'parent')),
            CodingJob('child', 'Read the result', str(source), str(tmp_path / 'child'))]
    original = batch._execute
    def coding(job, **kwargs):
        outputs = ([call('write_file', path='a', content='new'), call('final_answer', text='changed')]
                   if job.task_id == 'parent' else [call('read_file', path='a'), call('final_answer', text='new')])
        return run_coding_job(job, settings=kwargs['settings'], session_factory=factory(outputs))
    monkeypatch.setattr(integration, 'run_coding_job', coding)
    monkeypatch.setattr(batch, '_execute', lambda job, configuration:
        original(job, configuration) if isinstance(job, integration.DependentJob) else coding(job, settings=configuration))
    results = integration.run_agent_workflow(jobs, {'child': ['parent']}, settings=settings())
    assert [r['termination'] for r in results] == ['submitted', 'submitted']
    assert (Path(results[1]['workspace']) / 'a').read_text() == 'new'
    assert results[1]['acceptance'] == 'not_evaluated'
    assert (source / 'a').read_text() == 'old'


def test_merge_rejects_different_initial_bases(tmp_path):
    from rwkv_lh.agent_integration import integrate_deliveries
    source = tmp_path / 'source'; source.mkdir(); (source / 'a').write_text('old')
    parent = proposal(tmp_path, source, 'parent', 'a', 'new')
    (source / 'a').write_text('different base')
    with pytest.raises(ValueError, match='base mismatch'):
        integrate_deliveries(source, [parent], tmp_path / 'merged')
    assert not (tmp_path / 'merged').exists()


def test_merge_rejects_output_that_overlaps_parent(tmp_path):
    from rwkv_lh.agent_integration import integrate_deliveries
    source = tmp_path / 'source'; source.mkdir(); (source / 'a').write_text('old')
    parent = proposal(tmp_path, source, 'parent', 'a', 'new')
    with pytest.raises(ValueError, match='overlap'):
        integrate_deliveries(source, [parent], parent / 'nested')


def test_cli_exposes_dependencies_in_same_entry(tmp_path, monkeypatch, capsys):
    import scripts.run_rwkv_agent as cli
    jobs = tmp_path / 'jobs.json'
    jobs.write_text(json.dumps([{'task_id': 'a', 'request': 'Read', 'workspace': str(tmp_path),
        'output_dir': str(tmp_path / 'out'), 'tool_scope': 'coding', 'depends_on': []}]))
    monkeypatch.setattr('sys.argv', ['run_rwkv_agent', '--jobs', str(jobs)])
    monkeypatch.setattr(cli, 'load_local_env', lambda *a: None)
    monkeypatch.setattr(cli, 'get_runtime_settings', settings)
    seen = []
    monkeypatch.setattr(cli, 'run_agent_jobs', lambda jobs, **kwargs:
        seen.extend(jobs) or [{'termination': 'submitted'}])
    assert cli.main() == 0
    assert len(seen) == 1


def test_workflow_joins_two_branches_before_running_integration_task(tmp_path, monkeypatch):
    import rwkv_lh.agent_batch as batch
    import rwkv_lh.agent_integration as integration
    source = tmp_path / 'source'; source.mkdir()
    (source / 'a').write_text('old'); (source / 'b').write_text('old')
    jobs = [CodingJob(n, 'Apply or verify changes', str(source), str(tmp_path / n)) for n in ('one', 'two', 'verify')]
    original = batch._execute
    def coding(job, **kwargs):
        if job.task_id == 'verify':
            assert (Path(job.source_workspace) / 'a').read_text() == 'A'
            assert (Path(job.source_workspace) / 'b').read_text() == 'B'
            outputs = [call('final_answer', text='raw verification submission')]
        else:
            outputs = [call('write_file', path='a' if job.task_id == 'one' else 'b',
                            content='A' if job.task_id == 'one' else 'B'), call('final_answer', text='raw')]
        return run_coding_job(job, settings=kwargs['settings'], session_factory=factory(outputs))
    monkeypatch.setattr(integration, 'run_coding_job', coding)
    monkeypatch.setattr(batch, '_execute', lambda job, configuration:
        original(job, configuration) if isinstance(job, integration.DependentJob) else coding(job, settings=configuration))
    results = integration.run_agent_workflow(jobs, {'verify': ['one', 'two']}, settings=settings())
    assert all(r['termination'] == 'submitted' for r in results)
    assert results[-1]['acceptance'] == 'not_evaluated'
    assert (source / 'a').read_text() == 'old'


def test_delete_edit_conflict_is_not_silently_resolved(tmp_path):
    from rwkv_lh.agent_integration import integrate_deliveries
    source = tmp_path / 'source'; source.mkdir(); (source / 'a').write_text('old')
    delete = tmp_path / 'delete'
    run_coding_job(CodingJob('delete', 'Delete a', str(source), str(delete)), settings=settings(),
        session_factory=factory([call('delete_file', path='a'), call('final_answer', text='deleted')]))
    edit = proposal(tmp_path, source, 'edit', 'a', 'new')
    with pytest.raises(ValueError, match='conflict'):
        integrate_deliveries(source, [delete, edit], tmp_path / 'merged')
    assert not (tmp_path / 'merged').exists()
