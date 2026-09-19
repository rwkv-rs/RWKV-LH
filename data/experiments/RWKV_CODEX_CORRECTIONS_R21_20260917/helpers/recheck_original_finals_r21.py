from pathlib import Path
import json,hashlib,shutil
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917');rows=json.loads((D/'INVENTORY.json').read_text())['tasks']
for row in rows:
 if not row['known_original_passed']:continue
 root=Path(row['original_binding']['original_binding']['source_root']);p=root.parent/'workspace/solution.py';digest=hashlib.sha256(p.read_bytes()).hexdigest();state=json.loads((root/'state_snapshot.json').read_text());matches=[a for a in state['artifacts'].values() if a.get('sha256')==digest];assert matches,(row['id'],'final file has no production artifact')
 dest=D/'upload/original_finals'/row['id'];dest.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest/'solution.py');(dest/'PROVENANCE.json').write_text(json.dumps({'source':str(p),'sha256':digest,'artifacts':matches,'author':'original_RWKV'},indent=2))
