import sys,math
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
print('\n'.join(out))
