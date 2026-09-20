import sys
v=list(map(int,sys.stdin.buffer.read().split()));p=0;out=[];INF=10**100
while p<len(v):
 n=v[p];p+=1
 if n==0:break
 cost=[[INF]*(n+1) for _ in range(n+1)]
 for i in range(1,n+1):
  while v[p]!=0:
   j,w=v[p:p+2];p+=2
   if i!=j:cost[i][j]=min(cost[i][j],w)
  p+=1
 u=[0]*(n+1);pot=[0]*(n+1);matching=[0]*(n+1);way=[0]*(n+1);possible=True
 for i in range(1,n+1):
  matching[0]=i;j0=0;minimum=[INF]*(n+1);used=[False]*(n+1)
  while True:
   used[j0]=True;i0=matching[j0];delta=INF;j1=0
   for j in range(1,n+1):
    if not used[j]:
     value=cost[i0][j]-u[i0]-pot[j]
     if value<minimum[j]:minimum[j]=value;way[j]=j0
     if minimum[j]<delta:delta=minimum[j];j1=j
   if delta>=INF//2:possible=False;break
   for j in range(n+1):
    if used[j]:u[matching[j]]+=delta;pot[j]-=delta
    else:minimum[j]-=delta
   j0=j1
   if matching[j0]==0:break
  if not possible:break
  while j0:
   previous=way[j0];matching[j0]=matching[previous];j0=previous
 out.append(str(sum(cost[matching[j]][j] for j in range(1,n+1))) if possible else 'N')
print('\n'.join(out))
