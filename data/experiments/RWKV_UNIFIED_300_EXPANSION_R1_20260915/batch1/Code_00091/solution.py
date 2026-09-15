import sys
from collections import deque
a=iter(map(int,sys.stdin.buffer.read().split()));n,m=next(a),next(a);g=[[] for _ in range(n)]
for _ in range(m):
    u,v=next(a)-1,next(a)-1;g[u].append(v);g[v].append(u)
k=next(a);c=[next(a)-1 for _ in range(k)];ds=[]
for s in c:
    d=[-1]*n;d[s]=0;q=deque([s])
    while q:
        u=q.popleft()
        for v in g[u]:
            if d[v]<0:d[v]=d[u]+1;q.append(v)
    if any(d[v]<0 for v in c):print(-1);raise SystemExit
    ds.append([d[v] for v in c])
inf=10**9;dp=[[inf]*k for _ in range(1<<k)]
for i in range(k):dp[1<<i][i]=1
for mask in range(1,1<<k):
    left=((1<<k)-1)^mask
    for i,v in enumerate(dp[mask]):
        if v==inf:continue
        bits=left
        while bits:
            b=bits&-bits;j=b.bit_length()-1;bits-=b
            nxt=mask|b;cost=v+ds[i][j]
            if cost<dp[nxt][j]:dp[nxt][j]=cost
print(min(dp[-1]))
