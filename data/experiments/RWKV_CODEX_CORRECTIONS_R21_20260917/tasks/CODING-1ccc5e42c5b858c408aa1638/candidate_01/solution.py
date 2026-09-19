import sys
from collections import deque
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);m=next(it);values=[next(it) for _ in range(n)];source=n;sink=n+1;g=[[] for _ in range(n+2)]
def add(a,b,cap):g[a].append([b,cap,len(g[b])]);g[b].append([a,0,len(g[a])-1])
positive=0
for i,v in enumerate(values):
 if v>0:add(source,i,v);positive+=v
 elif v<0:add(i,sink,-v)
for _ in range(m):add(next(it)-1,next(it)-1,next(it))
flow=0
while True:
 level=[-1]*(n+2);level[source]=0;q=deque([source])
 while q:
  x=q.popleft()
  for y,cap,rev in g[x]:
   if cap and level[y]<0:level[y]=level[x]+1;q.append(y)
 if level[sink]<0:break
 current=[0]*(n+2)
 def send(x,limit):
  if x==sink:return limit
  while current[x]<len(g[x]):
   edge=g[x][current[x]];y,cap,rev=edge
   if cap and level[y]==level[x]+1:
    amount=send(y,min(limit,cap))
    if amount:edge[1]-=amount;g[y][rev][1]+=amount;return amount
   current[x]+=1
  return 0
 while True:
  amount=send(source,10**18)
  if not amount:break
  flow+=amount
print(positive-flow)
