from pathlib import Path
import json,hashlib
D=Path('/home/chase/GitHub/RWKV-LH/data/experiments/RWKV_CODEX_CORRECTIONS_R21_20260917');rows=json.loads((D/'INVENTORY.json').read_text())['tasks']
solutions={
8:('candidate_02', '''import sys
a=sys.stdin.buffer.read().split();n=int(a[0]);sys.stdout.buffer.write(b' '.join(a[1:n+1][::-1])+b'\\n')
''','Reverse original numeric tokens without unnecessary lexical rewriting; preserve leading signs and zeros. Candidate01 was numerically correct but changed representations.'),
11:('candidate_02','''import sys
a=list(map(int,sys.stdin.buffer.read().split()));print('\\n'.join(f'{a[i]-1} {a[i+1]}' for i in range(1,len(a),2)))
''','Independent exhaustive optimal-play recurrence yields (x-1,y); initial x-y formula rejected and preserved.'),
15:('candidate_01','''import sys
sys.setrecursionlimit(1000000)
f=sys.stdin.buffer;out=[]
while True:
 line=f.readline()
 if not line:break
 if not line.strip():continue
 n,m=map(int,line.split());rules=[]
 for _ in range(m):
  p=f.readline().replace(b':',b' ').split();a=int(p[0])-1;b=int(p[2])-1;u=2*a+(p[1]==b'right');v=2*b+(p[3]==b'right');rules.append((a,b,u,v))
 def feasible(h):
  size=2*(h-1)
  if not size:return True
  g=[[] for _ in range(size)];rev=[[] for _ in range(size)]
  for a,b,u,v in rules:
   if a<h-1 and b<h-1:
    g[u].append(v^1);rev[v^1].append(u);g[v].append(u^1);rev[u^1].append(v)
  seen=bytearray(size);order=[]
  def visit(v):
   seen[v]=1
   for w in g[v]:
    if not seen[w]:visit(w)
   order.append(v)
  for v in range(size):
   if not seen[v]:visit(v)
  comp=[-1]*size
  for v in reversed(order):
   if comp[v]>=0:continue
   comp[v]=v;stack=[v]
   while stack:
    z=stack.pop()
    for w in rev[z]:
     if comp[w]<0:comp[w]=v;stack.append(w)
  return all(comp[i]!=comp[i^1] for i in range(0,size,2))
 lo,hi=1,n
 while lo<hi:
  mid=(lo+hi+1)//2
  if feasible(mid):lo=mid
  else:hi=mid-1
 out.append(str(lo))
print('\\n'.join(out))
''','Prefix reachability is 2-SAT of mutually forbidden stair choices; binary search maximal reachable floor.'),
14:('candidate_01','''import sys,math
from array import array
f=sys.stdin.buffer;n,q=map(int,f.readline().split());a=list(map(int,f.readline().split()));g=[[] for _ in range(n)]
for _ in range(n-1):
 u,v=map(int,f.readline().split());u-=1;v-=1;g[u].append(v);g[v].append(u)
queries=[list(map(int,f.readline().split())) for _ in range(q)];mx=max(a+[p[2] for p in queries if p[0]==2]);spf=array('i',range(mx+1))
for p in range(2,math.isqrt(mx)+1):
 if spf[p]==p:
  for j in range(p*p,mx+1,p):
   if spf[j]==j:spf[j]=p
cache={1:()}
def factors(x):
 if x in cache:return cache[x]
 orig=x;r=[]
 while x>1:
  p=spf[x];r.append(p)
  while x%p==0:x//=p
 cache[orig]=tuple(r);return cache[orig]
parent=[-1]*n;depth=[0]*n;order=[0]
for v in order:
 for w in g[v]:
  if w!=parent[v]:parent[w]=v;depth[w]=depth[v]+1;order.append(w)
def rebuild():
 last={};answer=[-1]*n;stack=[(0,False,None)]
 while stack:
  v,exit,old=stack.pop();ps=factors(a[v])
  if exit:
   for p,z in zip(ps,old):
    if z<0:last.pop(p,None)
    else:last[p]=z
  else:
   prev=[last.get(p,-1) for p in ps];best=-1
   for z in prev:
    if z>=0 and (best<0 or depth[z]>depth[best]):best=z
   answer[v]=best+1 if best>=0 else -1
   for p in ps:last[p]=v
   stack.append((v,True,prev))
   for w in g[v]:
    if parent[w]==v:stack.append((w,False,None))
 return answer
ans=None;out=[]
for query in queries:
 if query[0]==2:a[query[1]-1]=query[2];ans=None
 else:
  if ans is None:ans=rebuild()
  out.append(str(ans[query[1]-1]))
print('\\n'.join(out))
''','At most 50 value changes: rebuild nearest shared-prime ancestor by DFS after updates; cache factorizations; read queries O(1).')
}
for i,(tag,code,note) in solutions.items():
 p=D/'tasks'/rows[i]['id']/tag;p.mkdir(exist_ok=False);(p/'solution.py').write_text(code);(p/'AUTHOR.json').write_text(json.dumps({'author':'Codex','task_sha256':rows[i]['task_sha256'],'solution_sha256':hashlib.sha256(code.encode()).hexdigest(),'reasoning':note,'hidden_cases_read':False,'training_admitted':False},indent=2))
