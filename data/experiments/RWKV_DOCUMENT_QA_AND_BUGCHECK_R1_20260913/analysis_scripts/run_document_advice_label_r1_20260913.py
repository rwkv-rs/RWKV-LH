from pathlib import Path
from dataclasses import replace
import sys,json,time,shutil
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as v
from rwkv_lh.read_only_agent import ReadOnlyJob,run_read_only_job
from rwkv_lh.runtime.settings import load_local_env,get_runtime_settings
D=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913/advice_label_probe'
def save(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
 reg=json.loads((D/'REGISTRATION.json').read_text());load_local_env(R/'.env.local')
 settings=replace(get_runtime_settings(),base_url=reg['base_url'],model=reg['model_name'],model_sha256=reg['model_sha256'],tool_disclosure_mode='full',return_token_ids=True,state_transport='native_required',state_profile_id='zero',state_profile_sha256='0'*64,read_timeout_seconds=180)
 rows=[]
 for e in reg['schedule']:
  assert all(v.file_digest(R/p)==sha for p,sha in reg['source_pins'].items())
  p=D/'runs'/e['id'];p.mkdir(parents=True,exist_ok=True);started=time.monotonic();kwargs={};parent_seconds=0
  if e['assistance']=='strong_advised':
   parent=Path(e['parent']);assert v.file_digest(parent/'RESULT.json')==e['parent_result_sha256'];assert v.file_digest(parent/'state_snapshot.json')==e['parent_state_sha256']
   state=json.loads((parent/'state_snapshot.json').read_text());workspace=Path(state['goal']['workspace_root']);parent_seconds=json.loads((parent/'RESULT.json').read_text())['elapsed_seconds']
   assert {name:v.file_digest(workspace/name) for name in e['files']}==e['files']
   src=Path(e['advice_source']);assert v.file_digest(src/'ADVICE.json')==e['advice_sha256'];shutil.copytree(src,p/'advice')
   save(p/'ADVICE_REUSE.json',{'source':str(src),'sha256':e['advice_sha256'],'new_strong_calls':0})
   receipt=json.loads((p/'advice/ADVICE.json').read_text());assert receipt['model']==reg['strong_model'];assert receipt['parent_result_sha256']==e['parent_result_sha256'];assert receipt['source_sha256']==e['files']
   kwargs={'reconsider_from':str(parent),'advice':receipt['advice'],'advice_model':receipt['model']}
  else:workspace=p/'workspace'
  args=dict(task_id=e['id'],request=e['request'],workspace=str(workspace),output_dir=str(p/'execution'),max_calls=6,max_seconds=300,tool_scope='files',**kwargs);save(p/'JOB.json',args)
  result=run_read_only_job(ReadOnlyJob(**args),settings=settings)
  rows.append({'id':e['id'],'result':result,'elapsed_seconds':time.monotonic()-started,'parent_elapsed_seconds':parent_seconds});save(D/'RESULTS.json',rows);print(e['id'],result['termination'],result['generation_started'],flush=True)
if __name__=='__main__':main()
