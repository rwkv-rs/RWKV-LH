import sys
from functools import lru_cache
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);m=next(v);q=next(v);grid=[[next(v) for _ in range(m)] for _ in range(n)]
seams=[0]*m
for i in range(1,m):
 mask=0
 for r in range(n):
  if grid[r][i-1]==grid[r][i]:mask|=1<<r
 seams[i]=mask
size=1<<(m-1).bit_length();tree=[None]*(2*size);twice=2*n
for col in range(m):
 labels=[];root=0;count=0
 for r in range(n):
  if r==0 or grid[r][col]!=grid[r-1][col]:root=r;count+=1
  labels.append(root)
 tree[size+col]=(count,bytes(labels+labels),col,col+1)
del grid
@lru_cache(maxsize=65536)
def boundary(a,b,mask):
 parent=list(a)+[x+twice for x in b];merged=0
 while mask:
  bit=mask&-mask;i=bit.bit_length()-1;mask-=bit;x=n+i;y=twice+i
  while parent[x]!=x:x=parent[x]
  while parent[y]!=y:y=parent[y]
  if x!=y:parent[y]=x;merged+=1
 labels=[];seen={}
 for x in list(range(n))+list(range(3*n,4*n)):
  while parent[x]!=x:x=parent[x]
  if x not in seen:seen[x]=len(labels)
  labels.append(seen[x])
 return bytes(labels),merged
def join(a,b):
 if a is None:return b
 if b is None:return a
 labels,merged=boundary(a[1],b[1],seams[b[2]])
 return (a[0]+b[0]-merged,labels,a[2],b[3])
for i in range(size-1,0,-1):tree[i]=join(tree[2*i],tree[2*i+1])
output=[]
for _ in range(q):
 l=next(v)-1+size;r=next(v)+size;left=right=None
 while l<r:
  if l&1:left=join(left,tree[l]);l+=1
  if r&1:r-=1;right=join(tree[r],right)
  l//=2;r//=2
 output.append(str(join(left,right)[0]))
sys.stdout.write('\n'.join(output))
