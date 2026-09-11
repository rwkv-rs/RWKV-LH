"""Continue the immutable finite queue one batch at a time; do not fabricate effective counts."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys,time
R=Path('/home/chase/GitHub/RWKV-LH');W=Path('/home/chase/GitHub/RWKV-LH-selector-500-r1-20260911')
C=R/'data/experiments/SELECTOR_500_CAMPAIGN_R1_20260911'
S=R/'data/experiments/SELECTOR_500_RUNTIME_R2_20260911'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):
    with p.open('x') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')
def progress(d):
    d['at']=datetime.now(timezone.utc).isoformat();(S/'PROGRESS.json').write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d),flush=True)
registration=json.loads((C/'REGISTRATION.json').read_text())
assert sha(C/'TASK_QUEUE.json')==registration['task_queue']['sha256']
S.mkdir(exist_ok=True)
write(S/'CONTINUATION_REGISTRATION.json',{'campaign_registration_sha256':sha(C/'REGISTRATION.json'),
 'driver_sha256':sha(Path(__file__)),'setup_driver_sha256':sha(R/'temp/prepare_selector_500_next_batch_20260911.py'),
 'source_commit':'3ae1efcc','finite_batches':list(range(2,10)),'review_gate_required_before_each_next_batch':True,'strict_single_model_collection_batch':True,
 'stop_boundary':'after current batch, on owner stop marker or independently recorded verified effective train>=500; raw rows never count',
 'no_training_or_dataset_publication':True,'optimizer_steps':0})
deadline=time.monotonic()+registration['maximum_campaign_model_seconds']+3600
postprocessors=[]
for number in range(2,10):
    previous=R/'data/experiments'/f'SELECTOR_500_BATCH{number-1:02d}_20260911'
    progress({'phase':'waiting_previous_batch','next_batch':number,'effective_target_reached':False})
    while not (previous/'COMPLETION.json').exists():
        if time.monotonic()>deadline:raise TimeoutError('Finite campaign budget exhausted waiting for previous batch')
        time.sleep(10)
    previous_result=json.loads((previous/'COMPLETION.json').read_text())
    assert previous_result['source_unchanged'],'Previous batch source identity changed'
    if (S/'STOP_AFTER_CURRENT_BATCH').exists():
        progress({'phase':'stopped_after_batch','completed_model_batch':number-1,'reason':'owner_or_operator_stop_marker','effective_target_reached':False});sys.exit(0)
    gate=S/'LATEST_EFFECTIVE_GATE.json'
    progress({'phase':'waiting_complete_reviewed_gate','completed_model_batch':number-1,'effective_target_reached':False})
    while True:
        if (S/'STOP_AFTER_CURRENT_BATCH').exists():
            progress({'phase':'stopped_after_batch','completed_model_batch':number-1,'reason':'owner_or_operator_stop_marker','effective_target_reached':False});sys.exit(0)
        if time.monotonic()>deadline:raise TimeoutError('Finite campaign budget exhausted waiting for reviewed effective data')
        if gate.exists():
            ref=json.loads(gate.read_text());assert sha(Path(ref['path']))==ref['sha256'];g=json.loads(Path(ref['path']).read_text())
            if g.get('completed_model_batches')==number-1 and g.get('pending_review')==0 and g.get('full_source_replay_verified') is True:
                break
        time.sleep(10)
    if g.get('status')=='valid' and g.get('effective_train_rows',0)>=500 and g.get('independent_train_boundaries',0)>=167:
        progress({'phase':'effective_data_target_reached','verified_gate':ref,'effective_target_reached':True,'optimizer_steps':0});sys.exit(0)
    out=R/'data/experiments'/f'SELECTOR_500_BATCH{number:02d}_20260911'
    if not out.exists():
        subprocess.run([sys.executable,str(R/'temp/prepare_selector_500_next_batch_20260911.py'),str(number)],cwd=W,check=True)
    driver=R/'temp'/f'run_selector_500_batch{number:02d}_20260911.py'
    if not (out/'all_zero/RUN_PROTOCOL.json').exists():
        with (out/'PREFLIGHT.log').open('x') as log:
            subprocess.run([sys.executable,str(driver),'prepare'],cwd=W,stdout=log,stderr=subprocess.STDOUT,check=True)
    assert not (out/'STARTED.json').exists(),'Do not rerun a started batch'
    progress({'phase':'collecting','batch':number,'effective_target_reached':False})
    with (out/'COLLECTION.log').open('x') as log:
        child=subprocess.run([sys.executable,str(driver),'collect'],cwd=W,stdout=log,stderr=subprocess.STDOUT,timeout=21700)
        assert child.returncode==0,'Collection driver failed; no automatic rerun'
    post=R/'temp'/f'postprocess_selector_500_batch{number:02d}_20260911.py'
    with (out/'POSTPROCESS.log').open('x') as log:
        child=subprocess.Popen([sys.executable,str(post)],cwd=W,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    postprocessors.append({'batch':number,'pid':child.pid})
progress({'phase':'registered_public_task_pool_finished','model_batches':9,'effective_target_reached':False,
          'meaning':'All queued model workers finished; source audit, independent label review and effective dedup still determine actual quantity.',
          'postprocessors':postprocessors,'optimizer_steps':0})
