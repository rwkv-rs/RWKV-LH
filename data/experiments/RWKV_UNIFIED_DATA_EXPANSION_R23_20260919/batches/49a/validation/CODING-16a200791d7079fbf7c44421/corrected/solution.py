import sys,bisect
v=list(map(int,sys.stdin.buffer.read().split()));n=v[0];primes=v[1:1+n];k=v[n+1];LIMIT=10**18
if k==1:print(1);raise SystemExit
def products(ps):
 values=[1]
 for p in ps:
  old=values[:]
  for x in old:
   while x<=LIMIT//p:x*=p;values.append(x)
 values.sort();return values
a=products(primes[::2]);b=products(primes[1::2])
if len(a)>len(b):a,b=b,a
def enough(value):
 count=0;j=len(b)-1
 for x in a:
  bound=value//x
  while j>=0 and b[j]>bound:j-=1
  if j<0:break
  count+=j+1
  if count>=k:return True
 return False
lo,hi=1,LIMIT
while lo<hi:
 mid=(lo+hi)//2
 if enough(mid):hi=mid
 else:lo=mid+1
print(lo)
