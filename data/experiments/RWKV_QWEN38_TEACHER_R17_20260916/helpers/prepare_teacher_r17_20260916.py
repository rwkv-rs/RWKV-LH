from pathlib import Path
import json,hashlib,shutil,subprocess
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_QWEN38_TEACHER_R17_20260916';B=D/'deployment';OLD=R/'data/experiments/RWKV_SERVER_TEACHER_R16_20260916/deployment';remote='/home/chase/GitHub/RWKV-LH-server-teacher-r17-20260916'
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
B.mkdir(parents=True,exist_ok=True)
shutil.copytree(R/'rwkv_lh',B/'rwkv_lh',ignore=shutil.ignore_patterns('__pycache__','*.pyc'),dirs_exist_ok=True)
selection=json.loads((OLD/'TASK_SELECTION.json').read_text());allrows=selection['tasks'];rows=allrows
for row in rows:
 source=OLD/'inputs'/row['id'];dest=B/'inputs'/row['id'];shutil.copytree(source,dest,dirs_exist_ok=True)
 for key in ['source_root','manifest','snapshot','conversion']:row[key]=row[key].replace('server-teacher-r16','server-teacher-r17')
 item=json.loads((dest/'ITEM.json').read_text());item['acceptance_path']=item['acceptance_path'].replace('server-teacher-r16','server-teacher-r17');save(dest/'ITEM.json',item)
save(B/'TASK_SELECTION.json',{'tasks':rows,'selection':'all20 from R15; owner explicitly requested full execution'})
s=(R/'temp/run_server_teacher_r16_20260916.py').read_text()
s=s.replace('from rwkv_lh.teacher_runtime import DeadlineStrongCompletion','from rwkv_lh.teacher_runtime import DeadlineStrongCompletion\nfrom rwkv_lh.teacher_input import build_teacher_input, TEACHER_INPUT_VERSION')
s=s.replace('qwen3-coder-next-fp8-r15','qwen3.8-27b-r17').replace('127.0.0.1:18243','127.0.0.1:18244').replace('max_model_len=32768','max_model_len=262144').replace('action_max_output_tokens=8192','action_max_output_tokens=16384')
s=s.replace("'top_k':40,'return_token_ids':True","'top_k':20,'return_token_ids':True,'reasoning_effort':'medium','chat_template_kwargs':{'enable_thinking':True}")
s=s.replace(' clients=[]',' clients=[]; context={}\n def teacher_input():\n  current=context["controller"].store.load(context["run_id"])\n  return build_teacher_input(goal=request,definitions=context["definitions"],failure_candidate=audit["original_output"],workspace_paths=context["paths"],state=current)')
s=s.replace("client=DeadlineStrongCompletion(strong,execution,12,max_seconds=1200,expected_input_sha256=row['input_sha256']);clients.append(client)","client=DeadlineStrongCompletion(strong,execution,24,max_seconds=1800,input_builder=teacher_input,max_context_tokens=262144);clients.append(client)")
a=s.index(' def seed(');z=s.index(' request=',a)
s=s[:a]+''' def seed(state,controller,model):
  context.update(controller=controller,run_id=state.run_id,definitions=model.direct_definitions(),paths=sorted(str(p.relative_to(workspace)) for p in workspace.rglob('*') if p.is_file()))
  system,payload=teacher_input()
  save(execution/'TEACHER_INITIAL_INPUT.json',{'system':system,'payload':payload})
  save(execution/'TRANSFER.json',{'source_root':row['source_root'],'source_request':row['request_id'],'original_input_sha256':row['input_sha256'],'teacher_input_version':TEACHER_INPUT_VERSION,'native_tensor_transfer':False,'teacher_fresh_task_at_source_workspace':True,'same_rwkv_input':False,'training_admitted':False})
''' +s[z:]
s=s.replace('str(execution),12,1200','str(execution),24,1800')
s=s.replace("assert prompt==actual['input_text'],'probe input mismatch'","assert context['run_id'],'teacher context missing'")
s=s.replace('original input preserved, baseline validator invoked on server (missing submission need not execute Python)','fresh teacher context constructed; source workspace retained')
out=R/'temp/run_teacher_r17_20260916.py';out.write_text(s);(B/'temp').mkdir(exist_ok=True);shutil.copy2(out,B/'temp'/out.name)
reg={'round':'R17','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'model':'Qwen/Qwen3.8-27B','revision':json.loads((D/'MODEL_SOURCE.json').read_text())['sha'],'context':262144,'max_calls':24,'max_seconds':1800,'max_output_tokens':16384,'sampling':{'temperature':1,'top_p':.95,'top_k':20,'reasoning_effort':'medium','enable_thinking':True},'teacher_input':'rwkv_lh.teacher_input.build_teacher_input; goal, schema, source candidate, workspace entry paths, own real action/observation history only','not_provided':['full RWKV history','private tests or answers','source later generations','audit hashes and checkpoint metadata'],'task_ids':[r['id'] for r in rows],'acceptance':'same private stdio exact_rstrip; truthful final separately manually audited, no literal answer match','authority':'strong_takeover; all candidates pending review; no automatic training admission','training':False,'stop':'20 tasks or infrastructure failure; context budget records task interruption then continues','comparison':'engineering/model/input/budget changed together; NOT isolated improvement attribution; R15/R16 immutable'}
save(D/'REGISTRATION.json',reg);save(B/'REGISTRATION.json',reg)
shutil.copy2(R/'temp/start_teacher_r17_when_ready_20260916.py',B/'temp/start_teacher_r17_when_ready_20260916.py')
files={str(p.relative_to(B)):sha(p) for p in sorted(B.rglob('*')) if p.is_file() and p.name!='FILES.json'};save(B/'FILES.json',{'files':files});save(D/'DEPLOYMENT_IDENTITY.json',{'remote_root':remote,'manifest_sha256':sha(B/'FILES.json'),'files':len(files)})
print((D/'DEPLOYMENT_IDENTITY.json').read_text())
