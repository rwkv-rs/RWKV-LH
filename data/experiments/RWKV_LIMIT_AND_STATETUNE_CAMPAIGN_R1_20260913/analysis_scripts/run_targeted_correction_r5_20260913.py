from pathlib import Path
import sys,json,hashlib,shutil,time,traceback
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R));D=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913/correction_r5'
from run_summary_advice_r3_20260913 import settings,hook,inventory,save
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import create_model_session
from rwkv_lh.harness import ActionHarness
from rwkv_lh.controller import LongHorizonController
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.schema import RunState,RunStatus,ModelEvent,CausalEventDraft
old=R/'data/experiments/RWKV_SUMMARY_ADVICE_DIAGNOSTIC_R3_20260913/runs/trial-2'
def freeze():
 D.mkdir();snapshot=json.loads((old/'pre_advice_state.json').read_text());original=json.loads((old/'RESULT.json').read_text())['baseline'];reg={'round':D.name,'created_at':time.time(),'source_state':str(old/'pre_advice_state.json'),'source_sha256':hashlib.sha256((old/'pre_advice_state.json').read_bytes()).hexdigest(),'original':original,'request':'阅读 server.py，核对原摘要中的这条陈述是否准确：该文件直接导入并使用了 threading 模块。请说明文件依据；若不准确，给出准确表述。只依据文件，不需要重写整份摘要。','schedule':[{'id':f'{arm}-{rep}','arm':arm,'repeat':rep} for rep in [1,2] for arm in ['fresh']],'max_calls':4,'max_output_tokens':1800,'max_wall_seconds':1800,'sampling':LongHorizonModel._SAMPLING.to_dict(),'model_sha256':settings().model_sha256,'pins':{str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [*R.glob('rwkv_lh/**/*.py'),Path(__file__)]},'score':'Targeted factual check: correctly distinguish direct threading import from imported http.server.ThreadingHTTPServer, explain source basis, no unsupported additions; other summary details not required. Correct task_pass requires actual complete file evidence, legal calls, State/input validity. No phrase matching or forced sequence. Same original candidate per arm; fresh versus continuation compares history/envelope, not pure State defect. Preserve all old scores.','stop':'first infrastructure exception ends batch; no semantic retry; up to16RWKV calls; no strong model'};save(D/'REGISTRATION.json',reg)
def run():
 reg=json.loads((D/'REGISTRATION.json').read_text());assert all(hashlib.sha256((R/p).read_bytes()).hexdigest()==h for p,h in reg['pins'].items());results=[];start=time.time()
 for item in reg['schedule']:
  p=D/'runs'/item['id'];p.mkdir(parents=True);source=old/'workspace';shutil.copytree(source,p/'workspace');model=LongHorizonModel(create_model_session(settings=settings(),audit_hook=hook(p/'model_trace.jsonl')),harness=ActionHarness());store=LongHorizonStore(p/'state');controller=LongHorizonController(store,model=model,harness=model.harness);row=dict(**item,final=None,actions=[],decisions=[],termination='budget');t=time.time();event=None
  if item['arm']=='continuation':
   state=RunState.from_dict(json.loads((old/'pre_advice_state.json').read_text()));state.status=RunStatus.RUNNING;state=store.save(state,expected_revision=-1,causal_event=CausalEventDraft.create('run_created',{'source':reg['source_state'],'source_sha256':reg['source_sha256']},subject_id=state.run_id));event=ModelEvent(event_type='user_message',event_id='CORRECTION-'+item['id'],scope_id=LongHorizonModel.ACTION_LANE_ID,payload={'text':reg['request'],'source':'owner_requested_fact_check'});save(p/'INITIAL_STATE.json',state.to_dict());save(p/'EVENT.json',event.to_dict())
  else:state=store.create_run(model.create_literal_goal(reg['request']+'\n\n原摘要：\n'+reg['original'],str(p/'workspace')),run_id=item['id'])
  try:
   for n in range(reg['max_calls']):
    assert time.time()-start<reg['max_wall_seconds'];d=model.next_command(state,controller._persist_callback,max_output_tokens=reg['max_output_tokens'],event=event);event=None;row['decisions'].append({'checkpoint':d.checkpoint.checkpoint_id,'wire':d.wire_command.to_wire_dict()})
    if d.wire_command.name=='final_answer':row.update(final=d.wire_command.arguments['text'],termination='submitted');break
    tool=model.harness.definition(d.command.name)
    if not tool.read_only or tool.side_effect:raise ValueError('readonly violation')
    action=controller._execute_decision(state,d);ev=controller._action_observation_event(state,action);model.append_action_observation(state,controller._persist_callback,ev);row['actions'].append(action.to_dict());save(p/f'observation_{len(row["actions"])}.json',ev.to_dict())
   state.final_output=row['final'] or '';state.status=RunStatus.COMPLETED if row['final'] is not None else RunStatus.INTERRUPTED;controller._persist(state,'run_completed' if row['final'] is not None else 'run_interrupted',{'final_output':state.final_output,'controller_rewritten':False})
  except Exception as e:row.update(termination=type(e).__name__,error=str(e),traceback=traceback.format_exc())
  row['elapsed_seconds']=time.time()-t;row['workspace_unchanged']=inventory(source)==inventory(p/'workspace');save(p/'state_snapshot.json',state.to_dict());save(p/'RESULT.json',row);results.append(row);save(D/'RESULTS.json',results);print(item['id'],row['termination'],flush=True)
  if 'error' in row:break
if __name__=='__main__':freeze() if sys.argv[1]=='freeze' else run()
