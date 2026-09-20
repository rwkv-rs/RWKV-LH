import sys
def solve(A,B):
 xs=sorted(set(A));N=len(xs);index={x:i for i,x in enumerate(xs)};size=4*N;mx=[0]*size;la=[0]*size;lb=[0]*size;assigned=[False]*size
 def apply(o,r,a,b,reset):
  if reset:mx[o]=a*xs[r]+b;la[o]=a;lb[o]=b;assigned[o]=True
  else:mx[o]+=a*xs[r]+b;la[o]+=a;lb[o]+=b
 def push(o,l,r):
  if assigned[o] or la[o] or lb[o]:
   mid=(l+r)//2;apply(o*2,mid,la[o],lb[o],assigned[o]);apply(o*2+1,r,la[o],lb[o],assigned[o]);la[o]=lb[o]=0;assigned[o]=False
 def update(o,l,r,ql,qr,a,b,reset):
  if ql<=l and r<=qr:apply(o,r,a,b,reset);return
  push(o,l,r);mid=(l+r)//2
  if ql<=mid:update(o*2,l,mid,ql,qr,a,b,reset)
  if qr>mid:update(o*2+1,mid+1,r,ql,qr,a,b,reset)
  mx[o]=mx[o*2+1]
 def value(o,l,r,pos):
  if l==r:return mx[o]
  push(o,l,r);mid=(l+r)//2
  if pos<=mid:return value(o*2,l,mid,pos)
  return value(o*2+1,mid+1,r,pos)
 def first_above(o,l,r,target):
  if mx[o]<=target:return N
  if l==r:return l
  push(o,l,r);mid=(l+r)//2
  if mx[o*2]>target:return first_above(o*2,l,mid,target)
  return first_above(o*2+1,mid+1,r,target)
 for a,b in zip(A,B):
  p=index[a];constant=value(1,0,N-1,p)+b
  update(1,0,N-1,0,p,1,b-a,False)
  end=first_above(1,0,N-1,constant)-1
  if end>p:update(1,0,N-1,p+1,end,0,constant,True)
 return mx[1]
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);A=[next(v) for _ in range(n)];B=[next(v) for _ in range(n)];print(solve(A,B))
