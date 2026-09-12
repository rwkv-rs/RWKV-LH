"""Frozen single-operation diagnostic; uses production model, persistence and Harness."""
from pathlib import Path
import sys,json,hashlib,shutil,time,traceback
from dataclasses import replace
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
D=R/'data/experiments/RWKV_SINGLE_READ_DIAGNOSTIC_R1_20260912'
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import create_model_session
from rwkv_lh.runtime.settings import get_runtime_settings
from rwkv_lh.harness import ActionHarness
from rwkv_lh.controller import LongHorizonController
from rwkv_lh.store import LongHorizonStore

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def inventory(w):return {str(p.relative_to(w)):sha(p) for p in sorted(w.rglob('*')) if p.is_file()}
def freeze():
 rows=json.loads((D/'HISTORICAL_READS.json').read_text()); chosen=[]
 # Deterministic source-order sampling, two unique examples per observed stratum.
 for category in ['full_text','full_code','offset','missing']:
  seen=set();n=0
  for x in rows:
   a=x['action'];args=a['arguments'];path=args['path'];offset=args.get('start_byte',0)
   cat='missing' if not a['result']['success'] else 'offset' if offset else 'full_text' if path.endswith('.md') else 'full_code'
   key=(x['case'],path,offset)
   if cat!=category or key in seen:continue
   seen.add(key);n+=1
   source=R/x['source'];workspace=source.parent/'workspace'
   request=f'读取文件 {path}，从字节偏移 {offset} 开始获取直到文件结尾的文本。只执行这一次读取，不修改文件；实际无法读取时保留工具错误。'
   chosen.append({'id':f'{category}-{n}','category':category,'case':x['case'],'path':path,'start_byte':offset,'request':request,'source_event_log':x['source'],'source_event_id':x['event_id'],'source_action_id':a['action_id'],'workspace_source':str(workspace.relative_to(R)),'workspace_sha256':inventory(workspace),'source_result':a['result']})
   if n==2:break
 assert len(chosen)==8
 pins={str(p.relative_to(R)):sha(p) for p in sorted((R/'rwkv_lh').rglob('*.py'))}
 pins[str(Path(__file__).relative_to(R))]=sha(Path(__file__))
 registration={'round':'RWKV_SINGLE_READ_DIAGNOSTIC_R1_20260912','created_at':time.time(),'cases':chosen,'repeats':3,'source_pins':pins,'sampling':LongHorizonModel._SAMPLING.to_dict(),'max_output_tokens':1800,'state':'fresh zero per case and repetition; append actual observation once; no second generation','menu':'production full menu, no eligible-operation filter, no Selector or Coordinator','score':'Exactly one accepted read_file at requested path and byte offset; real Harness output equals complete UTF-8 suffix, or FileNotFoundError for absent file; unchanged workspace; observation appended. Protocol failure and wrong choice score zero; no semantic retries.','stable_boundary':'3/3 per case; category stable only when all its cases score 3/3. Finite repeatability evidence only; no project Strict or final-answer competence claim.','missing_score':'Correct read attempt plus real FileNotFoundError is diagnostic pass, never tool success or completed task.','training':False,'new_dataset_version':False,'historical_schema_replayed':False,'source_type':'R5 actual production tool traces and their workspace snapshots; diagnostic request is a controlled reduction, not role training data','stop':'24 generations maximum, 1800 output tokens each, one hour wall time; infrastructure errors terminate batch, no retry of scored cases'}
 assert not (D/'REGISTRATION.json').exists();save(D/'REGISTRATION.json',registration)
 print('FROZEN',sha(D/'REGISTRATION.json'),[(c['id'],c['case'],c['path'],c['start_byte']) for c in chosen],flush=True)

def run():
 reg=json.loads((D/'REGISTRATION.json').read_text())
 for p,h in reg['source_pins'].items():assert sha(R/p)==h,p
 settings=replace(get_runtime_settings(),tool_disclosure_mode='full',return_token_ids=True,state_transport='native_required',state_profile_id='zero',state_profile_sha256='0'*64,read_timeout_seconds=180)
 assert settings.model_sha256=='559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65'
 results=[];start=time.time()
 for repeat in range(1,4):
  for c in reg['cases']:
   assert time.time()-start<3600
   out=D/'runs'/f"{c['id']}-r{repeat}";out.mkdir(parents=True,exist_ok=False)
   source=R/c['workspace_source'];assert inventory(source)==c['workspace_sha256']
   shutil.copytree(source,out/'workspace');before=inventory(out/'workspace')
   def audit(e):
    with (out/'model_trace.jsonl').open('a') as f:f.write(json.dumps(dict(e),ensure_ascii=False)+'\n')
   result={'case':c['id'],'repeat':repeat,'pass':False,'tool_success':False,'protocol_error':None,'infrastructure_error':None}
   state=None;t=time.time()
   try:
    session=create_model_session(settings=settings,audit_hook=audit)
    model=LongHorizonModel(session,harness=ActionHarness())
    store=LongHorizonStore(out/'state');controller=LongHorizonController(store,model=model,harness=model.harness)
    state=store.create_run(model.create_literal_goal(c['request'],str(out/'workspace')),run_id=out.name)
    save(out/'goal.json',state.goal.to_dict())
    decision=model.next_command(state,controller._persist_callback,max_output_tokens=reg['max_output_tokens'])
    result['raw_output']=decision.decision.raw_output if hasattr(decision.decision,'raw_output') else None
    result['command']={'name':decision.command.name,'arguments':dict(decision.command.arguments)}
    if decision.command.name!='final_answer':
     action=controller._execute_decision(state,decision)
     result['action']=action.to_dict();result['tool_success']=action.result['success']
     event=controller._action_observation_event(state,action)
     parent=state.lane_head('executor');child=model.append_action_observation(state,controller._persist_callback,event)
     result['observation_handoff']={'parent_checkpoint_id':parent,'child_checkpoint_id':child.checkpoint_id,'event_id':event.event_id,'present':event.event_id in child.event_ids,'parent_matches':child.parent_checkpoint_id==parent}
     args=action.arguments;p=out/'workspace'/c['path']
     correct_call=action.action_type=='read_file' and args.get('path')==c['path'] and args.get('start_byte',0)==c['start_byte']
     if c['category']=='missing': actual=not p.exists() and not action.result['success'] and (action.result.get('error') or {}).get('type')=='FileNotFoundError'
     else: actual=bool(action.result['success']) and action.result['output']==p.read_bytes()[c['start_byte']:].decode('utf-8')
     result.update(correct_call=correct_call,actual_result_correct=actual,workspace_unchanged=inventory(out/'workspace')==before)
     result['pass']=correct_call and actual and result['workspace_unchanged'] and result['observation_handoff']['present'] and result['observation_handoff']['parent_matches']
   except Exception as e:
    result['error_type']=type(e).__name__;result['error']=str(e);result['traceback']=traceback.format_exc()
    protocol=type(e).__name__ in ['ModelProtocolError','ModelIOError','InputBudgetError']
    result['protocol_error' if protocol else 'infrastructure_error']=type(e).__name__
   finally:
    if state is not None:save(out/'state_snapshot.json',state.to_dict())
    result['elapsed_seconds']=time.time()-t;save(out/'RESULT.json',result);results.append(result)
    save(D/'RESULTS.json',results);print(out.name,'pass',result['pass'],'tool_success',result['tool_success'],'error',result.get('error_type'),flush=True)
   if result['infrastructure_error']:return
if __name__=='__main__':freeze() if sys.argv[1]=='freeze' else run()
