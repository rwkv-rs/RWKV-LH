import sys,heapq
v=list(map(int,sys.stdin.buffer.read().split()));n,m,s,t=v[:4];d=v[4:4+n];edges=[[] for _ in range(n)];s-=1;t-=1
for i in range(n-1):edges[i+1].append((i,0))
for i in range(m):a,b=v[4+n+2*i:6+n+2*i];edges[a-1].append((b-1,d[b-1] if b>a else 0))
dist=[float('inf')]*n;dist[s]=0;heap=[(0,s)]
while heap:
 cost,u=heapq.heappop(heap)
 if cost!=dist[u]:continue
 if u==t:print(cost);break
 for w,price in edges[u]:
  new=cost+price
  if new<dist[w]:dist[w]=new;heapq.heappush(heap,(new,w))
