import sys,heapq
it=iter(map(int,sys.stdin.buffer.read().split()));n,q,s=next(it),next(it),next(it)-1
size=1
while size<n:size*=2
g=[[] for _ in range(4*size)];offset=2*size
for p in range(1,size):
 for c in (p*2,p*2+1):g[p].append((c,0));g[c+offset].append((p+offset,0))
for i in range(n):g[size+i].append((size+i+offset,0));g[size+i+offset].append((size+i,0))
for _ in range(q):
 t,v=next(it),next(it)-1
 if t==1:u,w=next(it)-1,next(it);g[size+v].append((size+u,w));continue
 l,r,w=next(it)-1,next(it),next(it);l+=size;r+=size
 while l<r:
  if l&1:
   if t==2:g[size+v].append((l,w))
   else:g[l+offset].append((size+v,w))
   l+=1
  if r&1:
   r-=1
   if t==2:g[size+v].append((r,w))
   else:g[r+offset].append((size+v,w))
  l//=2;r//=2
inf=10**30;dist=[inf]*len(g);dist[size+s]=0;heap=[(0,size+s)]
while heap:
 d,u=heapq.heappop(heap)
 if d!=dist[u]:continue
 for v,w in g[u]:
  z=d+w
  if z<dist[v]:dist[v]=z;heapq.heappush(heap,(z,v))
print(*[dist[size+i] if dist[size+i]<inf else -1 for i in range(n)])
