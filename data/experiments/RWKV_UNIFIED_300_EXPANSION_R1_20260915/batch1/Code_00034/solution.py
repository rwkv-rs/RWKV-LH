import sys,heapq
a=iter(map(int,sys.stdin.buffer.read().split()));n,m=next(a),next(a);g=[[] for _ in range(n)];near=[]
for _ in range(m):
    u,v,w=next(a)-1,next(a)-1,next(a)
    if u==0:near.append((v,w))
    elif v==0:near.append((u,w))
    else:g[u].append((v,w));g[v].append((u,w))
inf=10**30;ans=inf
for i,(start,first) in enumerate(near):
    dist=[inf]*n;dist[start]=0;q=[(0,start)]
    while q:
        d,u=heapq.heappop(q)
        if d!=dist[u]:continue
        for v,w in g[u]:
            if d+w<dist[v]:dist[v]=d+w;heapq.heappush(q,(d+w,v))
    for v,w in near[i+1:]:ans=min(ans,first+dist[v]+w)
print(-1 if ans==inf else ans)
