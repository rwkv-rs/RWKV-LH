from pathlib import Path
import json
import pytest
from rwkv_lh.read_only_agent import ReadOnlyJob, ReadOnlyHarness, run_read_only_job
from rwkv_lh.model_session import ModelSession
from test_unified_controller import QueueClient, call, settings


def factory(outputs):
    def create(*, settings, audit_hook):
        return ModelSession(QueueClient(outputs), settings=settings, audit_hook=audit_hook)
    return create


def test_agent_reads_and_exports_verbatim_material_without_rewriting_answer(tmp_path):
    workspace=tmp_path/'workspace';workspace.mkdir();(workspace/'doc.md').write_text('原文：健康检查不证明事务。')
    job=ReadOnlyJob('one','阅读 doc.md 并回答其用途',str(workspace),str(tmp_path/'run'),max_calls=3)
    result=run_read_only_job(job,settings=settings(),session_factory=factory([
        call('read_file',path='doc.md'),call('final_answer',text='原始回答，不由程序修饰。')]))
    assert result['final']=='原始回答，不由程序修饰。' and result['termination']=='submitted'
    materials=json.loads((tmp_path/'run/MATERIALS.json').read_text())
    span=materials['items'][0]['event']['payload']['result']['observation']['exact_spans'][0]
    assert span['content']=='原文：健康检查不证明事务。'
    assert materials['items'][0]['consumed_by_requests']
    assert result['acceptance']=='not_evaluated'


def test_read_only_scope_hides_mutations_and_rejects_attempt_without_writing(tmp_path):
    names={d['name'] for d in ReadOnlyHarness().g1i_tool_definitions()}
    assert 'read_file' in names and 'write_file' not in names
    workspace=tmp_path/'workspace';workspace.mkdir()
    job=ReadOnlyJob('one','只读检查',str(workspace),str(tmp_path/'run'),max_calls=2)
    result=run_read_only_job(job,settings=settings(),session_factory=factory([
        call('write_file',path='bad.txt',content='bad'),call('final_answer',text='未写入')]))
    assert not (workspace/'bad.txt').exists() and result['protocol_rejections']==1
    assert result['final']=='未写入'


def test_budget_never_requests_forced_final_and_output_directory_is_not_overwritten(tmp_path):
    workspace=tmp_path/'workspace';workspace.mkdir();(workspace/'doc.md').write_text('source')
    job=ReadOnlyJob('one','阅读并回答',str(workspace),str(tmp_path/'run'),max_calls=1)
    result=run_read_only_job(job,settings=settings(),session_factory=factory([call('read_file',path='doc.md')]))
    assert result['final'] is None and result['termination']=='budget'
    assert result['generation_started']==1
    with pytest.raises(FileExistsError):
        run_read_only_job(job,settings=settings(),session_factory=factory([]))


def test_batch_rejects_overlapping_outputs_before_dispatch(tmp_path):
    from rwkv_lh.read_only_agent import run_read_only_jobs
    workspace=tmp_path/'workspace';workspace.mkdir()
    jobs=[ReadOnlyJob('a','read',str(workspace),str(tmp_path/'run')),
          ReadOnlyJob('b','read',str(workspace),str(tmp_path/'run/child'))]
    with pytest.raises(ValueError,match='overlapping'):
        run_read_only_jobs(jobs,settings=settings(),concurrency=2)
    assert not (tmp_path/'run').exists()


def test_generation_limit_is_enforced_before_session_not_by_audit_callback():
    from rwkv_lh.read_only_agent import _BudgetedSession, ReadOnlyBudgetExpired
    import time
    class Session:
        calls=0
        def generate(self):
            self.calls+=1
            return 'raw'
    raw=Session();limited=_BudgetedSession(raw,1,time.monotonic()+10)
    assert limited.generate()=='raw'
    with pytest.raises(ReadOnlyBudgetExpired): limited.generate()
    assert raw.calls==1


def test_session_startup_failure_is_saved_as_error_without_delivery(tmp_path):
    workspace=tmp_path/'workspace';workspace.mkdir()
    job=ReadOnlyJob('offline','read',str(workspace),str(tmp_path/'run'))
    def unavailable(**kwargs):
        raise ConnectionError('service unavailable')
    result=run_read_only_job(job,settings=settings(),session_factory=unavailable)
    assert result['termination']=='error' and result['final'] is None
    assert result['generation_started']==0
    assert json.loads((tmp_path/'run/RESULT.json').read_text())['error']['type']=='ConnectionError'


