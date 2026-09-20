import sys
from collections import deque
sys.setrecursionlimit(20000)
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);a=next(v);parents=[next(v)-1 for _ in range(a-1)];x=[next(v)-1 for _ in range(n)];b=next(v);other=[next(v)-1 for _ in range(b-1)];y=[next(v)-1 for _ in range(n)];source=a+b;sink=source+1;graph=[[] for _ in range(sink+1)];INF=a+b+1

def add(u,v,capacity):graph[u].append([v,len(graph[v]),capacity]);graph[v].append([u,len(graph[u])-1,0])
for child,parent in enumerate(parents,1):add(child,parent,INF);add(child,sink,1)
for child,parent in enumerate(other,1):add(a+parent,a+child,INF);add(source,a+child,1)
for left,right in zip(x,y):add(a+right,left,INF)
flow=0
while True:
 level=[-1]*len(graph);level[source]=0;queue=deque([source])
 while queue:
  u=queue.popleft()
  for w,rev,capacity in graph[u]:
   if capacity and level[w]<0:level[w]=level[u]+1;queue.append(w)
 if level[sink]<0:break
 current=[0]*len(graph)
 def dfs(u,amount):
  if u==sink:return amount
  while current[u]<len(graph[u]):
   edge=graph[u][current[u]];w,rev,capacity=edge
   if capacity and level[w]==level[u]+1:
    sent=dfs(w,min(amount,capacity))
    if sent:edge[2]-=sent;graph[w][rev][2]+=sent;return sent
   current[u]+=1
  return 0
 while True:
  sent=dfs(source,INF)
  if not sent:break
  flow+=sent
print(a+b-2-flow)
