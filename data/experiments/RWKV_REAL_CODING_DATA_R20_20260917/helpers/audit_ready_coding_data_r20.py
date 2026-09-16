from pathlib import Path
import sys,json,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R));from rwkv_lh.statetune_core import collate_samples
from rwkv_lh.direct_trace_data import normalize_direct_row,protocol_identity
D=R/'data/experiments/RWKV_REAL_CODING_DATA_R20_20260917';rows=[json.loads(l) for l in (D/'READY_ROWS.jsonl').read_text().splitlines()]
b=collate_samples(rows,context_tokens=16384);counts=[]
for i,row in enumerate(rows):
 n=len(row['input_token_ids']);t=len(row['target_token_ids']);assert b['labels'][i,:n-1].eq(-100).all();assert b['labels'][i,n-1:n-1+t].tolist()==row['target_token_ids'];assert b['labels'][i,n-1+t:].eq(-100).all();counts.append(t)
old=R/'data/datasets/rwkv_direct_unified_corrections_v3/train.jsonl';prior=[json.loads(l) for l in old.read_text().splitlines()];keys={(x['request_id'],x['target_text']) for x in prior};duplicates=[r['sample_id'] for r in rows if (r['request_id'],r['target_text']) in keys];assert not duplicates
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
audit={'status':'passed','rows':len(rows),'target_tokens':counts,'total_supervised_tokens':sum(counts),'prompt_and_padding_masked':True,'context_tokens':16384,'no_truncation':True,'same_batch_collation_passed':True,'existing_train_exact_duplicates':duplicates,'prior_train_sha256':sha(old),'split':'all train candidates; repository-family grouped; no new dev/confirmation','holdout_read':False,'semantic_similarity_to_heldout':'not inspected; full dataset freeze must run existing isolation gate before training','training_started':False}
(D/'TRAINING_READINESS.json').write_text(json.dumps(audit,indent=2));print(audit)
reg=json.loads((D/'REGISTRATION.json').read_text());sources=[]
for c,row in zip(reg['cases'],rows):
 p=Path(c['source']['manifest']);sources.append({'sample_id':row['sample_id'],'source_run':c['source']['root'],'source_manifest':str(p),'source_manifest_sha256':sha(p),'checkpoint':row['candidate_checkpoint_id'],'family':row['family'],'input_sha256':hashlib.sha256(row['input_text'].encode()).hexdigest(),'target_sha256':hashlib.sha256(row['target_text'].encode()).hexdigest()})
(D/'MANIFEST.json').write_text(json.dumps({'version':'R20 candidate bundle','status':'validated_increment_for_next_freeze','rows_sha256':sha(D/'READY_ROWS.jsonl'),'sources':sources,'input_protocol':protocol_identity(),'scripts':{p.name:sha(p) for p in (R/'temp').glob('*coding*r20.py')},'split_algorithm':'all-source-repository-family-to-train; AnyIO rows never split across train/eval','similarity_parameters':{'exact_key':['request_id','target_text'],'semantic_holdout_gate':'deferred to combined dataset freeze'},'coverage':{'tasks':3,'repositories':2,'diagnostic_commands':3,'atomic_edits':0,'completed_tasks':0},'reviews':'two isolated Qwen3.8 contexts; same model, not independent model families; Codex authored and inspected commands','validation_location':'WSL UbuntuRecovered ActionHarness sandbox; Qwen reviews on rwkv-82 localhost, no API forwarding','training_admission':'must merge and freeze with current regression-isolation gate; no optimizer invoked'},indent=2))
