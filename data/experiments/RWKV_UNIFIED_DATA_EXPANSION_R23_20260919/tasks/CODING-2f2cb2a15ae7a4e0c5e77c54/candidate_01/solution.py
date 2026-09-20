import sys
import numpy as np
P=998244353;cache={}
def roots(n,inverse):
 key=(n,inverse)
 if key not in cache:
  w=pow(3,(P-1)//n,P)
  if inverse:w=pow(w,P-2,P)
  values=[1]*(n//2)
  for i in range(1,len(values)):values[i]=values[i-1]*w%P
  cache[key]=np.array(values,dtype=np.int64)
 return cache[key]
def transform(a,inverse=False):
 n=len(a)
 if not inverse:
  step=n
  while step>1:
   half=step//2;view=a.reshape(-1,step);u=view[:,:half].copy();v=view[:,half:].copy();view[:,:half]=(u+v)%P;view[:,half:]=((u-v)*roots(step,False))%P;step//=2
 else:
  step=2
  while step<=n:
   half=step//2;view=a.reshape(-1,step);u=view[:,:half].copy();v=view[:,half:]*roots(step,True)%P;view[:,:half]=(u+v)%P;view[:,half:]=(u-v)%P;step*=2
  a[:]=a*pow(n,P-2,P)%P
 return a
def multiply(a,b,limit):
 need=min(limit,len(a)+len(b)-1)
 if min(len(a),len(b))<24:
  out=[0]*need
  for i,x in enumerate(a):
   if i>=need:break
   for j,y in enumerate(b[:need-i]):out[i+j]=(out[i+j]+x*y)%P
  return out
 n=1<<(len(a)+len(b)-2).bit_length();x=np.zeros(n,dtype=np.int64);y=np.zeros(n,dtype=np.int64);x[:len(a)]=a;y[:len(b)]=b;transform(x);transform(y);x[:]=x*y%P;transform(x,True);return x[:need].tolist()
n,k,f=map(int,sys.stdin.buffer.read().split())
if f>2*k:print(0)
else:
 limit=min(k,f)+1;distribution=[1]*limit;total=(k+1)%P;indices=np.arange(limit,dtype=np.int64)
 for depth in range(2,n+1):
  conv=np.array(multiply(distribution,distribution,limit),dtype=np.int64);prefix=(np.cumsum(conv)-conv)%P;distribution=((total*total%P-prefix+(k-indices)*conv)%P).tolist();total=total*total*(k+1)%P
 answer=sum(distribution[i]*distribution[f-i] for i in range(max(0,f-k),min(k,f)+1))%P;print(answer)
