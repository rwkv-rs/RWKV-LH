import sys
v=list(map(int,sys.stdin.buffer.read().split()));p=0;out=[];INF=10**30
while p<len(v):
 n,c1,c2=v[p:p+3];p+=3
 if n==c1==c2==0:break
 graph=[[] for _ in range(n)]
 for _ in range(n-1):a,b=v[p:p+2];p+=2;a-=1;b-=1;graph[a].append(b);graph[b].append(a)
 parent=[-1]*n;order=[0]
 for u in order:
  for w in graph[u]:
   if w!=parent[u]:parent[w]=u;order.append(w)
 dp=[None]*n
 for u in reversed(order):
  children=[w for w in graph[u] if parent[w]==u];result=[INF]*12
  for pb in range(2):
   for own in range(3):
    for has in range(2):
     external=bool(own or pb or has);cost=[(0,c1,c2)[own],INF]
     for w in children:
      options=[INF,INF];child=dp[w];offset=6*int(own==2)
      for kind in range(3):
       for below in range(2):
        if external or kind or below:options[int(kind==2)]=min(options[int(kind==2)],child[offset+2*kind+below])
      cost=[cost[0]+options[0],min(cost[1]+min(options),cost[0]+options[1])]
     result[6*pb+2*own+has]=cost[has]
  dp[u]=result
 out.append(str(min(dp[0][:6])))
print('\n'.join(out))
