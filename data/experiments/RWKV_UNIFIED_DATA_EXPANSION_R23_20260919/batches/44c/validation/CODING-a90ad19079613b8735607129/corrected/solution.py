import sys
sys.setrecursionlimit(1000000)
seed=20260920
class Node:
 __slots__=('value','sum','size','left','right','priority','assign','add','step')
 def __init__(self,value):
  global seed
  seed^=(seed<<13)&0xffffffff;seed^=seed>>17;seed^=(seed<<5)&0xffffffff;seed&=0xffffffff
  self.value=self.sum=value;self.size=1;self.left=self.right=None;self.priority=seed;self.assign=None;self.add=self.step=0
def size(t):return t.size if t else 0
def total(t):return t.sum if t else 0
def pull(t):t.size=1+size(t.left)+size(t.right);t.sum=t.value+total(t.left)+total(t.right)
def assign(t,value):
 if t:t.value=value;t.sum=value*t.size;t.assign=value;t.add=t.step=0
def add(t,a,b):
 if t:t.value+=a+b*size(t.left);t.sum+=a*t.size+b*t.size*(t.size-1)//2;t.add+=a;t.step+=b
def push(t):
 if t.assign is not None:assign(t.left,t.assign);assign(t.right,t.assign);t.assign=None
 if t.add or t.step:add(t.left,t.add,t.step);add(t.right,t.add+t.step*(size(t.left)+1),t.step);t.add=t.step=0
def split(t,k):
 if not t:return None,None
 push(t)
 if size(t.left)>=k:a,t.left=split(t.left,k);pull(t);return a,t
 t.right,b=split(t.right,k-size(t.left)-1);pull(t);return t,b
def merge(a,b):
 if not a:return b
 if not b:return a
 if a.priority>b.priority:push(a);a.right=merge(a.right,b);pull(a);return a
 push(b);b.left=merge(a,b.left);pull(b);return b
it=iter(map(int,sys.stdin.buffer.read().split()));n,q=next(it),next(it);root=None
for _ in range(n):root=merge(root,Node(next(it)))
out=[]
for _ in range(q):
 op=next(it)
 if op==3:
  c,x=next(it),next(it);a,b=split(root,c-1);root=merge(merge(a,Node(x)),b)
 else:
  l,r=next(it),next(it);a,bc=split(root,l-1);b,c=split(bc,r-l+1)
  if op==1:assign(b,next(it))
  elif op==2:x=next(it);add(b,x,x)
  else:out.append(str(total(b)))
  root=merge(a,merge(b,c))
print('\n'.join(out))
