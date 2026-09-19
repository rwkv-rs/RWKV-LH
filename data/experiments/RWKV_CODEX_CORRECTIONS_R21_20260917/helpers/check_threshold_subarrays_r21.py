from pathlib import Path
import subprocess,random,json
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917');rows=json.loads((D/'INVENTORY.json').read_text())['tasks'];p=D/'tasks'/rows[58]['id']/'candidate_01/solution.py';rng=random.Random(20260919)
for trial in range(100):
 n=rng.randrange(1,25);a=[rng.randrange(10) for _ in range(n)];queries=[(rng.randrange(12),rng.randrange(0,n+3),rng.randrange(0,n+3)) for _ in range(30)];text=f'{n} {len(queries)}\n'+ ' '.join(map(str,a))+'\n'+'\n'.join(' '.join(map(str,q)) for q in queries);got=list(map(int,subprocess.check_output(['python3',str(p)],input=text.encode()).split()));expected=[sum(lo<=j-i+1<=hi and min(a[i:j+1])>=v for i in range(n) for j in range(i,n)) for v,lo,hi in queries]
 if got!=expected:
  print(json.dumps({'trial':trial,'input':text,'mismatches':[(q,g,e) for q,g,e in zip(queries,got,expected) if g!=e]}));break
else:print('all passed')
