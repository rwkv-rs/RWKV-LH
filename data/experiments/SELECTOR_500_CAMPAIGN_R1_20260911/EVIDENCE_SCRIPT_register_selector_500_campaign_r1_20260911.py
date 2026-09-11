from pathlib import Path
import sys,json,hashlib,collections,datetime,shutil
R=Path('/home/chase/GitHub/RWKV-LH');W=Path('/home/chase/GitHub/RWKV-LH-selector-500-r1-20260911')
sys.path.insert(0,str(W))
from scripts import run_rwkv_e2e_benchmark as b
from rwkv_lh.role_trace_artifacts import byte_5gram_cosine,split_project_family
C=R/'data/experiments/SELECTOR_500_CAMPAIGN_R1_20260911';C.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p),'sha256':sha(p)}
def write(p,d):
    with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
# Explicit allowlist: never enumerate/read final holdout resources.
suites=['core30','extension48','lh12','agentladderv1','agentv1']
queues={};catalogs=[];excluded=[]
for key in suites:
    tasks,cases=b.load_suite(key);tp,ap=b.suite_resource_paths(b.SUITES[key]);catalogs.append({'suite':key,'tasks':ref(tp),'acceptance':ref(ap)})
    queue=[]
    for t in tasks:
        control=cases[t['task_id']].get('runner_control',{})
        reason='unsupported_selector_mock_api' if control.get('enable_mock_api') else None
        if control.get('network_policy','offline')!='offline':reason='offline_collection_scope'
        if reason:excluded.append({'suite':key,'task_id':t['task_id'],'reason':reason});continue
        queue.append({'suite':key,'task_id':t['task_id'],'project_family':key+':'+t['task_id'],
                      'task':t,'acceptance':cases[t['task_id']]})
    queues[key]=collections.deque(sorted(queue,key=lambda x:x['task_id']))
ordered=[]
while any(queues.values()):
    for key in suites:
        if queues[key]:ordered.append(queues[key].popleft())
# Pre-generation duplicate exclusion by the unchanged public-request algorithm.
accepted=[];overlaps=[]
for entry in ordered:
    match=None
    for old in accepted:
        sim=byte_5gram_cosine(entry['task']['user_request'],old['task']['user_request'])
        if sim>=.95:match={'suite':old['suite'],'task_id':old['task_id'],'cosine':sim};break
    if match:overlaps.append({'suite':entry['suite'],'task_id':entry['task_id'],'duplicate_of':match})
    else:accepted.append(entry)
write(C/'TASK_QUEUE.json',accepted)
policy=R/'data/experiments/SELECTOR_SIMILARITY_POLICY_R1_20260910/PREREGISTRATION.json'
old=R/'data/experiments/SELECTOR_EQUIVALENCE_RENEWAL_R3_20260911/FINAL_GATE.json'
registration={'campaign_id':C.name,'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'owner_authorization':'2026-09-11 user explicitly requested push, more production data and at least500 effective samples, focused on Selector before the next role.',
 'target_role':'selector_intent','target_minimum_train_rows':500,'fixed_evaluation_anchor_rows':5,
 'unit':'A row is one verified Selector menu rendering. The same decision may contribute up to3 distinct menu-order variants; independent decision boundaries are reported separately, never called500 independent scenarios.',
 'minimum_independent_boundaries':167,'old_effective_gate':ref(old),'similarity_policy':ref(policy),
 'source_commit':'3ae1efcc','source_root':str(W),'production_source_changes':False,
 'task_queue':ref(C/'TASK_QUEUE.json'),'public_catalogs':catalogs,'excluded_before_generation':excluded,
 'public_request_duplicates_excluded':overlaps,'queued_task_count':len(accepted),
 'order':'fixed suite round-robin, lexical task ID per suite, before model generation; no split or result-driven reorder',
 'project_family_policy':'original suite:task_id; no rename or rehash to move rows to train',
 'batch_size':12,'case_concurrency':1,'max_transitions_per_case':200,'case_wall_seconds':1800,
 'max_wall_seconds_per_full_batch':21600,'maximum_campaign_model_seconds':len(accepted)*1800,
 'per_case_reruns':0,'native_transport_resume_attempts':1,'supervisor_pending_resume_attempts':0,
 'executor_max_output_tokens':1800,'role_states':'all_zero','models':'existing Selector2.9B, otherRWKV13.3B, official DeepSeek Planner low thinking',
 'stop':'after a whole batch when at least500 TRAIN rows survive independent review and unchanged dedup and all Selector quality gates pass; never truncate or lower policy to hit count',
 'if_pool_insufficient':'register an additional independent public/authored-task pool before any further generations; no synthetic role rows or hidden holdout',
 'next_role':'only after Selector StateTune and fixed regression qualification; freeze retained Selector State before Executor collection',
 'training_started':False,'optimizer_steps':0,'formal_dataset_created':False,
 'separate_gates':['input/token/checkpoint/source identity','label authority and independent review','unchanged fixed split and5anchors','coverage','similarity','effective train quantity','sealed replay/freeze','smoke and registered training/evaluation'],
 'hidden_holdout_accessed':False}
write(C/'REGISTRATION.json',registration)
write(C/'QUEUE_AUDIT.json',{'queued':len(accepted),'excluded':excluded,'duplicate_exclusions':overlaps,
 'family_splits':{e['project_family']:split_project_family(e['project_family']) for e in accepted},'score_inspected':False})
# Freeze first batch resources without changing any task or verifier bytes semantically.
O=R/'data/experiments/SELECTOR_500_BATCH01_20260911';O.mkdir(exist_ok=False);B=O/'bundle';B.mkdir()
batch=accepted[:12]
write(B/'tasks.json',{'schema_version':'rwkv-selector-500-collection.tasks.v1','tasks':[e['task'] for e in batch]})
write(B/'acceptance.json',{'schema_version':'rwkv-selector-500-collection.acceptance.v1','cases':{e['task_id']:e['acceptance'] for e in batch}})
write(B/'MANIFEST.json',{'files':{n:sha(B/n) for n in ['tasks.json','acceptance.json']},'campaign_registration':ref(C/'REGISTRATION.json'),'task_entries':[{'suite':e['suite'],'task_id':e['task_id'],'project_family':e['project_family']} for e in batch]})
shutil.copyfile(R/'data/experiments/EXECUTE_COVERAGE_COLLECTION_R2_20260911/COVERAGE_SCOPE.json',O/'COVERAGE_SCOPE.json')
write(O/'BATCH_PREREGISTRATION.json',{'campaign':ref(C/'REGISTRATION.json'),'batch':1,'source_commit':'3ae1efcc',
 'task_ids':[e['task_id'] for e in batch],'bundle':ref(B/'MANIFEST.json'),'model_requests_started':False,
 'family_membership_extension':'Owner-authorized new public task sources extend original provenance text, unchanged role coverage scope is not a task allowlist.',
 'max_wall_seconds':21600,'case_wall_seconds':1800,'case_concurrency':1,'max_transitions':200,
 'KEEP':'collection data retained only under source/evidence/label gates; not Agent improvement claim',
 'training_target_train_rows':500,'optimizer_steps':0})
print(json.dumps({'queued':len(accepted),'first_batch':[e['task_id'] for e in batch],
 'campaign_registration_sha256':sha(C/'REGISTRATION.json'),'task_queue_sha256':sha(C/'TASK_QUEUE.json')}),flush=True)
