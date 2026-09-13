from pathlib import Path
import sys,json,shutil
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as v
D=R/'data/experiments/RWKV_DOCUMENT_QA_AND_BUGCHECK_R1_20260913'
P=D/'budget_probe';P.mkdir();(P/'contracts').mkdir()
reg=json.loads((D/'REGISTRATION.json').read_text());reg['round']='RWKV_DOCUMENT_CODECHECK_BUDGET_PROBE_R1_20260913';reg['cases']=[c for c in reg['cases'] if c['id'] in ('api_bug','backup_check')]
reg['budget']={'max_calls':12,'max_seconds':400,'output_tokens':1800,'total_tasks':4,'total_calls_max':48,'total_task_seconds_max':1600}
reg['execution_identity']['budget']=v.digest(reg['budget']);reg['order']=[['serial',1],['serial',2]]
reg['question']='Do extra budgeted autonomous calls permit code-check delivery after baseline spent six calls obtaining source? No forced final, no strong-model advice, no new tool route. Both call and wall budgets grow, so not an isolated one-variable causal comparison.'
reg['gate']='two repeats of both code tasks met; illegal calls separately reported, any illegal call fails stability gate; no general quality or cost claim'
for c in reg['cases']:
    contract=v.load_contract(D/'contracts'/f'{c["id"]}.json');contract['execution_identity']=reg['execution_identity'];v.freeze_contract(contract,P/'contracts'/f'{c["id"]}.json')
    for repeat in (1,2):
        rid=f'{c["id"]}-serial-r{repeat}';p=P/'runs'/rid;p.mkdir(parents=True);shutil.copytree(D/'fixtures'/c['id'],p/'workspace')
for _,repeat in reg['order']:
    jobs=[{'task_id':f'{c["id"]}-serial-r{repeat}','request':c['request'],'workspace':str(P/'runs'/f'{c["id"]}-serial-r{repeat}'/'workspace'),'output_dir':str(P/'runs'/f'{c["id"]}-serial-r{repeat}'/'execution'),'max_calls':12,'max_seconds':400} for c in reg['cases']]
    v.write_once(P/f'JOBS_serial_{repeat}.json',jobs)
v.write_once(P/'REGISTRATION.json',reg);print(v.file_digest(P/'REGISTRATION.json'))
