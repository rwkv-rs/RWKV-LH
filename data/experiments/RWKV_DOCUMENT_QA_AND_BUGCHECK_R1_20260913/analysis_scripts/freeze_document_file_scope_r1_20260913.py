from pathlib import Path
import json,sys,shutil
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as v
D=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913';P=D/'file_scope_probe';P.mkdir();(P/'contracts').mkdir()
reg=json.loads((D/'REGISTRATION.json').read_text());reg['round']='RWKV_DOCUMENT_FILE_SCOPE_PROBE_R1_20260913'
source={str(p.relative_to(R)):v.file_digest(p) for p in sorted((R/'rwkv_lh').rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
for name in ['scripts/run_rwkv_read_only_agent.py','pyproject.toml','uv.lock']:source[name]=v.file_digest(R/name)
reg['source_pins']=source;reg['execution_identity']['source']=v.digest(source)
reg['budget']={'max_calls':6,'max_seconds':300,'output_tokens':1800,'total_tasks':8,'total_calls_max':48,'total_task_seconds_max':2400}
reg['execution_identity']['budget']=v.digest(reg['budget']);reg['order']=[['files',1],['files',2]]
reg['question']='Can RWKV answer known-file document questions and static code checks with only the original read_file capability plus final submission? Arguments and whether/when to read remain model choices.'
reg['comparison_limit']='No causal gain claim versus prior arms: scope and runtime robustness changed; the rules contract also moves a nonessential chunking detail to optional. Old scores remain untouched.'
reg['tool_scope']='files';reg['gate']='two repeats all4 tasks met, zero protocol rejections and false work claims; only fixed known-file tasks, not repository discovery or universal stability'
for c in reg['cases']:
    contract=v.load_contract(D/'contracts'/f'{c["id"]}.json');contract['execution_identity']=reg['execution_identity']
    if c['id']=='rag_rules':
        req=contract['requirements'][0];req['outcome']='Writer只使用Resolver选中的逐字证据作为回答材料';req['acceptance']=req['outcome']+'；允许等义表达，不限定工具路径';req['omission_policy']='正文overlap与原子切片为一般实现细节，允许省略'
        contract['requirements'].append({'id':'chunking','user_quote':'文本证据如何成为回答材料','outcome':'正文切片有overlap并保留列表表格等原子结构及父级上下文','level':'detail','missing_effect':'不影响对证据选择与回答材料的核心解释','acceptance':'若详述切片，应与原文一致','omission_policy':'允许全部省略，不影响主问题合格'})
    v.freeze_contract(contract,P/'contracts'/f'{c["id"]}.json')
    for repeat in (1,2):
        p=P/'runs'/f'{c["id"]}-files-r{repeat}';p.mkdir(parents=True);shutil.copytree(D/'fixtures'/c['id'],p/'workspace')
for _,repeat in reg['order']:
    jobs=[{'task_id':f'{c["id"]}-files-r{repeat}','request':c['request'],'workspace':str(P/'runs'/f'{c["id"]}-files-r{repeat}'/'workspace'),'output_dir':str(P/'runs'/f'{c["id"]}-files-r{repeat}'/'execution'),'max_calls':6,'max_seconds':300,'tool_scope':'files'} for c in reg['cases']]
    v.write_once(P/f'JOBS_files_{repeat}.json',jobs)
v.write_once(P/'REGISTRATION.json',reg)
for rel,sha in source.items():
    dest=P/'source'/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/rel,dest)
print(v.file_digest(P/'REGISTRATION.json'))
