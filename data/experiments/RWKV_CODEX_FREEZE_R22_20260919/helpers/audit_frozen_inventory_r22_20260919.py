from pathlib import Path
import sys,json,hashlib,collections
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.statetune_data import admit_dataset
from rwkv_lh.statetune_core import collate_samples
D=R/'data/experiments/RWKV_CODEX_FREEZE_R22_20260919'
paths=[R/'data/datasets/rwkv_direct_unified_corrections_v6',R/'data/experiments/RWKV_REAL_CODING_DATA_R20_20260917/frozen_increment',D/'frozen_increment']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
allrows=[];packages=[];mask_records=[]
for p in paths:
 m=json.loads((p/'manifest.json').read_text()); ref={'path':str(p/'manifest.json'),'sha256':sha(p/'manifest.json')}
 _,rows=admit_dataset(ref,role='direct_actor',expected_regression=m['regression']['fingerprint'],model_sha256=m['model_sha256'],context_tokens=24576,vocab_size=65536,bos_token_id=0)
 for r in rows:
  b=collate_samples([r],context_tokens=24576); labels=b['labels'][0]; n=len(r['input_token_ids']); t=r['target_token_ids']
  assert labels[:n-1].eq(-100).all().item();assert labels[n-1:n-1+len(t)].tolist()==t;assert labels.ne(-100).sum().item()==len(t)
  assert b['input_ids'][0].tolist()==(r['input_token_ids']+t)[:-1]
  mask_records.append({'sample_id':r['sample_id'],'prompt_tokens':n,'supervised_tokens':len(t),'passed':True})
 raw=[json.loads(l) for l in (p/'train.jsonl').read_text().splitlines()];allrows.extend(raw)
 packages.append({'manifest':ref,'rows':len(rows),'authority':dict(collections.Counter(r['label_authority'] for r in raw)),'regression_fingerprint':m['regression']['fingerprint'],'model_sha256':m['model_sha256'],'protocol_sha256':m['protocol_sha256'],'tokenizer_sha256':m['tokenizer_sha256']})
assert len({r['sample_id'] for r in allrows})==len(allrows)
assert len({(r['request_id'],r['input_checkpoint_id']) for r in allrows})==len(allrows)
for key in ('model_sha256','regression_fingerprint','protocol_sha256','tokenizer_sha256'):assert len({p[key] for p in packages})==1
out={'packages':packages,'aggregate_rows':len(allrows),'label_authority_counts':dict(collections.Counter(r['label_authority'] for r in allrows)),'distinct_source_ids':len({r['source_id'] for r in allrows}),'distinct_source_content_hashes':len({r['source_content_sha256'] for r in allrows}),'input_tokens':sum(len(r['input_token_ids']) for r in allrows),'target_tokens':sum(len(r['target_token_ids']) for r in allrows),'max_sequence_tokens':max(len(r['input_token_ids'])+len(r['target_token_ids'])-1 for r in allrows),'mask_checks':mask_records,'all_mask_checks_passed':True,'mask_policy':'existing production collate_samples; all prompt positions -100, corrected target only supervised; causal shift exact','combined_dataset_created':False,'training_steps':0,'agent_runs':0}
(D/'TRAINABLE_INVENTORY.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k not in ('packages','mask_checks')},ensure_ascii=False,indent=2))
