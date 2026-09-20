import sys
from functools import lru_cache
stream=sys.stdin.buffer;n,m,q=map(int,stream.readline().split());grid=[list(map(int,stream.readline().split())) for _ in range(n)]
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
@lru_cache(maxsize=65536)
def split_partition(labels):
 return (labels[:n],labels[n:]) if min(labels[n:])>=n else None
@lru_cache(maxsize=65536)
def seam_count(a,b,mask):
 parent=[x-n for x in a]+[x+n for x in b];merged=0
 while mask:
  bit=mask&-mask;i=bit.bit_length()-1;mask-=bit;x=i;y=n+i
  while parent[x]!=x:x=parent[x]
  while parent[y]!=y:y=parent[y]
  if x!=y:parent[y]=x;merged+=1
 return merged
def join(a,b):
 if a is None:return b
 if b is None:return a
 aa=split_partition(a[1]);bb=split_partition(b[1]);mask=seams[b[2]]
 if aa is not None and bb is not None:
  labels=aa[0]+bb[1];merged=seam_count(aa[1],bb[0],mask)
 else:labels,merged=boundary(a[1],b[1],mask)
 return (a[0]+b[0]-merged,labels,a[2],b[3])
for i in range(size-1,0,-1):tree[i]=join(tree[2*i],tree[2*i+1])
block=32;blocks=(m+block-1)//block;prefix=[None]*m;suffix=[None]*m;whole=[]
for start in range(0,m,block):
 end=min(start+block,m);acc=None
 for j in range(start,end):acc=join(acc,tree[size+j]);prefix[j]=acc
 whole.append(acc);acc=None
 for j in range(end-1,start-1,-1):acc=join(tree[size+j],acc);suffix[j]=acc
disjoint=[]
for level in range((blocks-1).bit_length()):
 half=1<<level;width=half*2;row=[None]*blocks
 for start in range(0,blocks,width):
  middle=min(start+half,blocks);end=min(start+width,blocks);acc=None
  for j in range(middle-1,start-1,-1):acc=join(whole[j],acc);row[j]=acc
  acc=None
  for j in range(middle,end):acc=join(acc,whole[j]);row[j]=acc
 disjoint.append(row)
output=[]
for _ in range(q):
 l,r=map(int,stream.readline().split());l-=1;r-=1;bl=l//block;br=r//block
 if bl!=br:
  a=bl+1;b=br-1;middle=None
  if a==b:middle=whole[a]
  elif a<b:
   row=disjoint[(a^b).bit_length()-1];middle=join(row[a],row[b])
  output.append(str(join(join(suffix[l],middle),prefix[r])[0]));continue
 l+=size;r+=size+1;left=right=None
 while l<r:
  if l&1:left=join(left,tree[l]);l+=1
  if r&1:r-=1;right=join(tree[r],right)
  l//=2;r//=2
 output.append(str(join(left,right)[0]))
sys.stdout.write('\n'.join(output))
