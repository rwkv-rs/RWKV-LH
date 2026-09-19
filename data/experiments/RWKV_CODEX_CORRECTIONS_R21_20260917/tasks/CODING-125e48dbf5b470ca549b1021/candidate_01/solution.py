import sys,re,math
from functools import lru_cache
lines=sys.stdin.read().splitlines();loops=[]
for line in lines[1:]:
 match=re.search(r'for ([a-z]) in range\(([^,]+),\s*([^\)]+)\)',line)
 if match:loops.append(tuple(x.strip() for x in match.groups()))
n=len(loops);names={x[0]:i for i,x in enumerate(loops)};reach=[1<<i for i in range(n)]
for i,(_,lo,hi) in enumerate(loops):
 if lo in names:reach[names[lo]]|=1<<i
 if hi in names:reach[i]|=1<<names[hi]
for k in range(n):
 for i in range(n):
  if reach[i]>>k&1:reach[i]|=reach[k]
components=[];owner=[-1]*n
for i in range(n):
 if owner[i]<0:
  group=[j for j in range(n) if reach[i]>>j&1 and reach[j]>>i&1]
  for j in group:owner[j]=len(components)
  components.append(group)
k=len(components);pred=[0]*k
for i in range(n):
 for j in range(n):
  if owner[i]!=owner[j] and reach[i]>>j&1:pred[owner[j]]|=1<<owner[i]
full=(1<<k)-1
@lru_cache(None)
def ways(done):
 if done==full:return 1
 remaining=full^done;available=0;bits=remaining
 while bits:
  b=bits&-bits;bits-=b;i=b.bit_length()-1
  if pred[i]&remaining==0:available|=b
 if available==remaining:return math.factorial(remaining.bit_count())
 total=0
 while available:
  b=available&-available;available-=b;total+=ways(done|b)
 return total
p=ways(0);q=math.factorial(k);g=math.gcd(p,q);print(k,f'{p//g}/{q//g}')
