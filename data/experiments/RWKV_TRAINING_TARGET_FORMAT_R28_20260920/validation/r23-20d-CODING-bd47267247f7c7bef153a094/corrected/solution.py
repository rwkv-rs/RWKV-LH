import sys
from collections import deque
sys.setrecursionlimit(10000)
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);m=next(v);source=n+m;sink=source+1;g=[[] for _ in range(sink+1)]
def edge(a,b,c):g[a].append([b,c,len(g[b])]);g[b].append([a,0,len(g[a])-1])
total=0
for i in range(n):
 income=next(v);t=next(v);total+=income;edge(source,i,income)
 for _ in range(t):machine=next(v)-1;rent=next(v);edge(i,n+machine,rent)
for j in range(m):edge(n+j,sink,next(v))
flow=0
while True:
 level=[-1]*len(g);level[source]=0;q=deque([source])
 while q:
  a=q.popleft()
  for b,c,r in g[a]:
   if c and level[b]<0:level[b]=level[a]+1;q.append(b)
 if level[sink]<0:break
 it=[0]*len(g)
 def dfs(a,pushed):
  if a==sink:return pushed
  while it[a]<len(g[a]):
   e=g[a][it[a]];b,c,r=e
   if c and level[b]==level[a]+1:
    sent=dfs(b,min(pushed,c))
    if sent:e[1]-=sent;g[b][r][1]+=sent;return sent
   it[a]+=1
  return 0
 while True:
  sent=dfs(source,10**30)
  if not sent:break
  flow+=sent
print(total-flow)
