from pathlib import Path
import sys,json,time,subprocess,urllib.request,hashlib,traceback
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_LOCAL_TEACHER_PILOT_R15_20260916'
sys.path.insert(0,str(R/'temp'))
from run_teacher_pilot_r15_20260916 import run

def save(status,**kw):
 (D/'STATUS.json').write_text(json.dumps({'phase':status,'time':time.time(),'training_rows':0,**kw},indent=2)+'\n')
def main():
 reg=json.loads((D/'REGISTRATION.json').read_text())
 for name,digest in reg['local_files'].items():
  if hashlib.sha256((R/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('frozen local source changed: '+name)
 save('waiting_for_verified_model_service');deadline=time.monotonic()+7200
 while time.monotonic()<deadline:
  try:
   with urllib.request.urlopen('http://127.0.0.1:29643/v1/models',timeout=5) as response:data=json.load(response)
   if any(x['id']=='qwen3-coder-next-fp8-r15' for x in data['data']):break
  except Exception:pass
  time.sleep(10)
 else:raise TimeoutError('model readiness exceeded two hours')
 remote='/home/chase/GitHub/RWKV-LH-teacher-r15-20260916/'
 for name in ['MODEL_MANIFEST.json','LAUNCH_IDENTITY.json']:
  subprocess.run(['scp','rwkv-8222:'+remote+name,str(D/name)],check=True)
 launch=json.loads((D/'LAUNCH_IDENTITY.json').read_text());model=json.loads((D/'MODEL_MANIFEST.json').read_text())
 assert launch['engine_manifest_sha256']==reg['engine_manifest_sha256']
 assert launch['model_manifest_sha256']==hashlib.sha256((D/'MODEL_MANIFEST.json').read_bytes()).hexdigest()
 assert model['revision']==reg['model_revision']
 upstream=json.loads((D/'MODEL_SOURCE.json').read_text());expected={x['rfilename']:x for x in upstream['siblings']}
 for row in model['files']:
  source=expected[row['path']];assert row['size']==source['size']
  if source.get('lfs'):assert row['sha256']==source['lfs']['sha256']
 rows=json.loads((D/'TASK_SELECTION.json').read_text())['tasks'];finished=[]
 for row in rows:
  save('correcting',recorded=len(finished),active_task=row['id'],target_tasks=20)
  result=run(row);finished.append({'id':row['id'],'termination':result['termination'],'termination_reason':result['termination_reason']})
  (D/'RUN_RESULTS.json').write_text(json.dumps(finished,indent=2)+'\n')
  if result['termination']=='error':raise RuntimeError('execution infrastructure error; stopped for trace inspection')
 save('execution_complete_pending_semantic_review',recorded=len(finished),target_tasks=20)
try:main()
except BaseException as exc:
 save('blocked',error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc());raise
