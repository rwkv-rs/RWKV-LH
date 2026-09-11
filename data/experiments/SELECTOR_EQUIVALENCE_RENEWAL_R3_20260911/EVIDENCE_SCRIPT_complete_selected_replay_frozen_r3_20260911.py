from pathlib import Path
import hashlib,json,sys,subprocess,shutil
R=Path('/home/chase/GitHub/RWKV-LH')
W=Path('/home/chase/GitHub/RWKV-LH-freeze-effective-r3-20260911')
sys.path.insert(0,str(W))
from rwkv_lh import role_trace_selection as selection,statetune_data
from rwkv_lh.goal_state_protocols import role_trace_dataset_v1 as trace
O=R/'data/experiments/SELECTOR_EQUIVALENCE_RENEWAL_R3_20260911'
D=R/'data/experiments/SELECTOR_EXECUTE_SIMILARITY_R1_20260911'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p):return {'path':str(p),'sha256':sha(p)}
def write(p,obj):
    with p.open('x') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
names=list(trace.SOURCE_CODE_PATHS)+['rwkv_lh/role_trace_selection.py']
for name in names:
    assert (W/name).read_bytes()==subprocess.check_output(['git','show','5edcccde:'+name],cwd=R),name
write(O/'FROZEN_REPLAY_IDENTITY.json',{'local_commit':subprocess.check_output(['git','rev-parse','5edcccde'],cwd=R,text=True).strip(),
      'code_root':str(W),'files':{name:sha(W/name) for name in names},
      'reason':'Shared working tree changed during composition; original refusal retained. Validate only frozen tested/reviewed commit, not concurrent edits.',
      'observed_main_worktree_changes':subprocess.check_output(['git','diff','--name-only'],cwd=R,text=True).splitlines(),
      'main_tree_file_shas':{name:sha(R/name) for name in ['rwkv_lh/harness.py','rwkv_lh/supervisor_openai.py']}})
source=O/'SELECTED_SOURCE_REGISTRATION.json'
out=W/'data/experiments/SELECTOR_EQUIVALENCE_RENEWAL_R3_20260911/effective_candidates'
manifest=selection.extract_selected_registration(source,out,roles=['selector_intent'])
assert manifest['status']=='valid'
assert (out/'candidates.jsonl').read_bytes()==(D/'final256/candidates.jsonl').read_bytes()
assert not manifest['regression_reused']
shutil.copytree(out,O/'effective_candidates')
rows=[json.loads(line) for line in (out/'candidates.jsonl').read_text().splitlines()]
normalized=[]
for row in rows:
    value=statetune_data.normalize_row(row,role='selector_intent',model_sha256=row['context']['initial_state']['model_sha256'],
          context_tokens=16384,vocab_size=65536,bos_token_id=0,expected_split=row['split'])
    normalized.append({'sample_id':row['sample_id'],'split':row['split'],'input_tokens':len(value['input_token_ids']),
                       'target_tokens':len(value['target_token_ids'])})
write(O/'NORMALIZATION.json',normalized)
boundaries={(r['source_run_id'],r['run_id'],r['boundary_event_id']) for r in rows}
train_boundaries={(r['source_run_id'],r['run_id'],r['boundary_event_id']) for r in rows if r['split']=='train'}
raw=json.loads((O/'RAW_REPLAY_RESULTS.json').read_text())
result={'candidate_manifest':ref(O/'effective_candidates/manifest.json'),'source_registration':ref(source),
 'row_selection':ref(O/'ROW_SELECTION.json'),'raw_rows_replayed':sum(r['rows'] for r in raw),
 'effective_rows':len(rows),'effective_counts':manifest['counts_by_role']['selector_intent'],
 'distinct_boundaries':len(boundaries),'distinct_train_boundaries':len(train_boundaries),
 'candidate_status':manifest['status'],'execute_coverage':manifest['coverage_audit']['selector_intent']['execute'],
 'exact_policy_candidate_bytes_equal':True,'normalization_passed':len(normalized),'fixed_evaluation_anchors_unchanged':True,
 'first_freeze_has_no_prior':True,'training_preregistration':ref(R/'data/experiments/EXECUTE_COVERAGE_COLLECTION_R2_20260911/REGISTRATION.json'),
 'minimum_verified_menu_rows':30,'minimum_distinct_boundaries':10,'minimum_rows_met':len(rows)>=30,
 'minimum_boundaries_met':len(boundaries)>=10,'freeze_executed':False,'smoke_executed':False,'optimizer_steps':0,
 'formal_dataset_created':False,'training_status':'BLOCKED_BY_PREREGISTERED_EFFECTIVE_DATA_MINIMUMS',
 'verified_source_commit':'5edcccde','verified_source_identity':ref(O/'FROZEN_REPLAY_IDENTITY.json'),
 'concurrent_main_worktree_edits_covered':False,
 'scope':'Real source replay on frozen tested and signed source; not a dataset freeze, training run or approval of concurrent edits.'}
write(O/'FINAL_GATE.json',result)
print(json.dumps(result),flush=True)
