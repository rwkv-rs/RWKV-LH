import sys,heapq
from collections import deque
sys.setrecursionlimit(1000000)
v=list(map(int,sys.stdin.buffer.read().split()));n,m=v[:2];cells=v[2:];graph=[[],[]];source=0;sink=1;ports=[];demand=[0,0];offset=0

def node():graph.append([]);return len(graph)-1
def add(u,v,capacity,cost):graph[u].append([v,len(graph[v]),capacity,cost]);graph[v].append([u,len(graph[u])-1,0,-cost])
for i,mask in enumerate(cells):
 color=(i//m+i%m)&1;count=mask.bit_count();mapping=[None]*4;groups=[]
 if count==2 and mask not in (5,10):
  groups=[node(),node()]
  for d in range(4):mapping[d]=(groups[d%2],0 if mask>>d&1 else 1)
  quotas=[1,1]
 elif count:
  groups=[node()];quotas=[count]
  if count==1:original=(mask&-mask).bit_length()-1
  if count==3:original=((15^mask)&-(15^mask)).bit_length()-1;offset+=2
  for d in range(4):
   if count==2 and not (mask>>d&1):continue
   distance=min((d-original)%4,(original-d)%4) if count in (1,3) else 0
   cost=distance if count==1 else 2-distance if count==3 else 0;mapping[d]=(groups[0],cost)
 for group,quota in zip(groups,quotas if groups else []):
  if color:add(group,sink,quota,0)
  else:add(source,group,quota,0)
  demand[color]+=quota
 ports.append(mapping)
if demand[0]!=demand[1]:print(-1);raise SystemExit
for i in range(n*m):
 r,c=divmod(i,m)
 if (r+c)&1:continue
 for d,(dr,dc) in enumerate([(-1,0),(0,1),(1,0),(0,-1)]):
  rr=r+dr;cc=c+dc
  if 0<=rr<n and 0<=cc<m and ports[i][d] is not None and ports[rr*m+cc][d^2] is not None:
   a,cost=ports[i][d];b,other=ports[rr*m+cc][d^2];add(a,b,1,cost+other)
size=len(graph);potential=[0]*size;flow=cost=0;INF=10**18
while flow<demand[0]:
 distance=[INF]*size;distance[source]=0;heap=[(0,source)]
 while heap:
  dist,u=heapq.heappop(heap)
  if dist!=distance[u]:continue
  for w,rev,capacity,c in graph[u]:
   if capacity:
    nd=dist+c+potential[u]-potential[w]
    if nd<distance[w]:distance[w]=nd;heapq.heappush(heap,(nd,w))
 if distance[sink]==INF:print(-1);raise SystemExit
 for u,d in enumerate(distance):
  if d<INF:potential[u]+=d
 while True:
  level=[-1]*size;level[source]=0;queue=deque([source])
  while queue:
   u=queue.popleft()
   for w,rev,capacity,c in graph[u]:
    if capacity and level[w]<0 and c+potential[u]-potential[w]==0:level[w]=level[u]+1;queue.append(w)
  if level[sink]<0:break
  current=[0]*size
  def dfs(u,amount):
   if u==sink:return amount
   while current[u]<len(graph[u]):
    edge=graph[u][current[u]];w,rev,capacity,c=edge
    if capacity and level[w]==level[u]+1 and c+potential[u]-potential[w]==0:
     sent=dfs(w,min(amount,capacity))
     if sent:edge[2]-=sent;graph[w][rev][2]+=sent;return sent
    current[u]+=1
   return 0
  while True:
   sent=dfs(source,demand[0]-flow)
   if not sent:break
   flow+=sent;cost+=sent*(potential[sink]-potential[source])
print(cost-offset)
