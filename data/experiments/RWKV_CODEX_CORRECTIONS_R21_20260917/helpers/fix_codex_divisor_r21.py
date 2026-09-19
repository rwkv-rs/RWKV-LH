from pathlib import Path
import json,hashlib,shutil,subprocess
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917');folder=D/'tasks/CODING-29f5dad8a725d59add91fc84';old=folder/'candidate_01';code=(old/'solution.py').read_text();code=code.replace('''   product=1
   for _ in range(64):
    x=(x*x+c)%n;y=(y*y+c)%n;y=(y*y+c)%n;product=product*abs(x-y)%n
   divisor=math.gcd(product,n)''','''   x=(x*x+c)%n;y=(y*y+c)%n;y=(y*y+c)%n
   divisor=math.gcd(abs(x-y),n)''');p=folder/'candidate_02';p.mkdir(exist_ok=False);(p/'solution.py').write_text(code);author=json.loads((old/'AUTHOR.json').read_text());author['solution_sha256']=hashlib.sha256(code.encode()).hexdigest();author['reasoning']+=' Candidate01 batching could hide an intermediate proper factor and loop on small composite cycles; candidate02 computes each Floyd-step GCD.';(p/'AUTHOR.json').write_text(json.dumps(author,indent=2));shutil.copytree(p,D/'upload/tasks'/folder.name/p.name,dirs_exist_ok=True)
records=[]
for n in [17*19,17*17,19*23,29*31,1009*1013,999983*1000003,10**15]:
 record={'n':n,'k':2}
 for tag in ['candidate_01','candidate_02']:
  try:r=subprocess.run(['python3',str(folder/tag/'solution.py')],input=f'{n} 2\n',text=True,capture_output=True,timeout=.5);record[tag]={'exit':r.returncode,'stdout':r.stdout,'timeout':False}
  except subprocess.TimeoutExpired:record[tag]={'timeout':True}
 records.append(record)
assert any(r['candidate_01']['timeout'] for r in records)
assert all(not r['candidate_02']['timeout'] and r['candidate_02']['exit']==0 for r in records)
(folder/'RHO_REGRESSION.json').write_text(json.dumps({'independent_public_boundary_examples':records,'private_cases_used_to_construct_inputs':False},indent=2));print(records)
