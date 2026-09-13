from pathlib import Path
import sys,json,shutil
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as v
from rwkv_lh.runtime.settings import load_local_env
from rwkv_lh.supervisor_openai import SupervisorAPISettings
Q=R/'data/experiments/RWKV_SOURCE_ATTRIBUTION_CONTROL_R1_20260913';D=R/'data/experiments/RWKV_FACT_CORRECTION_COMPARISON_R1_20260913';D.mkdir()
reg=json.loads((Q/'REGISTRATION.json').read_text());reg['round']=D.name;reg['cases']=[];reg['schedule']=[]
load_local_env(R/'.env.local');reg['strong_model']=SupervisorAPISettings.from_env().model
reg['source_pins']={p:v.file_digest(R/p) for p in reg['source_pins']};reg['source_pins']['scripts/request_rwkv_read_only_advice.py']=v.file_digest(R/'scripts/request_rwkv_read_only_advice.py');reg['execution_identity']['source']=v.digest(reg['source_pins'])
reg['budget']={'max_rwkv_calls_per_task':6,'rwkv_seconds':300,'rwkv_output_tokens':1800,'strong_calls':3,'strong_max_output_tokens':4096,'strong_request_timeout':180,'strong_retries':0,'strong_semantic_repairs':0,'total_tasks':6,'max_new_rwkv_calls':36};reg['execution_identity']['budget']=v.digest(reg['budget'])
reg['question']='Three already prepared correction candidates. One actual strong advice per candidate, then two isolated continuations of exactly the same original parent State and identical advice. Compare immutable parent quality, advice validity, RWKV adoption and task quality separately.'
reg['comparison_limit']='Original parents are three different user goals/histories. Do not pool old repeated runs, claim RWKV independent gain, or claim a fresh order-only causal effect. The two code candidates retain opposite actual read orders; advice differs by candidate. No unadvised extra continuation control: any change is observed after combined reconsideration and advice, not isolated advice causality.'
reg['gate']='Each candidate met on both continuations; zero material unsupported claims/false work claims and illegal calls. Advice correctness alone does not pass. Prior full quality gates/real execution positive coverage/reading regression remain separate.'
seeds=json.loads((Q/'correction_candidates/MANIFEST.json').read_text())['candidates']
contracts=[]
for seed in seeds:
 parent=R/seed['parent_execution'];state=json.loads((parent/'state_snapshot.json').read_text());goal=state['goal'];cid=seed['id'];origin=parent.parent.parent.parent;oldcid=parent.parent.name.rsplit('-',2)[0]
 contract=v.load_contract(origin/'contracts'/f'{oldcid}.json');contracts.append((cid,contract))
 files={str(p.relative_to(Path(goal['workspace_root']))):v.file_digest(p) for p in sorted(Path(goal['workspace_root']).rglob('*')) if p.is_file()}
 c=dict(id=cid,request=goal['request'],files=files,parent=str(parent),parent_result_sha256=v.file_digest(parent/'RESULT.json'),parent_state_sha256=v.file_digest(parent/'state_snapshot.json'),prepared_input_sha256=seed['input_sha256'],prepared_input=str(Q/'correction_candidates'/seed['input_path']),parent_contract=str(origin/'contracts'/f'{oldcid}.json'),parent_judgment=str(origin/'reviews'/f'{parent.parent.name}.judgment.json'))
 reg['cases'].append(c)
for repeat in (1,2):
 for c in reg['cases']:reg['schedule'].append(dict(c,id=f'{c["id"]}-advised-r{repeat}',case_id=c['id'],repeat=repeat,assistance='strong_advised'))
reg['execution_identity']['state']=v.digest({'policy':'two isolated forks of each exact original terminal State, same advice','parents':[(c['id'],c['parent_state_sha256']) for c in reg['cases']]})
for cid,contract in contracts:
 contract['task_id']=cid;contract['execution_identity']=reg['execution_identity'];v.freeze_contract(contract,D/'contracts'/f'{cid}.json')
v.write_once(D/'REGISTRATION.json',reg)
for rel in reg['source_pins']:
 p=D/'source'/rel;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(R/rel,p)
(D/'PLAN.zh-CN.md').write_text('三份既有纠正输入，各请求一次strong原始建议，再从同一父State隔离续接两遍RWKV。原答案/评分保留，同一候选两遍用同一建议，不挑选有利建议。3 strong+最多36 RWKV/每任务300秒1800输出。外部原任务契约沿用，仅更新run身份，不把隐藏要点放入建议输入。分别评建议正确性、实际采用和任务结果。未设置无建议继续组，不能把所有变化因果归于建议本身。无生产代码修改、训练或新数据集。\n')
print(v.file_digest(D/'REGISTRATION.json'))
