import sys
from collections import deque
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for case in range(1,next(it)+1):
 m=next(it);storage=next(it);data=[tuple(next(it) for _ in range(5)) for _ in range(m)];source=2*m;sink=source+1;size=sink+1;g=[[] for _ in range(size)]
 def add(x,y,capacity,cost):g[x].append([y,capacity,cost,len(g[y])]);g[y].append([x,0,-cost,len(g[x])-1])
 for i,(cost,capacity,price,sales,life) in enumerate(data):
  add(source,i,capacity,0);add(m+i,sink,sales,0)
  for j in range(i,min(m,i+life+1)):add(i,m+j,capacity,cost+(j-i)*storage-data[j][2])
 profit=0
 while True:
  d=[10**30]*size;d[source]=0;parent=[None]*size;inside=[False]*size;inside[source]=True;q=deque([source])
  while q:
   x=q.popleft();inside[x]=False
   for index,(y,capacity,cost,rev) in enumerate(g[x]):
    if capacity and d[x]+cost<d[y]:
     d[y]=d[x]+cost;parent[y]=(x,index)
     if not inside[y]:inside[y]=True;q.append(y)
  if d[sink]>=0:break
  amount=10**30;y=sink
  while y!=source:x,index=parent[y];amount=min(amount,g[x][index][1]);y=x
  y=sink
  while y!=source:x,index=parent[y];edge=g[x][index];edge[1]-=amount;g[y][edge[3]][1]+=amount;y=x
  profit-=amount*d[sink]
 out.append('Case '+str(case)+': '+str(profit))
print('\n'.join(out))
