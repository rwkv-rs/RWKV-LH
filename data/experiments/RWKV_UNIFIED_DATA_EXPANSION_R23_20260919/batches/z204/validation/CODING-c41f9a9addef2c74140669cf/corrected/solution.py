import sys,math
from collections import deque
a,b=map(int,sys.stdin.buffer.read().split());numbers=list(range(a,b+1));n=len(numbers);edges=[];adj=[[] for _ in numbers]
for i,x in enumerate(numbers):
 for j in range(i):
  y=numbers[j];z=math.isqrt(x*x-y*y)
  if z*z==x*x-y*y and math.gcd(y,z)==1:edges.append((i,j));adj[i].append(j);adj[j].append(i)
colour=[-1]*n
for i in range(n):
 if colour[i]>=0:continue
 colour[i]=0;todo=[i]
 for u in todo:
  for v in adj[u]:
   if colour[v]<0:colour[v]=colour[u]^1;todo.append(v)
source=n;sink=n+1;graph=[[] for _ in range(n+2)]
def add(u,v,cost):
 graph[u].append([v,1,cost,len(graph[v])]);graph[v].append([u,0,-cost,len(graph[u])-1])
for i in range(n):
 if colour[i]==0:add(source,i,0)
 else:add(i,sink,0)
for i,j in edges:
 if colour[i]==1:i,j=j,i
 assert colour[i]==0 and colour[j]==1
 add(i,j,-numbers[i]-numbers[j])
flow=0;cost=0
while True:
 dist=[10**18]*(n+2);dist[source]=0;parent=[None]*(n+2);queue=deque([source]);inside=[False]*(n+2);inside[source]=True
 while queue:
  u=queue.popleft();inside[u]=False
  for i,e in enumerate(graph[u]):
   v,capacity,weight,_=e
   if capacity and dist[u]+weight<dist[v]:
    dist[v]=dist[u]+weight;parent[v]=(u,i)
    if not inside[v]:queue.append(v);inside[v]=True
 if parent[sink] is None:break
 flow+=1;cost+=dist[sink];v=sink
 while v!=source:
  u,i=parent[v];e=graph[u][i];e[1]-=1;graph[v][e[3]][1]+=1;v=u
print(flow,-cost)
