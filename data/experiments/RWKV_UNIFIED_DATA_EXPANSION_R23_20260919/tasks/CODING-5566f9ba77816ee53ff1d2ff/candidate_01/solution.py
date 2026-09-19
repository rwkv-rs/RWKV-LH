import sys
from collections import deque
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);m=next(v);graph=[[] for _ in range(2*n)];reverse=[[] for _ in range(2*n)]
for _ in range(m):
 a,b=next(v)-1,next(v)-1
 for x,y in ((a,n+b),(n+a,b)):graph[x].append(y);reverse[y].append(x)
def attractor(target,allowed):
 seen=bytearray(2*n);degree=[sum(allowed[y] for y in edges) for edges in graph];queue=deque()
 for x in target:seen[x]=1;queue.append(x)
 while queue:
  y=queue.popleft()
  for x in reverse[y]:
   if not allowed[x] or seen[x]:continue
   degree[x]-=1
   if x>=n or degree[x]==0:seen[x]=1;queue.append(x)
 return seen
allowed=bytearray([1])*(2*n);hwin=attractor([x for x in range(n) if not graph[x]],allowed);remaining=bytearray(1-x for x in hwin);gwin=attractor([x for x in range(n,2*n) if not graph[x]],remaining)
print(''.join('L' if hwin[x] else 'W' if gwin[x] else 'D' for x in range(n)))
print(''.join('W' if hwin[x] else 'L' if gwin[x] else 'D' for x in range(n,2*n)))
