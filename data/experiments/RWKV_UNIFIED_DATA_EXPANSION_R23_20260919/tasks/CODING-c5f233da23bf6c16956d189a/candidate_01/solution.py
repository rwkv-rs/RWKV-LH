import sys,heapq
from array import array
it=iter(map(int,sys.stdin.buffer.read().split()));n,m=next(it),next(it);g=[[] for _ in range(n)];tree=[[] for _ in range(n)];dsu=list(range(n));special=set()
def find(x):
 while dsu[x]!=x:dsu[x]=dsu[dsu[x]];x=dsu[x]
 return x
for _ in range(m):
 u,v,w=next(it)-1,next(it)-1,next(it);g[u].append((v,w));g[v].append((u,w));a,b=find(u),find(v)
 if a!=b:dsu[a]=b;tree[u].append((v,w));tree[v].append((u,w))
 else:special.add(u)
parent=array('i',[-1])*n;depth=array('i',[0])*n;distance=[0]*n;parent[0]=0;order=[0]
for u in order:
 for v,w in tree[u]:
  if v!=parent[u]:parent[v]=u;depth[v]=depth[u]+1;distance[v]=distance[u]+w;order.append(v)
up=[parent]
for _ in range(n.bit_length()):old=up[-1];up.append(array('i',(old[old[i]] for i in range(n))))
def lca(a,b):
 if depth[a]<depth[b]:a,b=b,a
 delta=depth[a]-depth[b];k=0
 while delta:
  if delta&1:a=up[k][a]
  delta>>=1;k+=1
 if a==b:return a
 for row in reversed(up):
  if row[a]!=row[b]:a,b=row[a],row[b]
 return parent[a]
q=next(it);queries=[(next(it)-1,next(it)-1) for _ in range(q)];answer=[distance[a]+distance[b]-2*distance[lca(a,b)] for a,b in queries]
for s in special:
 dist=[10**30]*n;dist[s]=0;heap=[(0,s)]
 while heap:
  d,u=heapq.heappop(heap)
  if d!=dist[u]:continue
  for v,w in g[u]:
   z=d+w
   if z<dist[v]:dist[v]=z;heapq.heappush(heap,(z,v))
 for i,(a,b) in enumerate(queries):answer[i]=min(answer[i],dist[a]+dist[b])
print('\n'.join(map(str,answer)))
