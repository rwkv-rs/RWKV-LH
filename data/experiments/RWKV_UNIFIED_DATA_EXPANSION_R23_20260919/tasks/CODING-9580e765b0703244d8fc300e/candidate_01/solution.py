import sys
from collections import Counter
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(it)):
 n,m=next(it),next(it);g=[[] for i in range(n)]
 for i in range(n-1):a,b=next(it)-1,next(it)-1;g[a].append(b);g[b].append(a)
 blocked=bytearray(n);paths=[[] for i in range(n)];totals=[None]*n;subs={};jobs=[0];parent=[-1]*n;size=[0]*n
 while jobs:
  root=jobs.pop();order=[root];parent[root]=-1
  for u in order:
   for v in g[u]:
    if not blocked[v] and v!=parent[u]:parent[v]=u;order.append(v)
  length=len(order)
  for u in reversed(order):size[u]=1+sum(size[v] for v in g[u] if not blocked[v] and parent[v]==u)
  c=root
  for u in order:
   if max([length-size[u]]+[size[v] for v in g[u] if not blocked[v] and parent[v]==u])<=length//2:c=u;break
  blocked[c]=1;totals[c]=Counter({0:1});paths[c].append((c,0,-1))
  for child in g[c]:
   if blocked[child]:continue
   counts=Counter();stack=[(child,c,1)]
   while stack:
    u,p,d=stack.pop();counts[d]+=1;paths[u].append((c,d,child))
    for v in g[u]:
     if v!=p and not blocked[v]:stack.append((v,u,d+1))
   subs[c,child]=counts;totals[c].update(counts);jobs.append(child)
 for i in range(m):
  x,k=next(it)-1,next(it);answer=0
  for c,d,child in paths[x]:
   if d<=k:
    answer+=totals[c][k-d]
    if child>=0:answer-=subs[c,child][k-d]
  out.append(str(answer))
print('\n'.join(out))
