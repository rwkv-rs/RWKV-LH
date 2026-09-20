import sys
v=list(map(int,sys.stdin.buffer.read().split()));cases=[v[i:i+3] for i in range(1,len(v),3)];limit=max((n for n,k,m in cases),default=0);MOD=1000000007;fac=[1]*(limit+1)
for i in range(1,limit+1):fac[i]=fac[i-1]*i%MOD
inv=[1]*(limit+1);inv[-1]=pow(fac[-1],MOD-2,MOD)
for i in range(limit,0,-1):inv[i-1]=inv[i]*i%MOD
def choose(n,k):return fac[n]*inv[k]%MOD*inv[n-k]%MOD if 0<=k<=n else 0
out=[]
for n,k,m in cases:
 answer=0
 for j in range(min(k,(n-k)//m)+1):
  term=choose(k,j)*choose(n-j*m-1,k-1)%MOD;answer=(answer+term if j%2==0 else answer-term)%MOD
 out.append(str(answer))
print('\n'.join(out))
