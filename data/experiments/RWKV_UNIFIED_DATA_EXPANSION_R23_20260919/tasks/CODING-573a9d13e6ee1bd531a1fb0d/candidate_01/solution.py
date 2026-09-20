import sys
from collections import deque
sys.setrecursionlimit(10000)
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);B=[[next(it) for _ in range(n)] for _ in range(n)];C=[next(it) for _ in range(n)];source=n;sink=n+1;g=[[] for _ in range(n+2)]
def edge(u,v,c,d=0):g[u].append([v,len(g[v]),c]);g[v].append([u,len(g[u])-1,d])
weights=[2*(B[i][i]-C[i]) for i in range(n)]
for i in range(n):
 for j in range(i+1,n):
  w=B[i][j]+B[j][i]
  if w:weights[i]+=w;weights[j]+=w;edge(i,j,w,w)
total=0
for i,w in enumerate(weights):
 if w>0:edge(source,i,w);total+=w
 elif w<0:edge(i,sink,-w)
flow=0
while True:
 level=[-1]*(n+2);level[source]=0;q=deque([source])
 while q:
  u=q.popleft()
  for v,rev,c in g[u]:
   if c and level[v]<0:level[v]=level[u]+1;q.append(v)
 if level[sink]<0:break
 index=[0]*(n+2)
 def send(u,f):
  if u==sink:return f
  while index[u]<len(g[u]):
   e=g[u][index[u]];v,rev,c=e
   if c and level[v]==level[u]+1:
    z=send(v,min(f,c))
    if z:e[2]-=z;g[v][rev][2]+=z;return z
   index[u]+=1
  return 0
 while True:
  z=send(source,10**30)
  if not z:break
  flow+=z
print((total-flow)//2)
