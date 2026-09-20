import sys
from functools import lru_cache
mod=1000000007
@lru_cache(None)
def solve(n):
 if n==1:return (1,1,1)
 a=(n+1)//2;b=n//2;pa,qa,sa=solve(a);pb,qb,sb=solve(b)
 return ((pa+pb+b-1)%mod,(qa+qb+a-1)%mod,(sa+sb+b*qa+a*pb-1)%mod)
v=list(map(int,sys.stdin.buffer.read().split()));print('\n'.join(str(solve(n)[2]) for n in v[1:1+v[0]]))
