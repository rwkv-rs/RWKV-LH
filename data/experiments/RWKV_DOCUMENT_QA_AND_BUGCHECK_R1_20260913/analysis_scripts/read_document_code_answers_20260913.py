from pathlib import Path
import json
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913')
for phase in ['budget_probe','file_scope_probe','requested_advice_probe','advice_label_probe']:
 for p in sorted((D/phase/'runs').glob('*/execution/RESULT.json')):
  if 'api_bug' in str(p) or phase=='budget_probe' or (phase=='file_scope_probe' and 'backup' in str(p)):
   d=json.loads(p.read_text());print(phase,p.parent.parent.name);print(d['final'])
print(json.loads((D/'file_scope_probe/contracts/api_bug.json').read_text())['contract']['requirements'])
