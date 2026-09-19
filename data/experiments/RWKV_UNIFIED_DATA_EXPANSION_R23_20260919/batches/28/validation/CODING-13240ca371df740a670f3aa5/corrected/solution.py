import sys,math
v=list(map(int,sys.stdin.read().split()));a=v[1:];limit=math.isqrt(max(a));sieve=bytearray(b'\x01')*(limit+1);primes=[]
for p in range(2,limit+1):
 if sieve[p]:
  primes.append(p)
  if p*p<=limit:sieve[p*p:limit+1:p]=b'\x00'*(((limit-p*p)//p)+1)
cache={};best={};answer=0
for x in a:
 if x not in cache:
  value=x;divisors=[1]
  for p in primes:
   if p*p>value:break
   if value%p:continue
   base=divisors.copy();power=1
   while value%p==0:
    value//=p;power*=p;divisors.extend(d*power for d in base)
  if value>1:divisors.extend(d*value for d in divisors.copy())
  cache[x]=divisors
 length=1+max((best.get(d,0) for d in cache[x]),default=0);best[x]=length;answer=max(answer,length)
print(answer)
