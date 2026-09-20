import sys
from collections import deque
it=iter(map(int,sys.stdin.buffer.read().split()));n,budget=next(it),next(it);g=[[] for _ in range(n)]
def edge(u,v,cap,cost):g[u].append([v,len(g[v]),cap,cost]);g[v].append([u,len(g[u])-1,0,-cost])
for i in range(n):
 for j in range(n):
  c=next(it)
  if c:edge(i,j,c,0);edge(i,j,budget,1)
flow=0
while True:
 dist=[10**30]*n;dist[0]=0;parent=[None]*n;q=deque([0]);inside=[False]*n;inside[0]=True
 while q:
  u=q.popleft();inside[u]=False
  for i,(v,rev,cap,cost) in enumerate(g[u]):
   if cap and dist[u]+cost<dist[v]:
    dist[v]=dist[u]+cost;parent[v]=(u,i)
    if not inside[v]:inside[v]=True;q.append(v)
 if parent[-1] is None or dist[-1]>budget:break
 amount=10**30;v=n-1
 while v:u,i=parent[v];amount=min(amount,g[u][i][2]);v=u
 if dist[-1]>0:amount=min(amount,budget//dist[-1])
 if not amount:break
 budget-=amount*dist[-1];flow+=amount;v=n-1
 while v:
  u,i=parent[v];e=g[u][i];e[2]-=amount;g[v][e[1]][2]+=amount;v=u
print(flow)
