import sys
n,m=map(int,sys.stdin.buffer.readline().split());grid=[sys.stdin.buffer.readline().strip() for _ in range(n)];cells=[(r,c) for r in range(n) for c in range(m) if grid[r][c]==46];index={cell:i for i,cell in enumerate(cells)};size=len(cells)
if size<=1:print(1);raise SystemExit
matrix=[[0]*size for _ in range(size)]
for i,(r,c) in enumerate(cells):
 for neighbor in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
  j=index.get(neighbor)
  if j is not None:matrix[i][i]+=1;matrix[i][j]-=1
matrix=[row[:-1] for row in matrix[:-1]];size-=1;previous=1;sign=1
for k in range(size-1):
 if matrix[k][k]==0:
  pivot=next((i for i in range(k+1,size) if matrix[i][k]),None)
  if pivot is None:print(0);raise SystemExit
  matrix[k],matrix[pivot]=matrix[pivot],matrix[k];sign=-sign
 pivot=matrix[k][k]
 for i in range(k+1,size):
  factor=matrix[i][k]
  for j in range(k+1,size):matrix[i][j]=(matrix[i][j]*pivot-factor*matrix[k][j])//previous
  matrix[i][k]=0
 previous=pivot
print(sign*matrix[-1][-1]%1000000000)
