from dataclasses import replace
import pytest
from rwkv_lh.goal_delivery import GoalJob, run_goal_job
from test_unified_controller import settings


def result(termination='submitted', reason='answer_submitted', calls=2):
    return dict(id='raw-id', final='unaltered answer' if termination=='submitted' else None,
                termination=termination, termination_reason=reason, generation_started=calls,
                trace_complete=True, assistance='rwkv_independent', acceptance='not_evaluated')


def job(tmp_path):
    source=tmp_path/'source';source.mkdir()
    return GoalJob('goal','Fix the bug and test',str(source),str(tmp_path/'out'),max_calls=10,rwkv_max_calls=4)


def test_submission_is_returned_without_strong_review(tmp_path,monkeypatch):
    import rwkv_lh.goal_delivery as m
    j=job(tmp_path);original=result()
    monkeypatch.setattr(m,'run_coding_job',lambda *a,**kw:original)
    monkeypatch.setattr(m,'run_assisted_job',lambda *a,**kw:pytest.fail('unnecessary strong call'))
    r=run_goal_job(j,settings=settings())
    assert r['final']==original['final'] and r['acceptance']=='not_evaluated'
    assert r['assistance']=='rwkv_independent' and r['workflow']['model_calls']==2


def test_stall_transfers_same_goal_once_with_remaining_call_budget(tmp_path,monkeypatch):
    import rwkv_lh.goal_delivery as m
    j=job(tmp_path);seen=[]
    monkeypatch.setattr(m,'run_coding_job',lambda child,**kw:result('budget','generation_budget_exhausted',4))
    def strong(child,**kw):
        seen.append(child)
        return {**result(calls=3),'assistance':'strong_takeover'}
    monkeypatch.setattr(m,'run_assisted_job',strong)
    r=run_goal_job(j,settings=settings())
    assert len(seen)==1 and seen[0].max_calls==6
    assert seen[0].parent_run.endswith('/rwkv/execution')
    assert r['assistance']=='strong_takeover' and r['workflow']['model_calls']==7
    assert r['workflow']['stages'][0]['termination']=='budget'


@pytest.mark.parametrize('termination,reason,complete',[
    ('error','execution_error',True),('budget','wall_budget_exhausted',True),
    ('budget','generation_budget_exhausted',False),('budget','unrecognized_reason',True)])
def test_untrusted_or_infrastructure_failure_does_not_trigger_takeover(tmp_path,monkeypatch,termination,reason,complete):
    import rwkv_lh.goal_delivery as m
    j=job(tmp_path)
    monkeypatch.setattr(m,'run_coding_job',lambda *a,**kw:{**result(termination,reason), 'trace_complete':complete})
    monkeypatch.setattr(m,'run_assisted_job',lambda *a,**kw:pytest.fail('unsafe transfer'))
    assert run_goal_job(j,settings=settings())['final'] is None


def test_exhausted_total_calls_prevents_new_strong_call(tmp_path,monkeypatch):
    import rwkv_lh.goal_delivery as m
    j=replace(job(tmp_path),max_calls=4)
    monkeypatch.setattr(m,'run_coding_job',lambda *a,**kw:result('budget','generation_budget_exhausted',4))
    monkeypatch.setattr(m,'run_assisted_job',lambda *a,**kw:pytest.fail('budget exceeded'))
    assert run_goal_job(j,settings=settings())['workflow']['model_calls']==4


def test_bad_later_goal_budget_prevents_entire_batch_start(tmp_path,monkeypatch):
    import rwkv_lh.agent_batch as batch
    j=job(tmp_path)
    bad=replace(j,task_id='bad',output_dir=str(tmp_path/'bad'),rwkv_max_calls=11)
    monkeypatch.setattr(batch,'_execute',lambda *a:pytest.fail('partial batch start'))
    with pytest.raises(ValueError,match='budget'):
        batch.run_agent_jobs([j,bad],settings=settings())


def test_takeover_failure_preserves_failed_stage_and_does_not_invent_zero_cost(tmp_path,monkeypatch):
    import rwkv_lh.goal_delivery as m
    j=job(tmp_path)
    monkeypatch.setattr(m,'run_coding_job',lambda *a,**kw:result('budget','generation_budget_exhausted',4))
    def fail(*a,**kw):raise OSError('provider disconnected')
    monkeypatch.setattr(m,'run_assisted_job',fail)
    r=run_goal_job(j,settings=settings())
    assert r['termination']=='error' and r['final'] is None
    assert len(r['workflow']['stages'])==2 and r['workflow']['model_calls'] is None
    assert r['error']['message']=='provider disconnected'
