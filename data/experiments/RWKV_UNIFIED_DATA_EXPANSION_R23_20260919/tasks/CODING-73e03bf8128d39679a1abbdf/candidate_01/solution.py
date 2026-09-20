import sys,heapq
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for n in it:
 m,c=next(it),next(it)
 if n==m==c==0:break
 adj=[[] for _ in range(n)];edges=[]
 for _ in range(m):
  u,v,w=next(it)-1,next(it)-1,next(it);adj[u].append((v,w));edges.append((u,v))
 inf=10**30;dist=[inf]*n;dist[0]=0
 def relax(dist):
  heap=[(d,i) for i,d in enumerate(dist) if d<inf];heapq.heapify(heap)
  while heap:
   d,u=heapq.heappop(heap)
   if dist[u]!=d:continue
   for v,w in adj[u]:
    nd=d+w
    if nd<dist[v]:dist[v]=nd;heapq.heappush(heap,(nd,v))
  return dist
 dist=relax(dist);changes=0
 while dist[-1]>c:
  nxt=dist.copy()
  for u,v in edges:
   if dist[u]<nxt[v]:nxt[v]=dist[u]
  dist=relax(nxt);changes+=1
 out.append(str(changes))
print('\n'.join(out))
