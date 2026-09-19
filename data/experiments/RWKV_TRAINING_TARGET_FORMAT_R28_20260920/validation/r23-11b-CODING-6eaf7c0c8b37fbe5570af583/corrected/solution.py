import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,k=v[:2];a=v[2:];mod=998244353;coeff=[1]
for x in a:
 new=[0]*(len(coeff)+1)
 for i,value in enumerate(coeff):new[i]=(new[i]+value*x)%mod;new[i+1]=(new[i+1]+value)%mod
 coeff=new
answer=0;factor=1;inverse=pow(n,mod-2,mod)
for j in range(min(n,k)+1):
 answer=(answer+coeff[j]*factor)%mod;factor=factor*(k-j)%mod*inverse%mod
print(answer)
