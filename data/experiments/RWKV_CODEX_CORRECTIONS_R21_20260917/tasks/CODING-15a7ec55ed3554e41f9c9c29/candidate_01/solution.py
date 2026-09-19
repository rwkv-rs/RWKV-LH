import sys
from collections import deque
n,m,k=map(int,sys.stdin.buffer.readline().split());height=n+2*k;width=m+2*k;dist=[[-1]*width for _ in range(height)];queue=deque();water=0
for i in range(n):
 row=sys.stdin.buffer.readline().strip()
 for j,ch in enumerate(row):
  if ch==35:dist[i+k][j+k]=0;queue.append((i+k,j+k));water+=1
count=0
while queue:
 r,c=queue.popleft();count+=1
 if dist[r][c]==k:continue
 for rr,cc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
  if 0<=rr<height and 0<=cc<width and dist[rr][cc]<0:dist[rr][cc]=dist[r][c]+1;queue.append((rr,cc))
print(count-water)
