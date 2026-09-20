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
import heapq
it=iter(map(int,sys.stdin.buffer.read().split()));n=next(it);groups=[(next(it),next(it)) for _ in range(n)];k=sum(b for a,b in groups);invs=[0,1]+[0]*(k-1)
for i in range(2,k+1):invs[i]=P-(P//i)*invs[P%i]%P
heap=[];offset=0;serial=0
for a,b in groups:
 f=[1];mean=(2*offset+a+1)*((P+1)//2)%P;g=[0]
 for j in range(1,b+1):f.append(f[-1]*(a+j-1)%P*invs[j]%P*invs[j]%P);g.append(f[-1]*j*mean%P)
 heapq.heappush(heap,(b+1,serial,f,g));serial+=1;offset+=a
def merge(a,ga,b,gb):
 size=len(a)+len(b)-1
 if min(len(a),len(b))<24:
  f=[0]*size;g=[0]*size
  for i,(x,gx) in enumerate(zip(a,ga)):
   for j,(y,gy) in enumerate(zip(b,gb)):f[i+j]+=x*y;g[i+j]+=gx*y+x*gy
  return [x%P for x in f],[x%P for x in g]
 width=len(str(2*min(len(a),len(b))*(P-1)**2));zero='0'*width
 def pack(f,g):return Decimal(''.join(zero+str(y).zfill(width)+str(x).zfill(width) for x,y in zip(reversed(f),reversed(g))))
 aa=pack(a,ga);bb=pack(b,gb)
 with localcontext() as context:
  context.prec=3*width*(len(a)+len(b))+1;context.Emax=999999999;product=format(aa*bb,'f')
 product=product.zfill(3*width*size);end=len(product);f=[];g=[]
 for i in range(size):
  j=end-3*width*i;f.append(int(product[j-width:j])%P);g.append(int(product[j-2*width:j-width])%P)
 return f,g
while len(heap)>1:
 _,_,a,ga=heapq.heappop(heap);_,_,b,gb=heapq.heappop(heap);f,g=merge(a,ga,b,gb);heapq.heappush(heap,(len(f),serial,f,g));serial+=1
_,_,f,g=heap[0];answer=0;factorial=1
for i in range(1,k+1):factorial=factorial*i%P;answer=(answer+factorial*g[i])%P
print(answer)
