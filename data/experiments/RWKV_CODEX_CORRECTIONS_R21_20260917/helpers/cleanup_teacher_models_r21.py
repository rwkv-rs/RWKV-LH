from pathlib import Path
import shutil,json,hashlib,time,subprocess
roots=[Path('/home/chase/GitHub/RWKV-LH-teacher-r15-20260916'),Path('/home/chase/GitHub/RWKV-LH-teacher-r17-20260916')]
records=[]
for r in roots:
 p=r/'model';assert p.is_dir() and not p.is_symlink();m=r/'MODEL_MANIFEST.json';assert m.is_file()
 records.append({'path':str(p),'bytes':sum(x.stat().st_size for x in p.rglob('*') if x.is_file()),'manifest_sha256':hashlib.sha256(m.read_bytes()).hexdigest()})
receipt=roots[1]/'MODEL_REMOVAL_R21.json';receipt.write_text(json.dumps({'phase':'registered','records':records,'time':time.time()},indent=2))
for r in roots:shutil.rmtree(r/'model')
receipt.write_text(json.dumps({'phase':'removed','records':records,'time':time.time(),'preserved':'source manifests, engine venv, all task traces, all private validators'},indent=2));print(receipt.read_text())
