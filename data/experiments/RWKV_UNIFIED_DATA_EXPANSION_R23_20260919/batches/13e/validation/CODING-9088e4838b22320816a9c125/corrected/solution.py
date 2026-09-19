import sys
from functools import lru_cache
@lru_cache(None)
def total(x):
 if x<2:return 0
 maximum=x.bit_length()-1;counts=[0]*(maximum+1)
 for exponent in range(maximum,1,-1):
  low=1;high=1<<((x.bit_length()+exponent-1)//exponent)
  while low<high:
   mid=(low+high+1)//2
   if mid**exponent<=x:low=mid
   else:high=mid-1
  counts[exponent]=low-1-sum(counts[exponent*multiple] for multiple in range(2,maximum//exponent+1))
 counts[1]=x-1-sum(counts[2:]);return sum(i*count for i,count in enumerate(counts))
v=list(map(int,sys.stdin.buffer.read().split()));out=[]
for i in range(0,len(v),2):
 a,b=v[i:i+2]
 if a==b==0:break
 out.append(str(total(b)-total(a-1)))
print('\n'.join(out))
