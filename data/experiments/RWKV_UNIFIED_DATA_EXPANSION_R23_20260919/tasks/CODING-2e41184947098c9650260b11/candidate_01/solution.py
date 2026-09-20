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
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);c=next(v);m=next(v);coeff=[next(v) for _ in range(n)]
if c==0:out=[sum(coeff)%P]+[coeff[0]]*(m-1)
elif c==1:out=[sum(coeff)%P]*m
else:
 length=1<<(n+m-2).bit_length();a=np.zeros(length,dtype=np.int64);b=np.zeros(length,dtype=np.int64);inverse_c=pow(c,P-2,P);weight=step=1
 for i in range(n):a[n-1-i]=coeff[i]*weight%P;weight=weight*step%P;step=step*inverse_c%P
 weight=step=1
 for i in range(n+m-1):b[i]=weight;weight=weight*step%P;step=step*c%P
 transform(a);transform(b);a[:]=a*b%P;transform(a,True);weight=step=1;out=[]
 for j in range(m):out.append(int(a[n-1+j])*weight%P);weight=weight*step%P;step=step*inverse_c%P
print(' '.join(map(str,out)))
