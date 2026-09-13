import sys,importlib.util,json,tempfile
from pathlib import Path
R=Path('/home/chase/GitHub/RWKV-LH');sys.path[:0]=[str(R),str(R/'tests')]
from test_unified_controller import build,call
from rwkv_lh.run_lifecycle import RUN_LIFECYCLE_POLICY_KEY,run_lifecycle_policy_document
from rwkv_lh.schema import RunStatus
spec=importlib.util.spec_from_file_location('runner',R/'temp/run_feedback_task_baseline_r1_20260913.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
D=R/'data/experiments/RWKV_FEEDBACK_TASK_BASELINE_R1_20260913';root=D/'offline_policy_r2';root.mkdir(exist_ok=False)
records=[]
for name,outputs,limit in [('recover',[call('read_file',path='sample.txt',max_lines=10),call('read_file',path='sample.txt'),call('final_answer',text='原始总结')],6),('budget',[call('read_file',path='sample.txt')],1)]:
 p=root/name;p.mkdir()
 original,store,workspace,client,model=build(p,outputs,runtime_policy={RUN_LIFECYCLE_POLICY_KEY:run_lifecycle_policy_document('goal')})
 (workspace/'sample.txt').write_text('公开健康检查，不验证事务。')
 controller=runner.ReadOnlyController(store,model=model,harness=model.harness,max_transitions=limit,min_actions=0)
 result=controller.run('RUN');state=result.state
 if name=='recover':
  assert state.protocol_rejections==1 and len(state.actions)==1 and state.final_output=='原始总结'
  assert len(client.prompts)==3 and 'max_lines' in client.prompts[1] and 'protocol_rejection' in client.prompts[1]
  assert '公开健康检查' in client.prompts[2]
 else:
  assert state.status==RunStatus.RUNNING and any(e.event_type=="run_yielded" for e in state.causal_records.values()) and not state.final_output and len(client.prompts)==1
 for cp in state.model_states.values():assert len(cp.event_ids)==len(set(cp.event_ids))
 records.append({'case':name,'requests':len(client.prompts),'protocol_rejections':state.protocol_rejections,'actions':len(state.actions),'status':state.status.value,'answer':state.final_output,'no_duplicate_checkpoint_event_ids':True})
(D/'OFFLINE_POLICY_CHECK.json').write_text(json.dumps({'mock_only':True,'production_controller_run':True,'records':records},ensure_ascii=False,indent=2)+'\n');print(records)
