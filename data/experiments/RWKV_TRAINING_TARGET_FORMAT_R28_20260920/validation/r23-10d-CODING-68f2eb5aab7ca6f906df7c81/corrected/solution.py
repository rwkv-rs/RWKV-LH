import sys
it=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(it)):
 n=next(it);groups=next(it);a=sorted(next(it) for _ in range(n));prefix=[0]
 for x in a:prefix.append(prefix[-1]+x)
 def cost(l,r):
  mid=(l+r-1)//2;return a[mid]*(mid-l)-(prefix[mid]-prefix[l])+(prefix[r]-prefix[mid+1])-a[mid]*(r-mid-1)
 old=[0]+[10**30]*n
 for count in range(1,min(groups,n)+1):
  new=[10**30]*(n+1)
  def compute(left,right,optlo,opthi):
   if left>right:return
   mid=(left+right)//2;best=10**30;arg=optlo
   for split in range(optlo,min(mid-1,opthi)+1):
    value=old[split]+cost(split,mid)
    if value<best:best=value;arg=split
   new[mid]=best;compute(left,mid-1,optlo,arg);compute(mid+1,right,arg,opthi)
  compute(count,n,count-1,n-1);old=new
 out.append(str(old[n]))
print('\n'.join(out))
