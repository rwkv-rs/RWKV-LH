from pathlib import Path
import sys,json,hashlib,time,copy
from types import SimpleNamespace
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.strong_session import StrongCompletion
from rwkv_lh.supervisor_openai import SupervisorAPISettings
from rwkv_lh.model_session import ModelSession
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import ModelLaneKind,ModelCheckpointStatus
from rwkv_lh.read_only_agent import ReadOnlyJob,_run_job
from rwkv_lh.controller import LongHorizonController
from rwkv_lh.coding_agent import _RecordedHarness
from rwkv_lh.workspace_snapshot import copy_verified_workspace,tree_identity
from rwkv_lh.correction_snapshots import generation_snapshot_audit
from rwkv_lh.collection_acceptance import load_contract
from rwkv_lh.stdio_verifier import verify_python_submission
D=R/'data/experiments/RWKV_LOCAL_TEACHER_PILOT_R15_20260916'
def save(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class ExactStrong(StrongCompletion):
 def text_completion(self,prompt,max_tokens=8192,stop=None):
  if self.calls==0 and hashlib.sha256(prompt.encode()).hexdigest()!=self.expected_input:raise ValueError('first input differs from original generation boundary')
  start=len(self.events);response=super().text_completion(prompt,max_tokens=max_tokens,stop=stop)
  envelope=[e['raw_response'] for e in self.events[start:] if e['type']=='supervisor_response_envelope_received'][-1]
  choice=envelope['choices'][0];ids=choice.get('token_ids');prompt_ids=envelope.get('prompt_token_ids');usage=envelope.get('usage',{})
  if not isinstance(ids,list) or not isinstance(prompt_ids,list):raise ValueError('server omitted exact token ids')
  if len(ids)!=usage['completion_tokens'] or len(prompt_ids)!=usage['prompt_tokens']:raise ValueError('server token accounting differs')
  response.metadata={'token_ids':ids,'prompt_token_ids':prompt_ids};return response

def run(row,probe=False):
 actual=json.loads((D/'sources'/row['id']/'INPUT.json').read_text());audit=json.loads((D/'sources'/row['id']/'SOURCE_AUDIT.json').read_text())
 assert sha(Path(row['manifest']))==row['manifest_sha256']
 manifest=json.loads(Path(row['manifest']).read_text())
 for name,digest in manifest['source_files'].items():assert sha(Path(row['source_root'])/name)==digest,name
 source=Path(row['snapshot']);root=D/('engineering_probe' if probe else 'runs')/row['id'];workspace=root/'workspace';execution=root/'execution'
 copy_verified_workspace(source,workspace,audit_path=root/'COPY.json');contract=load_contract(json.loads(Path(row['conversion']).read_text()))
 save(root/'BASELINE.json',verify_python_submission(workspace,contract['cases']))
 settings=RuntimeSettings(base_url='http://127.0.0.1:29643/v1',api_key='local',model='qwen3-coder-next-fp8-r15',model_sha256='',state_transport='prompt_replay',state_profile_id='',state_profile_sha256='',max_model_len=32768,bos_token_count=0,tool_disclosure_mode='full',action_max_output_tokens=8192)
 strong=SupervisorAPISettings(base_url=settings.base_url,api_key='local',model=settings.model,stage_checker_model=settings.model,retry_attempts=1,semantic_repair_attempts=0,fallback_models=(),plan_cache_enabled=False,read_timeout_seconds=240,planner_request_options={'temperature':1.0,'top_p':0.95,'top_k':40,'return_token_ids':True})
 clients=[]
 def factory(*,settings,audit_hook):
  if probe:
   class Probe:
    model_name=settings.model
    def text_completion(self,prompt,**kwargs):
     assert prompt==actual['input_text'],'probe input mismatch'
     raise RuntimeError('EXPECTED_PROBE_STOP_AFTER_VERIFIED_INPUT')
   client=Probe()
  else:
   client=ExactStrong(strong,execution,12);client.expected_input=row['input_sha256'];clients.append(client)
  return ModelSession(client,settings=settings,audit_hook=generation_snapshot_audit(workspace=workspace,output=execution,audit_hook=audit_hook))
 def seed(state,controller,model):
  cp=model.session._checkpoint(lane_id=model.ACTION_LANE_ID,lane_kind=ModelLaneKind.ACTION,parent_checkpoint_id=None,transcript=actual['input_text'],event_ids=(),status=ModelCheckpointStatus.COMMITTED)
  state.model_states[cp.checkpoint_id]=cp;state.set_lane_head('executor',cp.checkpoint_id)
  save(execution/'TRANSFER.json',{'source_root':row['source_root'],'source_candidate_checkpoint':row['checkpoint'],'source_request':row['request_id'],'source_input_checkpoint':actual['input_checkpoint_id'],'target_checkpoint':cp.checkpoint_id,'input_sha256':row['input_sha256'],'native_tensor_transfer':False,'historical_text_only':True,'first_candidate_is_local_correction':True,'later_candidates_are_strong_continuation':True})
  controller._persist_callback(state,'action_session_started',{'lane_id':cp.lane_id,'checkpoint_id':cp.checkpoint_id,'source_input_sha256':row['input_sha256'],'execution_authority':'strong_takeover'})
 request=json.loads(Path(row['conversion']).read_text())['job']['request']
 job=ReadOnlyJob('TEACHER-'+row['id'],request,str(workspace),str(execution),12,1200,tool_scope='coding')
 try:result=_run_job(job,settings=settings,session_factory=factory,harness_factory=lambda:_RecordedHarness(execution),controller_type=LongHorizonController,allowed_scopes=('coding',),before_run=seed,execution_authority='strong_takeover')
 finally:
  for client in clients:client.client.close()
 save(root/'DELIVERY.json',{'result':result,'external_artifact':verify_python_submission(workspace,contract['cases']),'final_tree':tree_identity(workspace),'semantic_review':'pending','training_admitted':False})
 print(row['id'],result['termination_reason'],flush=True)
 return result
if __name__=='__main__':
 rows=json.loads((D/'TASK_SELECTION.json').read_text())['tasks']
 if '--probe' in sys.argv:
  result=run(rows[0],True);assert 'EXPECTED_PROBE_STOP_AFTER_VERIFIED_INPUT' in str(result['error']);print('PROBE PASSED: exact original production input reaches client')
 else:
  reg=json.loads((D/'REGISTRATION.json').read_text())
  for name,digest in reg['local_files'].items():assert sha(R/name)==digest,name
  for row in rows:
   result=run(row)
   if result['termination']=='error':raise RuntimeError('engineering error: stop pilot and inspect trace')
