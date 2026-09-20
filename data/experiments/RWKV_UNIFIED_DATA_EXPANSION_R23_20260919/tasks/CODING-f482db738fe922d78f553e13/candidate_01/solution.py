import sys
from collections import deque
sys.setrecursionlimit(10000)
v=sys.stdin.buffer.read().split();rows,cols=map(int,v[:2]);board=v[2:2+rows];size=rows+cols-1;blocked_a=[False]*size;blocked_b=[False]*size
for i,row in enumerate(board):
 for j,c in enumerate(row):
  if c!=46:blocked_a[i-j+cols-1]=True;blocked_b[i+j]=True
graph=[[] for _ in range(size)]
for i,row in enumerate(board):
 for j,c in enumerate(row):
  a=i-j+cols-1;b=i+j
  if c==46 and not blocked_a[a] and not blocked_b[b]:graph[a].append(b)
left=[-1]*size;right=[-1]*size;distance=[0]*size;answer=0
while True:
 queue=deque();found=False
 for u in range(size):
  if left[u]<0 and graph[u]:distance[u]=0;queue.append(u)
  else:distance[u]=-1
 while queue:
  u=queue.popleft()
  for v in graph[u]:
   mate=right[v]
   if mate<0:found=True
   elif distance[mate]<0:distance[mate]=distance[u]+1;queue.append(mate)
 if not found:break
 def augment(u):
  for v in graph[u]:
   mate=right[v]
   if mate<0 or (distance[mate]==distance[u]+1 and augment(mate)):
    left[u]=v;right[v]=u;return True
  distance[u]=-1;return False
 for u in range(size):
  if left[u]<0 and graph[u] and augment(u):answer+=1
print(answer)
