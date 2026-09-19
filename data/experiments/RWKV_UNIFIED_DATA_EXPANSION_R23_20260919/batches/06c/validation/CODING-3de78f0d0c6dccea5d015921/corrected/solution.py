import sys,heapq
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(it)):
 n=next(it);m=next(it);g=[[] for _ in range(n)]
 for _ in range(m):
  x=next(it)-1;y=next(it)-1;c=next(it);g[x].append((y,c));g[y].append((x,c))
 s=next(it)-1;a=next(it)-1;h=next(it)-1
 def distances(start):
  d=[10**30]*n;d[start]=0;q=[(0,start)]
  while q:
   cost,x=heapq.heappop(q)
   if cost!=d[x]:continue
   for y,c in g[x]:
    z=cost+c
    if z<d[y]:d[y]=z;heapq.heappush(q,(z,y))
  return d
 ds=distances(s);da=distances(a);dh=distances(h);out.append(str(max(ds[x]+2*da[x]+dh[x] for x in range(n) if x not in {s,a,h})))
print('\n'.join(out))
