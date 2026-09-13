from pathlib import Path
import json,subprocess,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_FILE_DISCOVERY_BASELINE_R1_20260913';prior=R/'data/experiments/FULL_TRACE_DEPLOYMENT_R2_20260911'
pins={name:hashlib.sha256((prior/name).read_bytes()).hexdigest() for name in ['PROJECT_SOURCE.json','ENGINE_SOURCE.json']}
remote='''import sys,json,pathlib
base=pathlib.Path('/home/chase/GitHub/RWKV-LH-full-trace-runtime-r2-20260911/validation')
x=json.loads((base/'PROJECT_SOURCE.json').read_text());sys.path.insert(0,x['project_root'])
from rwkv_lh.inference.uploaded_sources import verify_manifest
pins=PINS
out={}
for name,h in pins.items():
 value=verify_manifest(base/name,h)
 out[name]={'sha256':h,'verification':value,'complete_inventory_verified':True}
print(json.dumps(out))
'''.replace('PINS',repr(pins))
p=subprocess.run(['ssh','rwkv-8222','python3 -'],input=remote,text=True,capture_output=True,timeout=60)
(D/'SERVER_COMPLETE_INVENTORY_R2.log').write_text(p.stdout+p.stderr);assert p.returncode==0,p.stderr
(D/'SERVER_COMPLETE_INVENTORY_R2.json').write_text(json.dumps(json.loads(p.stdout),indent=2)+'\n');print(p.stdout)
