import sys
from functools import lru_cache
v=iter(map(int,sys.stdin.read().split()));out=[];case=0
for n in v:
 if n==0:break
 x=next(v);y=next(v);a=[next(v) for _ in range(n)];size=1<<n;sums=[0]*size
 for mask in range(1,size):bit=mask&-mask;sums[mask]=sums[mask^bit]+a[bit.bit_length()-1]
 @lru_cache(None)
 def possible(mask,w):
  area=sums[mask]
  if area%w:return False
  h=area//w
  if mask&(mask-1)==0:return True
  low=mask&-mask;sub=(mask-1)&mask
  while sub:
   if sub&low:
    other=mask^sub;sa=sums[sub];sb=area-sa
    if sa%w==0 and possible(sub,min(w,sa//w)) and possible(other,min(w,sb//w)):return True
    if sa%h==0 and possible(sub,min(h,sa//h)) and possible(other,min(h,sb//h)):return True
   sub=(sub-1)&mask
  return False
 ok=sums[-1]==x*y and possible(size-1,min(x,y));case+=1;out.append(f'Case {case}: '+('Yes' if ok else 'No'))
print('\n'.join(out))
