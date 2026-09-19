import sys
from collections import deque
sys.setrecursionlimit(10000)
v=iter(sys.stdin.read().split());out=[]
for _ in range(int(next(v))):
 n=int(next(v));distance=float(next(v));floes=[tuple(int(next(v)) for j in range(4)) for i in range(n)];total=sum(x[2] for x in floes);source=2*n;arcs=[]
 for i,(x,y,count,limit) in enumerate(floes):
  arcs.append((source,2*i,count));arcs.append((2*i,2*i+1,limit))
  for j,(xx,yy,_,__) in enumerate(floes):
   if i!=j and (x-xx)**2+(y-yy)**2<=distance*distance+1e-9:arcs.append((2*i+1,2*j,total))
 answer=[]
 for target in range(n):
  sink=2*target;g=[[] for _ in range(source+1)]
  for a,b,c in arcs:g[a].append([b,c,len(g[b])]);g[b].append([a,0,len(g[a])-1])
  flow=0
  while flow<total:
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
      sent=dfs(b,min(c,pushed))
      if sent:e[1]-=sent;g[b][r][1]+=sent;return sent
     it[a]+=1
    return 0
   while flow<total:
    sent=dfs(source,total-flow)
    if not sent:break
    flow+=sent
  if flow==total:answer.append(str(target))
 out.append(' '.join(answer) if answer else '-1')
print('\n'.join(out))
