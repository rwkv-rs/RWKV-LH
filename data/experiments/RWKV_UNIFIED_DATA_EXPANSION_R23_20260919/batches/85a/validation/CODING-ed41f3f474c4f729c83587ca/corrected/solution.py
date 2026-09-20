import sys
from functools import lru_cache
MOD=998244353
@lru_cache(None)
def shape(n):
 if n==0:return (),()
 if n==1:return (1,),(1,)
 h=n.bit_length()-1;half=1<<(h-1);left=half-1+min(n-((1<<h)-1),half);right=n-1-left
 a,x=shape(left);b,y=shape(right);depth=[1]+[0]*max(len(a),len(b));paths=[0]*max(len(x),len(y),len(a)+len(b)+1);paths[0]=1
 for i,value in enumerate(x):paths[i]=(paths[i]+value)%MOD
 for i,value in enumerate(y):paths[i]=(paths[i]+value)%MOD
 for i,value in enumerate(a):depth[i+1]+=value;paths[i+1]=(paths[i+1]+value)%MOD
 for i,value in enumerate(b):depth[i+1]+=value;paths[i+1]=(paths[i+1]+value)%MOD
 for i,u in enumerate(a):
  for j,w in enumerate(b):paths[i+j+2]=(paths[i+j+2]+u*w)%MOD
 return tuple(depth),tuple(paths)
v=list(map(int,sys.stdin.buffer.read().split()));out=[]
for n,m in zip(v[1::2],v[2::2]):
 _,counts=shape(n);degree=len(counts);sums=[0]*(degree+1)
 for value in range(1,m):
  power=value
  for length in range(1,degree+1):sums[length]=(sums[length]+power)%MOD;power=power*value%MOD
 inverse=pow(m,MOD-2,MOD);factor=pow(m,n,MOD);answer=0
 for distance,count in enumerate(counts):
  factor=factor*inverse%MOD;length=distance+1
  maximum_sum=(m*pow(m,length,MOD)-sums[length])%MOD
  answer=(answer+count*maximum_sum*factor)%MOD
 out.append(str(answer))
print('\n'.join(out))
