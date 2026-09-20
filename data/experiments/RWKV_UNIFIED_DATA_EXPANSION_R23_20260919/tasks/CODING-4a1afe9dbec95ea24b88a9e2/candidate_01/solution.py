import sys,random
sys.setrecursionlimit(1000000)
it=iter(map(int,sys.stdin.buffer.read().split()));n,q=next(it),next(it);left=[0]*(n+1);right=left.copy();parent=left.copy();size=[1]*(n+1);size[0]=0;rev=bytearray(n+1);rng=random.Random(1743);priority=[0]+[rng.getrandbits(64) for _ in range(n)]
def flip(p):
 if p:left[p],right[p]=right[p],left[p];rev[p]^=1
def push(p):
 if rev[p]:flip(left[p]);flip(right[p]);rev[p]=0
def pull(p):
 size[p]=1+size[left[p]]+size[right[p]]
 if left[p]:parent[left[p]]=p
 if right[p]:parent[right[p]]=p
def merge(a,b):
 if not a or not b:
  z=a or b
  if z:parent[z]=0
  return z
 if priority[a]>priority[b]:push(a);right[a]=merge(right[a],b);pull(a);parent[a]=0;return a
 push(b);left[b]=merge(a,left[b]);pull(b);parent[b]=0;return b
def split(p,k):
 if not p:return 0,0
 push(p)
 if size[left[p]]>=k:a,left[p]=split(left[p],k);pull(p);parent[p]=0;return a,p
 right[p],b=split(right[p],k-size[left[p]]-1);pull(p);parent[p]=0;return p,b
root=0
for i in range(1,n+1):root=merge(root,i)
out=[]
for _ in range(q):
 t,i=next(it),next(it)
 if t==1:
  j=next(it);a,b=split(root,i-1);b,c=split(b,j-i+1);flip(b);root=merge(a,merge(b,c))
 elif t==2:
  p=root
  while p:
   push(p);k=size[left[p]]+1
   if i==k:out.append(str(p));break
   if i<k:p=left[p]
   else:i-=k;p=right[p]
 else:
  path=[];p=i
  while p:path.append(p);p=parent[p]
  for p in reversed(path):push(p)
  rank=size[left[i]]+1;p=i
  while parent[p]:
   z=parent[p]
   if right[z]==p:rank+=size[left[z]]+1
   p=z
  out.append(str(rank))
print('\n'.join(out))
