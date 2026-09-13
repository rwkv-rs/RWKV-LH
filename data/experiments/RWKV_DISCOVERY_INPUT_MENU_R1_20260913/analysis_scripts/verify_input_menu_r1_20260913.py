from pathlib import Path
import subprocess,json,hashlib,urllib.request,tarfile,time
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_DISCOVERY_INPUT_MENU_R1_20260913'
remote='''import json,hashlib,pathlib
base=pathlib.Path('/home/chase/GitHub/RWKV-LH-full-trace-runtime-r2-20260911/validation')
out={}
for name,key in [('PROJECT_SOURCE.json','project_root'),('ENGINE_SOURCE.json','engine_root')]:
 p=base/name;d=json.loads(p.read_text());root=pathlib.Path(d[key]);bad=[]
 for f in d['files']:
  q=root/f['path']
  if not q.is_file() or hashlib.sha256(q.read_bytes()).hexdigest()!=f['sha256']:bad.append(f['path'])
 out[name]={'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'count':len(d['files']),'mismatches':bad}
print(json.dumps(out))
'''
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8','rwkv-8222','python3 -'],input=remote,text=True,capture_output=True,timeout=120)
assert r.returncode==0,r.stderr
d=json.loads(r.stdout)
for name,v in d.items():
 assert not v['mismatches'];assert v['sha256']==hashlib.sha256((R/'data/experiments/FULL_TRACE_DEPLOYMENT_R2_20260911'/name).read_bytes()).hexdigest()
d['capabilities']=json.load(urllib.request.urlopen('http://127.0.0.1:29613/v1/capabilities',timeout=10));d['verified_at_epoch']=time.time();d['remote_git_used']=False
(D/'SERVER_IDENTITY.json').write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(d))
