import sys
from collections import deque
v=list(map(int,sys.stdin.buffer.read().split()));n,m,k=v[:3];points=list(zip(v[3::2],v[4::2]));index={p:i for i,p in enumerate(points)};total=k+n+m+1;goal=total-1;graph=[[] for _ in range(total)]
for i,(r,c) in enumerate(points):
 for rr in (r-1,r,r+1):
  if 1<=rr<=n:node=k+rr-1;graph[i].append((node,1));graph[node].append((i,0))
 for cc in (c-1,c,c+1):
  if 1<=cc<=m:node=k+n+cc-1;graph[i].append((node,1));graph[node].append((i,0))
 for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
  j=index.get((r+dr,c+dc))
  if j is not None:graph[i].append((j,0))
if (n,m) in index:graph[index[n,m]].append((goal,0))
else:graph[k+n-1].append((goal,0));graph[k+n+m-1].append((goal,0))
dist=[10**9]*total;start=index[1,1];dist[start]=0;queue=deque([start])
while queue:
 u=queue.popleft()
 for w,cost in graph[u]:
  value=dist[u]+cost
  if value<dist[w]:
   dist[w]=value
   if cost:queue.append(w)
   else:queue.appendleft(w)
print(dist[goal] if dist[goal]<10**9 else -1)
