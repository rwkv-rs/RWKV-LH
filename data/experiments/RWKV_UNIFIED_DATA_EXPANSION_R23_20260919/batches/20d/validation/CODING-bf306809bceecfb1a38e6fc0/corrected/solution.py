import sys,math
from functools import lru_cache
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 n=next(v);a=[next(v) for i in range(n)];triangles=[[] for _ in range(n)]
 for i in range(n):
  for j in range(i+1,n):
   for k in range(j+1,n):
    x,y,z=sorted((a[i],a[j],a[k]))
    if x+y>z:
     area=math.sqrt((x+y+z)*(-x+y+z)*(x-y+z)*(x+y-z))/4;triangles[i].append(((1<<j)|(1<<k),area))
 @lru_cache(None)
 def dp(mask):
  if mask.bit_count()<3:return 0.
  bit=mask&-mask;i=bit.bit_length()-1;rest=mask^bit;best=dp(rest)
  for pair,area in triangles[i]:
   if rest&pair==pair:best=max(best,area+dp(rest^pair))
  return best
 out.append(f'{dp((1<<n)-1):.6f}')
print('\n'.join(out))
