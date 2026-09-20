import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,k=v[:2];k=min(n,k);p=2;costs=[]
for i in range(n):costs.append(v[p:p+n-i]);p+=n-i
columns=n+k;INF=10**100;cost=[[INF]*(columns+1) for _ in range(n+1)]
for job in range(1,n+1):
 for slot in range(1,k+1):cost[job][slot]=costs[0][job-1]
 for previous in range(1,job):cost[job][k+previous]=costs[previous][job-previous-1]
u=[0]*(n+1);pot=[0]*(columns+1);matching=[0]*(columns+1);way=[0]*(columns+1)
for row in range(1,n+1):
 matching[0]=row;j0=0;minimum=[INF]*(columns+1);used=[False]*(columns+1)
 while True:
  used[j0]=True;i0=matching[j0];delta=INF;j1=0
  for j in range(1,columns+1):
   if not used[j]:
    value=cost[i0][j]-u[i0]-pot[j]
    if value<minimum[j]:minimum[j]=value;way[j]=j0
    if minimum[j]<delta:delta=minimum[j];j1=j
  for j in range(columns+1):
   if used[j]:u[matching[j]]+=delta;pot[j]-=delta
   else:minimum[j]-=delta
  j0=j1
  if matching[j0]==0:break
 while j0:previous=way[j0];matching[j0]=matching[previous];j0=previous
print(sum(cost[matching[j]][j] for j in range(1,columns+1) if matching[j]))
