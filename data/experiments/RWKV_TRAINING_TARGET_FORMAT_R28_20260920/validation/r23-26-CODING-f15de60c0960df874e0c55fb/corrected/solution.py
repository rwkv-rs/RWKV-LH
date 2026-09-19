import sys
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 n=next(v);m=next(v);edges=[]
 for i in range(m):
  a=next(v)-1;b=next(v)-1;c=next(v);edges.append((c.bit_length()-1,a,b))
 parent=list(range(n));size=[1]*n
 def find(x):
  while parent[x]!=x:parent[x]=parent[parent[x]];x=parent[x]
  return x
 exponent=0
 for w,a,b in sorted(edges):
  a=find(a);b=find(b)
  if a==b:continue
  if size[a]<size[b]:a,b=b,a
  parent[b]=a;size[a]+=size[b];exponent+=w
 out.append(str(exponent+1))
print('\n'.join(out))
