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
def large(base,prefix,precision):
 with localcontext() as context:
  context.prec=precision;a=Decimal(base).log10();digits=len(str(prefix));lower=Decimal(prefix).log10()-(digits-1);upper=Decimal(prefix+1).log10()-(digits-1);start=65
  def count(n):return floor_sum(n-start,a,start*a+1-lower)-floor_sum(n-start,a,start*a+1-upper)
  lo=start;hi=start
  while count(hi+1)==0:hi*=2
  while lo<hi:
   mid=(lo+hi)//2
   if count(mid+1)>0:hi=mid
   else:lo=mid+1
  return lo
v=iter(map(int,sys.stdin.buffer.read().split()));out=[]
for case in range(1,next(v)+1):
 base=next(v);prefix=next(v);s=str(prefix);value=1;answer=None
 for e in range(1,65):
  value*=base
  if str(value).startswith(s):answer=e;break
 if answer is None:
  answer=large(base,prefix,80)
  if answer!=large(base,prefix,120):raise ArithmeticError('precision disagreement')
 out.append(f'Case {case}: {answer}')
print('\n'.join(out))
