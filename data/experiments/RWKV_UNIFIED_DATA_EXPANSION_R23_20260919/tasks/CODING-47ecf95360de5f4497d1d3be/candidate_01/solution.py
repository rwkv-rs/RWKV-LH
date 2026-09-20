import sys
from array import array
v=list(map(int,sys.stdin.buffer.read().split()));cases=list(zip(v[1::2],v[2::2]));M=max(max(x) for x in cases);MOD=1000000007;f=array('i',[1])*(M+1);g=array('i',[1])*(M+1)
for i in range(1,M+1):f[i]=f[i-1]*i%MOD
g[M]=pow(f[M],MOD-2,MOD)
for i in range(M,0,-1):g[i-1]=g[i]*i%MOD
def choose(n,k):return f[n]*g[k]%MOD*g[n-k]%MOD if 0<=k<=n else 0
out=[]
for n,m in cases:
 power=pow(2,n+m,MOD);answer=0
 for j in range(min(n,m)+1):
  a=(choose(n,j)+250000002*choose(n-1,j+1))%MOD;b=(choose(m,j)+250000002*choose(m-1,j+1))%MOD;answer=(answer+(j+1)*power%MOD*a%MOD*b)%MOD;power=power*500000004%MOD
 out.append(str(answer))
print('\n'.join(out))
