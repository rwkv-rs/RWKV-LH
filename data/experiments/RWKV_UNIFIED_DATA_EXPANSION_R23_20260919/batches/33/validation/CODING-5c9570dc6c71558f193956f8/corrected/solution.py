import sys
from array import array
v=iter(map(int,sys.stdin.buffer.read().split()));q=next(v);levels=(q+1).bit_length();inf=10**18;weights=[inf,0];up=[array('I',[0,0]) for _ in range(levels)];cost=[array('Q',[inf,inf]) for _ in range(levels)];last=0;out=[]
for _ in range(q):
 kind,p,value=next(v),next(v),next(v);r=p^last;value^=last
 if kind==1:
  parent=r
  if weights[parent]<value:
   for j in range(levels-1,-1,-1):
    ancestor=up[j][parent]
    if weights[ancestor]<value:parent=ancestor
   parent=up[0][parent]
  node=len(weights);weights.append(value);up[0].append(parent);cost[0].append(weights[parent])
  for j in range(1,levels):
   middle=up[j-1][node];up[j].append(up[j-1][middle]);cost[j].append(min(inf,cost[j-1][node]+cost[j-1][middle]))
 else:
  if weights[r]>value:last=0
  else:
   value-=weights[r];last=1
   for j in range(levels-1,-1,-1):
    if cost[j][r]<=value:value-=cost[j][r];last+=1<<j;r=up[j][r]
  out.append(str(last))
print('\n'.join(out))
