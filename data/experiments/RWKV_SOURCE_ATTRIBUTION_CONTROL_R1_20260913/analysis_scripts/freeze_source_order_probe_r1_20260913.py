from pathlib import Path
import sys,json,shutil
R=Path('/home/chase/GitHub/RWKV-LH');sys.path.insert(0,str(R))
from rwkv_lh import task_review as v
D=R/'data/experiments/RWKV_SOURCE_ATTRIBUTION_CONTROL_R1_20260913';P=D/'order_probe';P.mkdir()
reg=json.loads((D/'REGISTRATION.json').read_text());reg['round']='RWKV_SOURCE_ORDER_PROBE_R1_20260913';reg['cases']=[c for c in reg['cases'] if c['id']=='code_and_requirements'];reg['cases'][0]['request']=reg['cases'][0]['request'].replace('server.py、README.md。','README.md、server.py。',1)
reg['budget'].update(total_tasks=2,total_calls_max=12,total_task_seconds_max=600);reg['execution_identity']['budget']=v.digest(reg['budget'])
reg['question']='Reverse only the named file list; does RWKV choose the reverse read order, and does behavior attribution follow last observed file?'
reg['comparison_limit']='Model owns read order. If actual read order does not reverse, the intended exposure contrast did not occur. Even a reversal and quality difference is small fixed-source sensitivity evidence, not proof of numerical State loss or universal recency.'
for c in reg['cases']:
 contract=v.load_contract(D/'contracts'/f'{c["id"]}.json');contract['user_request']=c['request'];contract['execution_identity']=reg['execution_identity'];v.freeze_contract(contract,P/'contracts'/f'{c["id"]}.json')
 for repeat in (1,2):
  p=P/'runs'/f'{c["id"]}-focused-r{repeat}'/'workspace';p.mkdir(parents=True)
  for name in c['files']:shutil.copyfile(D/'runs'/f'{c["id"]}-focused-r1'/'workspace'/name,p/name)
for mode,repeat in reg['order']:v.write_once(P/f'JOBS_{mode}_{repeat}.json',[dict(task_id=f'{c["id"]}-{mode}-r{repeat}',request=c['request'],workspace=str(P/'runs'/f'{c["id"]}-{mode}-r{repeat}'/'workspace'),output_dir=str(P/'runs'/f'{c["id"]}-{mode}-r{repeat}'/'execution'),max_calls=6,max_seconds=300,tool_scope='files') for c in reg['cases']])
v.write_once(P/'REGISTRATION.json',reg)
print(v.file_digest(P/'REGISTRATION.json'))
