from pathlib import Path
import sys,json,time
sys.path.insert(0,'/home/chase/GitHub/RWKV-LH/tests')
from unittest.mock import patch
from test_read_only_agent import factory
from test_unified_controller import call,settings
from rwkv_lh.read_only_agent import ReadOnlyJob,run_read_only_job
from rwkv_lh.coding_agent import CodingJob,run_coding_job
root=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_ENGINEERING_AUDIT_R1_20260914')
source=root/'probe_source';source.mkdir(exist_ok=True)
(source/'a.txt').write_text('original')
from rwkv_lh.model_session import ModelSession
class FailedClient:
 model_name='test-rwkv'
 def text_completion(self,*args,**kwargs):raise ConnectionError('controlled transport failure')
def FailedSession(**kwargs):return ModelSession(FailedClient(),**kwargs)

r=run_read_only_job(ReadOnlyJob('disconnect','Read a.txt',str(source),str(root/'disconnect-wire'),max_calls=1),settings=settings(),session_factory=FailedSession)
results={'transport_failure':{k:r[k] for k in ('termination','termination_reason','trace_complete','generation_started','final')}}
import rwkv_lh.coding_agent as coding
original=coding.shutil.copytree
seen=False
def slow_copy(*args,**kwargs):
 global seen
 if not seen:
  seen=True;time.sleep(.15)
 return original(*args,**kwargs)
t=time.monotonic()
with patch.object(coding.shutil,'copytree',slow_copy):
 r=run_coding_job(CodingJob('copy','Read',str(source),str(root/'copy-second'),max_seconds=.05),settings=settings(),session_factory=factory([call('final_answer',text='raw')]))
results['copy_budget']={'declared_seconds':.05,'actual_seconds':time.monotonic()-t,'recorded_execution_seconds':r['elapsed_seconds'],'termination':r['termination']}
(root/'PROBES.json').write_text(json.dumps(results,indent=2));print(json.dumps(results,indent=2))
