import sys
v=list(map(int,sys.stdin.buffer.read().split()));n,circumference=v[:2];a=sorted(v[2:2+n]);b=sorted(v[2+n:2+2*n]);extended=[x-circumference for x in b]+b+[x+circumference for x in b];size=len(extended)
def feasible(bound):
 left=right=0;low=-size;high=size
 for i,x in enumerate(a):
  while left<size and extended[left]<x-bound:left+=1
  while right<size and extended[right]<=x+bound:right+=1
  low=max(low,left-i);high=min(high,right-1-i)
  if low>high:return False
 return True
low=-1;high=circumference//2
while low+1<high:
 mid=(low+high)//2
 if feasible(mid):high=mid
 else:low=mid
print(high)
