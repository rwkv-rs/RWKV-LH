"""Reconcile independent labels, replay sources and apply the unchanged policy; never train."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys,time
R=Path('/home/chase/GitHub/RWKV-LH');W=Path('/home/chase/GitHub/RWKV-LH-selector-500-r1-20260911')
sys.path.insert(0,str(W))
from rwkv_lh.goal_state_protocols.role_trace_dataset_v1 import extract_registration
from rwkv_lh import role_trace_selection as selection,statetune_data
V=R/'data/experiments/SELECTOR_BOUNDARY_REVIEW_BATCH01_20260911'
D=R/'data/experiments/SELECTOR_BOUNDARY_SIMILARITY_BATCH01_20260911'
O=R/'data/experiments/SELECTOR_BOUNDARY_EFFECTIVE_BATCH01_20260911'
S=R/'data/experiments/SELECTOR_BOUNDARY_CONTROL_BATCH01_20260911'
OLD=R/'data/experiments/SELECTOR_BOUNDARY_EFFECTIVE_R1_20260911'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(p),'sha256':sha(p)}
def write(p,d):
    with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
deadline=time.monotonic()+28000
while not all((V/f'DECISIONS_{suffix}.json').exists() for suffix in ('ONE','TWO')):
    if time.monotonic()>deadline:raise TimeoutError('Independent review has not completed; no automatic acceptance')
    time.sleep(10)
subprocess.run([sys.executable,str(R/'temp/reconcile_selector_boundary_batch01_20260911.py')],cwd=W,check=True)
raw_out=W/'data/experiments/SELECTOR_BOUNDARY_REVIEW_BATCH01_20260911/reviewed_candidates'
raw=extract_registration(V/'REVIEWED_SOURCE_REGISTRATION.json',raw_out,roles=['selector_intent'])
shutil.copytree(raw_out,V/'reviewed_candidates')
dispositions=json.loads((V/'FINAL_DISPOSITIONS.json').read_text())
accepted={d['sample_id']:d for d in dispositions['dispositions'] if d['decision']=='accept'}
rejected={d['sample_id'] for d in dispositions['dispositions'] if d['decision']=='reject'}
rs=[json.loads(x) for x in (raw_out/'candidates.jsonl').read_text().splitlines()]
hr=[r for r in rs if r['label_authority']=='human_double_review']
assert {r['sample_id'] for r in hr}==set(accepted)
assert all(r['target_text']==accepted[r['sample_id']]['target_text'] for r in hr)
assert {json.loads(x)['sample_id'] for x in (raw_out/'review_queue.jsonl').read_text().splitlines()}==rejected
write(V/'FORMAL_EXTRACTION_RESULT.json',{'candidate_count':len(rs),'automatic':len(rs)-len(hr),'dual_reviewed':len(hr),
 'rejected':len(rejected),'pending':0,'quality_status':raw['status'],'equivalence_waiver_used':False,'optimizer_steps':0})
old_source=json.loads((OLD/'SELECTED_SOURCE_REGISTRATION.json').read_text())
groups=list(old_source['source_groups'])
groups.append({'source_registration':ref(V/'REVIEWED_SOURCE_REGISTRATION.json'),'candidate_manifest':ref(V/'reviewed_candidates/manifest.json')})
D.mkdir(exist_ok=False)
policy=R/'data/experiments/SELECTOR_SIMILARITY_POLICY_R1_20260910/PREREGISTRATION.json'
shutil.copyfile(policy,D/'PREREGISTRATION.json')
write(D/'APPLICATION_REGISTRATION.json',{'policy':ref(policy),'algorithm_unchanged':True,'evaluation_anchors_unchanged_required':True,
 'groups':groups,'completed_boundary_pilots':1,'completed_boundary_expansion_batches':1,'selection_uses_agent_scores':False,'optimizer_steps':0})
bundles=[str(Path(g['candidate_manifest']['path']).parent) for g in groups]
subprocess.run([sys.executable,str(R/'temp/apply_selector_boundary_similarity_batch01_20260911.py'),'union',*bundles],cwd=W,check=True)
rows=[json.loads(x) for x in (D/'union/candidates.jsonl').read_text().splitlines()]
counts={s:sum(r['split']==s for r in rows) for s in ('train','dev','confirmation')}
O.mkdir(exist_ok=False)
write(O/'ROW_SELECTION.json',{'schema_version':selection.SELECTION_SCHEMA,'role':'selector_intent',
 'kept_sample_ids':[r['sample_id'] for r in rows],'counts':counts,
 'policy_evidence_refs':[ref(D/n) for n in ['PREREGISTRATION.json','APPLICATION_REGISTRATION.json','union.EXCLUSIONS.json','union.RESULT.json']]
                        +[ref(V/'FINAL_DISPOSITIONS.json')]})
source_path=O/'SELECTED_SOURCE_REGISTRATION.json'
write(source_path,{'schema_version':selection.SOURCE_SCHEMA,'role':'selector_intent','source_groups':groups,'row_selection':ref(O/'ROW_SELECTION.json')})
effective=W/'data/experiments/SELECTOR_BOUNDARY_EFFECTIVE_BATCH01_20260911/effective_candidates'
manifest=selection.extract_selected_registration(source_path,effective,roles=['selector_intent'])
assert (effective/'candidates.jsonl').read_bytes()==(D/'union/candidates.jsonl').read_bytes()
shutil.copytree(effective,O/'effective_candidates')
normal=[];errors=[]
for row in rows:
    try:
        item=statetune_data.normalize_row(row,role='selector_intent',model_sha256='1f920b94c4684e8463f36d8b71df23a8b50551f7776d39eec9ec6970471d460b',
               context_tokens=16384,vocab_size=65536,bos_token_id=0,expected_split=row['split'])
        normal.append({'sample_id':row['sample_id'],'split':row['split'],'input_tokens':len(item['input_token_ids']),'target_tokens':len(item['target_token_ids'])})
    except Exception as exc:errors.append({'sample_id':row['sample_id'],'error':str(exc)})
write(O/'NORMALIZATION.json',{'passed':normal,'errors':errors})
boundaries={(r['source_run_id'],r['run_id'],r['boundary_event_id']) for r in rows}
training_boundaries={(r['source_run_id'],r['run_id'],r['boundary_event_id']) for r in rows if r['split']=='train'}
result={'status':manifest['status'] if not errors else 'invalid','candidate_manifest':ref(O/'effective_candidates/manifest.json'),
 'completed_boundary_pilots':1,'completed_boundary_expansion_batches':1,'pending_review':0,'full_source_replay_verified':True,'frozen_source_commit':'3ae1efcc',
 'current_main_5ff6ed4a_covered':False,'effective_rows':len(rows),'effective_counts':counts,'effective_train_rows':counts['train'],
 'independent_boundaries':len(boundaries),'independent_train_boundaries':len(training_boundaries),
 'coverage':manifest['coverage_audit'],'fixed_five_evaluation_anchors_unchanged':True,'normalization_passed':len(normal),
 'target_train_rows':500,'target_independent_train_boundaries':167,'train_row_deficit':max(0,500-counts['train']),
 'train_boundary_deficit':max(0,167-len(training_boundaries)),'formal_dataset_created':False,'freeze_executed':False,
 'smoke_executed':False,'optimizer_steps':0,'next_role_started':False}
write(O/'FINAL_GATE.json',result)
S.mkdir(exist_ok=True)
temporary=S/'LATEST_EFFECTIVE_GATE.json.new';temporary.write_text(json.dumps(ref(O/'FINAL_GATE.json'),indent=2)+'\n');temporary.replace(S/'LATEST_EFFECTIVE_GATE.json')
print(json.dumps(result),flush=True)
