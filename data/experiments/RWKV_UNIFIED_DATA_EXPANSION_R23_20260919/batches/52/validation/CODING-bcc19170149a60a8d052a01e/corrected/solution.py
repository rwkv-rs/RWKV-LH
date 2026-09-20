import sys,heapq
it=iter(map(int,sys.stdin.buffer.read().split()));L,R=next(it),next(it);A=[next(it) for _ in range(L)];B=[next(it) for _ in range(R)];C=[[next(it) for _ in range(R)] for _ in range(L)];N=L+R+2;s=N-2;t=N-1;g=[[] for _ in range(N)]
def edge(u,v,cap,cost):g[u].append([v,len(g[v]),cap,cost]);g[v].append([u,len(g[u])-1,0,-cost])
for i,a in enumerate(A):edge(s,i,a,0)
for j,b in enumerate(B):edge(L+j,t,b,0)
for i in range(L):
 for j in range(R):edge(i,L+j,10000,-C[i][j])
potential=[0]*N
for j in range(R):potential[L+j]=-max(C[i][j] for i in range(L))
potential[t]=min(potential[L:L+R]);answer=0
while True:
 dist=[10**30]*N;dist[s]=0;parent=[None]*N;heap=[(0,s)]
 while heap:
  d,u=heapq.heappop(heap)
  if d!=dist[u]:continue
  for k,(v,rev,cap,cost) in enumerate(g[u]):
   z=d+cost+potential[u]-potential[v]
   if cap and z<dist[v]:dist[v]=z;parent[v]=(u,k);heapq.heappush(heap,(z,v))
 if parent[t] is None:break
 cost=dist[t]+potential[t]-potential[s]
 if cost>=0:break
 for u in range(N):
  if dist[u]<10**30:potential[u]+=dist[u]
 flow=10000;v=t
 while v!=s:u,k=parent[v];flow=min(flow,g[u][k][2]);v=u
 answer-=cost*flow;v=t
 while v!=s:u,k=parent[v];e=g[u][k];e[2]-=flow;g[v][e[1]][2]+=flow;v=u
print(answer)
