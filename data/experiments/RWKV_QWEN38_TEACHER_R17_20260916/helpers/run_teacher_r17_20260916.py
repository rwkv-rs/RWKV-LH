from pathlib import Path
import sys,json,hashlib,time,copy
from types import SimpleNamespace
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R))
from rwkv_lh.teacher_runtime import DeadlineStrongCompletion
from rwkv_lh.teacher_input import build_teacher_input, TEACHER_INPUT_VERSION
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
D=R
def save(p,obj):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def run(row,probe=False):
 actual=json.loads((D/'inputs'/row['id']/'INPUT.json').read_text());audit=json.loads((D/'inputs'/row['id']/'SOURCE_AUDIT.json').read_text())
 assert sha(Path(row['manifest']))==row['manifest_sha256']
 manifest=json.loads(Path(row['manifest']).read_text())
 for name,digest in manifest['source_files'].items():assert sha(Path(row['source_root'])/name)==digest,name
 source=Path(row['snapshot']);root=D/'outputs'/('engineering_probe' if probe else 'runs')/row['id'];workspace=root/'workspace';execution=root/'execution'
 copy_verified_workspace(source,workspace,audit_path=root/'COPY.json');contract=load_contract(json.loads(Path(row['conversion']).read_text()))
 save(root/'BASELINE.json',verify_python_submission(workspace,contract['cases']))
 settings=RuntimeSettings(base_url='http://127.0.0.1:18244/v1',api_key='local',model='qwen3.8-27b-r17',model_sha256='',state_transport='prompt_replay',state_profile_id='',state_profile_sha256='',max_model_len=262144,bos_token_count=0,tool_disclosure_mode='full',action_max_output_tokens=16384)
 strong=SupervisorAPISettings(base_url=settings.base_url,api_key='local',model=settings.model,stage_checker_model=settings.model,retry_attempts=1,semantic_repair_attempts=0,fallback_models=(),plan_cache_enabled=False,read_timeout_seconds=240,planner_request_options={'temperature':1.0,'top_p':0.95,'top_k':20,'return_token_ids':True,'reasoning_effort':'medium','chat_template_kwargs':{'enable_thinking':True}})
 clients=[]; context={}
 def teacher_input():
  current=context["controller"].store.load(context["run_id"])
  return build_teacher_input(goal=request,definitions=context["definitions"],failure_candidate=audit["original_output"],workspace_paths=context["paths"],state=current)
 def factory(*,settings,audit_hook):
  if probe:
   class Probe:
    model_name=settings.model
    def text_completion(self,prompt,**kwargs):
     assert context['run_id'],'teacher context missing'
     raise RuntimeError('EXPECTED_PROBE_STOP_AFTER_VERIFIED_INPUT')
   client=Probe()
  else:
   client=DeadlineStrongCompletion(strong,execution,24,max_seconds=1800,input_builder=teacher_input,max_context_tokens=262144);clients.append(client)
  return ModelSession(client,settings=settings,audit_hook=generation_snapshot_audit(workspace=workspace,output=execution,audit_hook=audit_hook))
 def seed(state,controller,model):
  context.update(controller=controller,run_id=state.run_id,definitions=model.direct_definitions(),paths=sorted(str(p.relative_to(workspace)) for p in workspace.rglob('*') if p.is_file()))
  system,payload=teacher_input()
  save(execution/'TEACHER_INITIAL_INPUT.json',{'system':system,'payload':payload})
  save(execution/'TRANSFER.json',{'source_root':row['source_root'],'source_request':row['request_id'],'original_input_sha256':row['input_sha256'],'teacher_input_version':TEACHER_INPUT_VERSION,'native_tensor_transfer':False,'teacher_fresh_task_at_source_workspace':True,'same_rwkv_input':False,'training_admitted':False})
 request=json.loads(Path(row['conversion']).read_text())['job']['request']
 job=ReadOnlyJob('TEACHER-'+row['id'],request,str(workspace),str(execution),24,1800,tool_scope='coding')
 try:result=_run_job(job,settings=settings,session_factory=factory,harness_factory=lambda:_RecordedHarness(execution),controller_type=LongHorizonController,allowed_scopes=('coding',),before_run=seed,execution_authority='strong_takeover')
 finally:
  for client in clients:client.client.close()
 save(root/'DELIVERY.json',{'result':result,'external_artifact':verify_python_submission(workspace,contract['cases']),'final_tree':tree_identity(workspace),'semantic_review':'pending','training_admitted':False})
 print(row['id'],result['termination_reason'],flush=True)
 return result
if __name__=='__main__':
 import socket,platform,os,traceback
 manifest=json.loads((R/'FILES.json').read_text())
 for name,digest in manifest['files'].items():
  if sha(R/name)!=digest:raise ValueError('frozen file changed: '+name)
 rows=json.loads((R/'TASK_SELECTION.json').read_text())['tasks']
 status=R/'outputs'/'STATUS.json'
 save(R/'outputs'/'HOST.json',{'hostname':socket.gethostname(),'python':sys.version,'platform':platform.platform(),'pid':os.getpid(),'endpoint':'http://127.0.0.1:18244/v1','execution_and_verification':'server','manifest_sha256':sha(R/'FILES.json')})
 if '--probe' in sys.argv:
  result=run(rows[0],True)
  assert 'EXPECTED_PROBE_STOP_AFTER_VERIFIED_INPUT' in str(result['error'])
  print('PROBE PASSED: fresh teacher context constructed; source workspace retained')
 else:
  completed=[]
  try:
   for row in rows:
    save(status,{'phase':'correcting','current':row['id'],'finished':completed,'time':time.time()})
    result=run(row)
    completed.append({'id':row['id'],'termination':result['termination'],'termination_reason':result['termination_reason']})
    if result['termination']=='error':raise RuntimeError('execution infrastructure error; stopped for trace inspection')
   save(status,{'phase':'complete_pending_semantic_review','finished':completed,'time':time.time(),'training_admitted':False})
  except BaseException as exc:
   save(status,{'phase':'blocked','finished':completed,'time':time.time(),'error':repr(exc),'traceback':traceback.format_exc()})
   raise
