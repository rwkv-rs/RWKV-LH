import sys,bisect
from functools import lru_cache
n=int(sys.stdin.read());fib=[1,2]
while fib[-1]<=n:fib.append(fib[-1]+fib[-2])
sums=[];total=0
for x in fib:total+=x;sums.append(total)
@lru_cache(None)
def count(i,x):
 if x==0:return 1
 if i<0 or x<0 or x>sums[i]:return 0
 if x>sums[i]//2:return count(i,sums[i]-x)
 i=min(i,bisect.bisect_right(fib,x)-1)
 return count(i-1,x)+count(i-1,x-fib[i])
print(count(len(fib)-1,n))
