import sys
from collections import deque
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);m=next(v);adj=[[] for _ in range(n)]
for i in range(m):
 a=next(v)-1;b=next(v)-1;adj[a].append((b,i))
def bfs(skip):
 d=[-1]*n;p=[None]*n;d[0]=0;q=deque([0])
 while q:
  x=q.popleft()
  if x==n-1:break
  for y,e in adj[x]:
   if e!=skip and d[y]<0:d[y]=d[x]+1;p[y]=(x,e);q.append(y)
 return d[-1],p
base,parent=bfs(-1);answer=[base]*m
if base>=0:
 x=n-1;path=[]
 while x:
  x,e=parent[x];path.append(e)
 for e in path:answer[e]=bfs(e)[0]
print('\n'.join(map(str,answer)))
