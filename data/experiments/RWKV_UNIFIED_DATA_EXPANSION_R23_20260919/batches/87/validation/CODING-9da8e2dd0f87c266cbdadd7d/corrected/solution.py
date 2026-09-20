import sys
from array import array
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);k=next(it);head=array('i',[-1])*(n+1);to=array('I');nxt=array('i')
for _ in range(n-1):
 a=next(it);b=next(it);to.append(b);nxt.append(head[a]);head[a]=len(to)-1;to.append(a);nxt.append(head[b]);head[b]=len(to)-1
del it
parent=array('I',[0])*(n+1);stack=[n]
while stack:
 u=stack.pop();e=head[u]
 while e>=0:
  v=to[e]
  if v!=parent[u]:parent[v]=u;stack.append(v)
  e=nxt[e]
del head,to,nxt,stack
up=[parent]
for _ in range(1,n.bit_length()):
 previous=up[-1];up.append(array('I',(previous[previous[i]] for i in range(n+1))))
selected=bytearray(n+1);selected[n]=1;budget=n-k-1
for v in range(n-1,0,-1):
 if selected[v]:continue
 u=v;cost=1
 for j in range(len(up)-1,-1,-1):
  ancestor=up[j][u]
  if ancestor and not selected[ancestor]:u=ancestor;cost+=1<<j
 if cost<=budget:
  budget-=cost;u=v
  while not selected[u]:selected[u]=1;u=parent[u]
print(' '.join(str(v) for v in range(1,n+1) if not selected[v]))
