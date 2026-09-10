from pathlib import Path
import json,collections
root=Path('/home/chase/GitHub/RWKV-LH')
for name in ['REALPROJECT_OFFICIAL_COLLECTION_R3_20260910','ULTRADATA_OFFICIAL_COLLECTION_R6_20260910']:
 for kind in ['candidates','review_queue']:
  p=root/'data/experiments'/name/'selector_candidates'/f'{kind}.jsonl';rows=[json.loads(x) for x in p.read_text().splitlines()]
  print(name,kind,'total',len(rows),'runs',dict(collections.Counter(r.get('run_id') for r in rows)))
  for r in rows:
   if r.get('run_id')=='RP-WEB-02':print({k:r.get(k) for k in ['run_id','request_id','boundary_event_id','label_authority','target_text','target','sample_id']})
