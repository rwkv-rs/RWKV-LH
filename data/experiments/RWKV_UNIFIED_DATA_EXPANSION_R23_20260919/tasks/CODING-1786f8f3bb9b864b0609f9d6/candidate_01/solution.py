import sys,random
v=sys.stdin.buffer.read().split();n,m,k=map(int,v[:3]);s=[x-97 for x in v[3]];counts=[[0]*k for _ in range(k)]
for a,b in zip(s,s[1:]):counts[a][b]+=1
rng=random.Random(918273)
class Node:
 __slots__=('start','end','c','priority','left','right')
 def __init__(self,start,end,c):self.start=start;self.end=end;self.c=c;self.priority=rng.getrandbits(64);self.left=None;self.right=None
def merge(a,b):
 if a is None:return b
 if b is None:return a
 if a.priority>b.priority:a.right=merge(a.right,b);return a
 b.left=merge(a,b.left);return b
def split(t,key):
 if t is None:return None,None
 if t.start<key:t.right,b=split(t.right,key);return t,b
 a,t.left=split(t.left,key);return a,t
def find(t,pos):
 answer=None
 while t is not None:
  if t.start<=pos:answer=t;t=t.right
  else:t=t.left
 return answer
root=None;start=0
for end in range(1,n+1):
 if end==n or s[end]!=s[start]:root=merge(root,Node(start,end,s[start]));start=end
def boundary(pos):
 global root
 if pos==0 or pos==n:return
 t=find(root,pos)
 if t.start==pos:return
 extra=Node(pos,t.end,t.c);t.end=pos;a,b=split(root,pos);root=merge(merge(a,extra),b)
p=4;out=[]
for _ in range(m):
 kind=int(v[p]);p+=1
 if kind==2:
  permutation=v[p];p+=1;rank=[0]*k
  for i,c in enumerate(permutation):rank[c-97]=i
  out.append(str(1+sum(counts[a][b] for a in range(k) for b in range(k) if rank[a]>=rank[b])));continue
 l,r,c=int(v[p])-1,int(v[p+1]),v[p+2][0]-97;p+=3;boundary(l);boundary(r)
 oldfirst=find(root,l).c;oldlast=find(root,r-1).c
 left=find(root,l-1).c if l else None;right=find(root,r).c if r<n else None
 if left is not None:counts[left][oldfirst]-=1
 if right is not None:counts[oldlast][right]-=1
 a,b=split(root,l);middle,b=split(b,r);stack=[];t=middle;previous=None
 while stack or t is not None:
  while t is not None:stack.append(t);t=t.left
  t=stack.pop();counts[t.c][t.c]-=t.end-t.start-1
  if previous is not None:counts[previous][t.c]-=1
  previous=t.c;t=t.right
 counts[c][c]+=r-l-1
 if left is not None:counts[left][c]+=1
 if right is not None:counts[c][right]+=1
 root=merge(merge(a,Node(l,r,c)),b)
print('\n'.join(out))
