from pathlib import Path
import sys,json,hashlib,shutil,time,traceback
from dataclasses import replace
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913/collection';S=D/'source';sys.path.insert(0,str(S))
from rwkv_lh.runtime.settings import get_runtime_settings,load_local_env
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import create_model_session
from rwkv_lh.harness import ActionHarness
from rwkv_lh.controller import LongHorizonController
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.schema import RunStatus
load_local_env(R/'.env.local')
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def inventory(w):return {str(p.relative_to(w)):sha(p) for p in sorted(w.rglob('*')) if p.is_file()}
def run():
 reg=json.loads((D/'REGISTRATION.json').read_text());assert all(sha(S/p)==h for p,h in reg['source_pins'].items());settings=replace(get_runtime_settings(),tool_disclosure_mode='full',return_token_ids=True,state_transport='native_required',state_profile_id='zero',state_profile_sha256='0'*64,read_timeout_seconds=180);assert settings.model_sha256==reg['model_sha256'];results=[];start=time.time()
 for c in reg['cases']:
  if c['split']!='train':continue
  assert time.time()-start<reg['max_wall_seconds'];p=D/'runs'/c['id'];p.mkdir(parents=True,exist_ok=False);source=R/c['workspace_source'];assert inventory(source)==c['workspace_sha256'];shutil.copytree(source,p/'workspace');before=inventory(p/'workspace')
  def audit(e):
   with (p/'model_trace.jsonl').open('a') as f:f.write(json.dumps(dict(e),ensure_ascii=False)+'\n')
  model=LongHorizonModel(create_model_session(settings=settings,audit_hook=audit),harness=ActionHarness());store=LongHorizonStore(p/'state');controller=LongHorizonController(store,model=model,harness=model.harness);state=store.create_run(model.create_literal_goal(c['request'],str(p/'workspace')),run_id=c['id']);save(p/'goal.json',state.goal.to_dict());row={'id':c['id'],'case':c['case'],'path':c['path'],'final':None,'actions':[],'decisions':[],'termination':'budget','error':None};t=time.time()
  try:
   for n in range(reg['max_calls_per_task']):
    assert time.time()-start<reg['max_wall_seconds'];d=model.next_command(state,controller._persist_callback,max_output_tokens=reg['max_output_tokens']);row['decisions'].append({'checkpoint':d.checkpoint.checkpoint_id,'wire':d.wire_command.to_wire_dict()})
    if d.wire_command.name=='final_answer':row.update(final=d.wire_command.arguments['text'],termination='submitted');break
    definition=model.harness.definition(d.command.name)
    if not definition.read_only or definition.side_effect:raise ValueError('readonly_permission_violation')
    action=controller._execute_decision(state,d);event=controller._action_observation_event(state,action);model.append_action_observation(state,controller._persist_callback,event);row['actions'].append(action.to_dict());save(p/f'observation_{len(row["actions"])}.json',event.to_dict())
  except Exception as e:row.update(termination=type(e).__name__,error=str(e),traceback=traceback.format_exc())
  finally:
   state.final_output=row['final'] or '';state.status=RunStatus.COMPLETED if row['final'] is not None else RunStatus.INTERRUPTED;controller._persist(state,'run_completed' if row['final'] is not None else 'run_interrupted',{'final_output':state.final_output,'controller_rewritten':False});save(p/'state_snapshot.json',state.to_dict());row.update(elapsed_seconds=time.time()-t,workspace_unchanged=inventory(p/'workspace')==before);save(p/'RESULT.json',row);results.append(row);save(D/'RESULTS.json',results)
   files=inventory(p);save(p/'SOURCE_MANIFEST.json',{'source_type':'native_production_trace','model_sha256':reg['model_sha256'],'collector_source_manifest_sha256':reg['source_manifest_sha256'],'server_identity_sha256':reg['server_identity_sha256'],'task_registration_sha256':reg['task_registration_sha256'],'files':files});print(c['id'],row['termination'],flush=True)
  if row['error'] and row['termination'] not in ['ModelProtocolError','ModelIOError','InputBudgetError','ValueError']:break
if __name__=='__main__':run()
