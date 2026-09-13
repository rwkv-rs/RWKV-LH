from pathlib import Path
import json
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_SOURCE_ATTRIBUTION_CONTROL_R1_20260913/order_probe')
for p in sorted((D/'runs').iterdir()):
 f=p/'execution/RESULT.json'
 if f.exists():
  d=json.loads(f.read_text());print(p.name,d['termination'],d['generation_started']);print(d['final'])
 else:
  t=p/'execution/model_trace.jsonl'
  if t.exists():
   es=[json.loads(l) for l in t.read_text().splitlines()];print(p.name,[(e['type'],e.get('request_id')) for e in es[-2:]])
