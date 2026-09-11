from pathlib import Path
from collections import Counter,defaultdict
import json,hashlib,subprocess
R=Path('/home/chase/GitHub/RWKV-LH');E=R/'data/experiments';O=E/'SELECTOR_DATA_PIPELINE_REVIEW_R1_20260911';O.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
    with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
selected=E/'SELECTOR_BOUNDARY_EFFECTIVE_BATCH01_20260911/SELECTED_SOURCE_REGISTRATION.json'
groups=json.loads(selected.read_text())['source_groups'];all_rows=[];group_records=[];corrections=[];rejects=[]
for group in groups:
    reg=Path(group['source_registration']['path']);root=reg.parent
    bundle=Path(group['candidate_manifest']['path']).parent
    rows=[json.loads(line) for line in (bundle/'candidates.jsonl').read_text().splitlines()];all_rows.extend(rows)
    dispositions=root/'FINAL_DISPOSITIONS.json'
    ds=json.loads(dispositions.read_text())['dispositions'] if dispositions.exists() else []
    byid={r['sample_id']:r for r in rows}
    for d in ds:
        if d['decision']=='reject':rejects.append(d);continue
        row=byid.get(d['sample_id'])
        if row is None:continue
        if row['original_target_text']!=row['target_text']:
            source=row['protocol_source'];progress=source['current_progress'];subtask=source['current_subtask']
            corrections.append({'sample_id':row['sample_id'],'source_run_id':row['source_run_id'],'run_id':row['run_id'],
              'boundary_event_id':row['boundary_event_id'],'original':row['original_target_text'].strip(),'target':row['target_text'].strip(),
              'objective':subtask['objective'],'phase':subtask['phase'],'eligible_labels':source['eligible_labels'],
              'assigned_action_count':progress['assigned_action_count'],'failed_action_count':progress['failed_action_count'],
              'last_action':progress['last_action'],'feedback':progress['feedback'],'recent_rejections_count':len(progress.get('recent_rejections',[])),
              'candidate_manifest':group['candidate_manifest'],'input_sha256':hashlib.sha256(row['input_text'].encode()).hexdigest(),
              'original_output_record_sha256':row['original_output_record_sha256']})
    group_records.append({'source_registration':group['source_registration'],'manifest':group['candidate_manifest'],
                         'admitted_rows':len(rows),'reconciled':len(ds),'rejected':sum(d['decision']=='reject' for d in ds)})
def boundary(r):return (r['source_run_id'],r['run_id'],r['boundary_event_id'])
matrix=Counter((r['original'],r['target']) for r in corrections)
effective=E/'SELECTOR_BOUNDARY_EFFECTIVE_BATCH01_20260911/effective_candidates/candidates.jsonl'
kept=[json.loads(line) for line in effective.read_text().splitlines()]
write(O/'DEFECT_INVENTORY.json',{'scope':'Seven fully replayed source groups through boundary expansion01; running expansion02 excluded from this frozen analysis snapshot',
 'groups':group_records,'admitted_rows':len(all_rows),'admitted_boundaries':len({boundary(r) for r in all_rows}),
 'automatic_rows':sum(r['label_authority']!='human_double_review' for r in all_rows),'dual_review_rows':sum(r['label_authority']=='human_double_review' for r in all_rows),
 'corrected_menu_rows':len(corrections),'boundaries_with_correction':len({boundary(r) for r in corrections}),
 'corrected_rows_after_prior_action':sum(r['assigned_action_count']>0 for r in corrections),
 'corrected_rows_with_prior_failure':sum(r['failed_action_count']>0 for r in corrections),
 'corrected_rows_with_feedback':sum(bool(r['feedback']) for r in corrections),
 'correction_matrix':[{'original':a,'target':b,'menu_rows':n} for (a,b),n in matrix.most_common()],
 'effective_rows':len(kept),'effective_counts':dict(Counter(r['split'] for r in kept)),
 'effective_labels':dict(Counter(r['target_text'].strip() for r in kept)),
 'effective_corrected_rows':sum(r['original_target_text']!=r['target_text'] for r in kept),
 'rejected_review_rows':len(rejects),'no_model_accuracy_claim':'This is a selected reviewed population, not an unbiased Selector accuracy estimate.',
 'correction_examples':corrections})
history=[]
for commit,path in [('9abb43ec^','scripts/generate_rwkv_state_tuning_stage1_selector_v1.py'),
 ('9abb43ec^','scripts/generate_rwkv_action_state_tuning_round1_2k_v1.py'),
 ('9abb43ec^','scripts/build_exact_tool_selector_dataset_v1.py'),
 ('aa8afe97^','rwkv_lh/goal_state_protocols/dataset_contract.py')]:
    raw=subprocess.check_output(['git','show',f'{commit}:{path}'],cwd=R)
    history.append({'commit':subprocess.check_output(['git','rev-parse',commit],cwd=R,text=True).strip(),'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'code_read_only':True,'restored_or_executed':False})
write(O/'HISTORICAL_CODE_REFERENCES.json',history)
print(json.dumps({'admitted_rows':len(all_rows),'boundaries':len({boundary(r) for r in all_rows}),'corrected_rows':len(corrections),'corrected_boundaries':len({boundary(r) for r in corrections}),'matrix':[{'from':a,'to':b,'rows':n} for (a,b),n in matrix.most_common(10)]},ensure_ascii=False))
