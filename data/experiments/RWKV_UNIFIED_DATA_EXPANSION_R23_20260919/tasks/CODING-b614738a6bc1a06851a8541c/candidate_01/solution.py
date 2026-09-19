import sys
from collections import deque
v=iter(map(int,sys.stdin.read().split()));n=next(v);m=next(v);g=[[] for _ in range(n)]
for _ in range(m):a=next(v)-1;b=next(v)-1;g[a].append(b);g[b].append(a)
d=[]
for start in range(n):
 dist=[-1]*n;dist[start]=0;q=deque([start])
 while q:
  x=q.popleft()
  for y in g[x]:
   if dist[y]<0:dist[y]=dist[x]+1;q.append(y)
 d.append(dist)
out=[]
for _ in range(next(v)):
 a=next(v)-1;b=next(v)-1;out.append(' '.join(str(x+1) for x in range(n) if d[a][x]+d[x][b]==d[a][b]))
print('\n'.join(out))
