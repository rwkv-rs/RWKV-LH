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
while len(heap)>1:
 _,_,a,ga=heapq.heappop(heap);_,_,b,gb=heapq.heappop(heap);size=len(a)+len(b)-1;f=multiply(a,b,size);x=multiply(a,gb,size);y=multiply(ga,b,size);g=[(v+w)%P for v,w in zip(x,y)];heapq.heappush(heap,(size,serial,f,g));serial+=1
_,_,f,g=heap[0];answer=0;factorial=1
for i in range(1,k+1):factorial=factorial*i%P;answer=(answer+factorial*g[i])%P
print(answer)
