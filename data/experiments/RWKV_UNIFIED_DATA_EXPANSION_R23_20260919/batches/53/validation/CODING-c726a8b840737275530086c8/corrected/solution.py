import sys,math
MOD=1000000007;tokens=list(map(int,sys.stdin.buffer.read().split()));out=[];fac=[1]*51
for i in range(1,51):fac[i]=fac[i-1]*i%MOD
invfac=[pow(x,MOD-2,MOD) for x in fac];inverse=[0]+[pow(i,MOD-2,MOD) for i in range(1,51)]
for N,M,K in zip(tokens[::3],tokens[1::3],tokens[2::3]):
 if math.comb(M+K-1,K-1)<N:out.append('0');continue
 powers=[0]*(N+1);coef=[1]*(M+1);mult=1
 for j in range(1,N+1):
  coef=[x*y%MOD for x,y in zip(coef,invfac)];mult=mult*fac[M]%MOD;dp=[1]+[0]*M
  for _ in range(K):
   new=[0]*(M+1)
   for a in range(M+1):
    if not dp[a]:continue
    for b in range(M-a+1):new[a+b]=(new[a+b]+dp[a]*coef[b])%MOD
   dp=new
  powers[j]=dp[M]*mult%MOD
 elementary=[1]+[0]*N
 for i in range(1,N+1):elementary[i]=sum((1 if j&1 else -1)*elementary[i-j]*powers[j] for j in range(1,i+1))*inverse[i]%MOD
 out.append(str(elementary[N]*fac[N]%MOD))
print('\n'.join(out))
