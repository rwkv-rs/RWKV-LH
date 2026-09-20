import sys
from collections import deque
from functools import lru_cache
sys.setrecursionlimit(10000)
v=list(map(int,sys.stdin.buffer.read().split()));n,e=v[:2];cat,mouse=v[2]-1,v[3]-1;adj=[[] for _ in range(n)]
for i in range(e):
 a,b=v[4+2*i]-1,v[5+2*i]-1;adj[a].append(b);adj[b].append(a)
for row in adj:row.sort()
distance=[];nextstep=[]
for target in range(n):
 dist=[-1]*n;dist[target]=0;q=deque([target])
 while q:
  u=q.popleft()
  for v in adj[u]:
   if dist[v]<0:dist[v]=dist[u]+1;q.append(v)
 move=[target]*n
 for u in range(n):
  if dist[u]>0:move[u]=next(v for v in adj[u] if dist[v]==dist[u]-1)
 distance.append(dist);nextstep.append(move)
@lru_cache(None)
def expected(c,m):
 d=distance[m][c]
 if d==0:return 0.0
 if d<=2:return 1.0
 c=nextstep[m][nextstep[m][c]]
 return 1+(expected(c,m)+sum(expected(c,v) for v in adj[m]))/(len(adj[m])+1)
print(f'{expected(cat,mouse):.3f}')
