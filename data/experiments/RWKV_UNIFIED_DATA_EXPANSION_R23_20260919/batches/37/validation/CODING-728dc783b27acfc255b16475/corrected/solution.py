import sys
n,k=map(int,sys.stdin.buffer.read().split());k=min(k,n-k);tree=[0]*(n+1)
def add(i):
 i+=1
 while i<=n:tree[i]+=1;i+=i&-i
def prefix(i):
 total=0
 while i:total+=tree[i];i-=i&-i
 return total
position=0;regions=1;total=0;out=[]
for _ in range(n):
 dest=(position+k)%n
 crossings=prefix(dest)-prefix(position+1) if position<dest else total-prefix(position+1)+prefix(dest)
 regions+=crossings+1;out.append(str(regions));add(position);add(dest);total+=2;position=dest
print(' '.join(out))
