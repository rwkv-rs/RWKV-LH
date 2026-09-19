import sys
from collections import deque
v=iter(map(int,sys.stdin.read().split()));m=next(v);n=next(v);supply=[next(v) for _ in range(m)];demand=[next(v) for _ in range(n)];cost=[[next(v) for _ in range(n)] for _ in range(m)];total=sum(supply)
def solve(sign):
 source=m+n;sink=source+1;g=[[] for _ in range(sink+1)]
 def edge(a,b,cap,c):g[a].append([b,cap,c,len(g[b])]);g[b].append([a,0,-c,len(g[a])-1])
 for i,x in enumerate(supply):edge(source,i,x,0)
 for j,x in enumerate(demand):edge(m+j,sink,x,0)
 for i in range(m):
  for j in range(n):edge(i,m+j,total,sign*cost[i][j])
 answer=0;sent=0;inf=10**40
 while sent<total:
  dist=[inf]*len(g);dist[source]=0;parent=[None]*len(g);active=[False]*len(g);active[source]=True;q=deque([source])
  while q:
   a=q.popleft();active[a]=False
   for index,(b,cap,c,rev) in enumerate(g[a]):
    if cap and dist[b]>dist[a]+c:
     dist[b]=dist[a]+c;parent[b]=(a,index)
     if not active[b]:active[b]=True;q.append(b)
  amount=total-sent;b=sink
  while b!=source:a,index=parent[b];amount=min(amount,g[a][index][1]);b=a
  b=sink
  while b!=source:
   a,index=parent[b];e=g[a][index];e[1]-=amount;g[b][e[3]][1]+=amount;b=a
  sent+=amount;answer+=amount*dist[sink]
 return sign*answer
print(solve(1));print(solve(-1))