@pytest.mark.parametrize('calls,seconds',[(True,1),(1.5,1),(1,float('inf')),(1,float('nan'))])
def test_invalid_resource_budget_rejected_before_creating_run(tmp_path,calls,seconds):
    workspace=tmp_path/'workspace';workspace.mkdir()
    job=ReadOnlyJob('bad','read',str(workspace),str(tmp_path/'run'),max_calls=calls,max_seconds=seconds)
    with pytest.raises(ValueError):
        run_read_only_job(job,settings=settings(),session_factory=factory([]))
    assert not (tmp_path/'run').exists()


def test_file_scope_rejects_search_but_model_can_recover_and_choose_read(tmp_path):
    workspace=tmp_path/'workspace';workspace.mkdir();(workspace/'doc.md').write_text('actual source')
    job=ReadOnlyJob('files','阅读 doc.md',str(workspace),str(tmp_path/'run'),max_calls=3,tool_scope='files')
    result=run_read_only_job(job,settings=settings(),session_factory=factory([
        call('search_text',path='.',pattern='doc'),call('read_file',path='doc.md'),call('final_answer',text='raw answer')]))
    assert result['protocol_rejections']==1
    assert [a['action_type'] for a in result['actions']]==['read_file']
    assert result['final']=='raw answer'


def test_wall_budget_includes_session_startup(tmp_path):
    import time
    workspace=tmp_path/'workspace';workspace.mkdir()
    job=ReadOnlyJob('slow','read',str(workspace),str(tmp_path/'run'),max_seconds=.02)
    def slow(**kwargs):
        time.sleep(.2)
        return factory([call('final_answer',text='late')])(**kwargs)
    started=time.monotonic()
    result=run_read_only_job(job,settings=settings(),session_factory=slow)
    assert time.monotonic()-started < .1
    assert result['termination']=='budget' and result['final'] is None
    assert result['generation_started']==0


def test_trace_write_failure_prevents_unrecorded_generation(tmp_path,monkeypatch):
    workspace=tmp_path/'workspace';workspace.mkdir()
    original=Path.open
    def open_file(path,mode='r',*args,**kwargs):
        if path.name=='model_trace.jsonl' and mode=='a':
            raise OSError('trace disk unavailable')
        return original(path,mode,*args,**kwargs)
    monkeypatch.setattr(Path,'open',open_file)
    job=ReadOnlyJob('trace','read',str(workspace),str(tmp_path/'run'))
    result=run_read_only_job(job,settings=settings(),session_factory=factory([call('final_answer',text='unrecorded')]))
    assert result['final'] is None and result['generation_started']==0
    assert result['trace_complete'] is False and result['acceptance']=='unreviewable'


def test_requested_advice_preserves_parent_answer_and_continues_its_state(tmp_path):
    from rwkv_lh.schema import RunState
    workspace=tmp_path/'workspace';workspace.mkdir();(workspace/'doc.md').write_text('original evidence')
    request='阅读 doc.md 并回答'
    first=ReadOnlyJob('first',request,str(workspace),str(tmp_path/'first'))
    run_read_only_job(first,settings=settings(),session_factory=factory([
        call('read_file',path='doc.md'),call('final_answer',text='original candidate')]))
    original=(tmp_path/'first/RESULT.json').read_bytes()
    before=RunState.from_dict(json.loads((tmp_path/'first/state_snapshot.json').read_text()))
    second=ReadOnlyJob('review',request,str(workspace),str(tmp_path/'review'),
        reconsider_from=str(tmp_path/'first'),advice='核对原文，不猜测。',advice_model='test-adviser')
    result=run_read_only_job(second,settings=settings(),session_factory=factory([call('final_answer',text='RWKV revised answer')]))
    assert result['final']=='RWKV revised answer' and result['assistance']=='strong_advised'
    assert (tmp_path/'first/RESULT.json').read_bytes()==original
    after=RunState.from_dict(json.loads((tmp_path/'review/state_snapshot.json').read_text()))
    trace=list(map(json.loads,(tmp_path/'review/model_trace.jsonl').read_text().splitlines()))
    start=next(e for e in trace if e['type']=='model_session_generation_started')
    child=after.model_states[start['input_checkpoint_id']]
    assert child.parent_checkpoint_id==before.lane_head('executor')
    assert set(before.model_states[before.lane_head('executor')].event_ids)<set(child.event_ids)


