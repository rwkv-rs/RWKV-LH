import sys
v=sys.stdin.buffer.read().split();n=int(v[0]);pieces=[x-48 for x in v[1]];graph=[[] for _ in range(n)]
for i in range(n-1):a,b=int(v[2+2*i])-1,int(v[3+2*i])-1;graph[a].append(b);graph[b].append(a)
parent=[-1]*n;order=[0]
for u in order:
 for w in graph[u]:
  if w!=parent[u]:parent[w]=u;order.append(w)
count=pieces[:];down=[0]*n
for u in reversed(order[1:]):count[parent[u]]+=count[u];down[parent[u]]+=down[u]+count[u]
total=[0]*n;total[0]=down[0];answer=None
for u in order:
 largest=total[u]-down[u]
 for w in graph[u]:
  if parent[w]==u:largest=max(largest,down[w]+count[w]);total[w]=total[u]+count[0]-2*count[w]
 if total[u]%2==0 and 2*largest<=total[u]:
  candidate=total[u]//2
  if answer is None or candidate<answer:answer=candidate
print(-1 if answer is None else answer)
