import sys
from collections import deque
n,m,k=map(int,sys.stdin.buffer.readline().split());stride=m+2;grid=bytearray(b'*'*stride)
for _ in range(n):grid.extend(b'*'+sys.stdin.buffer.readline().strip()+b'*')
grid.extend(b'*'*stride);start=grid.index(88);dist=[-1]*len(grid);dist[start]=0;q=deque([start]);steps=[(stride,'D'),(-1,'L'),(1,'R'),(-stride,'U')]
if k%2:print('IMPOSSIBLE');raise SystemExit
while q:
 x=q.popleft()
 for delta,_ in steps:
  y=x+delta
  if grid[y]!=42 and dist[y]<0:dist[y]=dist[x]+1;q.append(y)
x=start;out=[]
for remaining in range(k-1,-1,-1):
 for delta,ch in steps:
  y=x+delta
  if dist[y]>=0 and dist[y]<=remaining:x=y;out.append(ch);break
 else:print('IMPOSSIBLE');raise SystemExit
print(''.join(out))
