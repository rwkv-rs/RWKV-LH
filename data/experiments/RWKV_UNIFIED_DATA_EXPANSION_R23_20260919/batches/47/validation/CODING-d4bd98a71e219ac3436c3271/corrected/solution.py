import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n,m=next(it),next(it);adj=[[] for _ in range(n)]
for _ in range(n-1):u,v,w=next(it)-1,next(it)-1,next(it);adj[u].append((v,w));adj[v].append((u,w))
queries=[next(it) for _ in range(m)];pending=set(queries);found=set();blocked=[False]*n;tasks=[0]
while tasks and pending:
 root=tasks.pop();parent={root:-1};order=[root]
 for u in order:
  for v,w in adj[u]:
   if not blocked[v] and v!=parent[u]:parent[v]=u;order.append(v)
 sizes={u:1 for u in order}
 for u in reversed(order[1:]):sizes[parent[u]]+=sizes[u]
 total=len(order);centroid=root
 for u in order:
  largest=total-sizes[u]
  for v,w in adj[u]:
   if not blocked[v] and parent.get(v)==u:largest=max(largest,sizes[v])
  if largest*2<=total:centroid=u;break
 seen={0};maximum=max(pending)
 for v,w in adj[centroid]:
  if blocked[v]:continue
  distances=[];stack=[(v,centroid,w)]
  while stack:
   u,p,d=stack.pop()
   if d>maximum:continue
   distances.append(d)
   for z,cost in adj[u]:
    if z!=p and not blocked[z]:stack.append((z,u,d+cost))
  hits=set()
  for d in distances:
   for k in pending:
    if k-d in seen:hits.add(k)
  found.update(hits);pending.difference_update(hits);seen.update(distances)
 blocked[centroid]=True
 for v,w in adj[centroid]:
  if not blocked[v]:tasks.append(v)
print('\n'.join('AYE' if k in found else 'NAY' for k in queries))
