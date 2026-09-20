import sys,heapq
v=list(map(int,sys.stdin.buffer.read().split()));n,b,s,r=v[:4];graph=[[] for _ in range(n)];reverse=[[] for _ in range(n)]
for i in range(r):u,w,c=v[4+3*i:7+3*i];u-=1;w-=1;graph[u].append((w,c));reverse[w].append((u,c))
def distances(g):
 d=[10**30]*n;d[b]=0;heap=[(0,b)]
 while heap:
  cost,u=heapq.heappop(heap)
  if cost!=d[u]:continue
  for w,c in g[u]:
   new=cost+c
   if new<d[w]:d[w]=new;heapq.heappush(heap,(new,w))
 return d
one=distances(graph);two=distances(reverse);values=sorted(one[i]+two[i] for i in range(b));prefix=[0]
for x in values:prefix.append(prefix[-1]+x)
INF=10**30;dp=[INF]*(b+1);dp[0]=0
for groups in range(1,s+1):
 new=[INF]*(b+1)
 def compute(left,right,lo,hi):
  if left>right:return
  mid=(left+right)//2;best=INF;arg=lo;total=prefix[mid]
  for j in range(lo,min(hi,mid-1)+1):
   cost=dp[j]+(mid-j-1)*(total-prefix[j])
   if cost<best:best=cost;arg=j
  new[mid]=best;compute(left,mid-1,lo,arg);compute(mid+1,right,arg,hi)
 compute(groups,b,groups-1,b-1);dp=new
print(dp[b])
