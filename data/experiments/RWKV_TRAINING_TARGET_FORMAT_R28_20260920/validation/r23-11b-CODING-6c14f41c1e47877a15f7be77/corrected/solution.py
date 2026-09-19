import sys
from collections import deque
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);m=next(it);s=next(it)-1;t=next(it)-1;capacity=[[0]*n for _ in range(n)]
for _ in range(m):u=next(it)-1;v=next(it)-1;capacity[u][v]+=next(it)
flow=0
if s==t:print(0);raise SystemExit
while True:
 parent=[-1]*n;parent[s]=s;q=deque([s])
 while q and parent[t]<0:
  u=q.popleft()
  for v,c in enumerate(capacity[u]):
   if c>0 and parent[v]<0:parent[v]=u;q.append(v)
 if parent[t]<0:break
 amount=10**30;v=t
 while v!=s:u=parent[v];amount=min(amount,capacity[u][v]);v=u
 v=t
 while v!=s:u=parent[v];capacity[u][v]-=amount;capacity[v][u]+=amount;v=u
 flow+=amount
print(flow)
