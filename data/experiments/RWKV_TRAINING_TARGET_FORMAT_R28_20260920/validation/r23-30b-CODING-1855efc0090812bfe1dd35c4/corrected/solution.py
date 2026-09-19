import sys
n,mod=map(int,sys.stdin.read().split());inverse=[1]*(n+1)
for i in range(2,n+1):inverse[i]=mod-(mod//i)*inverse[mod%i]%mod
stirling=[0]*(n+2);stirling[1]=1;choose=1;answer=0
for k in range(n+1):
 choices=pow(2,n-k,mod);polynomial=0
 for j in range(k+1,0,-1):polynomial=(polynomial*choices+stirling[j])%mod
 term=choose*pow(2,pow(2,n-k,mod-1),mod)%mod*polynomial%mod;answer=(answer+(-term if k%2 else term))%mod
 if k<n:
  choose=choose*(n-k)%mod*inverse[k+1]%mod
  for j in range(k+2,0,-1):stirling[j]=(stirling[j]*j+stirling[j-1])%mod
print(answer)
