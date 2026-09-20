import sys
from array import array
it=iter(map(int,sys.stdin.buffer.read().split()));n,m=next(it),next(it);a=[next(it) for _ in range(n)];bits=[];totals=[];answer=0;power=1<<(n.bit_length()-1)
for b in range(17):
 tree=array('i',[0])*(n+1);run=0;total=0
 for i,x in enumerate(a,1):
  if x>>b&1:run+=1;answer+=run*(1<<b)
  else:tree[i]=1;total+=1;run=0
 for i in range(1,n+1):
  j=i+(i&-i)
  if j<=n:tree[j]+=tree[i]
 bits.append(tree);totals.append(total)
def prefix(tree,i):
 total=0
 while i:total+=tree[i];i-=i&-i
 return total
def kth(tree,k):
 p=0;step=power
 while step:
  q=p+step
  if q<=n and tree[q]<k:k-=tree[q];p=q
  step>>=1
 return p+1
out=[]
for _ in range(m):
 p,value=next(it),next(it);old=a[p-1];changed=old^value
 while changed:
  weight=changed&-changed;b=weight.bit_length()-1;tree=bits[b];before=prefix(tree,p-1);left=kth(tree,before) if before else 0;was_zero=not(old&weight);after_rank=before+1+was_zero;right=kth(tree,after_rank) if after_rank<=totals[b] else n+1;delta=(p-left)*(right-p)*weight;answer+=delta if was_zero else -delta;step=-1 if was_zero else 1;totals[b]+=step;j=p
  while j<=n:tree[j]+=step;j+=j&-j
  changed^=weight
 a[p-1]=value;out.append(str(answer))
print('\n'.join(out))
