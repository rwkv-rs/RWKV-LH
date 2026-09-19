import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);matrix=[[next(it) for _ in range(n)] for _ in range(n)]
def hungarian(sign):
 u=[0]*(n+1);v=[0]*(n+1);p=[0]*(n+1);way=[0]*(n+1)
 for i in range(1,n+1):
  p[0]=i;j0=0;minimum=[10**30]*(n+1);used=[False]*(n+1)
  while True:
   used[j0]=True;i0=p[j0];delta=10**30;j1=0
   for j in range(1,n+1):
    if used[j]:continue
    current=sign*matrix[i0-1][j-1]-u[i0]-v[j]
    if current<minimum[j]:minimum[j]=current;way[j]=j0
    if minimum[j]<delta:delta=minimum[j];j1=j
   for j in range(n+1):
    if used[j]:u[p[j]]+=delta;v[j]-=delta
    else:minimum[j]-=delta
   j0=j1
   if p[j0]==0:break
  while True:
   j1=way[j0];p[j0]=p[j1];j0=j1
   if j0==0:break
 return sum(matrix[p[j]-1][j-1] for j in range(1,n+1))
print(hungarian(1));print(hungarian(-1))
