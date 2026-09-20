import sys,random
from array import array
sys.setrecursionlimit(100000);rng=random.Random(1701);parent=array('I');weight=array('I');height=array('I')
def fresh(value):
 i=len(parent);parent.append(i);weight.append(1);height.append(value);return i
def find(i):
 while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
 return i
def unite(a,b):
 a=find(a);b=find(b)
 if a==b:return a
 if weight[a]<weight[b]:a,b=b,a
 parent[b]=a;weight[a]+=weight[b];return a
class Node:
 __slots__=('key','priority','rep','left','right')
 def __init__(self,key,rep):self.key=key;self.rep=rep;self.priority=rng.getrandbits(64);self.left=self.right=None
def split(root,key):
 if root is None:return None,None
 if root.key<key:
  root.right,b=split(root.right,key);return root,b
 a,root.left=split(root.left,key);return a,root
def merge(a,b):
 if a is None:return b
 if b is None:return a
 if a.priority>b.priority:a.right=merge(a.right,b);return a
 b.left=merge(a,b.left);return b
def put(root,key,rep):
 a,b=split(root,key);same,b=split(b,key+1)
 if same is not None:rep=unite(rep,same.rep);same.rep=rep
 else:same=Node(key,rep)
 height[find(rep)]=key;return merge(merge(a,same),b)
def collapse(root,value):
 rep=root.rep;stack=[root]
 while stack:
  node=stack.pop();rep=unite(rep,node.rep)
  if node.left is not None:stack.append(node.left)
  if node.right is not None:stack.append(node.right)
 height[find(rep)]=value;return rep
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);handles=array('I');root=None
for _ in range(n):
 value=next(it);rep=fresh(value);handles.append(rep);root=put(root,value,rep)
q=next(it);out=[]
for _ in range(q):
 kind=next(it)
 if kind==1:
  k=next(it)-1;value=next(it);rep=fresh(value);handles[k]=rep;root=put(root,value,rep)
 elif kind==2:out.append(str(height[find(handles[next(it)-1])]))
 else:
  l=next(it);r=next(it);mid=(l+r)//2;a,b=split(root,l);low,b=split(b,mid+1);high,b=split(b,r+1)
  if low is not None:a=put(a,l-1,collapse(low,l-1))
  if high is not None:b=put(b,r+1,collapse(high,r+1))
  root=merge(a,b)
print('\n'.join(out))
