"""A new explicit Goal continuation receives budgets, while history stays cumulative."""
import json
from pathlib import Path
import pytest
from rwkv_lh.assisted_agent import AssistedJob, continue_assisted
from rwkv_lh.read_only_agent import ReadOnlyJob, run_read_only_job
from test_read_only_agent import factory
from test_unified_controller import call, settings

@pytest.mark.parametrize('mode', ['advice','takeover'])
@pytest.mark.parametrize('kind,count,reason', [
 ('success',3,'identical_success_budget_exhausted'),
 ('protocol',12,'protocol_rejection_budget_exhausted'),
 ('failure',5,'identical_failure_budget_exhausted')])
def test_explicit_continuation_budgets_do_not_inherit_exhaustion(tmp_path, mode, kind, count, reason):
 workspace=tmp_path/'workspace';workspace.mkdir();(workspace/'a.py').write_text('value = 1\n')
 previous=tmp_path/'parent'
 operation=(call('read_file',path='a.py',max_lines=800) if kind=='protocol' else call('read_file',path='missing.py' if kind=='failure' else 'a.py'))
 first=run_read_only_job(ReadOnlyJob('parent','Read a.py and report honestly.',str(workspace),str(previous),max_calls=20),settings=settings(),session_factory=factory([operation]*count))
 assert first['termination']=='budget' and first['termination_reason']==reason
 original=(previous/'state_snapshot.json').read_bytes()
 child=tmp_path/'child'
 result=continue_assisted(AssistedJob('child',str(previous),str(child),mode,max_calls=3),settings=settings(),session_factory=factory([operation,call('final_answer',text='No modification or tests were performed.')]),advice='Inspect the actual evidence; report honestly.',advice_model='strong-fixture',isolate=False)
 assert result['termination']=='submitted'
 assert result['generation_started']==2
 assert result['final']=='No modification or tests were performed.'
 assert (previous/'state_snapshot.json').read_bytes()==original
 state=json.loads((child/'execution/state_snapshot.json').read_text())
 if kind=='protocol':assert state['protocol_rejections']==count+1
 else:assert max(state['observation_counts'].values())==count+1
