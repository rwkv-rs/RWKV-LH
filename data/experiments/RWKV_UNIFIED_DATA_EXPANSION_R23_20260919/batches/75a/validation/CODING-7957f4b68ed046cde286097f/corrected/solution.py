import sys
v=sys.stdin.buffer.read().split();n=int(v[0]);pieces=[x-48 for x in v[1]];graph=[[] for _ in range(n)]
for i in range(n-1):a,b=int(v[2+2*i])-1,int(v[3+2*i])-1;graph[a].append(b);graph[b].append(a)
parent=[-1]*n;order=[0]
for u in order:
 for w in graph[u]:
  if w!=parent[u]:parent[w]=u;order.append(w)
count=pieces[:];high=[0]*n;low=[0]*n
for u in reversed(order):
 biggest=0
 for w in graph[u]:
  if parent[w]==u:count[u]+=count[w];high[u]+=high[w]+count[w];biggest=max(biggest,low[w]+high[w]+2*count[w])
 low[u]=max(high[u]%2,biggest-high[u])
upcount=[0]*n;uphigh=[0]*n;uplow=[0]*n;answer=None
for u in order:
 contributions=[];total=0
 for w in graph[u]:
  if w==parent[u]:c,h,l=upcount[u],uphigh[u],uplow[u]
  else:c,h,l=count[w],high[w],low[w]
  demand=h+c;score=l+h+2*c;total+=demand;contributions.append((score,w,demand))
 largest=sorted(contributions,reverse=True)[:2];maximum=largest[0][0] if largest else 0
 if total%2==0 and maximum<=total:
  candidate=total//2
  if answer is None or candidate<answer:answer=candidate
 for score,w,demand in contributions:
  if parent[w]!=u:continue
  remaining=total-demand;other=largest[0][0] if largest[0][1]!=w else (largest[1][0] if len(largest)>1 else 0)
  upcount[w]=count[0]-count[w];uphigh[w]=remaining;uplow[w]=max(remaining%2,other-remaining)
print(-1 if answer is None else answer)
