from pathlib import Path
import json
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913')
s=Path('/home/chase/GitHub/RWKV-LH/temp/audit_document_requested_advice_r1_20260913.py').read_text().replace("/requested_advice_probe'","/advice_label_probe'").replace('sys.path.insert(0,str(R))','sys.path.insert(0,str(D/"source"))')
Path('/home/chase/GitHub/RWKV-LH/temp/audit_document_advice_label_r1_20260913.py').write_text(s)
for phase in ['budget_probe','file_scope_probe','requested_advice_probe','advice_label_probe']:
 reg=json.loads((D/phase/'REGISTRATION.json').read_text());print(phase,list(reg))
 for p in sorted((D/phase/'contracts').glob('*')):print(p.name,json.loads(p.read_text())['requirements'])
