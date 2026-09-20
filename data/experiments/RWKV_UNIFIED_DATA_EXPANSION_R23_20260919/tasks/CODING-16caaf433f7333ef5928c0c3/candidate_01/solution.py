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
def logarithm(a,count):
 derivative=[i*a[i]%P for i in range(1,min(len(a),count))]
 if not derivative:return [0]*count
 v=multiply(derivative,inverse(a,count),count-1)
 return [0]+[v[i-1]*invs[i]%P for i in range(1,count)]
def exponential(a,count):
 b=[1]
 while len(b)<count:
  size=min(count,len(b)*2);lb=logarithm(b,size);delta=[((a[i] if i<len(a) else 0)-lb[i])%P for i in range(size)];delta[0]=(delta[0]+1)%P;b=multiply(b,delta,size)
 return b
data=list(map(int,sys.stdin.buffer.read().split()));n=data[0];a=data[1:n+2];b=data[n+2:];invs=[0,1]+[0]*(n-1)
for i in range(2,n+1):invs[i]=P-(P//i)*invs[P%i]%P
integral=[0]+[b[i-1]*invs[i]%P for i in range(1,n+1)];e=exponential(integral,n);product=multiply(a[:n],e,n);g=[1]+[(-product[i-1]*invs[i])%P for i in range(1,n+1)];lg=logarithm(g,n+1);out=[1]+[(integral[i]-lg[i])%P for i in range(1,n+1)];print(*out)
