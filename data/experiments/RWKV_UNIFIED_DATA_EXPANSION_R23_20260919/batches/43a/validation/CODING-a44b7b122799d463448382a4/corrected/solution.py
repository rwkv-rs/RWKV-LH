import sys
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];p=v[1:1+n];q=v[1+n:1+2*n];mapping=[0]*n
for a,b in zip(p,q):mapping[a-1]=b-1
mod=1000000007;fac=[1]*(2*n+1)
for i in range(1,2*n+1):fac[i]=fac[i-1]*i%mod
inv=[1]*(2*n+1);inv[-1]=pow(fac[-1],mod-2,mod)
for i in range(2*n,0,-1):inv[i-1]=inv[i]*i%mod
def choose(a,b):return fac[a]*inv[b]%mod*inv[a-b]%mod if 0<=b<=a else 0
seen=[False]*n;poly=[1]
for start in range(n):
 if seen[start]:continue
 u=start;length=0
 while not seen[u]:seen[u]=True;length+=1;u=mapping[u]
 local=[1,1] if length==1 else [1]+[(choose(2*length-j,j)+choose(2*length-j-1,j-1))%mod for j in range(1,length+1)]
 result=[0]*(len(poly)+length)
 for i,a in enumerate(poly):
  for j,b in enumerate(local):result[i+j]=(result[i+j]+a*b)%mod
 poly=result
print(sum((-1 if k%2 else 1)*value*fac[n-k] for k,value in enumerate(poly))%mod)
