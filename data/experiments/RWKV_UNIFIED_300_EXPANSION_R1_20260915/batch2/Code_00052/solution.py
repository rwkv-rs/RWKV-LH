import sys,heapq
a=iter(map(int,sys.stdin.buffer.read().split()));n,m,s=next(a),next(a),next(a);g=[[] for _ in range(n)];mx=0
for _ in range(m):
    u,v,c,t=next(a)-1,next(a)-1,next(a),next(a);mx=max(mx,c);g[u].append((v,c,t));g[v].append((u,c,t))
exchange=[(next(a),next(a)) for _ in range(n)];cap=mx*(n-1);s=min(s,cap);inf=10**30;d=[[inf]*(cap+1) for _ in range(n)];d[0][s]=0;q=[(0,0,s)]
while q:
    t,u,coins=heapq.heappop(q)
    if t!=d[u][coins]:continue
    amount,elapsed=exchange[u];more=min(cap,coins+amount)
    if t+elapsed<d[u][more]:d[u][more]=t+elapsed;heapq.heappush(q,(t+elapsed,u,more))
    for v,c,w in g[u]:
        if coins>=c and t+w<d[v][coins-c]:d[v][coins-c]=t+w;heapq.heappush(q,(t+w,v,coins-c))
for row in d[1:]:print(min(row))
