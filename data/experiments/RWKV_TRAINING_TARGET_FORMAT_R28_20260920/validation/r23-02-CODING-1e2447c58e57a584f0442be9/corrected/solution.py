import sys
from collections import Counter
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];g=[[] for _ in range(n)]
for i in range(n-1):
 a,b=v[1+2*i]-1,v[2+2*i]-1;g[a].append(b);g[b].append(a)
parent=[-1]*n;depth=[0]*n;queue=[0]
for a in queue:
 for b in g[a]:
  if b!=parent[a]:parent[b]=a;depth[b]=depth[a]+1;queue.append(b)
x,y=v[-2]-1,v[-1]-1;dx,dy=depth[x],depth[y]
while depth[x]>depth[y]:x=parent[x]
while depth[y]>depth[x]:y=parent[y]
while x!=y:x=parent[x];y=parent[y]
print(max(depth)+1);print(max(Counter(depth).values()));print(2*(dx-depth[x])+dy-depth[x])
