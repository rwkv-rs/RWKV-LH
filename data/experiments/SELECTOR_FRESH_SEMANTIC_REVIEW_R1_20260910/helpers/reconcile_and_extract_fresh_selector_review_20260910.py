from pathlib import Path
import subprocess,sys,json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
s=(R/'temp/reconcile_selector_reviews_20260910.py').read_text().replace('SELECTOR_SEMANTIC_REVIEW_R1_20260910','SELECTOR_FRESH_SEMANTIC_REVIEW_R1_20260910').replace('len(indexed)!=126','len(indexed)!=43').replace('SELECTOR_WAIVER_RENEWAL_R1_20260910/SCOPED_SOURCE_REGISTRATION.json','COMMAND_PATH_COLLECTION_R1_20260910/FRESH_SOURCE_REGISTRATION.json').replace("'source_scope_addendum_required':True","'source_scope_addendum_required':False")
p=R/'temp/reconcile_fresh_selector_reviews_20260910.py';p.write_text(s);subprocess.run([str(R/'.venv/bin/python'),str(p)],cwd=R,check=True)
from rwkv_lh.goal_state_protocols.role_trace_dataset_v1 import extract_registration
O=R/'data/experiments/SELECTOR_FRESH_SEMANTIC_REVIEW_R1_20260910';manifest=extract_registration(O/'REVIEWED_SOURCE_REGISTRATION.json',O/'reviewed_candidates',roles=['selector_intent'])
q=list(map(json.loads,(O/'reviewed_candidates/review_queue.jsonl').read_text().splitlines()));r=list(map(json.loads,(O/'reviewed_candidates/candidates.jsonl').read_text().splitlines()));d=json.loads((O/'FINAL_DISPOSITIONS.json').read_text())
a={x['sample_id']:x for x in d['dispositions'] if x['decision']=='accept'};reject={x['sample_id'] for x in d['dispositions'] if x['decision']=='reject'};hr=[x for x in r if x['label_authority']=='human_double_review']
if {x['sample_id'] for x in hr}!=set(a) or {x['sample_id'] for x in q}!=reject or any(x['target_text']!=a[x['sample_id']]['target_text'] for x in hr):raise SystemExit('fresh extraction/review mismatch')
summary={'candidate_count':len(r),'automatic':len(r)-len(hr),'dual_reviewed':len(hr),'rejected':len(q),'pending':0,'quality_status':manifest['status'],'equivalence_waiver_used':False,'execute_coverage':manifest['coverage_audit']['selector_intent']['execute'],'source_registration_sha256':hashlib.sha256((O/'REVIEWED_SOURCE_REGISTRATION.json').read_bytes()).hexdigest(),'manifest_sha256':hashlib.sha256((O/'reviewed_candidates/manifest.json').read_bytes()).hexdigest(),'optimizer_steps':0}
with (O/'FORMAL_EXTRACTION_RESULT.json').open('x') as f:json.dump(summary,f,indent=2);f.write('\n')
print(json.dumps(summary))
