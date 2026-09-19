import sys
from collections import Counter
v=list(map(int,sys.stdin.buffer.read().split()));counts=Counter(v[1:1+v[0]]);mod=1000000007;answer=0
for side,c in counts.items():
 if c<2:continue
 pairs=0
 for left in range(1,(side+1)//2):pairs+=counts.get(left,0)*counts.get(side-left,0)
 if side%2==0:
  half=counts.get(side//2,0);pairs+=half*(half-1)//2
 answer=(answer+c*(c-1)//2*pairs)%mod
print(answer)
