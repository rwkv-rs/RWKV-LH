from pathlib import Path
import argparse,hashlib,json,shutil
R=Path('/home/chase/GitHub/RWKV-LH')
p=argparse.ArgumentParser();p.add_argument('batch',type=int);a=p.parse_args();assert 2<=a.batch<=9
number=a.batch
names=['reconcile_selector_500_batch01_20260911.py','apply_selector_500_similarity_batch01_20260911.py','finalize_selector_500_batch01_data_20260911.py']
outputs=[]
for name in names:
    source=(R/'temp'/name).read_text()
    source=source.replace('BATCH01_',f'BATCH{number:02d}_').replace('batch01_',f'batch{number:02d}_')
    source=source.replace("'completed_batches':1",f"'completed_batches':{number}").replace("'completed_model_batches':1",f"'completed_model_batches':{number}")
    if name.startswith('finalize_'):
        old="groups.append({'source_registration':ref(V/'REVIEWED_SOURCE_REGISTRATION.json'),'candidate_manifest':ref(V/'reviewed_candidates/manifest.json')})"
        new=f"""for prior_batch in range(1,{number+1}):
    prior=R/'data/experiments'/f'SELECTOR_500_REVIEW_BATCH{{prior_batch:02d}}_20260911'
    assert json.loads((prior/'RECONCILIATION.json').read_text())['pending']==0
    groups.append({{'source_registration':ref(prior/'REVIEWED_SOURCE_REGISTRATION.json'),'candidate_manifest':ref(prior/'reviewed_candidates/manifest.json')}})"""
        assert source.count(old)==1;source=source.replace(old,new)
    destination=R/'temp'/name.replace('batch01_',f'batch{number:02d}_');destination.write_text(source);outputs.append(destination)
O=R/'data/experiments'/f'SELECTOR_500_EFFECTIVE_CONTROL_BATCH{number:02d}_20260911';O.mkdir(exist_ok=False)
for path in outputs:shutil.copyfile(path,O/('EVIDENCE_SCRIPT_'+path.name))
(O/'REGISTRATION.json').write_text(json.dumps({'batch':number,'script_shas':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs},
 'source_groups':'all3 original groups and every fully reviewed campaign batch1..current; never discard previous data silently',
 'same_policy_and_anchors':True,'no_model_calls_or_training':True,'optimizer_steps':0},indent=2)+'\n')
print(str(outputs[-1]),flush=True)
