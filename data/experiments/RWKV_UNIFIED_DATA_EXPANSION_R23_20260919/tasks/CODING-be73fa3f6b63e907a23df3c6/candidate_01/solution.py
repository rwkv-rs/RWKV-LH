import sys
from functools import cmp_to_key
v=sys.stdin.read().split();n=int(v[0]);k=int(v[1]);a=v[2:2+n]
def cmp(x,y):return (x+y>y+x)-(x+y<y+x)
a.sort(key=cmp_to_key(cmp));dp=[None]*(k+1);dp[0]=''
for s in reversed(a):
 for j in range(k,0,-1):
  if dp[j-1] is not None:
   candidate=s+dp[j-1]
   if dp[j] is None or candidate<dp[j]:dp[j]=candidate
print(dp[k])
