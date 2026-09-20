import sys
from decimal import Decimal,localcontext
P=998244353
def multiply(a,b,limit):
 need=min(limit,len(a)+len(b)-1)
 if min(len(a),len(b))<24:
  out=[0]*need
  for i,x in enumerate(a):
   if i>=need:break
   for j,y in enumerate(b[:need-i]):out[i+j]=(out[i+j]+x*y)%P
  return out
 width=len(str(min(len(a),len(b))*(P-1)**2));fmt='0'+str(width)+'d'
 aa=Decimal(''.join(format(x,fmt) for x in reversed(a)));bb=aa if a is b else Decimal(''.join(format(x,fmt) for x in reversed(b)))
 with localcontext() as context:
  context.prec=width*(len(a)+len(b))+1;context.Emax=999999999;product=format(aa*bb,'f')
 product=product.zfill(width*need);end=len(product);return [int(product[end-width*(i+1):end-width*i])%P for i in range(need)]
n,k,f=map(int,sys.stdin.buffer.read().split())
if f>2*k:print(0)
else:
 limit=min(k,f)+1;distribution=[1]*limit;total=(k+1)%P
 for depth in range(2,n+1):
  conv=multiply(distribution,distribution,limit);prefix=0;new=[];square=total*total%P
  for i,x in enumerate(conv):new.append((square-prefix+(k-i)*x)%P);prefix=(prefix+x)%P
  distribution=new;total=square*(k+1)%P
 answer=sum(distribution[i]*distribution[f-i] for i in range(max(0,f-k),min(k,f)+1))%P;print(answer)
