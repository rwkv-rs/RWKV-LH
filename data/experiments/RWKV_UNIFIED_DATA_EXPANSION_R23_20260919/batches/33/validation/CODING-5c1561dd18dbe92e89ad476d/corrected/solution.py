import sys
n,k=map(int,sys.stdin.read().split());k=min(k,n-k);tree=[0]*(n+1)
def add(x):
 x+=1
 while x<=n:tree[x]+=1;x+=x&-x
def prefix(x):
 result=0
 while x:result+=tree[x];x-=x&-x
 return result
position=0;regions=1;out=[]
for step in range(n):
 target=(position+k)%n
 if position<target:crossings=prefix(target)-prefix(position+1)
 else:crossings=2*step-prefix(position+1)+prefix(target)
 regions+=crossings+1;out.append(str(regions));add(position);add(target);position=target
print(' '.join(out))
