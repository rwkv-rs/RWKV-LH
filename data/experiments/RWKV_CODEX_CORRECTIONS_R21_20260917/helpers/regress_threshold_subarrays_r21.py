from pathlib import Path
import subprocess,random,json,hashlib
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917');rows=json.loads((D/'INVENTORY.json').read_text())['tasks'];folder=D/'tasks'/rows[58]['id'];rng=random.Random(20260919);results=[]
for trial in range(50):
 n=rng.randrange(1,25);a=[rng.randrange(10) for _ in range(n)];queries=[(rng.randrange(12),rng.randrange(0,n+3),rng.randrange(0,n+3)) for _ in range(30)];text=f'{n} {len(queries)}\n'+' '.join(map(str,a))+'\n'+'\n'.join(' '.join(map(str,q)) for q in queries);expected=[sum(lo<=j-i+1<=hi and min(a[i:j+1])>=v for i in range(n) for j in range(i,n)) for v,lo,hi in queries];record={'input':text,'oracle':expected}
 for tag in ['candidate_01','candidate_02']:
  got=list(map(int,subprocess.check_output(['python3',str(folder/tag/'solution.py')],input=text.encode(),timeout=5).split()));record[tag]={'passed':got==expected,'output':got}
 results.append(record)
assert any(not r['candidate_01']['passed'] for r in results)
assert all(r['candidate_02']['passed'] for r in results)
report={'source':'Independent deterministic brute force from public specification, not original hidden acceptance','seed':20260919,'queries':1500,'before_failed_inputs':sum(not r['candidate_01']['passed'] for r in results),'after_passed_inputs':len(results),'results':results};(folder/'EMPTY_INTERVAL_REGRESSION.json').write_text(json.dumps(report,indent=2));print({k:v for k,v in report.items() if k!='results'})
