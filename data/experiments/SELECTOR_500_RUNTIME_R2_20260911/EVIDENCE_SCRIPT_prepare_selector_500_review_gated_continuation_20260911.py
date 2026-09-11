from pathlib import Path
import hashlib,json
R=Path('/home/chase/GitHub/RWKV-LH');S1=R/'data/experiments/SELECTOR_500_RUNTIME_R1_20260911';S2=R/'data/experiments/SELECTOR_500_RUNTIME_R2_20260911'
assert not (R/'data/experiments/SELECTOR_500_BATCH02_20260911/STARTED.json').exists()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
(S1/'STOPPED_BEFORE_NEXT_BATCH.json').write_text(json.dumps({'reason':'Strengthen finite campaign continuation: wait for complete reviewed effective gate covering the just-ended batch before starting another. A stale earlier batch gate must not trigger500 completion.','next_batch_started':False,'model_generation_interrupted':False,'running_batch01_unchanged':True},indent=2)+'\n')
source=(R/'temp/continue_selector_500_campaign_20260911.py').read_text()
source=source.replace('SELECTOR_500_RUNTIME_R1_20260911','SELECTOR_500_RUNTIME_R2_20260911')
source=source.replace("'finite_batches':list(range(2,10)),", "'finite_batches':list(range(2,10)),'review_gate_required_before_each_next_batch':True,")
start=source.index("    gate=S/'LATEST_EFFECTIVE_GATE.json'")
end=source.index("    out=R/'data/experiments'/f'SELECTOR_500_BATCH",start)
source=source[:start]+'''    gate=S/'LATEST_EFFECTIVE_GATE.json'
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
''' + source[end:]
path=R/'temp/continue_selector_500_review_gated_20260911.py';path.write_text(source)
S2.mkdir(exist_ok=False)
(S2/'PRE_GENERATION_CONTROL_REVIEW.json').write_text(json.dumps({'old_director_stopped_before_batch02':True,
 'same_immutable98_task_queue':True,'same_model_parameters':True,'same_sample_policy':True,'same500train_threshold':True,
 'new_control':'Require exact just-ended batch coverage, pending0 and full source replay before next generation batch. Only valid current gate can stop for500 target.',
 'driver_sha256':sha(path),'optimizer_steps':0},indent=2)+'\n')
print(str(path))
