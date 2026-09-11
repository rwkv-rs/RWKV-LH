from pathlib import Path
import json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');E=R/'data/experiments'
gate=E/'SELECTOR_BOUNDARY_PILOT_R1_20260911/BOUNDARY_MECHANISM_GATE.json'
assert json.loads(gate.read_text())['boundary_mechanism']=='KEEP'
s=(R/'temp/prepare_selector_boundary_pilot_20260911.py').read_text()
for old,new in [('SELECTOR_BOUNDARY_PILOT_R1_20260911','SELECTOR_BOUNDARY_BATCH01_20260911'),
('SELECTOR_BOUNDARY_REVIEW_R1_20260911','SELECTOR_BOUNDARY_REVIEW_BATCH01_20260911'),
('run_selector_boundary_pilot_20260911.py','run_selector_boundary_batch01_20260911.py'),
('postprocess_selector_boundary_pilot_20260911.py','postprocess_selector_boundary_batch01_20260911.py')]:s=s.replace(old,new)
s=s.replace('entries=queue[24:27]','entries=queue[27:39]').replace('queued_task_count=3','queued_task_count=12')
s=s.replace('maximum_campaign_model_seconds=5400,pilot_only=True','maximum_campaign_model_seconds=21600,pilot_only=False')
s=s.replace("i+1 for i,e in enumerate(entries)","(i%3)+1 for i,e in enumerate(entries)")
s=s.replace("'fixed_original_queue_slice':[24,27]","'fixed_original_queue_slice':[27,39]")
s=s.replace("'max_wall_seconds':5400","'max_wall_seconds':21600")
s=s.replace(".replace('assert len(tasks)==12','assert len(tasks)==3').replace('21600','5400')", "")
s=s.replace('N=1,2,3 by fixed pilot position','N=1,2,3 cyclically by fixed original queue position')
s=s.replace("continuation_after_pilot='Only after boundary checks pass; pilot does not establish all Selector coverage or500 rows'", "continuation_after_pilot='First12-task expansion after validated3-task pilot; no whole-Agent continuation;500 still requires reviewed deduped train rows'")
anchor="write(O/'CAMPAIGN_REGISTRATION.json',campaign)"
s=s.replace(anchor,"campaign['boundary_mechanism_gate']="+repr({'path':str(gate),'sha256':hashlib.sha256(gate.read_bytes()).hexdigest()})+'\n'+anchor)
p=R/'temp/materialize_selector_boundary_batch01_20260911.py';p.write_text(s)
compile(s,str(p),'exec')
print(str(p))
