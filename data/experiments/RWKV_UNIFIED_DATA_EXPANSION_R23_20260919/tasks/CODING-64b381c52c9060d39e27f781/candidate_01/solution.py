import sys
from collections import deque
v=sys.stdin.buffer.read().split();r,c=map(int,v[:2]);grid=b''.join(v[2:2+r]);text=v[2+r]+b'*';N=r*c;neighbors=[[] for _ in range(N)]
for p in range(N):
 x,y=divmod(p,c)
 for dx,dy in ((-1,0),(1,0),(0,-1),(0,1)):
  a,b=x+dx,y+dy
  while 0<=a<r and 0<=b<c and grid[a*c+b]==grid[p]:a+=dx;b+=dy
  if 0<=a<r and 0<=b<c:neighbors[p].append(a*c+b)
seen=bytearray(N*(len(text)+1));seen[0]=1;queue=deque([0]);distance=0;answer=None
while queue and answer is None:
 for _ in range(len(queue)):
  key=queue.popleft();i,p=divmod(key,N)
  if i==len(text):answer=distance;break
  if grid[p]==text[i]:targets=[key+N]
  else:targets=[i*N+z for z in neighbors[p]]
  for z in targets:
   if not seen[z]:seen[z]=1;queue.append(z)
 distance+=1
print(answer)
