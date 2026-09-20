import sys,math
from functools import lru_cache
v=list(map(int,sys.stdin.buffer.read().split()));values=v[1:1+v[0]];limit=math.isqrt(max(values,default=1));mark=bytearray(b'\x01')*(limit+1);primes=[]
for p in range(2,limit+1):
 if mark[p]:
  primes.append(p)
  for j in range(p*p,limit+1,p):mark[j]=0
@lru_cache(None)
def phi(n):
 answer=n
 for p in primes:
  if p*p>n:break
  if n%p==0:
   answer-=answer//p
   while n%p==0:n//=p
 if n>1:answer-=answer//n
 return answer
@lru_cache(None)
def solve(p):
 if p==1:return 0
 q=phi(p);return pow(2,solve(q)+q,p)
print('\n'.join(str(solve(p)) for p in values))
