import sys
sys.setrecursionlimit(10000)
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);a=[[0]*(n+1)]+[[0]+[-next(it) for _ in range(n)] for _ in range(n)];u=[0]*(n+1);v=[0]*(n+1);p=[0]*(n+1);way=[0]*(n+1)
for i in range(1,n+1):
 p[0]=i;j0=0;dist=[10**30]*(n+1);used=[False]*(n+1)
 while True:
  used[j0]=True;i0=p[j0];delta=10**30;j1=0
  for j in range(1,n+1):
   if not used[j]:
    cur=a[i0][j]-u[i0]-v[j]
    if cur<dist[j]:dist[j]=cur;way[j]=j0
    if dist[j]<delta:delta=dist[j];j1=j
  for j in range(n+1):
   if used[j]:u[p[j]]+=delta;v[j]-=delta
   else:dist[j]-=delta
  j0=j1
  if not p[j0]:break
 while j0:j1=way[j0];p[j0]=p[j1];j0=j1
match=[0]*(n+1)
for j in range(1,n+1):match[p[j]]=j
reach=[0]*(n+1)
for i in range(1,n+1):
 for j in range(1,n+1):
  if j!=match[i] and a[i][j]==u[i]+v[j]:reach[i]|=1<<p[j]
for k in range(1,n+1):
 for i in range(1,n+1):
  if reach[i]>>k&1:reach[i]|=reach[k]
print(-sum(a[i][match[i]] for i in range(1,n+1)))
for i in range(1,n+1):
 if not (reach[i]>>i&1):print(i,match[i])
