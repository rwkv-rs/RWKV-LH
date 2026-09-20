import sys,functools
from fractions import Fraction
v=sys.stdin.buffer.read().split();n=int(v[0]);grid=v[1:]
@functools.lru_cache(None)
def value(column):
 left=[];right=[]
 for i,c in enumerate(column):
  if c==46:continue
  removed=column[:i]+bytes([46])+column[i+1:]
  (left if c==66 else right).append(value(removed))
  if i and column[i-1]==46:
   moved=column[:i-1]+bytes([c,46])+column[i+1:];(left if c==87 else right).append(value(moved))
 low=max(left) if left else None;high=min(right) if right else None
 if low is None and high is None:return Fraction(0)
 if low is None:return Fraction(min(0,(high.numerator-1)//high.denominator))
 if high is None:return Fraction(max(0,low.numerator//low.denominator+1))
 assert low<high
 scale=1
 while True:
  first=(low.numerator*scale)//low.denominator+1;last=(high.numerator*scale-1)//high.denominator
  if first<=last:return Fraction(min(max(0,first),last),scale)
  scale*=2
total=sum((value(bytes(grid[i][j] for i in range(n))) for j in range(n)),Fraction(0));print('Takahashi' if total>0 else 'Snuke')
