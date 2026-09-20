import sys
from array import array
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];values=v[1:n+1];parents=v[n+1:];head=array('i',[-1])*n;following=array('i',[-1])*n
for i,p in enumerate(parents,1):following[i]=head[p-1];head[p-1]=i
order=[0]
for u in order:
 c=head[u]
 while c>=0:order.append(c);c=following[c]
L=array('i',[0]);R=array('i',[0]);parity=bytearray([0]);xor=array('i',[0]);roots=array('i',[0])*n;BITS=(max(values)+n).bit_length()
def node():L.append(0);R.append(0);parity.append(0);xor.append(0);return len(L)-1
def pull(p):parity[p]=parity[L[p]]^parity[R[p]];xor[p]=(xor[L[p]]<<1)^(xor[R[p]]<<1)^parity[R[p]]
def insert(p,value,depth):
 if not p:p=node()
 if not depth:parity[p]^=1;return p
 if value&1:R[p]=insert(R[p],value>>1,depth-1)
 else:L[p]=insert(L[p],value>>1,depth-1)
 pull(p);return p
def increment(p,depth):
 if not p or not depth:return
 L[p],R[p]=R[p],L[p];increment(L[p],depth-1);pull(p)
def merge(a,b,depth):
 if not a or not b:return a or b
 if not depth:parity[a]^=parity[b];return a
 L[a]=merge(L[a],L[b],depth-1);R[a]=merge(R[a],R[b],depth-1);pull(a);return a
answer=0
for u in reversed(order):
 root=0;c=head[u]
 while c>=0:
  other=roots[c];increment(other,BITS);root=merge(root,other,BITS);c=following[c]
 root=insert(root,values[u],BITS);roots[u]=root;answer+=xor[root]
print(answer)
