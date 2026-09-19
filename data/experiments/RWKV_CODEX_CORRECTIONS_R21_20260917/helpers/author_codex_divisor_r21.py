from pathlib import Path
import json,hashlib,shutil
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917');rows=json.loads((D/'INVENTORY.json').read_text())['tasks'];r=rows[181]
code='''import sys,math
n,k=map(int,sys.stdin.buffer.read().split())
def prime(n):
 if n<2:return False
 for p in (2,3,5,7,11,13,17,19,23,29,31,37):
  if n%p==0:return n==p
 d=n-1;s=0
 while d%2==0:d//=2;s+=1
 for a in (2,325,9375,28178,450775,9780504,1795265022):
  if a%n==0:continue
  x=pow(a,d,n)
  if x in (1,n-1):continue
  for _ in range(s-1):
   x=x*x%n
   if x==n-1:break
  else:return False
 return True
def factor(n):
 if n==1:return []
 if prime(n):return [n]
 for p in (2,3,5,7,11,13):
  if n%p==0:return [p]+factor(n//p)
 c=1
 while True:
  x=y=2;divisor=1
  while divisor==1:
   product=1
   for _ in range(64):
    x=(x*x+c)%n;y=(y*y+c)%n;y=(y*y+c)%n;product=product*abs(x-y)%n
   divisor=math.gcd(product,n)
  if divisor!=n:return factor(divisor)+factor(n//divisor)
  c+=1
factors=sorted(factor(n));divisors=[1];i=0
while i<len(factors):
 p=factors[i];old=divisors[:];power=1
 while i<len(factors) and factors[i]==p:power*=p;divisors.extend(x*power for x in old);i+=1
divisors.sort();print(divisors[k-1] if k<=len(divisors) else -1)
'''
p=D/'tasks'/r['id']/'candidate_01';p.mkdir(exist_ok=False);(p/'solution.py').write_text(code);(p/'AUTHOR.json').write_text(json.dumps({'author':'Codex','task_sha256':r['task_sha256'],'solution_sha256':hashlib.sha256(code.encode()).hexdigest(),'reasoning':'Factor n using deterministic 64-bit primality testing and Pollard rho, enumerate divisors from prime multiplicities. Avoid the original O(sqrt(n)) Python loop at 1e15. Original production pass and current timeout remain separate evidence.','hidden_cases_read':False,'training_admitted':False},indent=2));shutil.copytree(p,D/'upload/tasks'/r['id']/p.name,dirs_exist_ok=True)
