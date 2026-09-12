from pathlib import Path
import json,hashlib,subprocess,shlex,shutil,sys
sys.path.insert(0,"/home/chase/GitHub/RWKV-LH")
from rwkv_lh.inference.uploaded_sources import PROJECT_SCHEMA,source_inventory
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913/training_runtime';remote=Path('/home/chase/GitHub/RWKV-LH-direct-statetune-r1-20260913')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n');return sha(p)
subprocess.run(['scp',f'rwkv-8222:{remote}/validation/compat/RESULT.json',str(D/'COMPAT_FAILED_R1.json')],check=True)
for name in ['BUILD_MANIFEST.json','DEPENDENCIES.json','TOOLCHAIN.json','build.ninja']:
 subprocess.run(['scp',f'rwkv-8222:{remote}/native_build/{name}',str(D/('REBUILT_'+name))],check=True)
S=D/'source_r2';S.mkdir();
for folder in ['rwkv_lh','scripts']:shutil.copytree(R/folder,S/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name in ['pyproject.toml','uv.lock']:shutil.copyfile(R/name,S/name)
ps=save(D/'PROJECT_SOURCE_R2.json',{'schema_version':PROJECT_SCHEMA,'project_root':str(remote/'source_r2'),'source_root':'.','files':[{'path':p,'sha256':h,'bytes':n} for p,(h,n) in sorted(source_inventory(S).items())]})
subprocess.run(['rsync','-a',str(S)+'/',f'rwkv-8222:{remote}/source_r2/'],check=True)
runtime=json.loads((D/'NATIVE_RUNTIME.json').read_text());runtime['source_manifest']={'path':str(remote/'validation/PROJECT_SOURCE_R2.json'),'sha256':ps};runtime['build']={'path':str(remote/'native_build/BUILD_MANIFEST.json'),'sha256':sha(D/'REBUILT_BUILD_MANIFEST.json')};runtime['dependencies']={'path':str(remote/'native_build/DEPENDENCIES.json'),'sha256':sha(D/'REBUILT_DEPENDENCIES.json')};rh=save(D/'NATIVE_RUNTIME_R2.json',runtime)
reg=json.loads((D/'COMPAT_REGISTRATION.json').read_text());reg['source_manifest_sha256']=ps;reg['attempt']='R2 rebuilt native extension after compiler identity drift';reg['previous_failure_sha256']=sha(D/'COMPAT_FAILED_R1.json');ch=save(D/'COMPAT_REGISTRATION_R2.json',reg)
shell=(D/'validate.sh').read_text().replace(str(remote/'source'),str(remote/'source_r2')).replace('NATIVE_RUNTIME.json','NATIVE_RUNTIME_R2.json').replace(sha(D/'NATIVE_RUNTIME.json'),rh).replace('COMPAT_REGISTRATION.json','COMPAT_REGISTRATION_R2.json').replace(sha(D/'COMPAT_REGISTRATION.json'),ch).replace('--output '+str(remote/'validation/compat'),'--output '+str(remote/'validation/compat_r2'))
(D/'validate_r2.sh').write_text(shell)
subprocess.run(['rsync','-a',*[str(D/n) for n in ['NATIVE_RUNTIME_R2.json','COMPAT_REGISTRATION_R2.json','PROJECT_SOURCE_R2.json','validate_r2.sh']],f'rwkv-8222:{remote}/validation/'],check=True)
print(rh,ch,flush=True)
subprocess.run(['ssh','-o','BatchMode=yes','rwkv-8222','bash',str(remote/'validation/validate_r2.sh')],check=True)
