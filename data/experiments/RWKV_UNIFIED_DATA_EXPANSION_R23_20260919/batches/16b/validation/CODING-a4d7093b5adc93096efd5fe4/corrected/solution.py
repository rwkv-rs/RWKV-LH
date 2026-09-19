import sys
from functools import lru_cache
def count(n,k):
 if n<0:return 0
 bits=bin(n)[2:];L=len(bits)
 @lru_cache(None)
 def dp(i,d,tight):
  if i==L:return int(abs(d)==k)
  limit=int(bits[i]) if tight else 1;ans=0
  for b in range(limit+1):ans+=dp(i+1,d+b*(1 if (L-1-i)%2==0 else -1),tight and b==limit)
  return ans
 return dp(0,0,True)
v=iter(map(int,sys.stdin.read().split()));out=[]
for _ in range(next(v)):
 m=next(v);n=next(v);k=next(v);out.append(str(count(n,k)-count(m-1,k)))
print('\n'.join(out))
