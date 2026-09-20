import sys,bisect
v=list(map(int,sys.stdin.buffer.read().split()));money,fee,n=v[:3];foods=list(zip(v[3::2],v[4::2]));caps=sorted({life+1 for price,life in foods});prices=[min(price for price,life in foods if life+1>=cap) for cap in caps];prefix=[0]
for i,cap in enumerate(caps):prefix.append(prefix[-1]+prices[i]*(cap-(caps[i-1] if i else 0)))
def food_cost(days):
 if days==0:return 0
 i=bisect.bisect_left(caps,days);return prefix[i]+prices[i]*(days-(caps[i-1] if i else 0))
def affordable(days):
 if days==0:return True
 def total(deliveries):
  span,extra=divmod(days,deliveries);value=deliveries*fee+(deliveries-extra)*food_cost(span)
  if extra:value+=extra*food_cost(span+1)
  return value
 low=(days+caps[-1]-1)//caps[-1];high=days
 while low<high:
  mid=(low+high)//2
  if total(mid)<=total(mid+1):high=mid
  else:low=mid+1
 return total(low)<=money
lo=0;hi=money//min(prices)+1
while lo+1<hi:
 mid=(lo+hi)//2
 if affordable(mid):lo=mid
 else:hi=mid
print(lo)
