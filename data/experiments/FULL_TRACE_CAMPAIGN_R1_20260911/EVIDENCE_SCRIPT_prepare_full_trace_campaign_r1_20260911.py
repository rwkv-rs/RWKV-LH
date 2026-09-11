from pathlib import Path
import json,hashlib,shutil,itertools
R=Path('/home/chase/GitHub/RWKV-LH');W=R.with_name('RWKV-LH-full-trace-r1-20260911');C=R/'data/experiments/FULL_TRACE_CAMPAIGN_R1_20260911';O=R/'data/experiments/FULL_TRACE_COLLECTION_R1_20260911'
C.mkdir(exist_ok=True);O.mkdir(exist_ok=True);B=O/'bundle';B.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):
 with p.open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
suites=[('core30','rwkv_e2e_30'),('extension48','rwkv_e2e_extension48'),('lh12','rwkv_e2e_lh12'),('realprojectdevv1','rwkv_real_project_dev_v1'),('agentladderv1','rwkv_agent_capability_ladder_v1'),('agentv1','rwkv_agent_v1'),('diagfix2','rwkv_diag_fix_v1'),('executediagnostics','rwkv_execute_diagnostics_v1')]
lists=[];inventory=[]
for sid,folder in suites:
 base=W/'benchmarks/rwkv_e2e'/folder;tp=base/'tasks.json';ap=base/'acceptance.json';tasks=json.loads(tp.read_text())['tasks'];accept=json.loads(ap.read_text())['cases']
 rows=[dict(suite=sid,task_id=t['task_id'],project_family=sid+':'+t['task_id'],task=t,acceptance=accept[t['task_id']]) for t in tasks];lists.append(rows)
 inventory.append(dict(suite=sid,count=len(tasks),tasks_path=str(tp),tasks_sha256=sha(tp),acceptance_path=str(ap),acceptance_sha256=sha(ap)))
raw_queue=[e for group in itertools.zip_longest(*lists) for e in group if e is not None]
queue=[];seen={};duplicates=[]
for e in raw_queue:
 if e['task_id'] in seen:
  prior=seen[e['task_id']];assert prior['task']==e['task'] and prior['acceptance']==e['acceptance']
  duplicates.append({'task_id':e['task_id'],'also_in_suite':e['suite'],'executed_as_suite':prior['suite'],'task_and_acceptance_exact_equal':True})
 else:seen[e['task_id']]=e;queue.append(e)
assert len(queue)==117 and len({e['task_id'] for e in queue})==117
write(C/'TASK_QUEUE.json',queue)
write(C/'REGISTRATION.json',dict(round_id=C.name,owner_authorization='Owner requests all local public development task suites, including historical 90 and current 12, for full production raw trace accumulation; clarification says use local inventory rather than remembered 14.',source_commit='da067f25',production_change_commit='5ff6ed4a',task_queue_sha256=sha(C/'TASK_QUEUE.json'),suites=inventory,duplicate_memberships=duplicates,case_count=117,queue_order='round robin original suite order, original task order',case_wall_seconds=1800,total_wall_seconds=210600,case_concurrency=1,max_transitions=200,per_case_reruns=0,executor_output_tokens=1800,all_role_states='zero',collection_stop='normal production task termination or registered resource limit; no Selector boundary cutoff',training_optimizer_steps=0,formal_dataset_created=False,holdout_accessed=False,known_limitations=['LH09 asks for mock_api not exposed by current Selector; run and retain limitation instead of excluding it.','Two ladder L5 tasks retain original per-task network runner_control.','diagfix2 historical grader/fixture concerns retained; raw traces collected, grader validity must be distinguished from Agent outcome.'],excluded_non_model_suite={'path':'benchmarks/architecture_regression/lh_control_30/tasks.json','count':30,'reason':'architecture regression specifications, not production model requests with executable task fixtures'},role_data_policy='Raw collection is not automatic admission or training. Existing Selector data selection remains separate; no historical waiver reused for new SHA.'))
write(B/'tasks.json',{'schema_version':'rwkv-full-public-trace.tasks.v1','tasks':[e['task'] for e in queue]})
write(B/'acceptance.json',{'schema_version':'rwkv-full-public-trace.acceptance.v1','cases':{e['task_id']:e['acceptance'] for e in queue}})
write(B/'MANIFEST.json',{'files':{n:sha(B/n) for n in ['tasks.json','acceptance.json']},'campaign_registration':{'path':str(C/'REGISTRATION.json'),'sha256':sha(C/'REGISTRATION.json')},'task_entries':[{k:e[k] for k in ['suite','task_id','project_family']} for e in queue]})
shutil.copyfile(R/'data/experiments/SELECTOR_500_BATCH01_20260911/COVERAGE_SCOPE.json',O/'COVERAGE_SCOPE.json')
write(O/'BATCH_PREREGISTRATION.json',{'campaign_sha256':sha(C/'REGISTRATION.json'),'bundle_sha256':sha(B/'MANIFEST.json'),'task_count':117,'model_requests_started':False,'task_selection_uses_scores':False,'optimizer_steps':0})
s=(R/'temp/run_selector_500_batch01_20260911.py').read_text().replace('RWKV-LH-selector-500-r1-20260911',W.name).replace('SELECTOR_500_BATCH01_20260911',O.name).replace('SELECTOR_500_CAMPAIGN_R1_20260911',C.name).replace('3ae1efcc','da067f25').replace('assert len(tasks)==12','assert len(tasks)==117').replace('21600','210600').replace('selector500publicv1','fullpublictracev1').replace('Selector500 independent public-task production trace collection','Full public-task production raw trace collection').replace("'minimum_effective_train_rows_campaign':500,'minimum_independent_boundaries_campaign':167,", "'raw_collection_only':True,")
p=R/'temp/run_full_trace_collection_r1_20260911.py';p.write_text(s);shutil.copyfile(p,O/('EVIDENCE_SCRIPT_'+p.name));shutil.copyfile(Path(__file__),C/('EVIDENCE_SCRIPT_'+Path(__file__).name))
print(json.dumps({'count':len(queue),'suites':[(x['suite'],x['count']) for x in inventory],'driver':str(p)}))
