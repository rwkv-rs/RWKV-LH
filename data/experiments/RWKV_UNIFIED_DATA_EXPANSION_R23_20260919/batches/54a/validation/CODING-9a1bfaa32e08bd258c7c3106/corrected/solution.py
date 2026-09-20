import sys
from array import array
it=iter(map(int,sys.stdin.buffer.read().split()));Q=next(it);levels=(Q+1).bit_length();INF=10**18;up=[array('i',[0,0]) for _ in range(levels)];sums=[array('q',[INF,0 if k==0 else INF]) for k in range(levels)];weight=[INF,0];last=0;out=[]
for _ in range(Q):
 t,p,q=next(it),next(it),next(it);r,x=p^last,q^last
 if t==1:
  ancestor=r
  if weight[ancestor]<x:
   for k in range(levels-1,-1,-1):
    z=up[k][ancestor]
    if z and weight[z]<x:ancestor=z
   ancestor=up[0][ancestor]
  node=len(weight);weight.append(x);up[0].append(ancestor);sums[0].append(x)
  for k in range(1,levels):z=up[k-1][node];up[k].append(up[k-1][z]);sums[k].append(min(INF,sums[k-1][node]+sums[k-1][z]))
 else:
  answer=0
  for k in range(levels-1,-1,-1):
   if sums[k][r]<=x:x-=sums[k][r];r=up[k][r];answer+=1<<k
  last=answer;out.append(str(answer))
print('\n'.join(out))
