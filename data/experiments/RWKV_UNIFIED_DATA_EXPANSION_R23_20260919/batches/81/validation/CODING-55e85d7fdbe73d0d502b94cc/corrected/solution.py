import sys
from collections import deque
v=list(map(int,sys.stdin.buffer.read().split()));n,m=v[:2];p=2;graph=[[] for _ in range(n)];edgecount=0
for _ in range(m):
 k=v[p];p+=1;path=[x-1 for x in v[p:p+k]];p+=k
 for a,b in zip(path,path[1:]):graph[a].append((b,edgecount));graph[b].append((a,edgecount));edgecount+=1
parent=[-1]*n;pe=[-1]*n;depth=[-1]*n;depth[0]=0;order=[0];stack=[(0,iter(graph[0]))];cyclic=set();cycles=[[] for _ in range(n)]
while stack:
 u,it=stack[-1]
 try:w,e=next(it)
 except StopIteration:stack.pop();continue
 if e==pe[u]:continue
 if depth[w]<0:parent[w]=u;pe[w]=e;depth[w]=depth[u]+1;order.append(w);stack.append((w,iter(graph[w])))
 elif depth[w]<depth[u]:
  cycle=[w];cyclic.add(e);x=u
  while x!=w:cycle.append(x);cyclic.add(pe[x]);x=parent[x]
  cycles[w].append(cycle)
height=[0]*n;answer=0
for u in reversed(order):
 for w,e in graph[u]:
  if parent[w]==u and e not in cyclic:answer=max(answer,height[u]+height[w]+1);height[u]=max(height[u],height[w]+1)
 for cycle in cycles[u]:
  length=len(cycle);values=[height[x] for x in cycle];queue=deque();half=length//2
  for j in range(2*length):
   while queue and queue[0]<j-half:queue.popleft()
   if queue:answer=max(answer,values[j%length]+j+values[queue[0]%length]-queue[0])
   score=values[j%length]-j
   while queue and values[queue[-1]%length]-queue[-1]<=score:queue.pop()
   queue.append(j)
  height[u]=max(values[j]+min(j,length-j) for j in range(length))
print(answer)
