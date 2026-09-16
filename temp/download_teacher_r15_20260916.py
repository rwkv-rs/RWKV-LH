import pathlib,json,hashlib,subprocess,concurrent.futures,time
root=pathlib.Path('/home/chase/GitHub/RWKV-LH-teacher-r15-20260916'); info=json.loads((root/'MODEL_SOURCE.json').read_text()); dest=root/'model';dest.mkdir(exist_ok=True)
def fetch(f):
 name=f['rfilename']
 if name.startswith('.') or not (name.endswith(('.json','.safetensors','.jinja','.txt'))):return
 p=dest/name;p.parent.mkdir(parents=True,exist_ok=True); tmp=p.with_name(p.name+'.partial');url='https://hf-mirror.com/Qwen/Qwen3-Coder-Next-FP8/resolve/'+info['sha']+'/'+name
 expected=f.get('lfs',{}).get('sha256');size=f.get('size')
 if not p.exists():
  for attempt in range(6):
   x=subprocess.run(['curl','-fL','--retry','3','--connect-timeout','20','--max-time','14400','-C','-','-o',str(tmp),url],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
   if x.returncode==0 and tmp.stat().st_size==size:break
  else:raise RuntimeError('download failed '+name)
  if expected and hashlib.file_digest(tmp.open('rb'),'sha256').hexdigest()!=expected:raise RuntimeError('SHA mismatch '+name)
  tmp.rename(p)
 digest=hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
 if p.stat().st_size!=size or expected and digest!=expected:raise RuntimeError('verification failed '+name)
 print(json.dumps({'file':name,'bytes':size,'sha256':digest}),flush=True)
 return {'path':name,'size':size,'sha256':digest}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool: rows=list(pool.map(fetch,info['siblings']))
(root/'MODEL_MANIFEST.json').write_text(json.dumps({'revision':info['sha'],'files':[x for x in rows if x]},indent=2)+'\n')
print('COMPLETE',flush=True)
