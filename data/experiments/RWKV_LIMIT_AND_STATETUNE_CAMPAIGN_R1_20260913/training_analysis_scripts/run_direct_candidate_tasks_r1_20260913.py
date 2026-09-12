from pathlib import Path
import sys,json,hashlib,shutil,time,traceback
from dataclasses import replace
R=Path('/home/chase/GitHub/RWKV-LH');P=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913';D=P/'evaluation';S=P/'training_runtime/source_r2';sys.path.insert(0,str(S))
from rwkv_lh.runtime.settings import get_runtime_settings,load_local_env
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import create_model_session
from rwkv_lh.harness import ActionHarness
from rwkv_lh.controller import LongHorizonController
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.schema import RunStatus
from rwkv_lh.inference.uploaded_sources import source_inventory
load_local_env(R/'.env.local')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def inventory(p):return {str(f.relative_to(p)):sha(f) for f in sorted(p.rglob('*')) if f.is_file()}
def run(split):
 reg=json.loads((D/'RUN_REGISTRATION.json').read_text());assert sha(Path(__file__))==reg['runner_sha256'];er=json.loads((D/'REGRESSION_REGISTRATION.json').read_text());assert sha(D/'REGRESSION_REGISTRATION.json')==reg['regression_fingerprint'];assert {p:h for p,(h,n) in source_inventory(S).items()}==reg['source_pins']
 if split=='confirmation':assert json.loads((D/'DEV_GATE.json').read_text())['passed'] is True
 results=[];started=time.time()
 for repeat in [1,2]:
  for c in er['cases']:
   if c['split']!=split:continue
   for arm in (['zero','candidate'] if repeat==1 else ['candidate','zero']):
    assert time.time()-started<5400
    profile=reg['profiles'][arm];settings=replace(get_runtime_settings(),base_url=reg['base_url'],model=reg['model_name'],model_sha256=reg['model_sha256'],tool_disclosure_mode='full',return_token_ids=True,state_transport='native_required',state_profile_id=profile['id'],state_profile_sha256=profile['sha256'],read_timeout_seconds=180);assert LongHorizonModel._SAMPLING.to_dict()==er['sampling']
    p=D/split/f'{c["id"]}-{arm}-r{repeat}';p.mkdir(parents=True,exist_ok=False);source=R/c['workspace_source'];assert inventory(source)==c['workspace_sha256'];shutil.copytree(source,p/'workspace');before=inventory(p/'workspace')
    def audit(e):
     with (p/'model_trace.jsonl').open('a') as f:f.write(json.dumps(dict(e),ensure_ascii=False)+'\n')
    model=LongHorizonModel(create_model_session(settings=settings,audit_hook=audit),harness=ActionHarness());store=LongHorizonStore(p/'state');controller=LongHorizonController(store,model=model,harness=model.harness);state=store.create_run(model.create_literal_goal(c['request'],str(p/'workspace')),run_id=p.name);save(p/'goal.json',state.goal.to_dict());row={'id':p.name,'file_id':c['id'],'arm':arm,'repeat':repeat,'final':None,'actions':[],'decisions':[],'termination':'budget','error':None};t=time.time()
    try:
     for n in range(er['max_calls_per_task']):
      if time.time()-t>=er['max_seconds_per_task']:row['termination']='wall_budget';break
      decision=model.next_command(state,controller._persist_callback,max_output_tokens=er['max_output_tokens']);row['decisions'].append({'checkpoint':decision.checkpoint.checkpoint_id,'wire':decision.wire_command.to_wire_dict()})
      if decision.wire_command.name=='final_answer':row.update(final=decision.wire_command.arguments['text'],termination='submitted');break
      definition=model.harness.definition(decision.command.name)
      if not definition.read_only or definition.side_effect:raise ValueError('readonly_permission_violation')
      action=controller._execute_decision(state,decision);event=controller._action_observation_event(state,action);model.append_action_observation(state,controller._persist_callback,event);row['actions'].append(action.to_dict());save(p/f'observation_{len(row["actions"])}.json',event.to_dict())
    except Exception as e:row.update(termination=type(e).__name__,error=str(e),traceback=traceback.format_exc())
    finally:
     state.final_output=row['final'] or '';state.status=RunStatus.COMPLETED if row['final'] is not None else RunStatus.INTERRUPTED;controller._persist(state,'run_completed' if row['final'] is not None else 'run_interrupted',{'final_output':state.final_output,'controller_rewritten':False});save(p/'state_snapshot.json',state.to_dict());row.update(elapsed_seconds=time.time()-t,workspace_unchanged=inventory(p/'workspace')==before);save(p/'RESULT.json',row);results.append(row);save(D/(split.upper()+'_RESULTS.json'),results);print(p.name,row['termination'],flush=True)
    if row['error'] and row['termination'] not in ['ModelProtocolError','ModelIOError','InputBudgetError','ValueError']:return
if __name__=='__main__':run(sys.argv[1])
