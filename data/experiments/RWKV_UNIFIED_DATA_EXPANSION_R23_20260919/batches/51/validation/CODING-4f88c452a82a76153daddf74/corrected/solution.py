import sys
from collections import deque
v=iter(sys.stdin.buffer.read().split());r,c=int(next(v)),int(next(v));grid=b''.join(next(v) for _ in range(r));k=int(next(v));targets={};trigger=[0]*(r*c)
for _ in range(k):
 a,b,x,y=(int(next(v))-1 for _ in range(4));p=x*c+y
 if p not in targets:targets[p]=len(targets)
 trigger[a*c+b]^=1<<targets[p]
bit=[0]*(r*c)
for p,j in targets.items():bit[p]=1<<j
N=r*c;start=grid.index(b'S');goal=grid.index(b'T');seen=bytearray(N*(1<<len(targets)));seen[start]=1;queue=deque([(start,0,0)]);answer=-1
while queue:
 p,mask,d=queue.popleft()
 if p==goal:answer=d;break
 x,y=divmod(p,c)
 for a,b in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
  if not(0<=a<r and 0<=b<c):continue
  z=a*c+b
  if (grid[z]==35)==bool(mask&bit[z]):
   new=mask^trigger[z];key=new*N+z
   if not seen[key]:seen[key]=1;queue.append((z,new,d+1))
print(answer)
