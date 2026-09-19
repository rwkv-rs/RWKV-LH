import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,q=v[:2];size=1
while size<n:size*=2
nodes=[[] for _ in range(2*size)]
for i in range(q):
 l,r,x=v[2+3*i:5+3*i];l=l-1+size;r=r+size
 while l<r:
  if l&1:nodes[l].append(x);l+=1
  if r&1:r-=1;nodes[r].append(x)
  l//=2;r//=2
mask=(1<<(n+1))-1;answer=0;stack=[(1,1)]
while stack:
 index,bits=stack.pop()
 for x in nodes[index]:bits=(bits|(bits<<x))&mask
 if index>=size:
  if index-size<n:answer|=bits
 else:stack.extend(((2*index,bits),(2*index+1,bits)))
values=[str(i) for i in range(1,n+1) if answer>>i&1];print(len(values));print(' '.join(values))
