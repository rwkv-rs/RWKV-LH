import sys,heapq,bisect
v=iter(map(int,sys.stdin.read().split()));n=next(v);m=next(v);start=next(v)-1;end=next(v)-1;limit=next(v);g=[[] for _ in range(n)]
for _ in range(m):
 a=next(v)-1;b=next(v)-1;t=next(v);g[a].append((b,t))
s=next(v);special=list(dict.fromkeys([start,end]+[next(v)-1 for _ in range(s)]));index={x:i for i,x in enumerate(special)};count=len(special);matrix=[];candidates=set();inf=10**40
for root in special:
 dist=[inf]*n;dist[root]=0;queue=[(0,root)]
 while queue:
  d,a=heapq.heappop(queue)
  if d!=dist[a]:continue
  for b,t in g[a]:
   nd=d+t
   if nd<dist[b] and nd<=limit:dist[b]=nd;heapq.heappush(queue,(nd,b))
 row=[dist[x] for x in special];matrix.append(row);candidates.update(d for d in row if d<=limit)
def feasible(bound):
 dist=[inf]*count;dist[index[start]]=0;queue=[(0,index[start])]
 while queue:
  d,a=heapq.heappop(queue)
  if d!=dist[a]:continue
  if a==index[end]:return d<=limit
  for b,t in enumerate(matrix[a]):
   nd=d+t
   if t<=bound and nd<dist[b] and nd<=limit:dist[b]=nd;heapq.heappush(queue,(nd,b))
 return False
values=sorted(candidates);lo=0;hi=len(values)
while lo<hi:
 mid=(lo+hi)//2
 if feasible(values[mid]):hi=mid
 else:lo=mid+1
print(values[lo] if lo<len(values) else -1)
