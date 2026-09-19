import sys
v=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for _ in range(next(v)):
 n=next(v);budget=next(v);a=[(next(v),next(v)) for i in range(n)];a.sort(reverse=True);base=sum(l for l,r in a)
 def ok(x):
  need=(n+1)//2;cost=base
  for l,r in a:
   if l>=x:need-=1
  if need<=0:return True
  for l,r in a:
   if l<x<=r:
    cost+=x-l;need-=1
    if need==0:return cost<=budget
  return False
 lo=0;hi=max(r for l,r in a)+1
 while hi-lo>1:
  mid=(lo+hi)//2
  if ok(mid):lo=mid
  else:hi=mid
 out.append(str(lo))
print('\n'.join(out))
