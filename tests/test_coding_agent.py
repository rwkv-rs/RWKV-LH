import json
from pathlib import Path
import pytest
from rwkv_lh.coding_agent import CodingJob, run_coding_job
from test_read_only_agent import factory
from test_unified_controller import call, settings


def test_isolated_edit_test_and_original_answer_are_delivered(tmp_path):
    source=tmp_path/'source';source.mkdir();(source/'a.py').write_text('value = 1\n')
    output=tmp_path/'run'
    result=run_coding_job(CodingJob('edit','Change value and verify',str(source),str(output)),settings=settings(),session_factory=factory([
        call('read_file',path='a.py'),call('write_file',path='a.py',content='value = 2\n'),
        call('run_command',argv=['python3','-B','-c','from a import value; assert value == 2']),
        call('final_answer',text='Original model answer.')]))
    assert (source/'a.py').read_text()=='value = 1\n'
    assert (output/'workspace/a.py').read_text()=='value = 2\n'
    assert result['final']=='Original model answer.' and result['acceptance']=='not_evaluated'
    assert result['changed_files']==['a.py']
    assert (output/'execution/tool_snapshots/002/before/a.py').read_text()=='value = 1\n'
    assert (output/'execution/tool_snapshots/002/after/a.py').read_text()=='value = 2\n'
    events=json.loads((output/'execution/MATERIALS.json').read_text())['items']
    command=next(e for e in events if e['event']['payload']['operation']=='run_command')
    assert command['consumed_by_requests']


def test_failed_test_and_budget_are_not_accepted_as_completion(tmp_path):
    source=tmp_path/'source';source.mkdir()
    result=run_coding_job(CodingJob('failure','Verify',str(source),str(tmp_path/'run'),max_calls=1),settings=settings(),session_factory=factory([
        call('run_command',argv=['python3','-c','raise SystemExit(1)'],expected_exit_code=1)]))
    assert result['termination']=='budget' and result['final'] is None
    assert result['acceptance']=='not_evaluated'
    assert result['actions'][0]['result']['exit_code']==1
    assert result['actions'][0]['result']['success'] is True


def test_existing_or_overlapping_output_is_rejected_before_copy(tmp_path):
    source=tmp_path/'source';source.mkdir();(source/'file').write_text('keep')
    with pytest.raises(ValueError):
        run_coding_job(CodingJob('bad','edit',str(source),str(source/'run')),settings=settings())
    assert not (source/'run').exists()
    output=tmp_path/'run';output.mkdir();(output/'keep').write_text('keep')
    with pytest.raises(FileExistsError):
        run_coding_job(CodingJob('bad','edit',str(source),str(output)),settings=settings())
    assert (output/'keep').read_text()=='keep'


def test_symlink_cannot_escape_copy_and_git_worktree_pointer_is_not_carried(tmp_path):
    source=tmp_path/'source';source.mkdir();outside=tmp_path/'outside';outside.write_text('keep')
    (source/'link').symlink_to(outside)
    with pytest.raises(ValueError,match='symlink'):
        run_coding_job(CodingJob('bad','edit',str(source),str(tmp_path/'bad')),settings=settings())
    assert not (tmp_path/'bad').exists()
    (source/'link').unlink();(source/'.git').write_text('gitdir: /original/repository')
    result=run_coding_job(CodingJob('good','answer',str(source),str(tmp_path/'good')),settings=settings(),session_factory=factory([call('final_answer',text='raw')]))
    assert not (tmp_path/'good/workspace/.git').exists()
    assert (source/'.git').exists() and result['final']=='raw'


def test_identical_failure_boundary_is_distinct_from_generation_budget(tmp_path):
    source=tmp_path/'source';source.mkdir()
    result=run_coding_job(CodingJob('repeated','Verify',str(source),str(tmp_path/'run')),
        settings=settings(),session_factory=factory([
            call('run_command',argv=['python3','-B','-c','print(1)'],cwd='missing') for _ in range(5)]))
    assert result['termination_reason']=='identical_failure_budget_exhausted'
    assert result['termination_evidence']['event_type']=='run_yielded'
    assert result['generation_started']==5 and result['final'] is None
    assert all(c['execution_status']=='not_started' for c in result['command_executions'])


def test_nonzero_expected_exit_is_recorded_as_executed_not_as_test_pass(tmp_path):
    source=tmp_path/'source';source.mkdir()
    result=run_coding_job(CodingJob('exit','Verify',str(source),str(tmp_path/'run'),max_calls=1),
        settings=settings(),session_factory=factory([
            call('run_command',argv=['python3','-B','-c','raise SystemExit(1)'],expected_exit_code=1)]))
    assert result['termination_reason']=='transition_budget_exhausted'
    assert result['command_executions'][0]['execution_status']=='exited'
    assert result['command_executions'][0]['exit_code']==1
    assert result['acceptance']=='not_evaluated'


def test_generation_guard_stops_before_an_extra_model_call():
    import time
    from types import SimpleNamespace
    from rwkv_lh.read_only_agent import _BudgetedSession, ReadOnlyBudgetExpired
    called=[]
    session=_BudgetedSession(SimpleNamespace(generate=lambda:called.append(1)),1,time.monotonic()+60)
    session.generate()
    with pytest.raises(ReadOnlyBudgetExpired) as caught:session.generate()
    assert caught.value.reason=='generation_budget_exhausted'
    assert called==[1]


def test_resume_keeps_goal_parent_state_and_does_not_reuse_old_termination(tmp_path):
    import shutil
    from rwkv_lh.read_only_agent import ReadOnlyJob, _run_job
    from rwkv_lh.coding_agent import _RecordedHarness
    from rwkv_lh.controller import LongHorizonController
    from rwkv_lh.store import LongHorizonStore
    source=tmp_path/'source';source.mkdir();(source/'a.py').write_text('value = 1\n')
    run_coding_job(CodingJob('parent','Read',str(source),str(tmp_path/'parent'),max_calls=1),
        settings=settings(),session_factory=factory([call('read_file',path='a.py')]))
    parent=tmp_path/'parent/execution';snapshot=(parent/'state_snapshot.json').read_bytes()
    def prepare(workspace,output):
        shutil.copytree(parent/'state',output/'state')
        store=LongHorizonStore(output/'state',checkpoint_retention=1000)
        state=store.load('parent')
        return store,state,{'parent_final_decision_id':state.final_decision_id,'advice_model':''}
    output=tmp_path/'resume'
    result=_run_job(ReadOnlyJob('resume','Read',str(tmp_path/'parent/workspace'),str(output),tool_scope='coding'),
        settings=settings(),session_factory=factory([call('final_answer',text='Read value is 1.')]),
        harness_factory=lambda:_RecordedHarness(output),controller_type=LongHorizonController,
        allowed_scopes=('coding',),prepare_state=prepare)
    assert result['termination_reason']=='answer_submitted'
    assert result['final']=='Read value is 1.' and result['assistance']=='rwkv_independent'
    assert (parent/'state_snapshot.json').read_bytes()==snapshot
    after=json.loads((output/'state_snapshot.json').read_text())
    assert after['goal']==json.loads(snapshot)['goal']
    events=json.loads((output/'MATERIALS.json').read_text())['items']
    assert events[0]['consumed_by_requests']
