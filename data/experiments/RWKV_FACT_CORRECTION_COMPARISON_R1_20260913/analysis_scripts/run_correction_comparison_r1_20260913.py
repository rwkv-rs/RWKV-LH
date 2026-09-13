from pathlib import Path
from dataclasses import replace
import sys,json,time,subprocess
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as v
from rwkv_lh.read_only_agent import ReadOnlyJob,run_read_only_job
from rwkv_lh.runtime.settings import load_local_env,get_runtime_settings
D=R/'data/experiments/RWKV_FACT_CORRECTION_COMPARISON_R1_20260913'
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def main():
 reg=json.loads((D/'REGISTRATION.json').read_text());load_local_env(R/'.env.local')
 settings=replace(get_runtime_settings(),base_url=reg['base_url'],model=reg['model_name'],model_sha256=reg['model_sha256'],tool_disclosure_mode='full',return_token_ids=True,state_transport='native_required',state_profile_id='zero',state_profile_sha256='0'*64,read_timeout_seconds=180)
 rows=[]
 for e in reg['schedule']:
  assert all(v.file_digest(R/p)==s for p,s in reg['source_pins'].items());parent=Path(e['parent']);assert v.file_digest(parent/'RESULT.json')==e['parent_result_sha256'];assert v.file_digest(parent/'state_snapshot.json')==e['parent_state_sha256']
  workspace=Path(json.loads((parent/'state_snapshot.json').read_text())['goal']['workspace_root']);assert {n:v.file_digest(workspace/n) for n in e['files']}==e['files']
  p=D/'runs'/e['id'];p.mkdir(parents=True);advice=D/'advice'/e['case_id'];started=time.monotonic()
  if not advice.exists():
   cmd=[str(R/'.venv/bin/python'),str(R/'scripts/request_rwkv_read_only_advice.py'),'--parent',str(parent),'--output',str(advice),'--max-tokens','4096']
   for name in e['files']:cmd.extend(['--file',name])
   proc=subprocess.run(cmd,capture_output=True,text=True,timeout=210);(p/'ADVICE_CLI.log').write_text(proc.stdout+proc.stderr)
   if proc.returncode:raise RuntimeError('strong request failed; raw receipt preserved, no automatic retries')
  receipt=json.loads((advice/'ADVICE.json').read_text());assert receipt['model']==reg['strong_model'];assert receipt['parent_result_sha256']==e['parent_result_sha256'];assert receipt['source_sha256']==e['files']
  assert json.loads((advice/'INPUT.json').read_text())==json.loads(Path(e['prepared_input']).read_text()),'actual advice input must match prepared candidate'
  save(p/'ADVICE_REF.json',dict(path=str(advice),sha256=v.file_digest(advice/'ADVICE.json'),reused=e['repeat']==2))
  args=dict(task_id=e['id'],request=e['request'],workspace=str(workspace),output_dir=str(p/'execution'),max_calls=6,max_seconds=300,tool_scope='files',reconsider_from=str(parent),advice=receipt['advice'],advice_model=receipt['model']);save(p/'JOB.json',args)
  result=run_read_only_job(ReadOnlyJob(**args),settings=settings);rows.append(dict(id=e['id'],result=result,elapsed_seconds=time.monotonic()-started));save(D/'RESULTS.json',rows);print(e['id'],result['termination'],result['generation_started'],flush=True)
if __name__=='__main__':main()