def test_requested_advice_rejects_changed_source_without_generating(tmp_path):
    workspace=tmp_path/'workspace';workspace.mkdir();doc=workspace/'doc.md';doc.write_text('old')
    first=ReadOnlyJob('first','read',str(workspace),str(tmp_path/'first'))
    run_read_only_job(first,settings=settings(),session_factory=factory([
        call('read_file',path='doc.md'),call('final_answer',text='old answer')]))
    doc.write_text('new')
    second=ReadOnlyJob('review','read',str(workspace),str(tmp_path/'review'),
        reconsider_from=str(tmp_path/'first'),advice='check',advice_model='test-adviser')
    result=run_read_only_job(second,settings=settings(),session_factory=factory([]))
    assert result['termination']=='error' and result['generation_started']==0
    assert 'source changed' in result['error']['message']


def test_reconsideration_budget_does_not_report_parent_answer_as_new_delivery(tmp_path):
    workspace=tmp_path/'workspace';workspace.mkdir();(workspace/'doc.md').write_text('source')
    first=ReadOnlyJob('first','read',str(workspace),str(tmp_path/'first'))
    run_read_only_job(first,settings=settings(),session_factory=factory([
        call('read_file',path='doc.md'),call('final_answer',text='old candidate')]))
    second=ReadOnlyJob('review','read',str(workspace),str(tmp_path/'review'),max_calls=1,
        reconsider_from=str(tmp_path/'first'),advice='check',advice_model='test-adviser')
    result=run_read_only_job(second,settings=settings(),session_factory=factory([call('read_file',path='doc.md')]))
    assert result['termination']=='budget' and result['final'] is None
    assert json.loads((tmp_path/'first/RESULT.json').read_text())['final']=='old candidate'


def test_reconsideration_startup_failure_has_no_new_answer(tmp_path):
    workspace=tmp_path/'workspace';workspace.mkdir();(workspace/'doc.md').write_text('source')
    first=ReadOnlyJob('first','read',str(workspace),str(tmp_path/'first'))
    run_read_only_job(first,settings=settings(),session_factory=factory([
        call('read_file',path='doc.md'),call('final_answer',text='old candidate')]))
    second=ReadOnlyJob('review','read',str(workspace),str(tmp_path/'review'),
        reconsider_from=str(tmp_path/'first'),advice='check',advice_model='test-adviser')
    def unavailable(**kwargs): raise ConnectionError('unavailable')
    result=run_read_only_job(second,settings=settings(),session_factory=unavailable)
    assert result['termination']=='error' and result['final'] is None


def test_partial_advice_identity_is_not_silently_ignored(tmp_path):
    workspace=tmp_path/'workspace';workspace.mkdir()
    job=ReadOnlyJob('bad','read',str(workspace),str(tmp_path/'run'),advice='do not lose this')
    with pytest.raises(ValueError):run_read_only_job(job,settings=settings(),session_factory=factory([]))
    assert not (tmp_path/'run').exists()


def test_reconsideration_output_cannot_be_inside_parent_store(tmp_path):
    workspace=tmp_path/'workspace';workspace.mkdir()
    parent=tmp_path/'parent';parent.mkdir()
    nested=parent/'state/review'
    job=ReadOnlyJob('bad','read',str(workspace),str(nested),reconsider_from=str(parent),advice='check',advice_model='adviser')
    with pytest.raises(ValueError):run_read_only_job(job,settings=settings(),session_factory=factory([]))
    assert not nested.exists()


def test_repeated_requested_advice_retains_full_ancestral_trace(tmp_path):
    workspace=tmp_path/'workspace';workspace.mkdir();(workspace/'doc.md').write_text('source')
    first=ReadOnlyJob('first','read',str(workspace),str(tmp_path/'first'))
    run_read_only_job(first,settings=settings(),session_factory=factory([
        call('read_file',path='doc.md'),call('final_answer',text='one')]))
    previous=tmp_path/'first'
    for name in ('second','third'):
        job=ReadOnlyJob(name,'read',str(workspace),str(tmp_path/name),
            reconsider_from=str(previous),advice='check',advice_model='test-adviser')
        result=run_read_only_job(job,settings=settings(),session_factory=factory([call('final_answer',text=name)]))
        assert result['termination']=='submitted'
        previous=tmp_path/name
    history=list(map(json.loads,(previous/'PARENT_TRACE.jsonl').read_text().splitlines()))
    ids=[e['request_id'] for e in history if e['type']=='model_session_generation_returned']
    assert len(ids)==len(set(ids))==3
