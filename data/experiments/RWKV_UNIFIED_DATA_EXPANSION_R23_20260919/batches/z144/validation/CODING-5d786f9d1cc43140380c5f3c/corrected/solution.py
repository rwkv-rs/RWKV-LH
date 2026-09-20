import sys,heapq
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);source=n;sink=n+1;graph=[[] for _ in range(n+2)];balance=[0]*n;cost=0;INF=10**18

def add(u,v,capacity,c):
 graph[u].append([v,len(graph[v]),capacity,c]);graph[v].append([u,len(graph[u])-1,0,-c])
for u in range(n):
 k=next(v)
 for _ in range(k):
  w=next(v)-1;c=next(v);add(u,w,1000000000,c);balance[u]-=1;balance[w]+=1;cost+=c
for u in range(1,n):add(u,0,1000000000,0)
required=0
for u,b in enumerate(balance):
 if b>0:add(source,u,b,0);required+=b
 elif b<0:add(u,sink,-b,0)
potential=[0]*(n+2)
while required:
 distance=[INF]*(n+2);distance[source]=0;parent=[None]*(n+2);heap=[(0,source)]
 while heap:
  d,u=heapq.heappop(heap)
  if d!=distance[u]:continue
  for i,(w,rev,capacity,c) in enumerate(graph[u]):
   if capacity:
    nd=d+c+potential[u]-potential[w]
    if nd<distance[w]:distance[w]=nd;parent[w]=(u,i);heapq.heappush(heap,(nd,w))
 for u,d in enumerate(distance):
  if d<INF:potential[u]+=d
 amount=required;u=sink
 while u!=source:
  a,i=parent[u];amount=min(amount,graph[a][i][2]);u=a
 u=sink
 while u!=source:
  a,i=parent[u];edge=graph[a][i];edge[2]-=amount;graph[u][edge[1]][2]+=amount;cost+=amount*edge[3];u=a
 required-=amount
print(cost)
