"""Finite existing-pipeline dispatcher; never supplies independent review decisions."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,sys,time
R=Path('/home/chase/GitHub/RWKV-LH');E=R/'data/experiments';S=E/'SELECTOR_500_RUNTIME_R2_20260911'
O=E/'SELECTOR_500_DATA_WORKERS_R1_20260911';O.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
registration={'finite_batches':list(range(2,10)),'campaign_sha256':sha(E/'SELECTOR_500_CAMPAIGN_R1_20260911/REGISTRATION.json'),
              'script_sha256':sha(Path(__file__)),'preparation_script_sha256':sha(R/'temp/prepare_selector_500_later_data_workers_20260911.py'),
              'batch02_finalizer_already_started':True,'no_model_calls':True,'no_review_decisions_generated':True,
              'no_training_or_dataset_publication':True,'optimizer_steps':0}
(O/'REGISTRATION.json').write_text(json.dumps(registration,indent=2)+'\n')
(O/'EVIDENCE_SCRIPT_dispatch.py').write_bytes(Path(__file__).read_bytes())
deadline=time.monotonic()+180000
def progress(phase,batch):
    (O/'PROGRESS.json').write_text(json.dumps({'phase':phase,'batch':batch,'at':datetime.now(timezone.utc).isoformat()},indent=2)+'\n')
for number in range(2,10):
    batch=E/f'SELECTOR_500_BATCH{number:02d}_20260911';effective=E/f'SELECTOR_500_EFFECTIVE_BATCH{number:02d}_20260911'
    progress('waiting_registered_batch_start',number)
    while not (batch/'STARTED.json').exists():
        if (S/'STOP_AFTER_CURRENT_BATCH').exists():progress('stopped_between_batches',number);sys.exit(0)
        if time.monotonic()>deadline:raise TimeoutError('Finite data worker waiting budget exhausted')
        if (S/'PROGRESS.json').exists() and json.loads((S/'PROGRESS.json').read_text()).get('effective_target_reached') is True:
            progress('verified_effective_target_reached',number);sys.exit(0)
        time.sleep(10)
    child=None
    if number>2:
        assert not effective.exists(),'Do not overwrite any prior effective attempt'
        subprocess.run([sys.executable,str(R/'temp/prepare_selector_500_later_data_workers_20260911.py'),str(number)],cwd=R,check=True)
        control=E/f'SELECTOR_500_EFFECTIVE_CONTROL_BATCH{number:02d}_20260911'
        with (control/'FINALIZATION.log').open('x') as log:
            child=subprocess.Popen([sys.executable,str(R/'temp'/f'finalize_selector_500_batch{number:02d}_data_20260911.py')],cwd=R,stdout=log,stderr=subprocess.STDOUT)
    progress('waiting_dual_review_and_exact_replay',number)
    while not (effective/'FINAL_GATE.json').exists():
        if child is not None and child.poll() is not None:raise RuntimeError(f'Batch {number} finalizer exited without gate: {child.returncode}')
        if time.monotonic()>deadline:raise TimeoutError('Finite data worker budget exhausted before reviewed gate')
        time.sleep(10)
    if child is not None:assert child.wait()==0
    gate=json.loads((effective/'FINAL_GATE.json').read_text())
    assert gate['pending_review']==0 and gate['full_source_replay_verified'] is True
    if gate['status']=='valid' and gate['effective_train_rows']>=500 and gate['independent_train_boundaries']>=167:
        progress('verified_effective_target_reached',number);sys.exit(0)
progress('finite_pool_reviewed_target_not_reached',9)
