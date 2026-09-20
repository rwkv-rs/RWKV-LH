import sys
from decimal import Decimal,localcontext
def floor_sum(n,a,b):
 m=Decimal(1);answer=0
 while True:
  q=int(a//m);answer+=q*n*(n-1)//2;a-=q*m
  q=int(b//m);answer+=q*n;b-=q*m
  y=a*n+b
  if y<m:return answer
  n=int(y//m);b=y-n*m;m,a=a,m
def solve(value,precision):
 with localcontext() as context:
  context.prec=precision;a=Decimal(2).log10();digits=len(str(value));lower=Decimal(value).log10()-(digits-1);upper=Decimal(value+1).log10()-(digits-1)
  start=int(Decimal(2*digits)/a)+1
  def count(n):return floor_sum(n,a,1-lower)-floor_sum(n,a,1-upper)
  baseline=count(start);lo=start;hi=start
  while count(hi+1)==baseline:hi*=2
  while lo<hi:
   mid=(lo+hi)//2
   if count(mid+1)>baseline:hi=mid
   else:lo=mid+1
  return lo
out=[]
for word in sys.stdin.buffer.read().split():
 value=int(word)
 if value==0:out.append('no power of 2');continue
 first=solve(value,80);second=solve(value,120)
 if first!=second:raise ArithmeticError('precision disagreement')
 out.append(str(first))
print('\n'.join(out))
