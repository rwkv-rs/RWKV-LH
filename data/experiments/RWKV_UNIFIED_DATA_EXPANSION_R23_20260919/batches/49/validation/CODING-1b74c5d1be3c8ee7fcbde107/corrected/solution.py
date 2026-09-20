import sys
from collections import deque
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for case in range(1,next(it)+1):
 n,m=next(it),next(it);counts=[]
 for _ in range(n):
  a=[0]*m
  for j in range(next(it)):a[next(it)-1]+=1
  counts.append(a)
 size=m+n+1;source=m+n-1;sink=m+n;g=[[] for _ in range(size)]
 def edge(u,v,c):g[u].append([v,len(g[v]),c]);g[v].append([u,len(g[u])-1,0])
 for j in range(m):edge(source,j,counts[0][j]);edge(j,sink,1)
 for i in range(1,n):
  person=m+i-1
  for j in range(m):
   if counts[i][j]==0:edge(j,person,1)
   elif counts[i][j]>1:edge(person,j,counts[i][j]-1)
 answer=0
 while True:
  parent=[None]*size;parent[source]=(-1,-1);q=deque([source])
  while q and parent[sink] is None:
   u=q.popleft()
   for j,(w,rev,c) in enumerate(g[u]):
    if c and parent[w] is None:parent[w]=(u,j);q.append(w)
  if parent[sink] is None:break
  v=sink
  while v!=source:u,j=parent[v];g[u][j][2]-=1;g[v][g[u][j][1]][2]+=1;v=u
  answer+=1
 out.append(f'Case #{case}: {answer}')
print('\n'.join(out))
