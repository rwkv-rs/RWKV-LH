import sys
from collections import deque
v=sys.stdin.buffer.read().split();h=int(v[0]);w=int(v[1]);grid=v[2:];d=[10**9]*(h*w);d[0]=0;q=deque([(0,0)]);offsets=[(a,b) for a in range(-2,3) for b in range(-2,3) if (a or b) and not(abs(a)==2 and abs(b)==2)]
while q:
 p,old=q.popleft()
 if old!=d[p]:continue
 if p==h*w-1:break
 x,y=divmod(p,w)
 for a,b in ((0,1),(0,-1),(1,0),(-1,0)):
  xx=x+a;yy=y+b
  if 0<=xx<h and 0<=yy<w and grid[xx][yy]==46:
   z=xx*w+yy
   if d[z]>old:d[z]=old;q.appendleft((z,old))
 for a,b in offsets:
  xx=x+a;yy=y+b
  if 0<=xx<h and 0<=yy<w:
   z=xx*w+yy
   if d[z]>old+1:d[z]=old+1;q.append((z,old+1))
print(d[-1])
