from pathlib import Path
import hashlib,json,sys,shutil
R=Path('/home/chase/GitHub/RWKV-LH');W=Path('/home/chase/GitHub/RWKV-LH-selector-500-r1-20260911');sys.path.insert(0,str(W))
from rwkv_lh.goal_state_protocols.role_trace_dataset_v1 import register_case,extract_registration
O=R/'data/experiments/SELECTOR_BOUNDARY_PILOT_R1_20260911';case='AGENT-LADDER-L3-WEB01';C=O/'all_zero/cases'/case
reg=json.loads((O/'REGISTRATION.json').read_text());protocol=json.loads((O/'all_zero/RUN_PROTOCOL.json').read_text())
events=json.loads((C/'event_log.json').read_text());staged=[i for i,e in enumerate(events) if e['type']=='exact_tool_selection_staged']
assert len(staged)==1 and events[-1]['type']=='run_yielded'
assert events[-1]['data']['reason']=='selector_collection_boundary_reached'
trace=json.loads((C/'model_trace.json').read_text())
assert not any(e.get('type')=='model_session_generation_started' for e in trace)
assert not any(e['type']=='action_started' for e in events)
source=register_case(C,run_id=case,source_run_id=protocol['round'],project_family=reg['project_families'][case],suite=protocol['suite'])
scope=O/'COVERAGE_SCOPE.json';source['coverage_scope']={'path':str(scope),'sha256':hashlib.sha256(scope.read_bytes()).hexdigest()}
p=O/'FIRST_CASE_SOURCE_PREVIEW.json'
with p.open('x') as f:json.dump(source,f,indent=2);f.write('\n')
out=W/'data/experiments/SELECTOR_BOUNDARY_PILOT_R1_20260911/first_case_preview'
m=extract_registration(p,out,roles=['selector_intent']);shutil.copytree(out,O/'first_case_preview')
rows=[]
for name in ('candidates.jsonl','review_queue.jsonl'):
    p=out/name
    if p.exists():rows.extend(json.loads(line) for line in p.read_text().splitlines())
assert len(rows)==3
proof={'case':case,'durable_selector_boundaries':1,'replayed_selector_menu_rows':3,'no_executor_or_auditor_generation':True,'no_actions':True,
       'state_status':'running','stop_reason':events[-1]['data']['reason'],'new_waiver_used':False,'candidate_status':m['status'],
       'preview_only_do_not_count_again':True,'optimizer_steps':0}
with (O/'FIRST_CASE_BOUNDARY_CHECK.json').open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(proof))
