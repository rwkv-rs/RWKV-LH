import sys,heapq
words=iter(sys.stdin.buffer.read().split());out=[]
for token in words:
 h=int(token)
 if h==0:break
 radius=h-1;coords=[];kind=[]
 for r in range(-radius,radius+1):
  for q in range(max(-radius,-r-radius),min(radius,-r+radius)+1):coords.append((q,r));kind.append(next(words).decode())
 ids={p:i for i,p in enumerate(coords)};size=len(coords);cost=[int(x=='.') for x in kind];adj=[]
 for q,r in coords:adj.append([ids[p] for p in ((q-1,r),(q+1,r),(q,r-1),(q,r+1),(q-1,r+1),(q+1,r-1)) if p in ids])
 inf=10**9;dp=[[inf]*size for _ in range(16)]
 for i,c in enumerate(kind):
  if c!='.':dp[1<<(ord(c)-65)][i]=0
 for mask in range(1,16):
  dist=dp[mask];sub=(mask-1)&mask
  while sub:
   other=mask^sub
   if sub<other:
    a,b=dp[sub],dp[other]
    for i in range(size):
     value=a[i]+b[i]-cost[i]
     if value<dist[i]:dist[i]=value
   sub=(sub-1)&mask
  heap=[(d,i) for i,d in enumerate(dist) if d<inf];heapq.heapify(heap)
  while heap:
   d,u=heapq.heappop(heap)
   if d!=dist[u]:continue
   for v in adj[u]:
    nd=d+cost[v]
    if nd<dist[v]:dist[v]=nd;heapq.heappush(heap,(nd,v))
 out.append('You have to buy '+str(min(dp[15]))+' parcels.')
print('\n'.join(out))
