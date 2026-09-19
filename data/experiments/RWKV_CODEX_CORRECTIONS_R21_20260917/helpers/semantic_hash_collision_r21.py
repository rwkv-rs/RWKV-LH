from pathlib import Path
import subprocess,json,hashlib,re,time
R=Path('/home/chase/GitHub/RWKV-LH');D=R/'data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917';folder=D/'tasks/CODING-05981d20d9e758b8782d188e';candidate=folder/'candidate_01/solution.py';out=folder/'semantic_diagnostic';out.mkdir(exist_ok=False)
def check(k,text):
 lines=text.splitlines()
 if len(lines)!=k or len(set(lines))!=k:return False
 if any(not re.fullmatch('[A-Za-z]{1,1000}',s) for s in lines):return False
 hashes=[]
 for s in lines:
  h=0
  for ch in s:h=(h*31+ord(ch))&0xffffffff
  hashes.append(h)
 return len(set(hashes))==1
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
(out/'REGISTRATION.json').write_text(json.dumps({'scope':'new semantic diagnostic on complete public input domain; historical exact 0/34 unchanged','checker_sha256':sha(Path(__file__)),'candidate_sha256':sha(candidate),'task_sha256':sha(folder/'TASK.md'),'inputs':'all integers 2..1000 inclusive','criteria':['exact k lines','ASCII English letters only','1..1000 characters each','pairwise distinct','equal Java polynomial hash modulo 2^32'],'private_expected_used':False,'training_admitted':False},indent=2))
assert check(2,'Aa\nBB\n')
for k,text in [(2,'Aa\nAa\n'),(2,'Aa\nBC\n'),(2,'Aa\n'),(2,'Aa\nB1\n'),(2,'\nBB\n')]:assert not check(k,text)
records=[];start=time.time()
for k in range(2,1001):
 r=subprocess.run(['python3',str(candidate)],input=f'{k}\n',text=True,capture_output=True,timeout=3);passed=r.returncode==0 and check(k,r.stdout);records.append({'k':k,'passed':passed,'output_sha256':hashlib.sha256(r.stdout.encode()).hexdigest(),'bytes':len(r.stdout.encode())})
assert all(r['passed'] for r in records)
(out/'RESULTS.json').write_text(json.dumps({'passed':len(records),'total':len(records),'seconds':time.time()-start,'negative_checker_cases':5,'training_admitted':False,'historical_exact_result_unchanged':True,'records':records},indent=2));print('semantic diagnostic',len(records),'/',len(records))
