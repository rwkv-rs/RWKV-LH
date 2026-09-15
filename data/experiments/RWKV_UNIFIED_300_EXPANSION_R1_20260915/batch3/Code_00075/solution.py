import sys
from collections import deque
sys.setrecursionlimit(1000000)
n=int(input());grid=[input().strip() for _ in range(n)];s=n*n;t=s+1;g=[[] for _ in range(t+1)]
def add(u,v,c):
    g[u].append([v,c,len(g[v])]);g[v].append([u,0,len(g[u])-1])
inf=10**9
for i in range(n):
    for j in range(n):
        u=i*n+j;ch=grid[i][j]
        if ch!='?':
            color=(ch=='B')^((i+j)%2)
            if color:add(s,u,inf)
            else:add(u,t,inf)
        for di,dj in ((1,0),(0,1)):
            ii,jj=i+di,j+dj
            if ii<n and jj<n:v=ii*n+jj;add(u,v,1);add(v,u,1)
flow=0
while True:
    level=[-1]*len(g);level[s]=0;q=deque([s])
    while q:
        u=q.popleft()
        for v,c,r in g[u]:
            if c and level[v]<0:level[v]=level[u]+1;q.append(v)
    if level[t]<0:break
    it=[0]*len(g)
    def dfs(u,f):
        if u==t:return f
        while it[u]<len(g[u]):
            e=g[u][it[u]];v,c,r=e
            if c and level[v]==level[u]+1:
                sent=dfs(v,min(f,c))
                if sent:e[1]-=sent;g[v][r][1]+=sent;return sent
            it[u]+=1
        return 0
    while True:
        sent=dfs(s,inf)
        if not sent:break
        flow+=sent
print(2*n*(n-1)-flow)
