from pathlib import Path
import hashlib,json,shutil
R=Path('/home/chase/GitHub/RWKV-LH');E=R/'data/experiments'
mapping={'SELECTOR_500_BATCH01_20260911':'SELECTOR_BOUNDARY_PILOT_R1_20260911',
'SELECTOR_500_REVIEW_BATCH01_20260911':'SELECTOR_BOUNDARY_REVIEW_R1_20260911',
'SELECTOR_500_SIMILARITY_BATCH01_20260911':'SELECTOR_BOUNDARY_SIMILARITY_R1_20260911',
'SELECTOR_500_EFFECTIVE_BATCH01_20260911':'SELECTOR_BOUNDARY_EFFECTIVE_R1_20260911',
'SELECTOR_500_RUNTIME_R2_20260911':'SELECTOR_BOUNDARY_CONTROL_R1_20260911',
'SELECTOR_EQUIVALENCE_RENEWAL_R3_20260911':'SELECTOR_500_EFFECTIVE_BATCH02_20260911',
'reconcile_selector_500_batch01_20260911.py':'reconcile_selector_boundary_pilot_20260911.py',
'apply_selector_500_similarity_batch01_20260911.py':'apply_selector_boundary_similarity_20260911.py'}
O=E/'SELECTOR_BOUNDARY_CONTROL_R1_20260911';O.mkdir(exist_ok=False)
scripts=[]
for old,new in [('reconcile_selector_500_batch01_20260911.py','reconcile_selector_boundary_pilot_20260911.py'),
 ('apply_selector_500_similarity_batch01_20260911.py','apply_selector_boundary_similarity_20260911.py'),
 ('finalize_selector_500_batch01_data_20260911.py','finalize_selector_boundary_data_20260911.py')]:
    s=(R/'temp'/old).read_text()
    for left,right in mapping.items():s=s.replace(left,right)
    s=s.replace("'completed_model_batches':1","'completed_boundary_pilots':1")
    s=s.replace("'completed_batches':1","'completed_boundary_pilots':1")
    p=R/'temp'/new;p.write_text(s);shutil.copyfile(p,O/('EVIDENCE_SCRIPT_'+new))
    scripts.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(O/'REGISTRATION.json').write_text(json.dumps({'purpose':'Reconcile pilot labels, replay all5 previously admitted source groups plus pilot, unchanged dedup and fixed anchors','scripts':scripts,'no_training':True,'optimizer_steps':0},indent=2)+'\n')
print(str(R/'temp/finalize_selector_boundary_data_20260911.py'))
