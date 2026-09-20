import sys
from collections import deque
from array import array
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);k=next(v);r=next(v);N=2*n-1;g=[[] for _ in range(N)]
for middle in range(n,N):
 a=next(v)-1;b=next(v)-1;g[a].append(middle);g[b].append(middle);g[middle]=[a,b]
rest=[next(v)-1 for _ in range(r)];depth=[0]*N;parent=array('i',[0])*N;order=[0]
for u in order:
 for w in g[u]:
  if w!=parent[u]:parent[w]=u;depth[w]=depth[u]+1;order.append(w)
up=[parent]
for _ in range(N.bit_length()-1):
 p=up[-1];up.append(array('i',(p[p[i]] for i in range(N))))
def climb(u,d):
 bit=0
 while d:
  if d&1:u=up[bit][u]
  bit+=1;d>>=1
 return u
def lca(a,b):
 if depth[a]<depth[b]:a,b=b,a
 a=climb(a,depth[a]-depth[b])
 if a==b:return a
 for p in reversed(up):
  if p[a]!=p[b]:a=p[a];b=p[b]
 return parent[a]
owner=[-1]*N;distance=[-1]*N;dsu=list(range(N));size=[1]*N
for u in rest:distance[u]=0;owner[u]=u
q=deque(rest)
def find(u):
 while dsu[u]!=u:dsu[u]=dsu[dsu[u]];u=dsu[u]
 return u
def union(a,b):
 a=find(a);b=find(b)
 if a==b:return
 if size[a]<size[b]:a,b=b,a
 dsu[b]=a;size[a]+=size[b]
while q:
 u=q.popleft()
 for w in g[u]:
  if distance[w]<0:
   if distance[u]<k:distance[w]=distance[u]+1;owner[w]=owner[u];q.append(w)
  else:union(owner[u],owner[w])
output=[]
for _ in range(next(v)):
 a=next(v)-1;b=next(v)-1;c=lca(a,b);da=depth[a]-depth[c];db=depth[b]-depth[c];total=da+db
 if total<=2*k:output.append('YES');continue
 x=climb(a,k) if da>=k else climb(b,total-k)
 y=climb(b,k) if db>=k else climb(a,total-k)
 output.append('YES' if owner[x]>=0 and owner[y]>=0 and find(owner[x])==find(owner[y]) else 'NO')
print('\n'.join(output))
