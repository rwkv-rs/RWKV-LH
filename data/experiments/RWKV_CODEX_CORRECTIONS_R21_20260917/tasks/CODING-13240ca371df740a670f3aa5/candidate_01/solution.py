import sys,math
v=list(map(int,sys.stdin.buffer.read().split()));a=v[1:];limit=math.isqrt(max(a));sieve=bytearray(b'\1')*(limit+1);primes=[]
for p in range(2,limit+1):
 if sieve[p]:
  primes.append(p)
  if p*p<=limit:sieve[p*p::p]=b'\0'*((limit-p*p)//p+1)
best={};cached={};answer=0
for x in a:
 divisors=cached.get(x)
 if divisors is None:
  divisors=[1];y=x
  for p in primes:
   if p*p>y:break
   if y%p==0:
    old=divisors[:];power=1
    while y%p==0:y//=p;power*=p;divisors.extend(d*power for d in old)
  if y>1:divisors.extend([d*y for d in divisors])
  cached[x]=divisors
 value=max(best.get(d,0) for d in divisors)+1;best[x]=value;answer=max(answer,value)
print(answer)
