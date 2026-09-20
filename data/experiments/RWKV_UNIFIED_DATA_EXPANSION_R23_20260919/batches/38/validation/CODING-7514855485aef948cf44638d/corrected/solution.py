import sys
it=iter(sys.stdin.buffer.read().split());n,m=int(next(it)),int(next(it));adj=[[] for _ in range(n)]
for _ in range(n-1):
 u,v=int(next(it))-1,int(next(it))-1;adj[u].append(v);adj[v].append(u)
parent=[-1]*n;depth=[0]*n;order=[];stack=[0]
while stack:
 u=stack.pop();order.append(u)
 for v in adj[u]:
  if v!=parent[u]:parent[v]=u;depth[v]=depth[u]+1;stack.append(v)
size=[1]*n;heavy=[-1]*n;tin=[0]*n
for i,u in enumerate(order):tin[u]=i+1
for u in reversed(order):
 p=parent[u]
 if p>=0:
  size[p]+=size[u]
  if heavy[p]<0 or size[u]>size[heavy[p]]:heavy[p]=u
head=[0]*n
for u in order[1:]:head[u]=head[parent[u]] if heavy[parent[u]]==u else u
def lca(a,b):
 while head[a]!=head[b]:
  if depth[head[a]]<depth[head[b]]:a,b=b,a
  a=parent[head[a]]
 return a if depth[a]<depth[b] else b
bit=[0]*(n+2)
def add(i,value):
 while i<=n:bit[i]+=value;i+=i&-i
def count(u):
 i=tin[u];s=0
 while i:s+=bit[i];i-=i&-i
 return s
def change(u,value):add(tin[u],value);add(tin[u]+size[u],-value)
wars=[-1];out=[]
for _ in range(m):
 t=next(it)
 if t==b'U':change(wars[int(next(it))],-1)
 else:
  u,v=int(next(it))-1,int(next(it))-1
  if t==b'C':
   child=u if depth[u]>depth[v] else v;wars.append(child);change(child,1)
  else:out.append('Yes' if count(u)+count(v)-2*count(lca(u,v))==0 else 'No')
print('\n'.join(out))
