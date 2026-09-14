from pathlib import Path
import pytest
from rwkv_lh.coding_agent import CodingJob
from rwkv_lh.read_only_agent import ReadOnlyJob
from rwkv_lh.agent_batch import run_agent_jobs
from test_unified_controller import settings


def test_mixed_batch_preserves_raw_results_and_continues_after_worker_error(tmp_path, monkeypatch):
    import rwkv_lh.agent_batch as batch
    source=tmp_path/'source';source.mkdir()
    jobs=[ReadOnlyJob('read','Read',str(source),str(tmp_path/'read')),
          CodingJob('edit','Edit',str(source),str(tmp_path/'edit'))]
    def execute(job, configuration):
        if job.task_id=='read':raise OSError('recorded infrastructure failure')
        return {'id':'edit','final':'original model answer','termination':'submitted','acceptance':'not_evaluated'}
    monkeypatch.setattr(batch,'_execute',execute)
    results=run_agent_jobs(jobs,settings=settings())
    assert results[0]['termination']=='error' and results[0]['final'] is None
    assert results[1]['final']=='original model answer' and results[1]['acceptance']=='not_evaluated'


@pytest.mark.parametrize('concurrency',[0,True,1.5])
def test_invalid_concurrency_rejected_before_dispatch(concurrency):
    with pytest.raises(ValueError):run_agent_jobs([],settings=settings(),concurrency=concurrency)


def test_output_ancestor_of_any_source_is_rejected_before_dispatch(tmp_path, monkeypatch):
    import rwkv_lh.agent_batch as batch
    source=tmp_path/'output'/'source';source.mkdir(parents=True)
    other=tmp_path/'other';other.mkdir()
    jobs=[CodingJob('a','Edit',str(other),str(tmp_path/'output')),
          ReadOnlyJob('b','Read',str(source),str(tmp_path/'b'))]
    monkeypatch.setattr(batch,'_execute',lambda *args:pytest.fail('dispatched before validation'))
    with pytest.raises(ValueError,match='overlap'):run_agent_jobs(jobs,settings=settings(),concurrency=2)


def test_entire_batch_budget_preflight_prevents_partial_start(tmp_path, monkeypatch):
    import rwkv_lh.agent_batch as batch
    source=tmp_path/'source';source.mkdir()
    jobs=[CodingJob('a','Edit',str(source),str(tmp_path/'a')),
          ReadOnlyJob('b','Read',str(source),str(tmp_path/'b'),max_calls=0)]
    monkeypatch.setattr(batch,'_execute',lambda *args:pytest.fail('dispatched before validation'))
    with pytest.raises(ValueError,match='budget'):run_agent_jobs(jobs,settings=settings())
    assert not (tmp_path/'a').exists()
