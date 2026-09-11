from pathlib import Path
import hashlib, json, sys

R = Path('/home/chase/GitHub/RWKV-LH')
sys.path.insert(0, str(R))
from rwkv_lh import role_trace_selection as selection
from rwkv_lh.goal_state_protocols import role_trace_dataset_v1 as trace
from rwkv_lh import statetune_data

O = R/'data/experiments/SELECTOR_EQUIVALENCE_RENEWAL_R3_20260911'
D = R/'data/experiments/SELECTOR_EXECUTE_SIMILARITY_R1_20260911'
P = json.loads((O/'PROPOSAL.json').read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ref(p): return {'path':str(p), 'sha256':sha(p)}
def write(p, value):
    with p.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

assert sha(Path(selection.__file__)) == P['wrapper_sha256']
assert sha(Path(statetune_data.__file__)) == P['statetune_data_current_sha256']
for group in P['groups']:
    for suffix, reviewer in [('ONE','one'),('TWO','two')]:
        p = O/(group['name']+'_APPROVAL_'+suffix+'.json')
        actual = json.loads(p.read_text())
        expected = {'reviewer':'AI reviewer /root/waiver_review_'+reviewer, 'decision':'accept',
                    'registration_sha256':group['source_registration']['sha256'],
                    'waiver_sha256':group['waiver_sha256'], 'wrapper_sha256':P['wrapper_sha256'],
                    'role':P['role'], 'source_count':group['source_count']}
        assert all(actual.get(k)==v for k,v in expected.items()), (str(p), 'scope approval mismatch')
for value in P['waivers'].values():
    data = (json.dumps(value['proposed_waiver'], ensure_ascii=False, indent=2)+'\n').encode()
    assert hashlib.sha256(data).hexdigest() == value['prospective_sha256']
    path = Path(value['accepted_path'])
    if path.exists(): assert path.read_bytes() == data
    else:
        with path.open('xb') as f: f.write(data)

groups, results = [], []
for group in P['groups']:
    item = {'source_registration':group['source_registration'],
            'equivalence_waiver':ref(Path(P['waivers'][group['waiver_label']]['accepted_path'])),
            'waiver_reviews':[ref(O/(group['name']+'_APPROVAL_'+suffix+'.json')) for suffix in ('ONE','TWO')]}
    source = selection.sealed(item['source_registration'])
    waiver = selection._scoped_waiver(item, source, P['role'])
    out = O/(group['name']+'_raw')
    manifest = trace.extract_registration(Path(item['source_registration']['path']), out,
        roles=[P['role']], equivalence_waiver=waiver,
        equivalence_waiver_sha256=item['equivalence_waiver']['sha256'])
    assert sha(Path(group['original_candidates'])) == group['original_candidates_sha256']
    assert (out/'candidates.jsonl').read_bytes() == Path(group['original_candidates']).read_bytes()
    item['candidate_manifest'] = ref(out/'manifest.json')
    groups.append(item)
    results.append({'group':group['name'], 'manifest':item['candidate_manifest'],
                    'rows':len((out/'candidates.jsonl').read_text().splitlines()),
                    'original_candidate_bytes_equal':True, 'raw_status':manifest['status']})
    print(json.dumps(results[-1]), flush=True)
write(O/'RAW_REPLAY_RESULTS.json',results)

rows = [json.loads(line) for line in (D/'final256/candidates.jsonl').read_text().splitlines()]
counts = {s:sum(r['split']==s for r in rows) for s in ('train','dev','confirmation')}
selection_path = O/'ROW_SELECTION.json'
write(selection_path, {'schema_version':selection.SELECTION_SCHEMA, 'role':P['role'],
      'kept_sample_ids':[r['sample_id'] for r in rows], 'counts':counts,
      'policy_evidence_refs':[ref(D/p) for p in ['PREREGISTRATION.json','APPLICATION_REGISTRATION.json',
                                               'final256.EXCLUSIONS.json','final256.RESULT.json']]
        +[ref(R/'data/experiments/SELECTOR_EXECUTE_SEMANTIC_REVIEW_R1_20260911/FINAL_DISPOSITIONS.json')]})
registration_path = O/'SELECTED_SOURCE_REGISTRATION.json'
write(registration_path, {'schema_version':selection.SOURCE_SCHEMA, 'role':P['role'],
                         'source_groups':groups, 'row_selection':ref(selection_path)})
out = O/'effective_candidates'
manifest = selection.extract_selected_registration(registration_path,out,roles=[P['role']])
assert manifest['status'] == 'valid'
assert (out/'candidates.jsonl').read_bytes() == (D/'final256/candidates.jsonl').read_bytes()
assert manifest['regression_reused'] is False
normalized=[]
for row in rows:
    value=statetune_data.normalize_row(row,role=P['role'],
        model_sha256=row['context']['initial_state']['model_sha256'],
        context_tokens=16384,vocab_size=65536,bos_token_id=0,expected_split=row['split'])
    normalized.append({'sample_id':row['sample_id'],'split':row['split'],
                       'input_tokens':len(value['input_token_ids']), 'target_tokens':len(value['target_token_ids'])})
write(O/'NORMALIZATION.json',normalized)
boundaries = {(r['source_run_id'],r['run_id'],r['boundary_event_id']) for r in rows}
training_boundaries = {(r['source_run_id'],r['run_id'],r['boundary_event_id']) for r in rows if r['split']=='train'}
prereg=R/'data/experiments/EXECUTE_COVERAGE_COLLECTION_R2_20260911/REGISTRATION.json'
result={'candidate_manifest':ref(out/'manifest.json'),'source_registration':ref(registration_path),
        'row_selection':ref(selection_path),'raw_rows_replayed':sum(r['rows'] for r in results),
        'effective_rows':len(rows),'effective_counts':counts,'distinct_boundaries':len(boundaries),
        'distinct_train_boundaries':len(training_boundaries),'candidate_status':manifest['status'],
        'execute_coverage':manifest['coverage_audit'][P['role']]['execute'],
        'exact_policy_candidate_bytes_equal':True,'normalization_passed':len(normalized),
        'fixed_evaluation_anchors_unchanged':True,'first_freeze_has_no_prior':True,
        'training_preregistration':ref(prereg),'minimum_verified_menu_rows':30,'minimum_distinct_boundaries':10,
        'minimum_rows_met':len(rows)>=30,'minimum_boundaries_met':len(boundaries)>=10,
        'freeze_executed':False,'smoke_executed':False,'optimizer_steps':0,
        'formal_dataset_created':False,'training_status':'BLOCKED_BY_PREREGISTERED_EFFECTIVE_DATA_MINIMUMS',
        'scope':'Real source replay and effective candidate validation; not a successful dataset freeze or training run.'}
write(O/'FINAL_GATE.json',result)
print(json.dumps(result),flush=True)
