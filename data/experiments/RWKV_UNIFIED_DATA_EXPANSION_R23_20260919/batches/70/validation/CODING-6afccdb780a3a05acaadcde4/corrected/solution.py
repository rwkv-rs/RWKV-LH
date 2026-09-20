import sys
from functools import lru_cache
n,c=map(int,sys.stdin.buffer.read().split());MOD=998244353
if c==1:print(int(n<=2))
elif c==0:print(1)
else:
 q=(1-c)%MOD;inverse=pow(q,MOD-2,MOD)
 @lru_cache(None)
 def value(x):
  total=0;left=2
  while left<=x:
   quotient=x//left;right=x//quotient;total+=(right-left+1)*value(quotient);left=right+1
  return (1+c*(total%MOD))*inverse%MOD
 print(pow(q,n,MOD)*value(n)%MOD)
