import sys,math
n=int(sys.stdin.buffer.read());mod=1000000007;fac=[1]*(n+1)
for i in range(1,n+1):fac[i]=fac[i-1]*i%mod
inv=[1]*(n+1);inv[n]=pow(fac[n],mod-2,mod)
for i in range(n,0,-1):inv[i-1]=inv[i]*i%mod
limit=(math.isqrt(8*n+1)-1)//2;dp=[[0]*(n+1) for _ in range(limit+1)];dp[0][0]=1
for i in range(1,n+1):
 weight=inv[i]
 for k in range(min(i,limit),0,-1):
  old=dp[k-1];new=dp[k];minimum=i+(k-1)*k//2
  for total in range(n,minimum-1,-1):
   if old[total-i]:new[total]=(new[total]+old[total-i]*weight)%mod
answer=0
for k in range(1,limit+1):
 subtotal=0
 for total in range(k*(k+1)//2,n+1):
  if dp[k][total]:subtotal=(subtotal+dp[k][total]*inv[n-total]*pow(n-k,n-total,mod))%mod
 answer=(answer+(subtotal if k%2 else -subtotal))%mod
print(answer*fac[n]%mod)
