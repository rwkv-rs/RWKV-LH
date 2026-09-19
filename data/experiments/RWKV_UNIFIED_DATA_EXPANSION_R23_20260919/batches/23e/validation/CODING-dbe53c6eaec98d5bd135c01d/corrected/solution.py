import sys,heapq
v=sys.stdin.read().split();children=[{}];depth=[0];terminal=[False]
for word in v[1:1+int(v[0])]:
 p=0
 for c in word:
  if c not in children[p]:children[p][c]=len(children);children.append({});depth.append(depth[p]+1);terminal.append(False)
  p=children[p][c]
 terminal[p]=True
heaps=[None]*len(children)
for p in range(len(children)-1,-1,-1):
 group=[heaps[c] for c in children[p].values()];heap=max(group,key=len) if group else []
 for other in group:
  if other is not heap:
   for value in other:heapq.heappush(heap,value)
 if terminal[p]:heapq.heappush(heap,-depth[p])
 elif p and heap:heapq.heapreplace(heap,-depth[p])
 heaps[p]=heap
print(-sum(heaps[0]))
