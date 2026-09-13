import json, sys, shutil
from pathlib import Path
root=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(root))
from rwkv_lh import task_review as r
A=root/'data/experiments/TASK_OUTCOME_AUDIT_REFORM_R1_20260913'
M=root/'data/experiments/RWKV_DISCOVERY_INPUT_MENU_R1_20260913'
pins=json.loads((M/'RUN_REGISTRATION.json').read_text())['source_pins']
paths=sorted(set(pins)|{'rwkv_lh/task_review.py','scripts/review_agent_task.py'})
actual={p:r.file_digest(root/p) for p in paths}
r.write_once(A/'FORWARD_SOURCE_MANIFEST.json',actual)
for p in (A/'contracts').glob('*.json'):
 c=r.load_contract(p);c['kind']='task_trial';c['protocol_error_policy']='feedback';c['execution_identity']['source']=r.digest(actual)
 r.freeze_contract(c,A/'forward_contracts'/p.name)
r.write_once(A/'FORWARD_REGISTRATION.json',{'status':'frozen_contract_only_not_executed','source_manifest_sha256':r.file_digest(A/'FORWARD_SOURCE_MANIFEST.json'),'inherited_parameter_registration':str(M.relative_to(root))+'/REGRESSION_REGISTRATION.json','inherited_sha256':r.file_digest(M/'REGRESSION_REGISTRATION.json'),'task_ids':['health','smoke','validation','backup'],'repeats':2,'quality_gate':'complete fixed grid all met; outcome quality separate from reliability diagnostics','policy':'feedback through production protocol, no parameter repair','start_condition':'runner must prove actual production feedback/State continuation and bind this exact source identity before task_trial; otherwise new frozen registration required','no_inference_started':True,'no_dataset_created':True,'semantic_contract_review':'external user-bound criteria; old applications retrospective only; reference facts excluded from executor input'})
shutil.copyfile(__file__,A/'freeze_forward_script.py')
