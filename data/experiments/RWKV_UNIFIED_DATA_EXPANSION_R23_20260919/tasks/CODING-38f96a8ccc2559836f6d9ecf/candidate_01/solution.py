import sys,math
from collections import defaultdict
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);budget=next(it);groups=defaultdict(list)
for _ in range(n):
 x=next(it);y=next(it);t=next(it);v=next(it);g=math.gcd(abs(x),y);groups[(x//g,y//g)].append((x*x+y*y,t,v))
dp=[0]*(budget+1)
for group in groups.values():
 choices=[];elapsed=0;value=0
 for dist,t,v in sorted(group):
  elapsed+=t;value+=v
  if elapsed<=budget:choices.append((elapsed,value))
 old=dp;dp=old.copy()
 for t,v in choices:
  for b in range(t,budget+1):dp[b]=max(dp[b],old[b-t]+v)
print(dp[budget])
