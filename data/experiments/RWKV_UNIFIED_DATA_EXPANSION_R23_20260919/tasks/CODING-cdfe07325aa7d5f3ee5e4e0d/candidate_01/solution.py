import sys
v=iter(sys.stdin.read().split());s=next(v);n=len(s);size=1
while size<n:size*=2
tree=[0]*(2*size)
for i,c in enumerate(s):tree[size+i]=1<<(ord(c)-97)
for p in range(size-1,0,-1):tree[p]=tree[p*2]|tree[p*2+1]
out=[]
for _ in range(int(next(v))):
 op=int(next(v));a=int(next(v));b=next(v)
 if op==1:
  p=size+a-1;tree[p]=1<<(ord(b)-97);p//=2
  while p:tree[p]=tree[p*2]|tree[p*2+1];p//=2
 else:
  l=size+a-1;r=size+int(b);mask=0
  while l<r:
   if l&1:mask|=tree[l];l+=1
   if r&1:r-=1;mask|=tree[r]
   l//=2;r//=2
  out.append(str(mask.bit_count()))
print('\n'.join(out))
