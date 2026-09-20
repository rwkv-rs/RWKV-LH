import sys,math
from collections import deque
v=sys.stdin.buffer.read().split();n,m,T=map(int,v[:3]);a=[int(chr(c)) for row in v[3:] for c in row];size=n*m;adj=[[] for _ in range(size)]
for p in range(size):
 r,c=divmod(p,m)
 for dr,dc in ((1,0),(-1,0),(0,1),(0,-1)):
  rr,cc=r+dr,c+dc
  if 0<=rr<n and 0<=cc<m:adj[p].append(rr*m+cc)
answer=0
for start in range(size):
 if a[start]>T:continue
 dist=[T+1]*size;dist[start]=a[start];q=deque([start]);sr,sc=divmod(start,m)
 while q:
  u=q.popleft();d=dist[u]
  for w in adj[u]:
   nd=d+a[w]
   if nd<dist[w]:
    dist[w]=nd
    if a[w]:q.append(w)
    else:q.appendleft(w)
 for p in range(start+1,size):
  if dist[p]<=T:r,c=divmod(p,m);answer=max(answer,(sr-r)**2+(sc-c)**2)
print(f'{math.sqrt(answer):.6f}')
