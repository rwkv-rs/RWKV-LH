from pathlib import Path
import json
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913')
p=next((D/'requested_advice_probe/runs').glob('*/advice/strong_trace.jsonl'))
for line in p.read_text().splitlines():
 e=json.loads(line);print(e.keys());print({k:v for k,v in e.items() if 'token' in k or k in ['type','usage','elapsed_seconds','request_id']})
print(json.loads((D/'advice_label_probe/MECHANICAL.json').read_text()).keys())
