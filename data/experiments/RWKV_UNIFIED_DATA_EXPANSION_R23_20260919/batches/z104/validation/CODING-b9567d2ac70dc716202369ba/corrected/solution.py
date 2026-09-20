import sys
v=sys.stdin.buffer.read().split();n,L,R=map(int,v[:3]);ops=[(v[3+2*i],int(v[4+2*i])) for i in range(n)];q=int(v[3+2*n]);original=list(map(int,v[4+2*n:]));xs=sorted(set(original));m=len(xs);size=4*m;minimum=[0]*size;maximum=[0]*size;la=[1]*size;lb=[0]*size;lc=[0]*size
def build(u,l,r):
 minimum[u]=xs[l];maximum[u]=xs[r]
 if l<r:
  mid=(l+r)//2;build(u*2,l,mid);build(u*2+1,mid+1,r)
def apply(u,l,r,a,b,c):
 minimum[u]=a*minimum[u]+b*xs[l]+c;maximum[u]=a*maximum[u]+b*xs[r]+c
 if minimum[u]==maximum[u]:la[u]=lb[u]=0;lc[u]=minimum[u]
 else:la[u]*=a;lb[u]=a*lb[u]+b;lc[u]=a*lc[u]+c
def push(u,l,r):
 if la[u]!=1 or lb[u] or lc[u]:
  mid=(l+r)//2;apply(u*2,l,mid,la[u],lb[u],lc[u]);apply(u*2+1,mid+1,r,la[u],lb[u],lc[u]);la[u]=1;lb[u]=lc[u]=0
def clamp(u,l,r):
 if minimum[u]>=R:apply(u,l,r,0,0,R);return
 if maximum[u]<=L:apply(u,l,r,0,0,L);return
 if minimum[u]>=L and maximum[u]<=R:return
 push(u,l,r);mid=(l+r)//2;clamp(u*2,l,mid);clamp(u*2+1,mid+1,r);minimum[u]=minimum[u*2];maximum[u]=maximum[u*2+1]
build(1,0,m-1)
for op,a in ops:
 if op==b'+':apply(1,0,m-1,1,0,a)
 elif op==b'-':apply(1,0,m-1,1,0,-a)
 elif op==b'*':apply(1,0,m-1,a,0,0)
 else:apply(1,0,m-1,1,a,0)
 clamp(1,0,m-1)
answer={}
def collect(u,l,r):
 if l==r:answer[xs[l]]=minimum[u];return
 push(u,l,r);mid=(l+r)//2;collect(u*2,l,mid);collect(u*2+1,mid+1,r)
collect(1,0,m-1);print('\n'.join(str(answer[x]) for x in original))
