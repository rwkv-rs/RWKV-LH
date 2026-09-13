from pathlib import Path
import sys,json,time
from dataclasses import replace
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh.read_only_agent import ReadOnlyJob,run_read_only_jobs
from rwkv_lh.runtime.settings import get_runtime_settings,load_local_env
from rwkv_lh import task_review as v
D=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913'
def main():
    reg=json.loads((D/'REGISTRATION.json').read_text())
    assert all(v.file_digest(R/p)==sha for p,sha in reg['source_pins'].items())
    load_local_env(R/'.env.local')
    settings=replace(get_runtime_settings(),base_url=reg['base_url'],model=reg['model_name'],model_sha256=reg['model_sha256'],tool_disclosure_mode='full',return_token_ids=True,state_transport='native_required',state_profile_id='zero',state_profile_sha256='0'*64,read_timeout_seconds=180)
    groups=[]
    for mode,repeat in reg['order']:
        jobs=[ReadOnlyJob(**row) for row in json.loads((D/f'JOBS_{mode}_{repeat}.json').read_text())]
        started=time.monotonic();rows=run_read_only_jobs(jobs,settings=settings,concurrency=1 if mode=='serial' else 2)
        groups.append({'mode':mode,'repeat':repeat,'elapsed_seconds':time.monotonic()-started,'results':rows})
        (D/'GROUPS.json').write_text(json.dumps(groups,ensure_ascii=False,indent=2)+'\n')
        print(mode,repeat,[(r['id'],r['termination'],r['generation_started']) for r in rows],flush=True)
if __name__=='__main__':main()
