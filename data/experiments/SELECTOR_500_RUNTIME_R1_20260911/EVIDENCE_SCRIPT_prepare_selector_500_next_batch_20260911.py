"""Materialize the next fixed campaign slice; no score-dependent task choice."""
from pathlib import Path
import argparse,hashlib,json,shutil
R=Path('/home/chase/GitHub/RWKV-LH');C=R/'data/experiments/SELECTOR_500_CAMPAIGN_R1_20260911'
p=argparse.ArgumentParser();p.add_argument('batch',type=int);a=p.parse_args();assert 2<=a.batch<=9
campaign=json.loads((C/'REGISTRATION.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p),'sha256':sha(p)}
def write(p,d):
 with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
assert sha(C/'TASK_QUEUE.json')==campaign['task_queue']['sha256']
queue=json.loads((C/'TASK_QUEUE.json').read_text());batch=queue[(a.batch-1)*12:a.batch*12];assert batch
name=f'SELECTOR_500_BATCH{a.batch:02d}_20260911';O=R/'data/experiments'/name;O.mkdir(exist_ok=False);B=O/'bundle';B.mkdir()
write(B/'tasks.json',{'schema_version':'rwkv-selector-500-collection.tasks.v1','tasks':[e['task'] for e in batch]})
write(B/'acceptance.json',{'schema_version':'rwkv-selector-500-collection.acceptance.v1','cases':{e['task_id']:e['acceptance'] for e in batch}})
write(B/'MANIFEST.json',{'files':{n:sha(B/n) for n in ['tasks.json','acceptance.json']},'campaign_registration':ref(C/'REGISTRATION.json'),
 'task_entries':[{'suite':e['suite'],'task_id':e['task_id'],'project_family':e['project_family']} for e in batch]})
first=R/'data/experiments/SELECTOR_500_BATCH01_20260911'
shutil.copyfile(first/'COVERAGE_SCOPE.json',O/'COVERAGE_SCOPE.json')
write(O/'BATCH_PREREGISTRATION.json',{'campaign':ref(C/'REGISTRATION.json'),'batch':a.batch,'source_commit':'3ae1efcc',
 'task_ids':[e['task_id'] for e in batch],'bundle':ref(B/'MANIFEST.json'),'model_requests_started':False,
 'fixed_queue_slice':[(a.batch-1)*12,(a.batch-1)*12+len(batch)],'task_selection_uses_scores':False,
 'max_wall_seconds':len(batch)*1800,'case_wall_seconds':1800,'case_concurrency':1,'max_transitions':200,
 'training_target_train_rows':500,'optimizer_steps':0})
driver=(first/'EVIDENCE_SCRIPT_run_selector_500_batch01_20260911.py').read_text().replace('SELECTOR_500_BATCH01_20260911',name)
driver=driver.replace('assert len(tasks)==12',f'assert len(tasks)=={len(batch)}').replace('21600',str(len(batch)*1800))
anchor="    OUTPUT.mkdir(exist_ok=False)"
guard="""    reference=json.loads((RECORD_ROOT/'data/experiments/SELECTOR_500_BATCH01_20260911/all_zero/RUN_PROTOCOL.json').read_text())
    assert benchmark._goal_role_runtime_identities(roles)==reference['goal_role_runtimes']
    assert selector.runtime_identity()==reference['independent_selector']['runtime_identity']
    assert planner.public_dict()==reference['supervisor']['settings']
"""
assert driver.count(anchor)==1;driver=driver.replace(anchor,guard+anchor)
path=R/'temp'/f'run_selector_500_batch{a.batch:02d}_20260911.py';path.write_text(driver)
shutil.copyfile(path,O/('EVIDENCE_SCRIPT_'+path.name))
post=(first/'EVIDENCE_SCRIPT_postprocess_selector_500_batch01_20260911.py').read_text().replace('SELECTOR_500_BATCH01_20260911',name).replace('SELECTOR_500_REVIEW_BATCH01_20260911',f'SELECTOR_500_REVIEW_BATCH{a.batch:02d}_20260911')
postpath=R/'temp'/f'postprocess_selector_500_batch{a.batch:02d}_20260911.py';postpath.write_text(post)
shutil.copyfile(postpath,O/('EVIDENCE_SCRIPT_'+postpath.name))
write(O/'POSTPROCESS_REGISTRATION.json',{'script_path':str(postpath),'script_sha256':sha(postpath),
 'purpose':'Unchanged production source/token reconstruction, extraction and independent review packets; no label acceptance or rescore',
 'exclude_only_missing_or_integrity_failure':True,'optimizer_steps':0})
print(json.dumps({'batch':a.batch,'task_ids':[e['task_id'] for e in batch],'driver':str(path),'postprocessor':str(postpath)}),flush=True)
