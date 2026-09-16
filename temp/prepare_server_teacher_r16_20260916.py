from pathlib import Path
import json,hashlib,shutil,subprocess
R=Path('/home/chase/GitHub/RWKV-LH'); D=R/'data/experiments/RWKV_SERVER_TEACHER_R16_20260916'; OLD=R/'data/experiments/RWKV_LOCAL_TEACHER_PILOT_R15_20260916'; B=D/'deployment'; REM=Path('/home/chase/GitHub/RWKV-LH-server-teacher-r16-20260916')
def save(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
B.mkdir(parents=True,exist_ok=True)
shutil.copytree(R/'rwkv_lh',B/'rwkv_lh',ignore=shutil.ignore_patterns('__pycache__','*.pyc'),dirs_exist_ok=True)
rows=json.loads((OLD/'TASK_SELECTION.json').read_text())['tasks']; mapped=[]
for row in rows:
 dest=B/'inputs'/row['id'];dest.mkdir(parents=True,exist_ok=True)
 for name in ['INPUT.json','SOURCE_AUDIT.json']:
  shutil.copy2(OLD/'sources'/row['id']/name,dest/name)
 manifest=json.loads(Path(row['manifest']).read_text());shutil.copy2(row['manifest'],dest/'MANIFEST.json')
 root=Path(row['source_root'])
 for name,digest in manifest['source_files'].items():
  p=root/name;assert sha(p)==digest
  out=dest/'original'/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out)
 rel=Path(row['snapshot']).relative_to(root)
 shutil.copytree(row['snapshot'],dest/'original'/rel,dirs_exist_ok=True)
 item=json.loads(Path(row['conversion']).read_text());shutil.copy2(row['conversion'],dest/'ORIGINAL_ITEM.json')
 shutil.copy2(item['acceptance_path'],dest/'acceptance.json');assert sha(dest/'acceptance.json')==item['acceptance_sha256']
 item['acceptance_path']=str(REM/'inputs'/row['id']/'acceptance.json');save(dest/'ITEM.json',item)
 new=dict(row,source_root=str(REM/'inputs'/row['id']/'original'),manifest=str(REM/'inputs'/row['id']/'MANIFEST.json'),snapshot=str(REM/'inputs'/row['id']/'original'/rel),conversion=str(REM/'inputs'/row['id']/'ITEM.json'),original_binding=row)
 mapped.append(new)
save(B/'TASK_SELECTION.json',{'tasks':mapped,'original_selection_sha256':sha(OLD/'TASK_SELECTION.json')})
# Reuse frozen R15 execution logic; only filesystem placement and deadline adapter change.
s=(R/'temp/run_teacher_pilot_r15_20260916.py').read_text()
s=s.replace("R=Path('/home/chase/GitHub/RWKV-LH')","R=Path(__file__).resolve().parents[1]")
s=s.replace('from rwkv_lh.strong_session import StrongCompletion','from rwkv_lh.teacher_runtime import DeadlineStrongCompletion')
s=s.replace("D=R/'data/experiments/RWKV_LOCAL_TEACHER_PILOT_R15_20260916'","D=R")
a=s.index('class ExactStrong(');z=s.index('\ndef run(',a);s=s[:a]+s[z:]
s=s.replace("D/'sources'","D/'inputs'").replace("root=D/('engineering_probe' if probe else 'runs')","root=D/'outputs'/('engineering_probe' if probe else 'runs')")
s=s.replace('127.0.0.1:29643','127.0.0.1:18243')
s=s.replace("client=ExactStrong(strong,execution,12);client.expected_input=row['input_sha256'];clients.append(client)","client=DeadlineStrongCompletion(strong,execution,12,max_seconds=1200,expected_input_sha256=row['input_sha256']);clients.append(client)")
s=s[:s.index("if __name__=='__main__':")]+'''if __name__=='__main__':
 import socket,platform,os,traceback
 manifest=json.loads((R/'FILES.json').read_text())
 for name,digest in manifest['files'].items():
  if sha(R/name)!=digest:raise ValueError('frozen file changed: '+name)
 rows=json.loads((R/'TASK_SELECTION.json').read_text())['tasks']
 status=R/'outputs'/'STATUS.json'
 save(R/'outputs'/'HOST.json',{'hostname':socket.gethostname(),'python':sys.version,'platform':platform.platform(),'pid':os.getpid(),'endpoint':'http://127.0.0.1:18243/v1','execution_and_verification':'server','manifest_sha256':sha(R/'FILES.json')})
 if '--probe' in sys.argv:
  result=run(rows[0],True)
  assert 'EXPECTED_PROBE_STOP_AFTER_VERIFIED_INPUT' in str(result['error'])
  print('PROBE PASSED: original input preserved, baseline validator invoked on server (missing submission need not execute Python)')
 else:
  completed=[]
  try:
   for row in rows:
    save(status,{'phase':'correcting','current':row['id'],'finished':completed,'time':time.time()})
    result=run(row)
    completed.append({'id':row['id'],'termination':result['termination'],'termination_reason':result['termination_reason']})
    if result['termination']=='error':raise RuntimeError('execution infrastructure error; stopped for trace inspection')
   save(status,{'phase':'complete_pending_semantic_review','finished':completed,'time':time.time(),'training_admitted':False})
  except BaseException as exc:
   save(status,{'phase':'blocked','finished':completed,'time':time.time(),'error':repr(exc),'traceback':traceback.format_exc()})
   raise
'''
out=R/'temp/run_server_teacher_r16_20260916.py';out.write_text(s);(B/'temp').mkdir(exist_ok=True);shutil.copy2(out,B/'temp'/out.name)
reg={'round':'R16','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip(),'prior_run':'R15 retained unchanged; not rescored','tasks':20,'same_selection_sha256':sha(OLD/'TASK_SELECTION.json'),'model':'qwen3-coder-next-fp8-r15','model_revision':'da6e2ed27304dd39abadd9c82ef50e8de67bdd4c','sampling':{'temperature':1.0,'top_p':0.95,'top_k':40},'max_calls':12,'max_seconds':1200,'max_output_tokens':8192,'state':'prompt_replay, original first input text byte-identical; fresh teacher checkpoint; no RWKV tensor transfer','acceptance':'same private stdio cases/exact_rstrip, semantic review separate; no automatic training admission','changes':['scheduler, tools, verification, traces moved to server','HTTP timeout bounded by remaining task budget, no automatic retries','system Python venv symlink mapped into sandbox','AppArmor userns profile for /usr/bin/bwrap'],'comparison_limit':'location/runtime and timeout changed together; not a model or prompt efficacy isolation','stop':'20 tasks complete or infrastructure error; model budget failures retained','endpoint':'remote loopback18243; no SSH model forwarding'}
save(B/'REGISTRATION.json',reg);save(D/'REGISTRATION.json',reg)
for name in ['check_server_sandbox_r16_20260916.py','install_bwrap_profile_r16_20260916.sh']:
 shutil.copy2(R/'temp'/name,B/'temp'/name)
files={str(p.relative_to(B)):sha(p) for p in sorted(B.rglob('*')) if p.is_file() and p.name!='FILES.json'}
save(B/'FILES.json',{'files':files});save(D/'DEPLOYMENT_IDENTITY.json',{'remote_root':str(REM),'manifest_sha256':sha(B/'FILES.json'),'files':len(files),'bytes':sum(p.stat().st_size for p in B.rglob('*') if p.is_file())})
print((D/'DEPLOYMENT_IDENTITY.json').read_text())
