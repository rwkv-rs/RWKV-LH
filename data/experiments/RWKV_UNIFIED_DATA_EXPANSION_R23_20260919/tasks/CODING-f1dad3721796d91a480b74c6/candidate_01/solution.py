import sys
from collections import deque
sys.setrecursionlimit(10000)
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];points=[tuple(v[1+3*i:4+3*i]) for i in range(n)];index={(x,y):i for i,(x,y,w) in enumerate(points)};source=2*n;sink=source+1;graph=[[] for _ in range(sink+1)];total=sum(w for x,y,w in points);INF=total+1
class Edge:
 __slots__=('to','cap','reverse')
 def __init__(self,to,cap,reverse):self.to=to;self.cap=cap;self.reverse=reverse
def add(a,b,cap):
 forward=Edge(b,cap,None);backward=Edge(a,0,forward);forward.reverse=backward;graph[a].append(forward);graph[b].append(backward)
for i,(x,y,w) in enumerate(points):
 add(2*i,2*i+1,w)
 if x%2 and y%2:add(2*i+1,sink,INF);continue
 if x%2:add(source,2*i,INF);neighbors=((x-1,y),(x+1,y))
 elif y%2:neighbors=((x-1,y),(x+1,y))
 else:neighbors=((x,y-1),(x,y+1))
 for coordinate in neighbors:
  if coordinate in index:add(2*i+1,2*index[coordinate],INF)
flow=0
while True:
 level=[-1]*len(graph);level[source]=0;queue=deque([source])
 while queue:
  u=queue.popleft()
  for e in graph[u]:
   if e.cap and level[e.to]<0:level[e.to]=level[u]+1;queue.append(e.to)
 if level[sink]<0:break
 at=[0]*len(graph)
 def send(u,bound):
  if u==sink:return bound
  while at[u]<len(graph[u]):
   e=graph[u][at[u]]
   if e.cap and level[e.to]==level[u]+1:
    sent=send(e.to,min(bound,e.cap))
    if sent:e.cap-=sent;e.reverse.cap+=sent;return sent
   at[u]+=1
  return 0
 while True:
  sent=send(source,INF)
  if not sent:break
  flow+=sent
print(total-flow)
