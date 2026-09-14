import inspect
import json
import pytest
from rwkv_lh.assisted_agent import AssistedJob, load_parent, continue_assisted
from rwkv_lh.read_only_agent import ReadOnlyJob, run_read_only_job
from test_read_only_agent import factory
from test_unified_controller import call, settings


def parent(tmp_path):
    workspace=tmp_path/'workspace';workspace.mkdir();(workspace/'a.py').write_text('value = 1\n')
    out=tmp_path/'parent'
    run_read_only_job(ReadOnlyJob('parent','Read a.py and report',str(workspace),str(out)),settings=settings(),session_factory=factory([call('read_file',path='a.py'),call('final_answer',text='value is 1')]))
    return workspace,out


def test_advice_continues_same_state_and_preserves_parent(tmp_path):
    workspace,previous=parent(tmp_path);original=(previous/'state_snapshot.json').read_bytes()
    job=AssistedJob('child',str(previous),str(tmp_path/'child'),'advice',max_calls=2)
    r=continue_assisted(job,settings=settings(),session_factory=factory([call('final_answer',text='original child answer')]),advice='Check the visible evidence.',advice_model='test-strong',isolate=False)
    assert r['final']=='original child answer' and r['assistance']=='strong_advised'
    assert (previous/'state_snapshot.json').read_bytes()==original
    assert r['continuation']['parent_checkpoint_id']


def test_changed_parent_observed_file_is_rejected(tmp_path):
    workspace,previous=parent(tmp_path);(workspace/'a.py').write_text('value = 2\n')
    with pytest.raises(ValueError,match='changed'):load_parent(AssistedJob('child',str(previous),str(tmp_path/'child'),'advice'))


def test_takeover_uses_new_text_state_not_parent_native_state(tmp_path):
    workspace,previous=parent(tmp_path)
    r=continue_assisted(AssistedJob('strong',str(previous),str(tmp_path/'strong'),'takeover'),settings=settings(),session_factory=factory([call('final_answer',text='strong original answer')]),isolate=False)
    assert r['assistance']=='strong_takeover' and r['execution_authority']=='strong_takeover'
    transfer=json.loads((tmp_path/'strong/execution/TRANSFER.json').read_text())
    assert transfer['native_tensor_transfer'] is False
    s=json.loads((tmp_path/'strong/execution/state_snapshot.json').read_text())
    assert s['model_states'][transfer['target_checkpoint']]['parent_checkpoint_id'] is None


def test_retired_worker_launch_is_not_an_available_stack_option():
    from rwkv_lh.runtime.stack import RuntimeStackManager
    assert 'proactive_worker' not in inspect.signature(RuntimeStackManager.up).parameters


@pytest.mark.parametrize('mode',['advice','takeover'])
def test_unconsumed_parent_observation_is_accounted_once_before_intervention(tmp_path, mode):
    workspace=tmp_path/'workspace';workspace.mkdir();(workspace/'a.py').write_text('value = 1\n')
    previous=tmp_path/'parent'
    run_read_only_job(ReadOnlyJob('parent','Read a.py',str(workspace),str(previous),max_calls=1),settings=settings(),session_factory=factory([call('read_file',path='a.py')]))
    out=tmp_path/'child'
    continue_assisted(AssistedJob('child',str(previous),str(out),mode),settings=settings(),session_factory=factory([call('final_answer',text='value is 1')]),advice='Review.',advice_model='test-strong',isolate=False)
    s=json.loads((out/'execution/state_snapshot.json').read_text())
    records=[s['causal_records'][k] for k in s['causal_order']]
    observed=[e for e in records if e['event_type']=='action_observation_appended' and e['payload'].get('event_id')=='EV-ACTION-A00001']
    assert len(observed)==1
    intervention=next(e for e in records if e['event_type']=='action_observation_appended' and e['payload'].get('event_id') in ('ADVICE-child','TAKEOVER-child'))
    assert observed[0]['sequence'] < intervention['sequence']
    if mode=='takeover':assert observed[0]['payload']['projected_into_assignment'] is True
