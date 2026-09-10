"""Read-only training-data checks; never starts optimizer or creates a dataset version."""
from pathlib import Path
import hashlib,inspect,json,sys
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import statetune_data
from rwkv_lh.token_budget import VOCAB_PATH,tokenizer
O=R/'data/experiments/SELECTOR_TRAINING_PREFLIGHT_R1_20260910';O.mkdir(exist_ok=False)
B=R/'data/experiments/SELECTOR_SIMILARITY_POLICY_R1_20260910/reviewed162'
rows=list(map(json.loads,(B/'candidates.jsonl').read_text().splitlines()));manifest=json.loads((B/'manifest.json').read_text())
model_shas={r['context']['initial_state']['model_sha256'] for r in rows}
if len(model_shas)!=1:raise SystemExit('model mismatch')
results=[]
for row in rows:
 try:
  normalized=statetune_data.normalize_row(row,role='selector_intent',model_sha256=next(iter(model_shas)),context_tokens=16384,vocab_size=65536,bos_token_id=0,expected_split=row['split'])
  results.append({'sample_id':row['sample_id'],'split':row['split'],'valid':True,'input_tokens':len(normalized['input_token_ids']),'target_tokens':len(normalized['target_token_ids'])})
 except Exception as exc:results.append({'sample_id':row['sample_id'],'split':row['split'],'valid':False,'error':str(exc)})
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
result={'candidate_manifest':{'path':str(B/'manifest.json'),'sha256':sha(B/'manifest.json')},'candidate_status':manifest['status'],'rows_normalized':len(results),'normalization_failures':sum(not r['valid'] for r in results),'all_input_profiles_zero':all(r['context']['initial_state']['profile_id']=='zero' and r['context']['initial_state']['profile_sha256']=='0'*64 for r in rows),'model_sha256':next(iter(model_shas)),'tokenizer_sha256':sha(VOCAB_PATH),'tokenizer_matches_every_row':all(r['target_tokenizer_sha256']==sha(VOCAB_PATH) for r in rows),'prior_regression_triple_pin_ready':False,'prior_regression_reason':'No valid regression was published by these INVALID candidates; preserve five candidate anchors, do not fabricate a prior fingerprint.','optimizer_smoke_started':False,'optimizer_steps':0,'training_run_registered':False,'dataset_version_created':False,'rows':results,'freeze_entrypoint_sha256':sha(statetune_data.__file__),'additional_integration_gap':{'file':'rwkv_lh/statetune_data.py','function':'freeze_dataset','evidence':'Reproduction calls trace.extract_registration without equivalence_waiver and without registered row-selection policy, then requires exact manifest equality. Current reviewed+clustered artifact therefore is not directly freezeable, even after execute coverage is repaired.','handling':'Do not bypass reproduction or modify production during frozen budget arms. Register a separate integration repair if advancing to the actual training freeze.'}}
(O/'DATA_PREFLIGHT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('rows','additional_integration_gap')},ensure_ascii=False))
