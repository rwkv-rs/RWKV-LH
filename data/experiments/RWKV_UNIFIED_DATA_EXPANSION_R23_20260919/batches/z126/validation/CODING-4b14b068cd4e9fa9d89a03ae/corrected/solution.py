import sys
from collections import deque
v=list(map(int,sys.stdin.buffer.read().split()));n,limit,k=v[:3];values=v[3:3+n*n];blocked=set((r-1)*n+c-1 for r,c in zip(v[3+n*n::2],v[4+n*n::2]));source=2*n*n;sink=source+1;graph=[[] for _ in range(sink+1)]
def add(u,w,cap,cost):
 graph[u].append([w,len(graph[w]),cap,cost]);graph[w].append([u,len(graph[u])-1,0,-cost])
for r in range(n):
 for c in range(n):
  u=r*n+c
  if u in blocked:continue
  if (r+c)%2==0:
   if r%2==0:add(source,u,1,0)
   else:add(u,sink,1,0)
  else:
   add(u,u+n*n,1,-values[u])
   for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
    rr=r+dr;cc=c+dc
    if 0<=rr<n and 0<=cc<n:
     w=rr*n+cc
     if w not in blocked:
      if rr%2==0:add(w,u,1,0)
      else:add(u+n*n,w,1,0)
answer=sum(values);inf=10**30
for _ in range(limit):
 dist=[inf]*len(graph);previous=[None]*len(graph);queued=[False]*len(graph);queue=deque([source]);queued[source]=True;dist[source]=0
 while queue:
  u=queue.popleft();queued[u]=False
  for i,e in enumerate(graph[u]):
   w,rev,cap,cost=e
   if cap and dist[w]>dist[u]+cost:
    dist[w]=dist[u]+cost;previous[w]=(u,i)
    if not queued[w]:queue.append(w);queued[w]=True
 if dist[sink]>=0:break
 answer+=dist[sink];u=sink
 while u!=source:
  p,i=previous[u];e=graph[p][i];e[2]-=1;graph[u][e[1]][2]+=1;u=p
print(answer)
