from pathlib import Path
import sys,json,hashlib,collections
ROOT=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(ROOT))
from rwkv_lh.goal_state_protocols.role_trace_dataset_v1 import load_source_run,extract_source
out=ROOT/'data/experiments/EXECUTION_EVIDENCE_REVALIDATION_R1_20260910'
w=json.loads((ROOT/'data/experiments/EXECUTION_EVIDENCE_REPAIR_R1_20260910/EQUIVALENCE_WAIVER_DRAFT.json').read_text())
waiver={e['path']:(e['frozen_sha256'],e['current_sha256']) for e in w['entries']}
res={'purpose':'Read-only independent source audit; direct diagnostic mapping does not approve draft waiver','registrations':[],'sources':[]}
for run in ['REALPROJECT_OFFICIAL_COLLECTION_R3_20260910','ULTRADATA_OFFICIAL_COLLECTION_R6_20260910']:
 p=ROOT/'data/experiments'/run/'SOURCE_REGISTRATION.json'
 res['registrations'].append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 for record in json.loads(p.read_text())['source_runs']:
  s=load_source_run(record,base_dir=p.parent,equivalence_waiver=waiver)
  rows,exc=extract_source(s,roles=('selector_intent',))
  acts=[]
  for a in s.final_state.actions.values():
   ar=a.result or {}
   acts.append({'id':a.action_id,'type':a.action_type,'status':a.status.value,'arguments':a.wire_arguments,'result':ar})
  r={'id':record['run_id'],'registration_source':run,'status':s.final_state.status.value,'action_counts':dict(collections.Counter(a['type'] for a in acts)),'actions':acts,'selector_samples':len(rows),'selector_exclusions':len(exc),'selector_exclusion_reasons':dict(collections.Counter(e['reason'] for e in exc)),'selector_token_complete':sum(bool(x['context'].get('token_ids_complete')) for x in rows) if rows and 'context' in rows[0] else None,'sample_keys':list(rows[0]) if rows else [],'all_selector_boundaries':len(rows)+len(exc)}
  res['sources'].append(r)
  print(r['id'],r['action_counts'],r['selector_samples'],r['selector_exclusions'],flush=True)
(out/'WAIVER_SCOPED_REVIEW_TWO_EVIDENCE.json').write_text(json.dumps(res,ensure_ascii=False,indent=2)+'\n')
