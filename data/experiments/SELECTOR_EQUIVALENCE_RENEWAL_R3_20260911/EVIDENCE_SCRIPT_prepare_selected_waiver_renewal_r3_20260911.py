from pathlib import Path
import json,hashlib,copy
R=Path('/home/chase/GitHub/RWKV-LH');W=Path('/home/chase/GitHub/RWKV-LH-freeze-effective-r3-20260911');O=R/'data/experiments/SELECTOR_EQUIVALENCE_RENEWAL_R3_20260911';O.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
old= json.loads((R/'data/experiments/SELECTOR_WAIVER_RENEWAL_R1_20260910/SCOPED_EQUIVALENCE_WAIVER_ACCEPTED.json').read_text())
for e in old['entries']:assert sha(W/e['path'])==e['current_sha256']
target='rwkv_lh/statetune_data.py';current=sha(W/target)
source_paths=[('HISTORICAL14','SELECTOR_SEMANTIC_REVIEW_R1_20260910','OLD_SOURCES'),('COMMAND4','SELECTOR_FRESH_SEMANTIC_REVIEW_R1_20260910','OLD_SOURCES'),('ROUND_A4','SELECTOR_EXECUTE_SEMANTIC_REVIEW_R1_20260911','ROUND_A_SOURCES')]
old_frozen={x['path']:x['sha256'] for x in json.loads((R/'data/experiments/COMMAND_PATH_COLLECTION_R1_20260910/all_zero/source_tree_manifest.json').read_text())}[target]
a_frozen={x['path']:x['sha256'] for x in json.loads((R/'data/experiments/EXECUTE_COVERAGE_COLLECTION_R2_20260911/all_zero/source_tree_manifest.json').read_text())}[target]
waivers={}
for label,frozen in [('OLD_SOURCES',old_frozen),('ROUND_A_SOURCES',a_frozen)]:
 entries=copy.deepcopy(old['entries']) if label=='OLD_SOURCES' else []
 entries.append({'path':target,'frozen_sha256':frozen,'current_sha256':current,
  'rationale':'Selector-only source-identity waiver for the exact source registrations and current replay wrapper jointly signed in this renewal. Changes only data freeze/replay/selection auditing; no role protocol, prompt construction, model inference, or State transition changes. It does not approve training, broaden historical command semantics, manufacture evidence, or waive any source/token/checkpoint/label/split/similarity defense. Earlier ten entries retain their narrower historical14-only scope; they do not apply to the current-byte command sources.',
  'evidence_refs':['data/experiments/STATETUNE_EFFECTIVE_FREEZE_R3_20260911/REPAIR.diff','data/experiments/STATETUNE_EFFECTIVE_FREEZE_R3_20260911/INDEPENDENT_REVIEW_TWO_SCOPE_FINAL.json','data/experiments/EXECUTE_COVERAGE_COLLECTION_R2_20260911/EVIDENCE_SHA256.json']})
 value={'schema_version':old['schema_version'],'decision':'accept','reviewers':['AI reviewer /root/waiver_review_one','AI reviewer /root/waiver_review_two'],'entries':entries}
 encoded=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode();waivers[label]={'proposed_waiver':value,'prospective_sha256':hashlib.sha256(encoded).hexdigest(),'accepted_path':str(O/(label+'_WAIVER_ACCEPTED.json'))}
 draft=copy.deepcopy(value);draft['decision']='draft';write(O/(label+'_WAIVER_DRAFT.json'),draft)
groups=[]
for name,folder,label in source_paths:
 p=R/'data/experiments'/folder/'REVIEWED_SOURCE_REGISTRATION.json';doc=json.loads(p.read_text())
 groups.append({'name':name,'source_registration':{'path':str(p),'sha256':sha(p)},'source_count':len(doc['source_runs']),'source_ids':[[x['source_run_id'],x['run_id']] for x in doc['source_runs']],'waiver_label':label,'waiver_sha256':waivers[label]['prospective_sha256'],'original_candidates':str(R/'data/experiments'/folder/'reviewed_candidates/candidates.jsonl'),'original_candidates_sha256':sha(R/'data/experiments'/folder/'reviewed_candidates/candidates.jsonl')})
write(O/'PROPOSAL.json',{'scope':'Only Selector and these22 exact sources; current production raw extractor plus current scoped selection replay module. No training approval.','groups':groups,'waivers':waivers,'wrapper_path':str(W/'rwkv_lh/role_trace_selection.py'),'wrapper_sha256':sha(W/'rwkv_lh/role_trace_selection.py'),'statetune_data_current_sha256':current,'repair_diff_sha256':sha(R/'data/experiments/STATETUNE_EFFECTIVE_FREEZE_R3_20260911/REPAIR.diff'),'role':'selector_intent','optimizer_steps':0})
print(json.dumps({'source_counts':[x['source_count'] for x in groups],'new_statetune_sha256':current,'wrapper_sha256':sha(W/'rwkv_lh/role_trace_selection.py')}))
