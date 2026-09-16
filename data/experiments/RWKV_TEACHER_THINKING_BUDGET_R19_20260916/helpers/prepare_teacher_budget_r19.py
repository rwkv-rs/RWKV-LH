from pathlib import Path
import json,shutil,hashlib
R=Path('/home/chase/GitHub/RWKV-LH');E=R/'data/experiments/RWKV_TEACHER_THINKING_BUDGET_R19_20260916';D=E/'deployment';D.mkdir(exist_ok=True)
B=R/'data/experiments/RWKV_QWEN38_TEACHER_R17_20260916/bulk_deployment';remote='/home/chase/GitHub/RWKV-LH-teacher-budget-r19-20260916'
shutil.copytree(B/'rwkv_lh',D/'rwkv_lh',dirs_exist_ok=True)
rows=json.loads((B/'TASK_SELECTION.json').read_text())['tasks'][:2]
for row in rows:
 shutil.copytree(B/'inputs'/row['id'],D/'inputs'/row['id'],dirs_exist_ok=True)
 for k in ['source_root','manifest','snapshot','conversion']:row[k]=row[k].replace('/home/chase/GitHub/RWKV-LH-teacher-1024-r17-20260916',remote)
 p=D/'inputs'/row['id']/'ITEM.json';x=json.loads(p.read_text());x['acceptance_path']=x['acceptance_path'].replace('/home/chase/GitHub/RWKV-LH-teacher-1024-r17-20260916',remote);p.write_text(json.dumps(x))
(D/'TASK_SELECTION.json').write_text(json.dumps({'tasks':rows},indent=2));(D/'temp').mkdir(exist_ok=True)
s=(B/'temp/run_teacher_r17_20260916.py').read_text().replace('import sys,json,hashlib,time,copy','import sys,json,hashlib,time,copy,os').replace("root=D/'outputs'/('engineering_probe' if probe else 'runs')/row['id']","root=D/'outputs'/('budget'+os.environ['TEACHER_THINKING_BUDGET'])/row['id']").replace("'return_token_ids':True,","'return_token_ids':True,'seed':19,'thinking_token_budget':int(os.environ['TEACHER_THINKING_BUDGET']),")
(D/'temp/run_teacher_r17_20260916.py').write_text(s)
reg={'tasks':[x['id'] for x in rows],'arms':[2048,4096],'model':'same R18 Graph BF16','seed':19,'budget':'24calls/1800sec/16384total output per call; only thinking cap changes','evaluation':'unchanged source private artifact verifier; submission and mutation separate, protocol/errors and exact usage recorded','selection':'first two original R17 length-exhaustion failures','gate':'no automatic rollout based solely on nonempty content; at least one private artifact pass and no execution integrity failures; fixed two tasks do not prove general quality','no_training':True}
(E/'REGISTRATION.json').write_text(json.dumps(reg,indent=2));(D/'REGISTRATION.json').write_text(json.dumps(reg,indent=2))
