from pathlib import Path
import json,hashlib,tarfile,shutil
R=Path('/home/chase/GitHub/RWKV-LH');P=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913';D=P/'evaluation_r2'
def put(p,x):
 assert not p.exists(),p
 p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
mechanical=json.loads((D/'DEV_MECHANICAL.json').read_text());resources={}
for arm in ['zero','candidate']:
 rows=[r for r in mechanical if r['arm']==arm]
 resources[arm]=dict(generated_calls=sum(len(r['calls']) for r in rows),input_tokens_full_logical=sum(c['input_tokens'] for r in rows for c in r['calls']),output_tokens=sum(c['output_tokens'] for r in rows for c in r['calls']),end_to_end_seconds=sum(r['elapsed_seconds'] for r in rows),tool_calls=sum(r['tool_calls'] for r in rows),repeated_read_tasks=sum(r['read_calls']>1 for r in rows))
put(D/'DEV_RESOURCES.json',resources)
pre=json.loads((P/'PRETRAINING_RESOURCE_LEDGER.json').read_text());r1=json.loads((P/'evaluation/DEV_RESOURCES.json').read_text());reads=[r for a in ['zero','candidate'] for r in json.loads((D/f'read_{a}/MECHANICAL_AUDIT.json').read_text())]
runs=[json.loads((P/f'{d}/remote_run/RESULT.json').read_text()) for d in ['training','training_r2']]
ledger=dict(rwkv_calls=pre['rwkv_calls']+sum(x['generated_calls'] for x in r1.values())+sum(x['generated_calls'] for x in resources.values())+len(reads),input_tokens_full_logical_context=pre['input_tokens_full_logical_context']+sum(x['input_tokens_full_logical'] for x in r1.values())+sum(x['input_tokens_full_logical'] for x in resources.values())+sum(x['input_tokens'] for x in reads),output_tokens_exact=pre['output_tokens_exact']+sum(x['output_tokens'] for x in r1.values())+sum(x['output_tokens'] for x in resources.values())+sum(x['output_tokens'] for x in reads),strong_responses=20,strong_provider_tokens=174691,optimizer_steps=sum(x['optimizer_steps'] for x in runs),training_elapsed_seconds=sum(x['elapsed_seconds'] for x in runs),training_peak_allocated_bytes=max(x['peak_allocated_bytes'] for x in runs),training_target_tokens=sum(x['target_tokens_seen'] for x in runs),cost_money=None,note='Includes failed first candidate and curation failures. Full logical input is not incremental recurrent prefill computation. Training elapsed includes cold load/hash. No project throughput, billing or qualified-project cost evidence. Native validation 496.21 seconds recorded separately in R1 archive.')
assert ledger['rwkv_calls']==161 and ledger['optimizer_steps']==108
put(P/'CAMPAIGN_RESOURCE_LEDGER.json',ledger)
put(P/'SERVICE_FINAL_STATUS.json',dict(unit='rwkv-lh-direct-statetune-eval-r3.service',status='inactive',action='stopped only campaign evaluation service after evidence collection',production_default_changed=False,remote_git_used=False,github_updated=False))
expected={'rwkv_lh/controller.py':'bcdc77c5c6b19e0c24d2c9d32ae98cb3dfa5335fc8d59fdb721b659d3367d83a','rwkv_lh/model.py':'bd1c44985062692ebcb357e7e9fbe64c03bbd2c49e8d4e126db131f3fff76c20','rwkv_lh/supervisor_openai.py':'1ed4b58917f17266d95cedcdc1a4c893e7944f8b782c398357d3f19740d7cb10','tests/test_hybrid_supervisor.py':'0cd03caa0c56c084cc018f0f2930cf6de07338b3bcd14b74e0addcff197684b8','tests/test_supervisor_openai.py':'32c61aeeb3dcb07a616c24bba20e5c72eafbe65ef36f6d278502a56b444caeb5'}
assert all(hashlib.sha256((R/f).read_bytes()).hexdigest()==s for f,s in expected.items());put(P/'PREEXISTING_FINAL_PRESERVED.json',expected)
adir=P/'training_r2_analysis_scripts';adir.mkdir(exist_ok=False)
for name in ['run_direct_candidate_tasks_r2_20260913.py','audit_direct_candidate_tasks_r2_20260913.py','freeze_direct_candidate_evaluation_r2_20260913.py','freeze_and_run_direct_read_regression_r2_20260913.py','run_direct_original_read_r1_20260913.py','score_direct_dev_r2_20260913.py','audit_direct_read_r2_20260913.py','audit_advice_read_regression_r3_20260913.py','analyze_learning_rate_contrast_r2_20260913.py','prepare_direct_eval_service_r3_20260913.py','launch_direct_training_r2_20260913.py','seal_direct_training_r2_20260913.py']:
 shutil.copy2(R/'temp'/name,adir/name)
files=[p for d in ['training_r2','evaluation_r2','evaluation_service_r2','training_r2_analysis_scripts'] for p in (P/d).rglob('*') if p.is_file() and '__pycache__' not in p.parts and not p.name.endswith(('-wal','-shm'))]
files += [P/f for f in ['TRAINING_R2.log','EVAL_SERVICE_R3.log','LEARNING_RATE_CONTRAST.json','LEARNING_RATE_LOSS.csv','LEARNING_RATE_R2_REGISTRATION.json','CAMPAIGN_RESOURCE_LEDGER.json','SERVICE_FINAL_STATUS.json','PREEXISTING_FINAL_PRESERVED.json']]
pin={str(p.relative_to(P)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files};put(P/'TRAINING_R2_FILES.json',pin)
archive=P/'TRAINING_R2_EVIDENCE.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as t:
 for p in files:t.add(p,arcname=str(p.relative_to(P)),recursive=False)
put(P/'TRAINING_R2_SEAL.json',dict(files=len(files),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),archive_bytes=archive.stat().st_size,manifest_sha256=hashlib.sha256((P/'TRAINING_R2_FILES.json').read_bytes()).hexdigest()))
print(json.dumps(ledger,indent=2));print(resources)
