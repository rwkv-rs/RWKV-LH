import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
while True:
 try:n=next(v);m=next(v);unused=next(v)
 except StopIteration:break
 matrix=[[-1]*n for _ in range(n)]
 for i in range(n):matrix[i][i]=n-1
 for _ in range(m):
  a=next(v)-1;b=next(v)-1;matrix[a][a]-=1;matrix[b][b]-=1;matrix[a][b]=matrix[b][a]=0
 a=[row[:-1] for row in matrix[:-1]];size=n-1;previous=1;sign=1;zero=False
 for k in range(size-1):
  if a[k][k]==0:
   pivot=next((i for i in range(k+1,size) if a[i][k]),None)
   if pivot is None:zero=True;break
   a[k],a[pivot]=a[pivot],a[k];sign=-sign
  pivot=a[k][k]
  for i in range(k+1,size):
   for j in range(k+1,size):a[i][j]=(a[i][j]*pivot-a[i][k]*a[k][j])//previous
  for i in range(k+1,size):a[i][k]=0
  previous=pivot
 answer=0 if zero else sign*a[-1][-1] if size else 1;out.append(str(answer))
print('\n'.join(out))
