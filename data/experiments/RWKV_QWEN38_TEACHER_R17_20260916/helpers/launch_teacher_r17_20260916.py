from pathlib import Path
import json,hashlib,os,time,subprocess
root=Path('/home/chase/GitHub/RWKV-LH-teacher-r17-20260916')
engine=Path('/home/chase/GitHub/RWKV-LH-teacher-r15-20260916')
def verify(manifest,base):
 for row in json.loads(manifest.read_text())['files']:
  with (base/row['path']).open('rb') as stream:
   if hashlib.file_digest(stream,'sha256').hexdigest()!=row['sha256']:raise RuntimeError('manifest mismatch '+row['path'])
verify(engine/'ENGINE_MANIFEST.json',engine/'venv/lib/python3.12/site-packages')
while not (root/'MODEL_MANIFEST.json').exists():
 if subprocess.run(['systemctl','--user','is-active','--quiet','rwkv-lh-teacher-download-r17.service']).returncode:raise RuntimeError('download stopped before verified manifest')
 time.sleep(10)
verify(root/'MODEL_MANIFEST.json',root/'model')
os.environ.update(CUDA_VISIBLE_DEVICES='GPU-1faf7f09-25f4-2515-b707-6e0766aa841d,GPU-a9570da2-547a-c2b3-0cab-7bbdc1a8a8b0',OMP_NUM_THREADS='8',HF_HUB_OFFLINE='1',VLLM_NO_USAGE_STATS='1')
args=[str(engine/'venv/bin/python'),'-m','vllm.entrypoints.cli.main','serve',str(root/'model'),'--host','127.0.0.1','--port','18244','--served-model-name','qwen3.8-27b-r17','--tensor-parallel-size','2','--disable-custom-all-reduce','--max-model-len','262144','--max-num-seqs','2','--gpu-memory-utilization','0.80','--enforce-eager','--language-model-only','--reasoning-parser','qwen3','--enable-auto-tool-choice','--tool-call-parser','qwen3_coder']
(root/'LAUNCH_IDENTITY.json').write_text(json.dumps({'engine_manifest_sha256':hashlib.sha256((engine/'ENGINE_MANIFEST.json').read_bytes()).hexdigest(),'model_manifest_sha256':hashlib.sha256((root/'MODEL_MANIFEST.json').read_bytes()).hexdigest(),'argv':args,'cuda_visible_devices':os.environ['CUDA_VISIBLE_DEVICES']},indent=2)+'\n')
os.execv(args[0],args)
