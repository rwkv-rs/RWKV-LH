import sys
from collections import deque
it=iter(map(int,sys.stdin.buffer.read().split()));m,n=next(it),next(it);rows=[[next(it) for _ in range(m+r)] for r in range(n)];ids=[];count=0
for row in rows:ids.append(list(range(count,count+len(row))));count+=len(row)
def solve(vertex_cap,edge_cap):
 size=2*count+2;source=size-2;sink=size-1;g=[[] for _ in range(size)]
 def edge(u,v,cap,cost):g[u].append([v,len(g[v]),cap,cost]);g[v].append([u,len(g[u])-1,0,-cost])
 for r,row in enumerate(rows):
  for c,value in enumerate(row):
   u=ids[r][c];edge(2*u,2*u+1,vertex_cap,-value)
   if r==0:edge(source,2*u,1,0)
   if r==n-1:edge(2*u+1,sink,m,0)
   else:
    for j in (c,c+1):edge(2*u+1,2*ids[r+1][j],edge_cap,0)
 total=0
 for _ in range(m):
  dist=[10**30]*size;dist[source]=0;parent=[None]*size;q=deque([source]);queued=bytearray(size);queued[source]=1
  while q:
   u=q.popleft();queued[u]=0
   for i,(v,rev,cap,cost) in enumerate(g[u]):
    if cap and dist[u]+cost<dist[v]:
     dist[v]=dist[u]+cost;parent[v]=(u,i)
     if not queued[v]:queued[v]=1;q.append(v)
  total-=dist[sink];v=sink
  while v!=source:u,i=parent[v];g[u][i][2]-=1;g[v][g[u][i][1]][2]+=1;v=u
 return total
print(solve(1,1));print(solve(m,1));print(solve(m,m))
