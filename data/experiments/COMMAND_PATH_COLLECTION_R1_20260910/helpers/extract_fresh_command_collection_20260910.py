from pathlib import Path
import hashlib,json,sys
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.goal_state_protocols.role_trace_dataset_v1 import register_case,extract_registration
O=R/'data/experiments/COMMAND_PATH_COLLECTION_R1_20260910';reg=json.loads((O/'REGISTRATION.json').read_text());completion=json.loads((O/'COMPLETION.json').read_text());protocol=json.loads((O/'all_zero/RUN_PROTOCOL.json').read_text())
if not completion['source_unchanged'] or not all(c['result_recorded'] for c in completion['cases']):raise SystemExit('incomplete or source changed')
registration=None
for task in reg['task_ids']:
 current=register_case(O/'all_zero/cases'/task,run_id=task,source_run_id=protocol['round'],project_family=reg['project_families'][task],suite=protocol['suite'])
 if registration is None:registration=current
 else:registration['source_runs'].extend(current['source_runs'])
scope=O/'COVERAGE_SCOPE.json';registration['coverage_scope']={'path':str(scope),'sha256':hashlib.sha256(scope.read_bytes()).hexdigest()}
p=O/'FRESH_SOURCE_REGISTRATION.json'
with p.open('x') as f:json.dump(registration,f,ensure_ascii=False,indent=2);f.write('\n')
manifest=extract_registration(p,O/'fresh_selector_candidates',roles=['selector_intent'])
queue=O/'fresh_selector_candidates/review_queue.jsonl'
summary={'source_count':len(registration['source_runs']),'equivalence_waiver_used':False,'source_admission_restored':True,'status':manifest['status'],'candidates':manifest['row_count'],'pending_review':len(queue.read_text().splitlines()) if queue.exists() else 0,'coverage':manifest['coverage_audit'],'gates':manifest['quality_gates'],'source_registration_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'manifest_sha256':hashlib.sha256((O/'fresh_selector_candidates/manifest.json').read_bytes()).hexdigest(),'optimizer_steps':0}
with (O/'FRESH_EXTRACTION_RESULT.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps(summary))
