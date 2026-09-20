import sys
MOD=998244353
def ntt(a,inverse=False):
 n=len(a);j=0
 for i in range(1,n):
  bit=n>>1
  while j&bit:j^=bit;bit>>=1
  j^=bit
  if i<j:a[i],a[j]=a[j],a[i]
 length=2
 while length<=n:
  root=pow(3,(MOD-1)//length,MOD)
  if inverse:root=pow(root,MOD-2,MOD)
  half=length//2
  for start in range(0,n,length):
   w=1
   for j in range(start,start+half):
    u,v=a[j],a[j+half]*w%MOD;a[j]=(u+v)%MOD;a[j+half]=(u-v)%MOD;w=w*root%MOD
  length*=2
 if inverse:
  inv=pow(n,MOD-2,MOD)
  for i in range(n):a[i]=a[i]*inv%MOD
def multiply(a,b,K):
 length=min(K+1,len(a)+len(b)-1)
 if min(len(a),len(b))<24:
  c=[0]*length
  for i,x in enumerate(a):
   for j,y in enumerate(b[:length-i]):c[i+j]=(c[i+j]+x*y)%MOD
  return c
 size=1
 while size<len(a)+len(b)-1:size*=2
 a=a+[0]*(size-len(a));b=b+[0]*(size-len(b));ntt(a);ntt(b)
 for i in range(size):a[i]=a[i]*b[i]%MOD
 ntt(a,True);return a[:length]
it=iter(map(int,sys.stdin.buffer.read().split()));N,K=next(it),next(it);A=[next(it) for _ in range(N)];Q=next(it);out=[]
for _ in range(Q):
 kind,q=next(it),next(it);a=A[:]
 if kind==1:i,d=next(it)-1,next(it);a[i]=d
 else:
  l,r,d=next(it)-1,next(it),next(it)
  for i in range(l,r):a[i]+=d
 polys=[[1,(q-x)%MOD] for x in a]
 while len(polys)>1:polys=[multiply(polys[i],polys[i+1],K) if i+1<len(polys) else polys[i] for i in range(0,len(polys),2)]
 out.append(str(polys[0][K]))
print('\n'.join(out))
