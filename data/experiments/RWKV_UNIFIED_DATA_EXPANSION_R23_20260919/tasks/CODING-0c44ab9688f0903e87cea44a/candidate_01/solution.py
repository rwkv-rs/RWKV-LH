import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,m=v[:2];p=2;edges=[];graph=[[] for _ in range(n)]
for _ in range(m):
 k=v[p];p+=1;path=[x-1 for x in v[p:p+k]];p+=k
 for a,b in zip(path,path[1:]):
  e=len(edges);edges.append((a,b));graph[a].append((b,e));graph[b].append((a,e))
parent=[-1]*n;pe=[-1]*n;depth=[-1]*n;depth[0]=0;order=[0];cycles=[];cyclic=set()
for u in order:
 for w,e in graph[u]:
  if e==pe[u]:continue
  if depth[w]<0:depth[w]=depth[u]+1;parent[w]=u;pe[w]=e;order.append(w)
# Use a true DFS tree: a stack with adjacency iterators ensures every non-tree edge joins ancestors.
parent=[-1]*n;pe=[-1]*n;depth=[-1]*n;depth[0]=0;order=[0];stack=[(0,iter(graph[0]))]
while stack:
 u,it=stack[-1]
 try:w,e=next(it)
 except StopIteration:stack.pop();continue
 if e==pe[u]:continue
 if depth[w]<0:parent[w]=u;pe[w]=e;depth[w]=depth[u]+1;order.append(w);stack.append((w,iter(graph[w])))
 elif depth[w]<depth[u]:
  cycle=[w];cyclic.add(e);x=u
  while x!=w:cycle.append(x);cyclic.add(pe[x]);x=parent[x]
  cycles.append(cycle)
size=[1]*n;answer=0
for u in reversed(order[1:]):
 if pe[u] not in cyclic:answer+=size[u]*(n-size[u])-1
 size[parent[u]]+=size[u]
dsu=list(range(n));sizes=[1]*n
def root(x):
 while dsu[x]!=x:dsu[x]=dsu[dsu[x]];x=dsu[x]
 return x
bridges=0
for e,(a,b) in enumerate(edges):
 if e not in cyclic:
  bridges+=1;a=root(a);b=root(b)
  if sizes[a]<sizes[b]:a,b=b,a
  dsu[b]=a;sizes[a]+=sizes[b]
base=sum(sizes[i]*(sizes[i]-1)//2 for i in range(n) if root(i)==i)-bridges
for cycle in cycles:
 total=0;pairs=0
 for u in cycle:s=sizes[root(u)];pairs+=total*s;total+=s
 length=len(cycle);answer+=length*(base+pairs-length)
print(answer)
