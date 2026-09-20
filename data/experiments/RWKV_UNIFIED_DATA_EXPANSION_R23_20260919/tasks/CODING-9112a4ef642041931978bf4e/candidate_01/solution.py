import sys,heapq
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];p=1;source=n;sink=n+1;adj=[[] for _ in range(n+2)];balance=[0]*n;answer=0;infinity=10**9

def add(u,w,cap,cost):
 adj[u].append([w,len(adj[w]),cap,cost]);adj[w].append([u,len(adj[u])-1,0,-cost])
for u in range(n):
 k=v[p];p+=1
 for _ in range(k):
  w,cost=v[p:p+2];p+=2;w-=1;add(u,w,infinity,cost);balance[u]-=1;balance[w]+=1;answer+=cost
for u in range(1,n):add(u,0,infinity,0)
need=0
for u,b in enumerate(balance):
 if b>0:add(source,u,b,0);need+=b
 elif b<0:add(u,sink,-b,0)
potential=[0]*(n+2)
while need:
 distance=[10**30]*(n+2);distance[source]=0;previous=[None]*(n+2);queue=[(0,source)]
 while queue:
  d,u=heapq.heappop(queue)
  if d!=distance[u]:continue
  for i,(w,rev,cap,cost) in enumerate(adj[u]):
   nd=d+cost+potential[u]-potential[w]
   if cap and nd<distance[w]:distance[w]=nd;previous[w]=(u,i);heapq.heappush(queue,(nd,w))
 for u,d in enumerate(distance):
  if d<10**30:potential[u]+=d
 amount=need;u=sink
 while u!=source:
  before,i=previous[u];amount=min(amount,adj[before][i][2]);u=before
 u=sink
 while u!=source:
  before,i=previous[u];edge=adj[before][i];answer+=amount*edge[3];edge[2]-=amount;adj[u][edge[1]][2]+=amount;u=before
 need-=amount
print(answer)
