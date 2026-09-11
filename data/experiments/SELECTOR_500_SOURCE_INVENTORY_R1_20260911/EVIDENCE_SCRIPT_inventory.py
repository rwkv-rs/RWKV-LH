from pathlib import Path
import json, hashlib
R=Path('/home/chase/GitHub/RWKV-LH')
E=R/'data/experiments'
O=E/'SELECTOR_500_SOURCE_INVENTORY_R1_20260911'
O.mkdir(exist_ok=False)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
selected=json.loads((E/'SELECTOR_500_EFFECTIVE_BATCH01_20260911/SELECTED_SOURCE_REGISTRATION.json').read_text())
used=set()
for group in selected['source_groups']:
    for row in json.loads(Path(group['source_registration']['path']).read_text())['source_runs']:
        used.add((row['source_run_id'],row['run_id']))
current=json.loads((E/'SELECTOR_500_BATCH01_20260911/FRESH_SOURCE_REGISTRATION.json').read_text())['source_runs'][0]['protocol_sha256']
names=['ULTRADATA_COLLECTION_R1_20260909','ULTRADATA_COLLECTION_R2_20260909','ULTRADATA_COLLECTION_R3_20260909','ULTRADATA_COLLECTION_R4_20260910','ULTRADATA_OFFICIAL_COLLECTION_R5_20260910','ULTRADATA_OFFICIAL_COLLECTION_R6_20260910','REALPROJECT_HANDOFF_COLLECTION_R1_20260910','REALPROJECT_OFFICIAL_COLLECTION_R2_20260910','REALPROJECT_OFFICIAL_COLLECTION_R3_20260910','COMMAND_PATH_COLLECTION_R1_20260910','EXECUTE_COVERAGE_COLLECTION_R2_20260911']
records=[]
for name in names:
    p=E/name/'SOURCE_REGISTRATION.json'
    if not p.exists():
        records.append({'collection':name,'registration_found':False});continue
    rows=json.loads(p.read_text())['source_runs']
    cases=[]
    for row in rows:
        changed=[role for role,value in current.items() if row['protocol_sha256'].get(role)!=value]
        cases.append({'source_run_id':row['source_run_id'],'run_id':row['run_id'],
                      'already_consumed':(row['source_run_id'],row['run_id']) in used,
                      'nonwaivable_protocol_mismatches':changed,
                      'admission_not_tested_by_inventory':True})
    records.append({'collection':name,'registration':str(p),'sha256':sha(p),'cases':cases})
(O/'INVENTORY.json').write_text(json.dumps({'scope':'Explicit historical public development collection registrations only; no holdout or private acceptance read','current_protocol_identity_from':str(E/'SELECTOR_500_BATCH01_20260911/FRESH_SOURCE_REGISTRATION.json'),'records':records,'optimizer_steps':0},ensure_ascii=False,indent=2)+'\n')
for rec in records:
    cases=rec.get('cases',[])
    print(rec['collection'],len(cases),'consumed',sum(c['already_consumed'] for c in cases),'unconsumed_same_protocol',sum(not c['already_consumed'] and not c['nonwaivable_protocol_mismatches'] for c in cases))
