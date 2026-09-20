import sys
v=sys.stdin.buffer.read().split();rows,cols=map(int,v[:2]);grid=v[2:];n=rows*cols;huge=n+1;cost=[[huge]*n for _ in range(n)];directions=[(76,0,-1),(82,0,1),(85,-1,0),(68,1,0)]
for y in range(rows):
 for x in range(cols):
  u=y*cols+x
  for code,dy,dx in directions:
   w=((y+dy)%rows)*cols+(x+dx)%cols;cost[u][w]=min(cost[u][w],int(grid[y][x]!=code))
u=[0]*(n+1);vpot=[0]*(n+1);owner=[0]*(n+1);way=[0]*(n+1)
for row in range(1,n+1):
 owner[0]=row;j0=0;best=[10**9]*(n+1);used=[False]*(n+1)
 while True:
  used[j0]=True;i0=owner[j0];delta=10**9;j1=0;values=cost[i0-1]
  for j in range(1,n+1):
   if not used[j]:
    candidate=values[j-1]-u[i0]-vpot[j]
    if candidate<best[j]:best[j]=candidate;way[j]=j0
    if best[j]<delta:delta=best[j];j1=j
  for j in range(n+1):
   if used[j]:u[owner[j]]+=delta;vpot[j]-=delta
   else:best[j]-=delta
  j0=j1
  if owner[j0]==0:break
 while j0:
  before=way[j0];owner[j0]=owner[before];j0=before
print(-vpot[0])
