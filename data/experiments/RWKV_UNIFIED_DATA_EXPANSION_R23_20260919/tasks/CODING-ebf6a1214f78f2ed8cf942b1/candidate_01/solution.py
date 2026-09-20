import sys
from array import array
v=list(map(int,sys.stdin.buffer.read().split()));n,m=v[:2];A=v[2:2+n];B=v[2+n:2+n+m];p=2+n+m;size=1<<n;demand=array('q',[0])*size;masks=[0]*m
for i in range(n):
 for j in range(m):
  if v[p]:masks[j]|=1<<i
  p+=1
for mask,b in zip(masks,B):demand[mask]+=b
for bit in range(n):
 step=1<<bit
 for base in range(0,size,2*step):
  for j in range(base+step,base+2*step):demand[j]+=demand[j-step]
supply=array('i',[0])*size;minimum=sum(A)
for mask in range(1,size):
 low=mask&-mask;supply[mask]=supply[mask-low]+A[low.bit_length()-1]
 if demand[mask]:minimum=min(minimum,supply[mask]-demand[mask])
if minimum<0:print(0,1);raise SystemExit
X=minimum+1;marked=bytearray(size)
for mask in range(1,size):
 if demand[mask] and supply[mask]-demand[mask]==minimum:marked[mask]=1
for bit in range(n):
 step=1<<bit
 for base in range(0,size,2*step):
  for j in range(base,base+step):marked[j]|=marked[j+step]
MOD=998244353;total=sum(A);f=array('i',[1])*(total+1);g=array('i',[1])*(total+1)
for i in range(1,total+1):f[i]=f[i-1]*i%MOD
g[total]=pow(f[total],MOD-2,MOD)
for i in range(total,0,-1):g[i-1]=g[i]*i%MOD
ways=array('i',[0])*size;factor=g[X]
for mask in range(size):
 a=supply[mask]
 if a>=X:ways[mask]=f[a]*factor%MOD*g[a-X]%MOD
for bit in range(n):
 step=1<<bit
 for base in range(0,size,2*step):
  for j in range(base+step,base+2*step):ways[j]=(ways[j]-ways[j-step])%MOD
print(X,sum(w for w,mark in zip(ways,marked) if mark)%MOD)
