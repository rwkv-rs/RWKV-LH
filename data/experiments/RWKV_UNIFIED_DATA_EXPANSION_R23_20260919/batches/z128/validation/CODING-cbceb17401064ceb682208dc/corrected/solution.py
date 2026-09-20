import sys
from collections import deque
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(it)):
 n=next(it);duration=next(it);cooldown=next(it);sx=next(it);sy=next(it);points=[(next(it),next(it)) for i in range(n)];graph=[[] for _ in range(n)];initial=[]
 for i,(x,y) in enumerate(points):
  if (x-sx)**2+(y-sy)**2<=100:initial.append(i)
  for j in range(i):
   xx,yy=points[j]
   if (x-xx)**2+(y-yy)**2<=2500:graph[i].append(j);graph[j].append(i)
 if not initial:out.append('0');continue
 active=set(initial)
 if cooldown<duration:
  out.append("You're always welcome!" if any(v not in active for u in initial for v in graph[u]) else str(duration));continue
 distance=[-1]*n;queue=deque(initial)
 for i in initial:distance[i]=0
 while queue:
  u=queue.popleft()
  for v in graph[u]:
   if distance[v]<0:distance[v]=distance[u]+1;queue.append(v)
 out.append(str((max(distance)+1)*duration))
print('\n'.join(out))
