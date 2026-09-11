from pathlib import Path
import json,hashlib,shutil
R=Path('/home/chase/GitHub/RWKV-LH');E=R/'data/experiments';O=E/'SELECTOR_BOUNDARY_CONTROL_BATCH01_20260911';O.mkdir(exist_ok=False)
pairs=[('SELECTOR_BOUNDARY_PILOT_R1_20260911','SELECTOR_BOUNDARY_BATCH01_20260911'),
('SELECTOR_BOUNDARY_REVIEW_R1_20260911','SELECTOR_BOUNDARY_REVIEW_BATCH01_20260911'),
('SELECTOR_BOUNDARY_SIMILARITY_R1_20260911','SELECTOR_BOUNDARY_SIMILARITY_BATCH01_20260911'),
('SELECTOR_BOUNDARY_EFFECTIVE_R1_20260911','SELECTOR_BOUNDARY_EFFECTIVE_BATCH01_20260911'),
('SELECTOR_BOUNDARY_CONTROL_R1_20260911','SELECTOR_BOUNDARY_CONTROL_BATCH01_20260911'),
('SELECTOR_500_EFFECTIVE_BATCH02_20260911','SELECTOR_BOUNDARY_EFFECTIVE_R1_20260911'),
('reconcile_selector_boundary_pilot_20260911.py','reconcile_selector_boundary_batch01_20260911.py'),
('apply_selector_boundary_similarity_20260911.py','apply_selector_boundary_similarity_batch01_20260911.py')]
scripts=[]
for old,new in [('reconcile_selector_boundary_pilot_20260911.py','reconcile_selector_boundary_batch01_20260911.py'),
('apply_selector_boundary_similarity_20260911.py','apply_selector_boundary_similarity_batch01_20260911.py'),
('finalize_selector_boundary_data_20260911.py','finalize_selector_boundary_batch01_data_20260911.py')]:
    s=(R/'temp'/old).read_text()
    for left,right in pairs:s=s.replace(left,right)
    s=s.replace("'completed_boundary_pilots':1","'completed_boundary_pilots':1,'completed_boundary_expansion_batches':1")
    compile(s,new,'exec');p=R/'temp'/new;p.write_text(s);shutil.copyfile(p,O/('EVIDENCE_SCRIPT_'+new))
    scripts.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(O/'REGISTRATION.json').write_text(json.dumps({'purpose':'Replay full six prior source groups plus boundary expansion, reconcile two independent AI reviews, preserve immutable similarity policy and5anchors','scripts':scripts,'optimizer_steps':0},indent=2)+'\n')
