import sys
v=sys.stdin.buffer.read().split();n,m=map(int,v[:2]);grid=v[2:];cells=[];row=[[] for _ in range(n)];col=[[] for _ in range(m)];arrows=[]
for i in range(n):
 for j in range(m):
  if grid[i][j]!=46:
   k=len(cells);cells.append((i,j));row[i].append(k);col[j].append(k);arrows.append(grid[i][j])
k=len(cells);base=[[-1]*k for _ in range(4)]
for groups,a,b in ((row,0,1),(col,2,3)):
 for group in groups:
  for x,y in zip(group,group[1:]):base[b][x]=y;base[a][y]=x
direction={76:0,82:1,85:2,68:3};best=count=0
for start in range(k):
 L,R,U,D=[a[:] for a in base];links=[L,R,U,D];u=start;score=0
 while u>=0:
  nxt=links[direction[arrows[u]]][u];l,r,t,b=L[u],R[u],U[u],D[u]
  if l>=0:R[l]=r
  if r>=0:L[r]=l
  if t>=0:D[t]=b
  if b>=0:U[b]=t
  score+=1;u=nxt
 if score>best:best=score;count=1
 elif score==best:count+=1
print(best,count)
