import sys
from array import array
v=sys.stdin.buffer.read().split();n,m=int(v[0]),int(v[1]);s=v[2];weights=[[0]*m for _ in range(m)]
for a,b in zip(s,s[1:]):
 a-=97;b-=97
 if a!=b:weights[a][b]+=1;weights[b][a]+=1
N=1<<m;cut=array('i',[0])*N;dp=array('q',[0])*N;degree=list(map(sum,weights));index={1<<i:i for i in range(m)}
for mask in range(1,N):
 bit=mask&-mask;i=index[bit];rest=mask^bit;inside=0;t=rest
 while t:b=t&-t;inside+=weights[i][index[b]];t^=b
 cut[mask]=cut[rest]+degree[i]-2*inside
 best=10**18;t=mask
 while t:b=t&-t;best=min(best,dp[mask^b]);t^=b
 dp[mask]=best+cut[mask]
print(dp[-1])
