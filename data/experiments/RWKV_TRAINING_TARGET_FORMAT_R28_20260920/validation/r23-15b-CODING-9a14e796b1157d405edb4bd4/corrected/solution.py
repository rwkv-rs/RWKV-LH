import sys
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);size=1
while size<n:size*=2
tree=[None]*(2*size)
def merge(a,b):
 if a is None:return b
 if b is None:return a
 return (a[0]+b[0],max(a[1],a[0]+b[1]),max(b[2],b[0]+a[2]),max(a[3],b[3],a[2]+b[1]))
for i in range(n):x=next(v);tree[size+i]=(x,x,x,x)
for p in range(size-1,0,-1):tree[p]=merge(tree[2*p],tree[2*p+1])
out=[]
for _ in range(next(v)):
 op=next(v);x=next(v);y=next(v)
 if op==0:
  p=size+x-1;tree[p]=(y,y,y,y);p//=2
  while p:tree[p]=merge(tree[p*2],tree[p*2+1]);p//=2
 else:
  l=size+x-1;r=size+y;left=right=None
  while l<r:
   if l&1:left=merge(left,tree[l]);l+=1
   if r&1:r-=1;right=merge(tree[r],right)
   l//=2;r//=2
  out.append(str(merge(left,right)[3]))
print('\n'.join(out))
