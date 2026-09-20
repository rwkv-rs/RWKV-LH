import sys
from collections import deque
sys.setrecursionlimit(10000)
v=list(map(int,sys.stdin.buffer.read().split()));m,n=v[:2];a=v[2:];cells=m*n;source=2*cells;sink=source+1;graph=[[] for _ in range(sink+1)];inf=sum(x for x in a if x>0)+1
def edge(u,v,c):
 graph[u].append([v,c,len(graph[v])]);graph[v].append([u,0,len(graph[u])-1])
for r in range(m):
 for c in range(n):
  k=r*n+c
  if a[k]<0:continue
  edge(2*k,2*k+1,inf if a[k]==0 else a[k])
  if a[k]==0:edge(source,2*k,inf)
  if r==0 or c==0 or r==m-1 or c==n-1:edge(2*k+1,sink,inf)
  for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
   if 0<=rr<m and 0<=cc<n and a[rr*n+cc]>=0:edge(2*k+1,2*(rr*n+cc),inf)
answer=0
while True:
 level=[-1]*len(graph);level[source]=0;q=deque([source])
 while q:
  u=q.popleft()
  for dest,cap,rev in graph[u]:
   if cap and level[dest]<0:level[dest]=level[u]+1;q.append(dest)
 if level[sink]<0:break
 at=[0]*len(graph)
 def send(u,amount):
  if u==sink:return amount
  while at[u]<len(graph[u]):
   e=graph[u][at[u]];dest,cap,rev=e
   if cap and level[dest]==level[u]+1:
    pushed=send(dest,min(amount,cap))
    if pushed:e[1]-=pushed;graph[dest][rev][1]+=pushed;return pushed
   at[u]+=1
  return 0
 while True:
  pushed=send(source,inf)
  if not pushed:break
  answer+=pushed
print(answer)
