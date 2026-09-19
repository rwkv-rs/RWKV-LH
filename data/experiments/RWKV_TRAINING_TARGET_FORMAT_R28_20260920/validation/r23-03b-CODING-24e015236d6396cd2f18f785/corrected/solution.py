import sys
from functools import lru_cache
v=list(map(int,sys.stdin.buffer.read().split()));n,x=v[:2];a=v[2:]
@lru_cache(None)
def solve(i,amount):
 if i==n-1:return amount
 ratio=a[i+1]//a[i];q,r=divmod(amount,ratio)
 return min(r+solve(i+1,q),ratio-r+solve(i+1,q+1)) if r else solve(i+1,q)
print(solve(0,x))
