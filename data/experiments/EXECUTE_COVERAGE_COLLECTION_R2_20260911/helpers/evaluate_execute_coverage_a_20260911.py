"""Evaluate preregistered A command/execute criteria from original causal snapshots."""
from pathlib import Path
import json,hashlib,sys
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.goal_state_protocols.role_trace_dataset_v1 import load_source_run
from rwkv_lh.goal_loop_protocol import rolling_goal_plan
O=R/'data/experiments/EXECUTE_COVERAGE_COLLECTION_R2_20260911'
reg=json.loads((O/'FRESH_SOURCE_REGISTRATION.json').read_text());fresh=json.loads((O/'FRESH_EXTRACTION_RESULT.json').read_text())
commands=[];handoffs=[]
for record in reg['source_runs']:
 source=load_source_run(record,base_dir=O,coverage_scope_sha256=hashlib.sha256((O/'COVERAGE_SCOPE.json').read_bytes()).hexdigest())
 for e in source.final_state.causal_records.values():
  if e.event_type!='goal_action_plan_step_assigned':continue
  action=source.final_state.actions[e.payload['action_id']]
  if action.action_type not in ('check_command','run_command'):continue
  snap=source.snapshots[e.event_id];plan=rolling_goal_plan(snap);step=plan.steps[e.payload['step_id']]
  assert plan.step_revisions.get(step.step_id,1)==e.payload['step_revision']
  raw=action.to_dict();result=raw.get('result') or {};metadata=result.get('metadata') or {}
  commands.append({'run_id':source.final_state.run_id,'action_id':e.payload['action_id'],'assignment_event_id':e.event_id,'step_id':step.step_id,'step_revision':e.payload['step_revision'],'phase':step.phase,'action_type':action.action_type,'status':raw['status'],'exit_code':result.get('exit_code'),'expected_exit_code':raw.get('arguments',{}).get('expected_exit_code',0),'arguments':raw.get('arguments'),'result_metadata':metadata,'output_sha256':hashlib.sha256(result.get('output','').encode()).hexdigest(),'error':result.get('error'),'workspace_digest_before':raw.get('workspace_digest_before'),'workspace_digest_after':raw.get('workspace_digest_after')})
 h=json.loads((O/f"{source.final_state.run_id}.HANDOFF_VERIFICATION.json").read_text());handoffs.append({k:h[k] for k in ['case','generation_contexts','role_inputs','all_verified']})
qualified=[x for x in commands if x['status']=='succeeded' and x['phase']=='execute']
coverage=fresh['coverage'].get('selector_intent',{}).get('execute',0)
keep=bool(qualified) and coverage>=1 and all(h['all_verified'] for h in handoffs)
result={'decision':'KEEP' if keep else 'NO_KEEP','successful_execute_commands':len(qualified),'commands':commands,'fresh_no_waiver_execute_rows':coverage,'waiver_used':fresh['equivalence_waiver_used'],'handoffs':handoffs,'all_returned_handoffs_verified':all(h['all_verified'] for h in handoffs),'training_candidate_status':fresh['status'],'training_sufficient':False,'tmp_overlay_live_agent_verified':False,'timeout_output_live_agent_verified':False,'command_evidence_note':'Inspect actual metadata before claiming overlay/timeout exercised; a command call alone is not proof of timeout or discarded writes.','minimum_training_rows':30,'minimum_training_boundaries':10,'optimizer_steps':0,'evaluation_script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
with (O/'KEEP_EVALUATION.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['commands','handoffs']},ensure_ascii=False))
