import sys
n,m,limit=map(int,sys.stdin.buffer.read().split());MOD=1000000007;half=(MOD+1)//2;paths=n-m;degree=m
factorial=[1]*(n+1)
for i in range(1,n+1):factorial[i]=factorial[i-1]*i%MOD
inverses=[0]+[pow(i,MOD-2,MOD) for i in range(1,n+1)]
def multiply(a,b):
 out=[0]*min(degree+1,len(a)+len(b)-1)
 for i,x in enumerate(a):
  if x:
   for j in range(min(len(b),len(out)-i)):out[i+j]=(out[i+j]+x*b[j])%MOD
 return out
def bounded(bound):
 if bound<1:return 0
 base=[1]+[half]*min(bound-1,degree);power=paths;poly=[1]
 while power:
  if power&1:poly=multiply(poly,base)
  power//=2
  if power:base=multiply(base,base)
 cycle=[0]*(degree+1);prefix=[0]*(degree+2);cycle[0]=1;prefix[1]=1
 for i in range(1,degree+1):
  value=cycle[i-2] if bound>=2 and i>=2 else 0
  if bound>=3 and i>=3:value+=half*(prefix[i-2]-prefix[max(0,i-bound)])
  cycle[i]=value*inverses[i]%MOD;prefix[i+1]=(prefix[i]+cycle[i])%MOD
 coefficient=sum(x*cycle[degree-i] for i,x in enumerate(poly))%MOD
 return coefficient*factorial[n]%MOD*pow(factorial[paths],MOD-2,MOD)%MOD
print((bounded(limit)-bounded(limit-1))%MOD)
