from pathlib import Path
import sys,json,hashlib,shutil,subprocess,shlex
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R));D=R/'data/experiments/RWKV_LIMIT_AND_STATETUNE_CAMPAIGN_R1_20260913/artifact';remote=Path('/home/chase/GitHub/RWKV-LH-direct-statetune-r1-20260913');D.mkdir();bundle=D/'source';bundle.mkdir()
from rwkv_lh.inference.uploaded_sources import PROJECT_SCHEMA,source_inventory
for n in ['rwkv_lh','scripts']:shutil.copytree(R/n,bundle/n,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for n in ['pyproject.toml','uv.lock']:shutil.copyfile(R/n,bundle/n)
files=[{'path':p,'sha256':h,'bytes':s} for p,(h,s) in sorted(source_inventory(bundle).items())];manifest={'schema_version':PROJECT_SCHEMA,'project_root':str(remote/'artifact_source'),'source_root':'.','files':files};(D/'SOURCE_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n');sha=hashlib.sha256((D/'SOURCE_MANIFEST.json').read_bytes()).hexdigest()
engine='/home/chase/GitHub/RWKV-LH-full-trace-runtime-r2-20260911/engine';em='/home/chase/GitHub/RWKV-LH-full-trace-runtime-r2-20260911/validation/ENGINE_SOURCE.json';python='/home/chase/GitHub/RWKV-LH/data/runtime/engines/vllm-rwkv-67f0c5996c50/.venv/bin/python'
args=[python,'-B',str(remote/'artifact_source/scripts/prepare_rwkv_vllm_artifact.py'),'--engine-root',engine,'--engine-source-manifest',em,'--engine-source-manifest-sha256','016d3ac4af9c5eca71fa27b82d3fe71d4e029314bee3f0c1a1513bc00b839693','--engine-revision','67f0c5996c50dca0ad779da545cb491527de988f','--source','/mnt/nas-model/g1j/rwkv7-g1j-13.3b-20260831-ctx16384.pth','--output',str(remote/'model'),'--source-model','rwkv7-g1j-13.3b-20260831-ctx16384','--source-sha256','559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65','--context-length','16384']
env={'PYTHONPATH':str(remote/'artifact_source')+':'+engine,'PYTHONDONTWRITEBYTECODE':'1','OMP_NUM_THREADS':'4','CUDA_VISIBLE_DEVICES':''}
verify="from pathlib import Path; from rwkv_lh.inference.uploaded_sources import verify_manifest, PROJECT_SCHEMA; verify_manifest(Path("+repr(str(remote/'ARTIFACT_SOURCE_MANIFEST.json'))+"),"+repr(sha)+",expected_schema=PROJECT_SCHEMA,expected_root=Path("+repr(str(remote/'artifact_source'))+"))"
launcher='#!/bin/bash\nset -euo pipefail\n'+''.join('export '+k+'='+shlex.quote(v)+'\n' for k,v in env.items())+shlex.join([python,'-B','-c',verify])+'\nexec timeout 1800 '+shlex.join(args)+'\n';(D/'prepare.sh').write_text(launcher)
(D/'REGISTRATION.json').write_text(json.dumps({'purpose':'value-preserving model container preparation; no inference, no optimizer','source_manifest_sha256':sha,'source_weight_sha256':'559371f5b9aef13189ae54b345ac096af4ad2b689996c05d89de687612b3ae65','source_tensor_count':2019,'existing_artifact_preserved':True,'max_seconds':1800,'new_dataset':False,'gpu_devices':[],'command':args},indent=2)+'\n')
subprocess.run(['ssh','-o','BatchMode=yes','rwkv-8222','mkdir','-p',str(remote/'artifact_source')],check=True)
subprocess.run(['rsync','-a',str(bundle)+'/',f'rwkv-8222:{remote}/artifact_source/'],check=True)
subprocess.run(['rsync','-a',str(D/'SOURCE_MANIFEST.json'),f'rwkv-8222:{remote}/ARTIFACT_SOURCE_MANIFEST.json'],check=True)
subprocess.run(['rsync','-a',str(D/'prepare.sh'),f'rwkv-8222:{remote}/prepare_artifact.sh'],check=True)
print('uploaded frozen source',len(files),sha,flush=True)
subprocess.run(['ssh','-o','BatchMode=yes','rwkv-8222','bash',str(remote/'prepare_artifact.sh')],check=True)
