import sys
from fractions import Fraction
from functools import lru_cache
x,y,n=map(int,sys.stdin.read().split())
@lru_cache(None)
def solve(ratio,count):
 if ratio<1:return solve(1/ratio,count)
 if count==1:return ratio
 best=ratio*count
 for part in range(1,count//2+1):
  other=count-part
  best=min(best,max(solve(ratio*part/count,part),solve(ratio*other/count,other)),max(solve(ratio*count/part,part),solve(ratio*count/other,other)))
 return best
print(format(float(solve(Fraction(x,y),n)),'.6f'))
