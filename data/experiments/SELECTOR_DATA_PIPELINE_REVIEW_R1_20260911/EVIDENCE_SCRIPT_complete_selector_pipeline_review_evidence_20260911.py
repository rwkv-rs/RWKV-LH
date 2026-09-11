from pathlib import Path
from collections import Counter
import hashlib,json,shutil
R=Path('/home/chase/GitHub/RWKV-LH');E=R/'data/experiments';O=E/'SELECTOR_DATA_PIPELINE_REVIEW_R1_20260911'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p),'sha256':sha(p)}
def write(p,d):
    with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
inv=json.loads((O/'DEFECT_INVENTORY.json').read_text());all_rows=[]
for group in inv['groups']:
    for key in ('source_registration','manifest'):
        assert sha(Path(group[key]['path']))==group[key]['sha256']
    all_rows.extend(json.loads(line) for line in (Path(group['manifest']['path']).parent/'candidates.jsonl').read_text().splitlines())
assert len({r['sample_id'] for r in all_rows})==len(all_rows)==621
corrected=[r for r in all_rows if r['original_target_text']!=r['target_text']]
assert len(corrected)==inv['corrected_menu_rows']==231
train=[r for r in corrected if r['split']=='train']
bound=lambda r:(r['source_run_id'],r['run_id'],r['boundary_event_id'])
repeat=[r for r in inv['correction_examples'] if r['feedback'] and r['last_action'] and r['last_action']['operation']==r['original'].split(': ',1)[1]]
write(O/'CHECKED_COUNTS.json',{'source_references_sha_verified':True,'admitted_rows':621,'unique_sample_ids':621,
 'corrected_rows':231,'train_corrected_rows':len(train),'train_boundaries_with_correction':len({bound(r) for r in train}),
 'feedback_and_repeat_wrong_operation_menu_rows':len(repeat),'feedback_and_repeat_wrong_operation_boundaries':len({bound(r) for r in repeat}),
 'generated_or_readmitted_rows':0,'optimizer_steps':0})
S=E/'SELECTOR_DATA_LATENCY_DIAGNOSIS_R1_20260911/SIMILARITY_DIAGNOSIS.json'
shutil.copyfile(S,O/'SIMILARITY_DIAGNOSIS.json')
later=E/'SELECTOR_BOUNDARY_BATCH02_20260911';review=E/'SELECTOR_BOUNDARY_REVIEW_BATCH02_20260911'
one=json.loads((review/'DECISIONS_ONE.json').read_text())['decisions'];two=json.loads((review/'DECISIONS_TWO.json').read_text())['decisions']
one={d['sample_id']:d for d in one};two={d['sample_id']:d for d in two};assert one.keys()==two.keys()
joint=Counter()
for key,a in one.items():
    b=two[key]
    joint['agree_'+a['decision'] if a['decision']==b['decision'] and a.get('suggested_operation')==b.get('suggested_operation') else 'disagree']+=1
write(O/'LATER_BATCH02_SUPPLEMENT.json',{'scope':'Collected and independently reviewed during this analysis; not included in frozen621-row replay snapshot',
 'agent_summary':ref(later/'AGENT_SUMMARY.json'),'fresh_extraction':ref(later/'FRESH_EXTRACTION_RESULT.json'),
 'reviews':[ref(review/'DECISIONS_ONE.json'),ref(review/'DECISIONS_TWO.json')],'joint_decisions':dict(joint),
 'formally_reextracted_or_selected_in_this_analysis':False,'effective_count_not_incremented':True,'optimizer_steps':0})
for name in ['inventory_selector_defect_data_plan_20260911.py','diagnose_selector_similarity_overhead_20260911.py','complete_selector_pipeline_review_evidence_20260911.py']:
    shutil.copyfile(R/'temp'/name,O/('EVIDENCE_SCRIPT_'+name))
write(O/'EVIDENCE_SHA256.json',{'files':[{'path':str(p.relative_to(O)),'sha256':sha(p)} for p in sorted(O.rglob('*')) if p.is_file()],'production_files_modified':False,'new_data_generated':False,'training_started':False})
print(json.dumps({'checked':True,'train_corrected_rows':len(train),'train_corrected_boundaries':len({bound(r) for r in train}),'later_batch_joint':dict(joint),'evidence_sha256':sha(O/'EVIDENCE_SHA256.json')}))
