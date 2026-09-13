from pathlib import Path
import json
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913')
for phase in ['requested_advice_probe','advice_label_probe']:
 for p in sorted((D/phase/'runs').glob('*/execution/RESULT.json')):
  if 'backup' in str(p) or ('advice_label' in str(p) and 'rag_' in str(p)):
   d=json.loads(p.read_text());print(p.parent.parent.name);print(d['final'])
