import sys
it=iter(map(int,sys.stdin.buffer.read().split()));n,m=next(it),next(it);a=[next(it) for _ in range(n)];MOD=10**9;f=[0,1]
for _ in range(n+2):f.append((f[-1]+f[-2])%MOD)
x=[0]*(4*n);y=x.copy();lazy=x.copy()
def join(a,b):
 u,v,k=a;p,q,l=b
 if not k:return b
 if not l:return a
 return ((u+f[k-1]*p+f[k]*q)%MOD,(v+f[k]*p+f[k+1]*q)%MOD,k+l)
def pull(p,l,r):
 k=(l+r)//2-l+1;u=p*2;v=u+1;x[p]=(x[u]+f[k-1]*x[v]+f[k]*y[v])%MOD;y[p]=(y[u]+f[k]*x[v]+f[k+1]*y[v])%MOD
def build(p,l,r):
 if l==r:y[p]=a[l];return
 mid=(l+r)//2;build(p*2,l,mid);build(p*2+1,mid+1,r);pull(p,l,r)
def apply(p,length,d):x[p]=(x[p]+d*(f[length+1]-1))%MOD;y[p]=(y[p]+d*(f[length+2]-1))%MOD;lazy[p]=(lazy[p]+d)%MOD
def push(p,l,r):
 if lazy[p] and l<r:
  mid=(l+r)//2;apply(p*2,mid-l+1,lazy[p]);apply(p*2+1,r-mid,lazy[p]);lazy[p]=0
def update(p,l,r,L,R,d,assign=False):
 if L<=l and r<=R:
  if assign:x[p]=0;y[p]=d;lazy[p]=0
  else:apply(p,r-l+1,d)
  return
 push(p,l,r);mid=(l+r)//2
 if L<=mid:update(p*2,l,mid,L,R,d,assign)
 if R>mid:update(p*2+1,mid+1,r,L,R,d,assign)
 pull(p,l,r)
def query(p,l,r,L,R):
 if L<=l and r<=R:return x[p],y[p],r-l+1
 push(p,l,r);mid=(l+r)//2
 if R<=mid:return query(p*2,l,mid,L,R)
 if L>mid:return query(p*2+1,mid+1,r,L,R)
 return join(query(p*2,l,mid,L,R),query(p*2+1,mid+1,r,L,R))
build(1,0,n-1);out=[]
for _ in range(m):
 t,l,r=next(it),next(it),next(it)
 if t==1:update(1,0,n-1,l-1,l-1,r,True)
 elif t==2:out.append(str(query(1,0,n-1,l-1,r-1)[1]))
 else:update(1,0,n-1,l-1,r-1,next(it))
print('\n'.join(out))
