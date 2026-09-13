from pathlib import Path
import json
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_SOURCE_ATTRIBUTION_CONTROL_R1_20260913')
for p in sorted((D/'runs').glob('*/execution/model_trace.jsonl')):
 print(p.parent.parent.name)
 for line in p.read_text().splitlines():
  e=json.loads(line)
  if e['type']=='model_session_generation_returned':
   r=e['raw_generation'];print(e['request_id'],r['finish_reason'],len(r['raw_token_ids']),r['raw_output'][:160])
