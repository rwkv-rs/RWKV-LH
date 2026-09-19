import sys
from collections import deque
sys.setrecursionlimit(100000)
it=iter(map(int,sys.stdin.buffer.read().split()));h=next(it);w=next(it);c=next(it);n=h*w;values=[next(it) for _ in range(n)];source=n;sink=n+1;g=[[] for _ in range(n+2)];pairs=[];degree=[0]*n
for r in range(h-1):
 for col in range(w):
  x=r*w+col
  for cc in (col-1,col+1):
   if 0<=cc<w:y=(r+1)*w+cc;pairs.append((x,y));degree[x]+=1;degree[y]+=1
def add(x,y,cap):g[x].append([y,cap,len(g[y])]);g[y].append([x,0,len(g[x])-1])
positive=0
for i,a in enumerate(values):
 weight=2*a-4*c+c*degree[i]
 if weight>0:add(source,i,weight);positive+=weight
 elif weight<0:add(i,sink,-weight)
for x,y in pairs:add(x,y,c);add(y,x,c)
flow=0
while True:
 level=[-1]*(n+2);level[source]=0;queue=deque([source])
 while queue:
  x=queue.popleft()
  for y,cap,rev in g[x]:
   if cap and level[y]<0:level[y]=level[x]+1;queue.append(y)
 if level[sink]<0:break
 pointer=[0]*(n+2)
 def send(x,amount):
  if x==sink:return amount
  while pointer[x]<len(g[x]):
   edge=g[x][pointer[x]];y,cap,rev=edge
   if cap and level[y]==level[x]+1:
    pushed=send(y,min(amount,cap))
    if pushed:edge[1]-=pushed;g[y][rev][1]+=pushed;return pushed
   pointer[x]+=1
  return 0
 while True:
  pushed=send(source,10**30)
  if not pushed:break
  flow+=pushed
print((positive-flow)//2)
