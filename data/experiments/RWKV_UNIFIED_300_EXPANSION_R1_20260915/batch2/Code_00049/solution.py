import sys
from functools import lru_cache
a=list(map(int,sys.stdin.buffer.read().split()))[1:];xor=0
for v in a[2:]:xor^=v
s=a[0]+a[1]
if s<xor or (s-xor)%2:print(-1);raise SystemExit
common=(s-xor)//2
if common&xor:print(-1);raise SystemExit
bound=a[0];bits=max(s.bit_length(),1)
@lru_cache(None)
def choose(i,tight):
    if i<0:return 0
    limit=(bound>>i)&1 if tight else 1
    options=(1,) if common>>i&1 else ((1,0) if xor>>i&1 else (0,))
    for b in options:
        if b>limit:continue
        rest=choose(i-1,tight and b==limit)
        if rest is not None:return (b<<i)|rest
    return None
x=choose(bits-1,True)
print(-1 if x is None or x<1 else a[0]-x)
