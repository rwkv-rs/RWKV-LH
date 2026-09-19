import sys
from itertools import accumulate
v=list(map(int,sys.stdin.buffer.read().split()));n,budget=v[:2];items=[tuple(v[2+2*i:4+2*i]) for i in range(n)];base=min(x for x,y in items);groups=[[] for _ in range(4)]
for price,value in items:groups[price-base].append(value)
pref=[list(accumulate(sorted(g,reverse=True),initial=0)) for g in groups];answer=0
for i,x in enumerate(pref[0]):
 for j,y in enumerate(pref[1]):
  for k,z in enumerate(pref[2]):
   cost=i*base+j*(base+1)+k*(base+2)
   if cost>budget:continue
   take=min(len(pref[3])-1,(budget-cost)//(base+3));answer=max(answer,x+y+z+pref[3][take])
print(answer)
