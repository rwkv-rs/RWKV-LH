from pathlib import Path
import hashlib,json,subprocess
root=Path('/home/chase/GitHub/RWKV-LH')
w=json.loads((root/'data/experiments/EXECUTION_EVIDENCE_REPAIR_R1_20260910/EQUIVALENCE_WAIVER_DRAFT.json').read_text())
for e in w['entries']:
 frozen=hashlib.sha256(subprocess.check_output(['git','show','e7c455b6:'+e['path']],cwd=root)).hexdigest()
 current=hashlib.sha256((root/e['path']).read_bytes()).hexdigest()
 print(json.dumps({'path':e['path'],'frozen':frozen,'current':current,'both_pins_match':frozen==e['frozen_sha256'] and current==e['current_sha256']}))
