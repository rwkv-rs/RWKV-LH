from pathlib import Path
from datetime import datetime
import json,time,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');O=R/'data/experiments/SELECTOR_BOUNDARY_PILOT_R1_20260911'
deadline=time.monotonic()+6000
while not (O/'FRESH_EXTRACTION_RESULT.json').exists():
    if time.monotonic()>deadline:raise TimeoutError('Pilot extraction did not finish; no KEEP assumed')
    time.sleep(5)
reg=json.loads((O/'CAMPAIGN_REGISTRATION.json').read_text());completion=json.loads((O/'COMPLETION.json').read_text())
assert completion['source_unchanged']
assert not json.loads((O/'SOURCE_ADMISSION_EXCLUSIONS.json').read_text())
cases=[]
for case,limit in reg['boundary_limits'].items():
    C=O/'all_zero/cases'/case;events=json.loads((C/'event_log.json').read_text());trace=json.loads((C/'model_trace.json').read_text())
    staged=[i for i,e in enumerate(events) if e['type']=='exact_tool_selection_staged']
    assert len(staged)==limit,(case,len(staged),limit)
    following=events[staged[-1]+1:]
    assert len(following)==1 and following[0]['type']=='run_yielded'
    assert following[0]['data']['reason']=='selector_collection_boundary_reached'
    result=json.loads((O/'all_zero'/f'{case}.result.json').read_text())
    assert result['status']=='running' and not result['agent_completed']
    plans=[e for e in events if e['type']=='goal_plan_patch_committed']
    plans_seconds=(datetime.fromisoformat(plans[0]['timestamp'])-datetime.fromisoformat(events[0]['timestamp'])).total_seconds() if plans else None
    calls=[e for e in trace if e.get('type')=='model_session_generation_started']
    cases.append({'case':case,'selector_boundaries':len(staged),'expected_menu_rows':len(staged)*3,'no_event_after_final_selection_except_collection_yield':True,
                  'state_status':result['status'],'completed':False,'prior_rwkv_generation_calls':len(calls),'initial_plan_commit_seconds':plans_seconds,
                  'wall_seconds':next(c['wall_seconds'] for c in completion['cases'] if c['task_id']==case)})
extraction=json.loads((O/'FRESH_EXTRACTION_RESULT.json').read_text())
assert extraction['raw_candidates']+extraction['pending_review']==sum(c['expected_menu_rows'] for c in cases)
proof={'boundary_mechanism':'KEEP','cases':cases,'source_unchanged':True,'sources':extraction['sources'],
       'automatic_candidates':extraction['raw_candidates'],'pending_independent_review':extraction['pending_review'],
       'whole_agent_evaluation_keep_claimed':False,'all_selector_coverage_claimed':False,'train500_claimed':False,'optimizer_steps':0}
with (O/'BOUNDARY_MECHANISM_GATE.json').open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
print(json.dumps(proof),flush=True)
