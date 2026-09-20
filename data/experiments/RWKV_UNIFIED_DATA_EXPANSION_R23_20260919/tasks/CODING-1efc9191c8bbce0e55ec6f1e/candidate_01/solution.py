import sys
from collections import deque
v=list(map(int,sys.stdin.buffer.read().split()));n,k=v[:2];delta=sorted({x-n for x in v[2:]})
if 0 in delta:print(1)
elif delta[0]>0 or delta[-1]<0:print(-1)
else:
 bound=max(abs(delta[0]),abs(delta[-1]));distance={0:0};queue=deque([0]);answer=-1
 while queue and answer<0:
  u=queue.popleft()
  for d in delta:
   w=u+d
   if w==0:answer=distance[u]+1;break
   if -bound<=w<=bound and w not in distance:distance[w]=distance[u]+1;queue.append(w)
 print(answer)
