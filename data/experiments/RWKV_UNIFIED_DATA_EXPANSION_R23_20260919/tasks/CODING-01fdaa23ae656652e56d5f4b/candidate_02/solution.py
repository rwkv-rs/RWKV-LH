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
def inverse(a,count):
 b=[pow(a[0],P-2,P)]
 while len(b)<count:
  size=min(count,len(b)*2);ab=multiply(a[:size],b,size);ab=[(-x)%P for x in ab];ab[0]=(ab[0]+2)%P;b=multiply(b,ab,size)
 return b
n=int(sys.stdin.buffer.read());fac=[1]*(n+1)
for i in range(1,n+1):fac[i]=fac[i-1]*i%P
ifact=[1]*(n+1);ifact[n]=pow(fac[n],P-2,P)
for i in range(n,0,-1):ifact[i-1]=ifact[i]*i%P
h=[];two=1;power=1
for i in range(n+1):
 h.append(((-1 if i&1 else 1)*ifact[i]*power)%P);power=power*two%P;two=two*((P+1)//2)%P
u=inverse(h,n+1);two=1;power=1
for i in range(n+1):u[i]=u[i]*power%P;power=power*two%P;two=two*2%P
derivative=[i*u[i]%P for i in range(1,n+1)];log_derivative=multiply(derivative,inverse(u,n),n)
print('\n'.join(str(log_derivative[i-1]*fac[i-1]%P) for i in range(1,n+1)))
