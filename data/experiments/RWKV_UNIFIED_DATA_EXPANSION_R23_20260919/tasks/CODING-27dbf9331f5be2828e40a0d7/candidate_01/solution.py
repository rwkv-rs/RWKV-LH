import sys
import numpy as np
P=998244353;cache={}
def roots(n,inverse):
 key=(n,inverse)
 if key not in cache:
  w=pow(3,(P-1)//n,P)
  if inverse:w=pow(w,P-2,P)
  values=[1]*(n//2)
  for i in range(1,len(values)):values[i]=values[i-1]*w%P
  cache[key]=np.array(values,dtype=np.int64)
 return cache[key]
def transform(a,inverse=False):
 n=len(a)
 if not inverse:
  step=n
  while step>1:
   half=step//2;view=a.reshape(-1,step);u=view[:,:half].copy();v=view[:,half:].copy();view[:,:half]=(u+v)%P;view[:,half:]=((u-v)*roots(step,False))%P;step//=2
 else:
  step=2
  while step<=n:
   half=step//2;view=a.reshape(-1,step);u=view[:,:half].copy();v=view[:,half:]*roots(step,True)%P;view[:,:half]=(u+v)%P;view[:,half:]=(u-v)%P;step*=2
  a[:]=a*pow(n,P-2,P)%P
 return a
def multiply(a,b,limit):
 need=min(limit,len(a)+len(b)-1)
 if min(len(a),len(b))<24:
  out=[0]*need
  for i,x in enumerate(a):
   if i>=need:break
   for j,y in enumerate(b[:need-i]):out[i+j]=(out[i+j]+x*y)%P
  return out
 n=1<<(len(a)+len(b)-2).bit_length();x=np.zeros(n,dtype=np.int64);y=np.zeros(n,dtype=np.int64);x[:len(a)]=a;y[:len(b)]=b;transform(x);transform(y);x[:]=x*y%P;transform(x,True);return x[:need].tolist()
from collections import Counter
import heapq
v=iter(map(int,sys.stdin.buffer.read().split()));n=next(v);m=next(v);distances=[next(v) for _ in range(n)];levels=Counter(distances);remaining=m-(n-1)
if remaining<0 or distances[0]!=0 or levels[0]!=1:print(0)
else:
 limit=remaining+1;invs=[0,1]+[0]*max(0,remaining-1)
 for i in range(2,remaining+1):invs[i]=(P-P//i)*invs[P%i]%P
 def binomials(top,count):
  result=[1]
  for i in range(1,count):result.append(result[-1]*((top-i+1)%P)%P*invs[i]%P)
  return result
 # Need binomial(p,j+1), so prepare inverses through the largest p.
 maxp=max(levels.values());needed=max(remaining,maxp)
 if needed>=len(invs):
  old=len(invs);invs.extend([0]*(needed+1-old))
  for i in range(old,needed+1):invs[i]=(P-P//i)*invs[P%i]%P
 grouped=Counter();inside=0
 for depth,count in levels.items():
  inside+=count*(count-1)//2
  if depth:
   previous=levels[depth-1]
   if not previous:raise ValueError('impossible distance sequence')
   if previous>1:grouped[previous]+=count
 polys=[];serial=0
 for previous,count in grouped.items():
  base=binomials(previous,min(previous+1,limit+1))[1:];value=[1]
  while count:
   if count&1:value=multiply(value,base,limit)
   count//=2
   if count:base=multiply(base,base,limit)
  heapq.heappush(polys,(len(value),serial,value));serial+=1
 while len(polys)>1:
  _,_,a=heapq.heappop(polys);_,_,b=heapq.heappop(polys);value=multiply(a,b,limit);heapq.heappush(polys,(len(value),serial,value));serial+=1
 product=polys[0][2] if polys else [1];internal=binomials(inside,limit);print(sum(x*internal[remaining-i] for i,x in enumerate(product))%P)
