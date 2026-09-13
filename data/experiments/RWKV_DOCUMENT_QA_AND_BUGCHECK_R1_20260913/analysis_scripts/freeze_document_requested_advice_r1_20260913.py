from pathlib import Path
import json,sys,shutil
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as v
from rwkv_lh.runtime.settings import load_local_env
from rwkv_lh.supervisor_openai import SupervisorAPISettings
D=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913';P=D/'requested_advice_probe';P.mkdir();(P/'contracts').mkdir()
reg=json.loads((D/'file_scope_probe/REGISTRATION.json').read_text());reg['round']='RWKV_DOCUMENT_REQUESTED_ADVICE_PROBE_R1_20260913'
source={str(p.relative_to(R)):v.file_digest(p) for p in sorted((R/'rwkv_lh').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
for name in ['scripts/run_rwkv_read_only_agent.py','scripts/request_rwkv_read_only_advice.py','pyproject.toml','uv.lock']:source[name]=v.file_digest(R/name)
reg['source_pins']=source;reg['execution_identity']['source']=v.digest(source)
load_local_env(R/'.env.local');reg['strong_model']=SupervisorAPISettings.from_env().model
reg['budget']={'max_rwkv_calls_per_task':6,'rwkv_seconds':300,'rwkv_output_tokens':1800,'strong_calls':6,'strong_max_output_tokens':4096,'strong_request_timeout':180,'strong_retries':0,'strong_semantic_repairs':0,'total_tasks':8,'max_new_rwkv_calls':48}
reg['execution_identity']['budget']=v.digest(reg['budget']);reg['order']=[['mixed',1],['mixed',2]]
reg['question']='Owner-requested advice for previously difficult document overview/API/backup cases, followed by RWKV continuing the exact prior State. Rules tasks stay RWKV-only. This is a bounded intervention trial, not a mandatory reviewer or an autonomous help-selection benchmark.'
reg['comparison_limit']='All prior answers and scores stay immutable. Report strong-advised completion separately. No RWKV-independent gain or same-quality cost benefit claim.'
reg['advised_case_ids']=['rag_overview','api_bug','backup_check'];reg['schedule']=[]
for repeat in (1,2):
 for c in reg['cases']:
    rid=f'{c["id"]}-mixed-r{repeat}';entry={'id':rid,'case_id':c['id'],'repeat':repeat,'request':c['request'],'files':c['files']}
    if c['id'] in reg['advised_case_ids']:
        parent=D/'file_scope_probe/runs'/f'{c["id"]}-files-r{repeat}'/'execution'
        entry.update(parent=str(parent),parent_result_sha256=v.file_digest(parent/'RESULT.json'),parent_state_sha256=v.file_digest(parent/'state_snapshot.json'),assistance='strong_advised')
    else:
        entry['assistance']='rwkv_independent';dest=P/'runs'/rid/'workspace';dest.parent.mkdir(parents=True);shutil.copytree(D/'fixtures'/c['id'],dest)
    reg['schedule'].append(entry)
reg['execution_identity']['state']=v.digest({'policy':'fresh zero for independent jobs; exact corresponding prior State for requested advice','parents':[(e['id'],e.get('parent_state_sha256')) for e in reg['schedule']]})
for c in reg['cases']:
    contract=v.load_contract(D/'file_scope_probe/contracts'/f'{c["id"]}.json');contract['execution_identity']=reg['execution_identity'];v.freeze_contract(contract,P/'contracts'/f'{c["id"]}.json')
v.write_once(P/'REGISTRATION.json',reg)
for rel,sha in source.items():
    dest=P/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/rel,dest)
print(v.file_digest(P/'REGISTRATION.json'))
